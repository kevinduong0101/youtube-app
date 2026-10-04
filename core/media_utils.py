import subprocess
import os
import shutil
import tempfile
import imageio_ffmpeg

def get_ffprobe_exe():
    """
    Finds the ffprobe executable path with fallback to common system locations.
    """
    found = shutil.which("ffprobe")
    if found:
        return found
    for candidate in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "/usr/bin/ffprobe"]:
        if os.path.exists(candidate):
            return candidate
    return "ffprobe"

def get_audio_duration(audio_path):
    """
    Returns the duration of the audio file in seconds using ffprobe.
    """
    ffprobe = get_ffprobe_exe()
    command = [
        ffprobe, 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        audio_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Could not get duration with ffprobe: {result.stderr}")
    return float(result.stdout.strip())

def get_video_dimensions(video_path):
    """
    Returns (width, height) of the video file using ffprobe.
    """
    ffprobe = get_ffprobe_exe()
    command = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        video_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0 and "x" in result.stdout:
        try:
            parts = result.stdout.strip().split("x")
            return int(parts[0]), int(parts[1])
        except Exception:
            pass
    return 1080, 1920

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

def generate_preview_frame(video_in, subtitle_ass, timestamp_sec=1.5, output_img_path=None, font_dir=None, aspect_mode="original", show_safe_area=False):
    """
    Extracts a single representative video frame and burns the subtitles on it.
    Fast (< 1 second) execution for live visual feedback in UI.
    """
    if output_img_path is None:
        fd, output_img_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        
    sub_path_escaped = os.path.abspath(subtitle_ass).replace('\\', '/').replace(':', '\\\\:')
    font_opt = f":fontsdir='{font_dir}'" if font_dir else ""
    
    vf_filters = []
    if aspect_mode == "vertical_9_16":
        vf_filters.append("scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")
    
    vf_filters.append(f"ass='{sub_path_escaped}'{font_opt}")
    
    if show_safe_area:
        # TikTok / Reels UI Safe Zone Guides (Green/Cyan safe box, Red bottom danger zone)
        vf_filters.append("drawbox=x=40:y=220:w=900:h=1320:color=cyan@0.6:t=3,drawbox=x=0:y=1540:w=1080:h=380:color=red@0.2:t=fill")
        
    filter_str = ",".join(vf_filters)
    
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-ss", str(max(0.0, float(timestamp_sec))),
        "-i", video_in,
        "-vf", filter_str,
        "-vframes", "1",
        "-q:v", "2",
        output_img_path
    ]
    
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        fallback_cmd = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-ss", str(max(0.0, float(timestamp_sec))),
            "-i", video_in,
            "-vframes", "1",
            "-q:v", "2",
            output_img_path
        ]
        subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
    return output_img_path


def process_video_subtitles_only(
    video_in, 
    subtitle_ass, 
    output_path, 
    font_dir=None, 
    aspect_mode="original", 
    enhance_quality=False
):
    """
    Standard high-performance subtitle burn pipeline.
    Preserves 100% original audio fidelity (zero compression / mastering distortion).
    """
    sub_path_escaped = os.path.abspath(subtitle_ass).replace('\\', '/').replace(':', '\\\\:')
    font_opt = f":fontsdir='{font_dir}'" if font_dir else ""
    
    vf_parts = []
    
    # Optional light enhancement
    if enhance_quality:
        vf_parts.append("unsharp=3:3:0.5:3:3:0.0,eq=saturation=1.05:contrast=1.02")
        
    # Aspect Ratio Mode
    if aspect_mode == "vertical_9_16":
        vf_parts.append("scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")
        
    vf_parts.append(f"ass='{sub_path_escaped}'{font_opt}")
    filter_chain = ",".join(vf_parts)
    
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i", video_in,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "copy", # Copy audio directly to ensure 100% identical sound quality
        output_path
    ]
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    
    # If audio copy failed (e.g. incompatible container or non-aac stream), fallback to aac 320k
    if process.returncode != 0:
        command_fallback = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-i", video_in,
            "-vf", filter_chain,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "aac",
            "-b:a", "320k",
            "-ar", "48000",
            output_path
        ]
        proc2 = subprocess.Popen(command_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out2, err2 = proc2.communicate()
        if proc2.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with error: {err2.decode()}")
            
    return output_path

def process_video_with_audio_replace(
    video_in, 
    audio_in, 
    subtitle_ass, 
    output_path, 
    font_dir=None, 
    aspect_mode="original", 
    enhance_quality=False
):
    """
    Replaces original video audio with the uploaded audio file and burns subtitles.
    """
    sub_path_escaped = os.path.abspath(subtitle_ass).replace('\\', '/').replace(':', '\\\\:')
    font_opt = f":fontsdir='{font_dir}'" if font_dir else ""
    
    vf_parts = []
    if enhance_quality:
        vf_parts.append("unsharp=3:3:0.5:3:3:0.0,eq=saturation=1.05:contrast=1.02")
    if aspect_mode == "vertical_9_16":
        vf_parts.append("scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black")
    vf_parts.append(f"ass='{sub_path_escaped}'{font_opt}")
    filter_chain = ",".join(vf_parts)
    
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-i", video_in,
        "-i", audio_in,
        "-vf", filter_chain,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        output_path
    ]
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with error: {stderr.decode()}")
        
    return output_path

# Backward compatibility alias
process_video = process_video_with_audio_replace
burn_subtitles_to_video = process_video_subtitles_only
