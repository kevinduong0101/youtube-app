import whisper
import os
import re
import difflib

# Model cache to avoid reloading on every request
_whisper_models = {}

def get_whisper_model(model_name="base"):
    """
    Loads and caches the Whisper model in memory.
    """
    global _whisper_models
    if model_name not in _whisper_models:
        # Load on CPU with float32 for maximum stability across platforms
        _whisper_models[model_name] = whisper.load_model(model_name, device="cpu")
    return _whisper_models[model_name]

def format_ass_time(seconds):
    """
    Converts seconds (float) to ASS time format: H:MM:SS.cs
    """
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def transcribe_audio(audio_path, model_name="base", language="vi"):
    """
    Transcribes audio using local Whisper model with word-level timestamps.
    """
    model = get_whisper_model(model_name)
    if language:
        result = model.transcribe(audio_path, word_timestamps=True, language=language, fp16=False)
    else:
        result = model.transcribe(audio_path, word_timestamps=True, fp16=False)
    return result

# Backward compatibility alias
call_nvidia_whisper = transcribe_audio

def create_smart_rhythm_chunks(words, max_words=4, max_chars=24, silence_threshold=0.35, max_duration=2.8):
    """
    Splits a continuous stream of words into readable, rhythm-aware subtitle chunks.
    Respects pauses in speech, punctuation marks, and character limits.
    """
    if not words:
        return []
    
    chunks = []
    current_chunk = []
    
    for i, w in enumerate(words):
        current_chunk.append(w)
        
        # If last word, loop will finish and append outside
        if i == len(words) - 1:
            break
            
        next_w = words[i + 1]
        should_split = False
        
        # Condition 1: Significant silence / pause between words (e.g. natural breath)
        silence_gap = next_w.get('start', 0) - w.get('end', 0)
        if silence_gap >= silence_threshold:
            should_split = True
            
        # Condition 2: Sentence-ending punctuation (. ! ? ...)
        word_text = w.get('word', '').strip()
        if any(word_text.endswith(p) for p in ['.', '!', '?', '...']):
            should_split = True
            
        # Condition 3: Clause-breaking punctuation (, ; : -) if chunk already has at least 2 words
        if any(word_text.endswith(p) for p in [',', ';', ':', ' - ']) and len(current_chunk) >= 2:
            should_split = True
            
        # Condition 4: Reached max words or max characters
        chunk_text_len = sum(len(x.get('word', '')) for x in current_chunk) + len(current_chunk) - 1
        if len(current_chunk) >= max_words or chunk_text_len >= max_chars:
            should_split = True
            
        # Condition 5: Duration exceeded
        chunk_dur = w.get('end', 0) - current_chunk[0].get('start', 0)
        if chunk_dur >= max_duration and len(current_chunk) >= 2:
            should_split = True
            
        if should_split:
            chunks.append(current_chunk)
            current_chunk = []
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def extract_flat_words_from_transcript(transcript_json):
    """
    Extracts a flat list of word dictionaries from Whisper transcript response.
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
            dur = max(0.1, seg_end - seg_start)
            for i, w in enumerate(word_list):
                whisper_words.append({
                    "word": w,
                    "start": seg_start + (i / len(word_list)) * dur,
                    "end": seg_start + ((i + 1) / len(word_list)) * dur
                })
        else:
            for w in words:
                whisper_words.append({
                    "word": w.get("word", "").strip(),
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0))
                })
    return whisper_words

def generate_ass_subtitle(
    transcript_json, 
    output_path, 
    video_width=1080, 
    video_height=1920, 
    margin_v=150, 
    outline_size=6, 
    correct_text="", 
    highlight_color="&H0000FFFF", 
    audio_duration=10.0, 
    font_name="UVN Ban Tay", 
    font_size=65, 
    sub_style="YouTube Vlog", 
    sub_offset_ms=0,
    pre_chunked_data=None
):
    """
    Generates an optimized .ass subtitle file with karaoke tracking and custom styles.
    """
    # Define ASS Styles based on selected preset
    if sub_style == "YouTube Vlog":
        # Crisp white text with thick black outline and soft shadow
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
            f"-1,0,0,0,100,100,0,0,1,{outline_size},2,2,20,20,{margin_v},1"
        )
    elif sub_style == "Netflix Style":
        # Classic clean movie subtitles, thin outline, no karaoke bounce
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,"
            f"0,0,0,0,100,100,0,0,1,3,1,2,20,20,{margin_v},1"
        )
    else:
        # TikTok Karaoke (Mask box on Layer 0, Highlighted text on Layer 1)
        styles_str = (
            f"Style: MaskStyle,{font_name},{font_size},"
            f"&HFF000000,&HFF000000,&HAA000000,&HAA000000,"
            f"-1,0,0,0,100,100,0,0,3,{outline_size + 4},0,2,20,20,{margin_v},1\n"
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,"
            f"-1,0,0,0,100,100,0,0,1,4,2,2,20,20,{margin_v},1"
        )

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
    
    if pre_chunked_data:
        chunks = pre_chunked_data
    else:
        whisper_words = extract_flat_words_from_transcript(transcript_json)
        
        # FORCED ALIGNMENT (DIFFLIB EXACT MATCHING) if custom text provided
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
                            
            # Interpolate missing timestamps smoothly
            i = 0
            last_known_end = 0.0
            while i < len(aligned_user_words):
                if aligned_user_words[i]['start'] is not None:
                    last_known_end = aligned_user_words[i]['end']
                    i += 1
                    continue
                    
                j = i
                while j < len(aligned_user_words) and aligned_user_words[j]['start'] is None:
                    j += 1
                    
                if j < len(aligned_user_words):
                    next_known_start = aligned_user_words[j]['start']
                else:
                    next_known_start = last_known_end + (j - i) * 0.3
                    
                if next_known_start < last_known_end:
                    next_known_start = last_known_end
                    
                gap = next_known_start - last_known_end
                dur_per_word = gap / (j - i) if (j - i) > 0 else 0.3
                dur_per_word = min(dur_per_word, 0.5)
                
                for k in range(i, j):
                    aligned_user_words[k]['start'] = last_known_end + (k - i) * dur_per_word
                    aligned_user_words[k]['end'] = aligned_user_words[k]['start'] + dur_per_word
                    
                last_known_end = aligned_user_words[j-1]['end']
                i = j
                
            words_to_chunk = aligned_user_words
        else:
            words_to_chunk = whisper_words
            
        # Apply global offset slider
        offset_sec = sub_offset_ms / 1000.0
        for w in words_to_chunk:
            w['start'] = max(0.0, w['start'] + offset_sec)
            w['end'] = max(0.0, w['end'] + offset_sec)
            
        # SMART RHYTHM CHUNKING
        chunks = create_smart_rhythm_chunks(words_to_chunk)
        
    for chunk in chunks:
        if not chunk: 
            continue
        chunk_start = chunk[0]['start']
        chunk_end = chunk[-1]['end']
        
        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)
        full_text = ' '.join(w['word'] for w in chunk).replace('\n', '')
        
        # Layer 0: Mask background box (TikTok Karaoke preset only)
        if sub_style == "TikTok Karaoke":
            ass_content += f"Dialogue: 0,{start_str},{end_str},MaskStyle,,0,0,0,,{{\\alpha&HFF&}}{full_text}\n"
            
        # Netflix Style: Static chunk, no karaoke word animation
        if sub_style == "Netflix Style":
            ass_content += f"Dialogue: 1,{start_str},{end_str},TextStyle,,0,0,0,,{full_text}\n"
            continue
        
        # Layer 1: Karaoke word highlight tracking
        last_time = chunk_start
        for i, target_word in enumerate(chunk):
            w_start = max(target_word['start'], last_time)
            
            # Bound end time so words never overlap
            if i < len(chunk) - 1:
                w_end = min(target_word['end'], chunk[i+1]['start'])
            else:
                w_end = target_word['end']
                
            w_end = max(w_start + 0.01, w_end)
            
            # Gap before this word: render neutral white text
            if w_start > last_time + 0.01:
                gap_start = format_ass_time(last_time)
                gap_end = format_ass_time(w_start)
                
                parts = [w['word'].replace('\n', '') for w in chunk]
                line_text = ' '.join(parts)
                ass_content += f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{line_text}\n"
                
            # Active word: highlighted with highlight_color
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
            
        # Trailing gap at the end of the chunk
        if chunk_end > last_time + 0.01:
            gap_start = format_ass_time(last_time)
            gap_end = format_ass_time(chunk_end)
            parts = [w['word'].replace('\n', '') for w in chunk]
            line_text = ' '.join(parts)
            ass_content += f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{line_text}\n"
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
        
    return output_path
