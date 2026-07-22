import whisper
import json
from openai import OpenAI

# Tải model whisper cục bộ (dùng mô hình 'base' hoặc 'small' để chạy nhanh trên máy cá nhân)
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model("base")
    return _whisper_model

def format_ass_time(seconds):
    """Convert seconds to ASS time format: H:MM:SS.cs"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def call_nvidia_whisper(audio_path, api_key):
    """
    Sử dụng Local Whisper thay vì NVIDIA API để bóc băng (Do NVIDIA API không hỗ trợ endpoint này cho key của bạn).
    Trả về định dạng tương đương API để không phải sửa code phía sau.
    """
    model = get_whisper_model()
    result = model.transcribe(audio_path, word_timestamps=True)
    return result

def auto_sync_audio(video_transcript, audio_transcript, api_key):
    """
    Uses an LLM to compare the two transcripts and find the start time.
    """
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    vid_segments = []
    for s in video_transcript.get("segments", []):
        vid_segments.append(f"[{s.get('start', 0):.2f}s] {s.get('text', '').strip()}")
    vid_text = "\\n".join(vid_segments)
    
    aud_text = " ".join([s.get("text", "") for s in audio_transcript.get("segments", [])]).strip()
    
    prompt = f"""
I have a video with the following English transcript (including timestamps in seconds):
{vid_text}

I have a dubbed Vietnamese audio track that translates a portion of this video. The translated text is:
"{aud_text}"

Find the best matching starting timestamp in the English transcript that corresponds to the beginning of the Vietnamese translated text.
Return ONLY the timestamp as a float number (e.g. 12.5), without any additional words.
"""
    
    try:
        completion = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=10
        )
        content = completion.choices[0].message.content.strip()
        import re
        match = re.search(r"\\d+\\.?\\d*", content)
        if match:
            return float(match.group())
    except Exception as e:
        print("Lỗi khi đồng bộ:", e)
    return 0.0


import difflib
import re

def generate_ass_subtitle(transcript_json, output_path, video_width=1920, video_height=1080, margin_v=80, outline_size=10, correct_text=""):
    """
    Generates an .ass subtitle file from the Whisper response.
    Features: 
    - Forced alignment if correct_text is provided
    - Max 6 words per line for better readability
    - BorderStyle=3 (Opaque box) to mask original subs
    - Beautiful bold yellow font
    """
    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,75,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,3,{outline_size},0,2,20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    segments = transcript_json.get("segments", [])
    whisper_words = []
    
    for segment in segments:
        words = segment.get("words", [])
        if not words:
            # Fallback if no word timestamps, split text and distribute time
            text = segment.get("text", "").strip()
            word_list = text.split()
            seg_start = segment.get("start", 0)
            seg_end = segment.get("end", 0)
            for i, w in enumerate(word_list):
                whisper_words.append({
                    "word": w,
                    "start": seg_start + (i / len(word_list)) * (seg_end - seg_start),
                    "end": seg_start + ((i + 1) / len(word_list)) * (seg_end - seg_start)
                })
        else:
            whisper_words.extend(words)
            
    # FORCED ALIGNMENT
    if correct_text and correct_text.strip():
        user_words_raw = re.findall(r'\\S+', correct_text.strip())
        
        def clean_word(w):
            return re.sub(r'[^\\w\\s]', '', w.lower())
            
        w_words_clean = [clean_word(w.get("word", "")) for w in whisper_words]
        u_words_clean = [clean_word(w) for w in user_words_raw]
        
        matcher = difflib.SequenceMatcher(None, w_words_clean, u_words_clean)
        
        aligned_user_words = [{"word": w, "start": None, "end": None} for w in user_words_raw]
            
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for k in range(j2 - j1):
                    aligned_user_words[j1 + k]["start"] = whisper_words[i1 + k].get("start", 0)
                    aligned_user_words[j1 + k]["end"] = whisper_words[i1 + k].get("end", 0)
                    
        known_points = [(j, uw["start"], uw["end"]) for j, uw in enumerate(aligned_user_words) if uw["start"] is not None]
        if not known_points:
            for j, uw in enumerate(aligned_user_words):
                uw["start"] = j * 0.5
                uw["end"] = (j+1) * 0.5
        else:
            for j, uw in enumerate(aligned_user_words):
                if uw["start"] is None:
                    left = [p for p in known_points if p[0] < j]
                    right = [p for p in known_points if p[0] > j]
                    
                    if left and right:
                        l_idx, _, l_end = left[-1]
                        r_idx, r_start, _ = right[0]
                        fraction = (j - l_idx) / (r_idx - l_idx)
                        uw["start"] = l_end + fraction * (r_start - l_end)
                        uw["end"] = uw["start"] + 0.3
                    elif left:
                        l_idx, _, l_end = left[-1]
                        uw["start"] = l_end + (j - l_idx) * 0.3
                        uw["end"] = uw["start"] + 0.3
                    elif right:
                        r_idx, r_start, _ = right[0]
                        uw["start"] = max(0, r_start - (r_idx - j) * 0.3)
                        uw["end"] = uw["start"] + 0.3
                        
        words_to_chunk = aligned_user_words
    else:
        words_to_chunk = whisper_words
        
    chunks = []
    MAX_WORDS = 6
    current_chunk_words = []
    current_chunk_start = 0
    
    for w in words_to_chunk:
        if not current_chunk_words:
            current_chunk_start = w.get("start", 0)
        
        current_chunk_words.append(w.get("word", "").strip())
        
        if len(current_chunk_words) >= MAX_WORDS:
            chunk_text = " ".join(current_chunk_words)
            chunk_end = w.get("end", 0)
            chunks.append({"text": chunk_text, "start": current_chunk_start, "end": chunk_end})
            current_chunk_words = []
            
    if current_chunk_words:
        chunk_text = " ".join(current_chunk_words)
        chunk_end = words_to_chunk[-1].get("end", 0)
        chunks.append({"text": chunk_text, "start": current_chunk_start, "end": chunk_end})
            
    
    import sys
    sys.stdout.write("
=== DEBUG INFO ===
")
    sys.stdout.write(f"user_words_raw: {len(user_words_raw) if 'user_words_raw' in locals() else 'None'}
")
    sys.stdout.write(f"words_to_chunk: {len(words_to_chunk)}
")
    sys.stdout.write(f"chunks: {len(chunks)}
")
    sys.stdout.flush()
    for chunk in chunks:
        start_time = format_ass_time(chunk["start"])
        end_time = format_ass_time(chunk["end"])
        text = chunk["text"].replace('\n', '\\N')
        ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
        
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
        
    return output_path

