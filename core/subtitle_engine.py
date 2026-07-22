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

def call_nvidia_whisper(audio_path, api_key, language=None):
    """
    Sử dụng Local Whisper thay vì NVIDIA API để bóc băng (Do NVIDIA API không hỗ trợ endpoint này cho key của bạn).
    Trả về định dạng tương đương API để không phải sửa code phía sau.
    """
    model = get_whisper_model()
    if language:
        result = model.transcribe(audio_path, word_timestamps=True, language=language)
    else:
        result = model.transcribe(audio_path, word_timestamps=True)
    return result

def auto_sync_scenes(video_transcript, audio_transcript, api_key, total_audio_duration):
    """
    Uses an LLM to compare the two transcripts and find multiple matching scenes.
    Returns a list of cuts: [{"vid_start": 50.0, "duration": 3.0}, ...]
    """
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    vid_segments = []
    for s in video_transcript.get("segments", []):
        vid_segments.append(f"[{s.get('start', 0):.2f}s] {s.get('text', '').strip()}")
    vid_text = "\\n".join(vid_segments)
    
    aud_segments_info = []
    aud_segments = audio_transcript.get("segments", [])
    
    # Calculate durations so they perfectly tile the total audio duration
    for i, s in enumerate(aud_segments):
        start = s.get("start", 0)
        if i < len(aud_segments) - 1:
            next_start = aud_segments[i+1].get("start", start + 2.0)
            dur = next_start - start
        else:
            dur = total_audio_duration - start
            
        if dur <= 0: dur = 2.0
        aud_segments_info.append({"idx": i, "text": s.get("text", "").strip(), "duration": dur})
    
    # Fallback if Whisper returned no segments
    if not aud_segments_info:
        aud_segments_info.append({"idx": 0, "text": "Full Audio", "duration": total_audio_duration})
        
    aud_text_lines = []
    for s in aud_segments_info:
        aud_text_lines.append(f"{s['idx']}: {s['text']}")
    aud_text = "\\n".join(aud_text_lines)
    
    prompt = f"""
I have an original video transcript (English, Chinese, or other) with timestamps:
{vid_text}

I have a summarized Vietnamese audio track, divided into numbered segments:
{aud_text}

Task: For each numbered Vietnamese segment, find the BEST matching starting timestamp in the original video transcript based on semantic meaning.
Output your response as a valid JSON array of floats ONLY. For example, if there are 3 segments, output:
[12.5, 50.0, 100.2]

Do NOT output any markdown blocks, explanations, or text. JUST the JSON array.
"""
    
    cuts = []
    import random
    
    try:
        completion = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200
        )
        content = completion.choices[0].message.content.strip()
        import re
        import json
        
        # Extract JSON array
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        if match:
            timestamps = json.loads(match.group())
            for i in range(len(aud_segments_info)):
                if i < len(timestamps):
                    vid_start = float(timestamps[i])
                else:
                    # Fallback random spot if AI missed this segment
                    vid_start = random.uniform(0.0, 20.0)
                    
                cuts.append({
                    "vid_start": vid_start,
                    "duration": aud_segments_info[i]["duration"]
                })
            return cuts
    except Exception as e:
        print("Lỗi khi đồng bộ các phân cảnh:", e)
    
    # Complete Fallback if failed
    for info in aud_segments_info:
        cuts.append({
            "vid_start": random.uniform(0.0, 20.0),
            "duration": info["duration"]
        })
    return cuts


import random

