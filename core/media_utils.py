import subprocess
import os
import imageio_ffmpeg

def get_audio_duration(audio_path):
    """
    Returns the duration of the audio file in seconds using ffprobe.
    """
    command = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        audio_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Could not get duration with ffprobe: {result.stderr}")
    return float(result.stdout.strip())

def extract_video_audio(video_path, output_audio_path):
    """
    Extracts the audio track from a video and saves it as an mp3 file.
    """
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i", video_path,
        "-vn",
        "-c:a", "libmp3lame",
        "-q:a", "2",
        output_audio_path
    ]
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"Could not extract audio with ffmpeg: {process.stderr}")
    return output_audio_path

def process_video(video_in, audio_in, subtitle_ass, cuts, output_path, audio_delay_ms=0, total_audio_duration=10.0, bg_audio_path=None, font_dir=None):
    """
    Runs ffmpeg to:
    1. Cut the video into multiple segments based on `cuts`.
    2. Stitch the segments together using the `concat` filter.
    3. Enhance video (1080x1920 vertical, sharpen, denoise, color).
    4. Apply the `subtitle_ass` filter on the stitched video.
    5. Enhance audio (denoise, clarify) and mix with `audio_in` with delay/mastering/fade.
    6. Optionally mix in a looping `bg_audio_path` with a lower volume.
    """
    fade_duration = 2.0
    fade_start = max(0, total_audio_duration - fade_duration)
    
    sub_path_escaped = os.path.abspath(subtitle_ass).replace('\\', '/').replace(':', '\\\\:')
    
    audio_filter = ""
    if audio_delay_ms > 0:
        audio_filter = f"adelay=delays={audio_delay_ms}:all=1,"
    elif audio_delay_ms < 0:
        trim_sec = abs(audio_delay_ms) / 1000.0
        audio_filter = f"atrim=start={trim_sec},asetpts=PTS-STARTPTS,"
        
    audio_mastering = "highpass=f=80,treble=g=5,loudnorm=I=-14:TP=-1.5:LRA=11,acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=2"
    
    filter_complex = ""
    v_out_names = []
    
    if cuts and len(cuts) > 0:
        for i, cut in enumerate(cuts):
            v_start = cut.get("vid_start", 0.0)
            dur = cut.get("duration", 2.0)
            filter_complex += f"[0:v]trim=start={v_start}:duration={dur},setpts=PTS-STARTPTS[v{i}];"
            v_out_names.append(f"[v{i}]")
            
        concat_str = "".join(v_out_names)
        if len(cuts) > 1:
            filter_complex += f"{concat_str}concat=n={len(cuts)}:v=1:a=0[v_stitched];"
        else:
            filter_complex += f"{concat_str}copy[v_stitched];"
    else:
        # Fallback if no cuts provided
        filter_complex += f"[0:v]trim=start=0:duration={total_audio_duration},setpts=PTS-STARTPTS[v_stitched];"
    # Video Enhancement: Denoise, Sharpen, Color, 1080x1920 Vertical
    v_enhancement = "hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.0:5:5:0.0,eq=saturation=1.1:contrast=1.05,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black"
    filter_complex += f"[v_stitched]{v_enhancement}[v_enhanced];"
        
    # Apply subtitles to stitched video
    font_opt = f":fontsdir='{font_dir}'" if font_dir else ""
    filter_complex += f"[v_enhanced]ass='{sub_path_escaped}'{font_opt}[v_sub];"
    filter_complex += f"[v_sub]fade=t=out:st={fade_start}:d={fade_duration}[v_out];"
    
    # Audio processing
    if bg_audio_path:
        # We have BGM!
        # [1:a] -> main audio
        # [2:a] -> bgm audio
        filter_complex += f"[1:a]{audio_filter}{audio_mastering}[a_main];"
        filter_complex += f"[2:a]volume=0.15[a_bg];"
        # amix inputs
        filter_complex += f"[a_main][a_bg]amix=inputs=2:duration=first:dropout_transition=2,afade=t=out:st={fade_start}:d={fade_duration}[a_out]"
    else:
        filter_complex += f"[1:a]{audio_filter}{audio_mastering},afade=t=out:st={fade_start}:d={fade_duration}[a_out]"
    
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-stream_loop", "-1",
        "-y",
        "-i", video_in,
        "-i", audio_in
    ]
    
    if bg_audio_path:
        command.extend(["-stream_loop", "-1", "-i", bg_audio_path])
        
    command.extend([
        "-filter_complex", filter_complex,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        output_path
    ])
    
    # Run process
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with error: {stderr.decode()}")
    
    return output_path

def process_video_subtitles_only(video_in, subtitle_ass, output_path, bg_audio_path=None, font_dir=None):
    """
    Simpler ffmpeg pipeline that only burns subtitles to a video and optionally mixes in BGM.
    Applies heavy AV enhancements.
    Does not trim or concat.
    """
    sub_path_escaped = os.path.abspath(subtitle_ass).replace('\\', '/').replace(':', '\\\\:')
    font_opt = f":fontsdir='{font_dir}'" if font_dir else ""
    
    v_enhancement = "hqdn3d=1.5:1.5:6:6,unsharp=5:5:1.0:5:5:0.0,eq=saturation=1.1:contrast=1.05,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black"
    
    filter_complex = f"[0:v]{v_enhancement}[v_enhanced]; [v_enhanced]ass='{sub_path_escaped}'{font_opt}[v_out];"
    
    audio_mastering = "highpass=f=80,treble=g=5,loudnorm=I=-14:TP=-1.5:LRA=11,acompressor=threshold=-20dB:ratio=4:attack=5:release=50:makeup=2"
    
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i", video_in
    ]
    
    if bg_audio_path:
        # If we have BGM, we need to mix original audio [0:a] with BGM [1:a]
        # ducking BGM volume down to 15%
        command.extend(["-stream_loop", "-1", "-i", bg_audio_path])
        filter_complex += f"[0:a]{audio_mastering}[a_main]; [1:a]volume=0.15[a_bg]; "
        filter_complex += f"[a_main][a_bg]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
        
        command.extend([
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "[a_out]"
        ])
    else:
        # No BGM, just map and master the original audio
        filter_complex += f"[0:a]{audio_mastering}[a_out]"
        command.extend([
            "-filter_complex", filter_complex,
            "-map", "[v_out]",
            "-map", "[a_out]"
        ])
        
    command.extend([
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        output_path
    ])
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with error: {stderr.decode()}")
    
    return output_path
