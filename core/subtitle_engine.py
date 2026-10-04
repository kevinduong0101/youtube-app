import whisper
import os
import re
import difflib

from core.subtitle_renderer import render_ass_script
from core.presets import get_preset

# Model cache to avoid reloading on every request
_whisper_models = {}

def get_whisper_model(model_name="base"):
    """
    Loads and caches the Whisper model in memory.
    """
    global _whisper_models
    if model_name not in _whisper_models:
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
    margin_v=220, 
    outline_size=None, 
    correct_text="", 
    highlight_color=None, 
    audio_duration=10.0, 
    font_name=None, 
    font_size=None, 
    sub_style="hormozi", 
    sub_offset_ms=0,
    animation_mode=None,
    text_transform=None,
    max_words_per_chunk=3,
    pre_chunked_data=None
):
    """
    Orchestrates subtitle chunking, timing alignment, and delegates styling to core.subtitle_renderer.
    """
    # 1. Determine preset id
    clean_style = str(sub_style).lower()
    if "hormozi" in clean_style:
        preset_id = "hormozi"
    elif "vlog" in clean_style:
        preset_id = "vlog_pro"
    elif "pill" in clean_style or "tiktok" in clean_style:
        preset_id = "pill_badge"
    elif "neon" in clean_style or "cyberpunk" in clean_style:
        preset_id = "neon_glow"
    elif "cinematic" in clean_style or "netflix" in clean_style:
        preset_id = "cinematic"
    else:
        preset_id = "hormozi"

    # 2. Process Chunks
    if pre_chunked_data:
        chunks = pre_chunked_data
    else:
        whisper_words = extract_flat_words_from_transcript(transcript_json)
        
        # FORCED ALIGNMENT (DIFFLIB EXACT MATCHING)
        if correct_text and correct_text.strip():
            user_words_raw = re.findall(r'\S+', correct_text.strip())
            aligned_user_words = [{"word": w, "start": None, "end": None} for w in user_words_raw]
            
            whisper_texts = [re.sub(r'[^\w\s]', '', w['word'].strip().lower()) for w in whisper_words]
            user_texts = [re.sub(r'[^\w\s]', '', w.strip().lower()) for w in user_words_raw]
            
            sm = difflib.SequenceMatcher(None, whisper_texts, user_texts)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag == 'equal':
                    for i, j in zip(range(i1, i2), range(j1, j2)):
                        if i < len(whisper_words) and j < len(aligned_user_words):
                            aligned_user_words[j]['start'] = whisper_words[i].get('start', 0.0)
                            aligned_user_words[j]['end'] = whisper_words[i].get('end', 0.0)
                            
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
            
        chunks = create_smart_rhythm_chunks(words_to_chunk, max_words=max_words_per_chunk)

    # 3. Build overrides
    overrides = {}
    if font_name:
        overrides["font_family"] = font_name
    if font_size:
        overrides["font_size"] = font_size
    if margin_v is not None:
        overrides["margin_v"] = margin_v
    if outline_size is not None:
        overrides["outline_width"] = outline_size
    if highlight_color:
        overrides["highlight_color"] = highlight_color
    if animation_mode:
        overrides["animation_mode"] = animation_mode
    if text_transform:
        overrides["all_caps"] = (text_transform == "uppercase")

    # 4. Delegate to dedicated ASS motion renderer
    return render_ass_script(
        chunks=chunks,
        output_path=output_path,
        preset_id=preset_id,
        custom_overrides=overrides,
        video_width=video_width,
        video_height=video_height
    )