def recommend_bgm(audio_transcript, bgm_list, api_key):
    """
    Analyzes the audio_transcript to understand the mood and suggests the best matching bgm from bgm_list.
    """
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )
    
    aud_text = " ".join([s.get("text", "") for s in audio_transcript.get("segments", [])]).strip()
    
    # Randomly sample if bgm_list is too large
    if len(bgm_list) > 100:
        bgm_list = random.sample(bgm_list, 100)
    bgm_str = "\\n".join([f"- {bgm}" for bgm in bgm_list])
    
    prompt = f"""
You are an expert video editor and music supervisor. I have a summarized Vietnamese audio track that will be the voiceover for a video.
Here is the voiceover transcript:
"{aud_text}"

I have a directory of background music files available:
{bgm_str}

Based on the mood, tone, and topic of the voiceover, which ONE background music file from the list above is the most suitable?
Return ONLY the exact filename from the list, with no additional text or explanation.
"""
    
    try:
        completion = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=50
        )
        content = completion.choices[0].message.content.strip()
        # Clean up any surrounding quotes or markdown
        content = content.replace("'", "").replace('"', '').strip()
        if content in bgm_list:
            return content
        else:
            # Fallback exact matching check
            for bgm in bgm_list:
                if bgm.lower() in content.lower():
                    return bgm
    except Exception as e:
        print("Lỗi khi AI gợi ý nhạc:", e)
    
    # Fallback to a random funny or default track
    if bgm_list:
        return random.choice(bgm_list)
    return None

import difflib
import re

def generate_ass_subtitle(transcript_json, output_path, video_width=1920, video_height=1080, margin_v=80, outline_size=10, correct_text="", highlight_color="&H0000FFFF", audio_duration=10.0, font_name="Arial", font_size=75, sub_style="TikTok Karaoke", sub_offset_ms=0):
    """
    Generates an .ass subtitle file from the Whisper response.
    Features: 
    - Multiple subtitle styles: TikTok Karaoke, YouTube Vlog, Netflix Style
    - Adjustable sync offset (sub_offset_ms)
    - Forced alignment if correct_text is provided using proportional mapping
    - Max 6 words per line for better readability
    """
    if sub_style == "YouTube Vlog":
        styles_str = f"Style: TextStyle,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,10,2,2,20,20,{margin_v},1"
    elif sub_style == "Netflix Style":
        styles_str = f"Style: TextStyle,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,4,1,2,20,20,{margin_v},1"
    else:
        # TikTok Karaoke
        styles_str = f"Style: MaskStyle,{font_name},{font_size},&HFF000000,&HFF000000,&HAA000000,&HAA000000,-1,0,0,0,100,100,0,0,3,{outline_size},0,2,20,20,{margin_v},1\nStyle: TextStyle,{font_name},{font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,6,2,2,20,20,{margin_v},1"

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_str}

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
            
    # FORCED ALIGNMENT (DIFFLIB EXACT MATCHING)
    if correct_text and correct_text.strip():
        user_words_raw = re.findall(r'\S+', correct_text.strip())
        aligned_user_words = [{"word": w, "start": None, "end": None} for w in user_words_raw]
        
        whisper_texts = [re.sub(r'[^\w\s]', '', w['word'].strip().lower()) for w in whisper_words]
        user_texts = [re.sub(r'[^\w\s]', '', w.strip().lower()) for w in user_words_raw]
        
        sm = difflib.SequenceMatcher(None, whisper_texts, user_texts)
        
        # Map exact matches
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    if i < len(whisper_words) and j < len(aligned_user_words):
                        aligned_user_words[j]['start'] = whisper_words[i].get('start', 0.0)
                        aligned_user_words[j]['end'] = whisper_words[i].get('end', 0.0)
                        
        # Interpolate missing timestamps
        i = 0
        last_known_end = 0.0
        while i < len(aligned_user_words):
            if aligned_user_words[i]['start'] is not None:
                last_known_end = aligned_user_words[i]['end']
                i += 1
                continue
                
            # Find contiguous block of missing timestamps
            j = i
            while j < len(aligned_user_words) and aligned_user_words[j]['start'] is None:
                j += 1
                
            if j < len(aligned_user_words):
                next_known_start = aligned_user_words[j]['start']
            else:
                # If at the end, just assume each remaining word takes 0.3s
                next_known_start = last_known_end + (j - i) * 0.3
                
            if next_known_start < last_known_end:
                next_known_start = last_known_end
                
            gap = next_known_start - last_known_end
            dur_per_word = gap / (j - i) if (j - i) > 0 else 0.3
            dur_per_word = min(dur_per_word, 0.5) # Max 0.5s per word for missing words
            
            for k in range(i, j):
                aligned_user_words[k]['start'] = last_known_end + (k - i) * dur_per_word
                aligned_user_words[k]['end'] = aligned_user_words[k]['start'] + dur_per_word
                
            last_known_end = aligned_user_words[j-1]['end']
            i = j
            
        words_to_chunk = aligned_user_words
    else:
        words_to_chunk = whisper_words
        
    # Apply global offset
    offset_sec = sub_offset_ms / 1000.0
    for w in words_to_chunk:
        w['start'] = max(0.0, w['start'] + offset_sec)
        w['end'] = max(0.0, w['end'] + offset_sec)
        
    chunks = []
    MAX_WORDS = 6
    current_chunk = []
    
    for w in words_to_chunk:
        current_chunk.append(w)
        if len(current_chunk) >= MAX_WORDS:
            chunks.append(current_chunk)
            current_chunk = []
            
    if current_chunk:
        chunks.append(current_chunk)
        
    for chunk in chunks:
        if not chunk: continue
        chunk_start = chunk[0]['start']
        chunk_end = chunk[-1]['end']
        
        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)
        full_text = ' '.join(w['word'] for w in chunk).replace('\n', '')
        
        # 1. Mask Layer (Layer 0) - Semi-transparent box to hide hardsubs (TikTok only)
        if sub_style == "TikTok Karaoke":
            ass_content += f"Dialogue: 0,{start_str},{end_str},MaskStyle,,0,0,0,,{{\\alpha&HFF&}}{full_text}\n"
            
        # If Netflix style, just show the whole text with no highlights
        if sub_style == "Netflix Style":
            ass_content += f"Dialogue: 1,{start_str},{end_str},TextStyle,,0,0,0,,{full_text}\n"
            continue
        
        # 2. Text Layer (Layer 1) - Karaoke Highlights (Continuous with precise tracking)
        last_time = chunk_start
        for i, target_word in enumerate(chunk):
            w_start = max(target_word['start'], last_time)
            
            # Cắt gọt timestamp: Thời gian kết thúc không được đè lên thời gian bắt đầu của chữ tiếp theo
            if i < len(chunk) - 1:
                w_end = min(target_word['end'], chunk[i+1]['start'])
            else:
                w_end = target_word['end']
                
            w_end = max(w_start + 0.01, w_end)
            
            # Nếu có khoảng hở giữa 2 chữ (VD: người đọc ngắt quãng), in ra dòng không có highlight
            if w_start > last_time + 0.01:
                gap_start = format_ass_time(last_time)
                gap_end = format_ass_time(w_start)
                
                parts = []
                for w in chunk:
                    parts.append(w['word'].replace('\n', ''))
                line_text = ' '.join(parts)
                ass_content += f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{line_text}\n"
                
            # In ra dòng có highlight chữ hiện tại
            word_start_str = format_ass_time(w_start)
            word_end_str = format_ass_time(w_end)
            
            parts = []
            for j, w in enumerate(chunk):
                word_text = w['word'].replace('\n', '')
                if j == i:
                    parts.append(f"{{\\c{highlight_color}&}}{word_text}{{\\c&H00FFFFFF&}}")
                else:
                    parts.append(word_text)
            line_text = ' '.join(parts)
            ass_content += f"Dialogue: 1,{word_start_str},{word_end_str},TextStyle,,0,0,0,,{line_text}\n"
            
            last_time = w_end
            
        # Lấp đầy khoảng hở ở cuối câu (nếu có)
        if chunk_end > last_time + 0.01:
            gap_start = format_ass_time(last_time)
            gap_end = format_ass_time(chunk_end)
            parts = []
            for w in chunk:
                parts.append(w['word'].replace('\n', ''))
            line_text = ' '.join(parts)
            ass_content += f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{line_text}\n"
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
        
    return output_path

