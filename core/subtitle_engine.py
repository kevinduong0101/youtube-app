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

# ==============================================================================
# BỘ TỪ ĐIỂN TỪ GHÉP & NGỮ NGHĨA TIẾNG VIỆT (COMPOUND-WORD AWARENESS)
# ==============================================================================
VIETNAMESE_COMPOUND_PAIRS = {
    # Kế hoạch & Công việc
    ("kế", "hoạch"), ("dự", "án"), ("bài", "toán"), ("nhiệm", "vụ"), ("công", "việc"),
    ("làm", "việc"), ("thực", "hiện"), ("hoàn", "thành"), ("hoàn", "thiện"), ("chuẩn", "bị"),
    ("tiến", "hành"), ("bắt", "đầu"), ("kết", "thúc"), ("tiến", "độ"), ("kết", "quả"),
    ("thành", "công"), ("thất", "bại"), ("khó", "khăn"), ("thuận", "lợi"), ("chiến", "lược"),
    ("mục", "tiêu"), ("hành", "động"), ("phương", "pháp"), ("kỹ", "năng"), ("kinh", "nghiệm"),
    # Công nghệ & Lập trình & Mạng xã hội
    ("lập", "trình"), ("máy", "tính"), ("máy", "chủ"), ("trí", "tuệ"), ("nhân", "tạo"),
    ("phần", "mềm"), ("phần", "cứng"), ("hệ", "thống"), ("công", "nghệ"), ("nền", "tảng"),
    ("ứng", "dụng"), ("công", "cụ"), ("thiết", "bị"), ("điện", "thoại"), ("mạng", "xã"),
    ("xã", "hội"), ("tin", "tức"), ("dữ", "liệu"), ("thông", "tin"), ("nội", "dung"),
    ("kênh", "youtube"), ("video", "clip"), ("người", "xem"), ("tương", "tác"), ("bình", "luận"),
    ("chia", "sẻ"), ("đăng", "ký"), ("theo", "dõi"), ("thu", "âm"), ("phụ", "đề"),
    ("tải", "về"), ("tải", "lên"), ("cài", "đặt"), ("gỡ", "bỏ"), ("nâng", "cấp"),
    ("cập", "nhật"), ("sửa", "chữa"), ("khắc", "phục"), ("sự", "cố"), ("bảo", "mật"),
    ("an", "toàn"), ("nguy", "hiểm"), ("rủi", "ro"), ("tối", "ưu"), ("phân", "tích"),
    # Từ mượn công nghệ phổ biến
    ("browse", "web"), ("lướt", "web"), ("xem", "phim"), ("nghe", "nhạc"), ("đọc", "sách"),
    ("data", "science"), ("machine", "learning"), ("deep", "learning"), ("artificial", "intelligence"),
    # Phát triển bản thân & Tư duy
    ("phát", "triển"), ("nghiên", "cứu"), ("học", "tập"), ("tập", "trung"), ("bản", "thân"),
    ("tự", "giác"), ("tự", "động"), ("suy", "nghĩ"), ("tư", "duy"), ("ý", "tưởng"),
    ("sáng", "tạo"), ("đổi", "mới"), ("kiến", "thức"), ("hiểu", "biết"), ("nhận", "thức"),
    ("cảm", "xúc"), ("tinh", "thần"), ("năng", "lượng"), ("động", "lực"), ("sức", "khỏe"),
    ("ý", "nghĩa"), ("giá", "trị"), ("tiêu", "chuẩn"), ("chất", "lượng"), ("số", "lượng"),
    # Kinh doanh & Thị trường
    ("kinh", "doanh"), ("khách", "hàng"), ("sản", "phẩm"), ("dịch", "vụ"), ("thị", "trường"),
    ("tiềm", "năng"), ("cơ", "hội"), ("thách", "thức"), ("vấn", "đề"), ("giải", "pháp"),
    ("đầu", "tư"), ("lợi", "nhuận"), ("doanh", "thu"), ("chi", "phí"), ("ngân", "sách"),
    ("quản", "lý"), ("điều", "hành"), ("lãnh", "đạo"), ("tổ", "chức"), ("sắp", "xếp"),
    ("cung", "cấp"), ("hỗ", "trợ"), ("hợp", "tác"), ("kết", "nối"), ("trao", "đổi"),
    # Thời gian & Không gian
    ("thời", "gian"), ("không", "gian"), ("hôm", "nay"), ("ngày", "mai"), ("hiện", "tại"),
    ("tương", "lai"), ("quá", "khứ"), ("lâu", "dài"), ("ngắn", "hạn"), ("bền", "vững"),
    ("nhanh", "chóng"), ("chính", "xác"), ("rõ", "ràng"), ("chi", "tiết"), ("cụ", "thể"),
    ("đơn", "giản"), ("hiệu", "quả"), ("tuyệt", "vời"), ("quan", "trọng"), ("cần", "thiết")
}

DANGLING_PARTICLES = {
    "để", "và", "với", "của", "cho", "như", "là", "trong", "tại", "khi", "mà", 
    "hoặc", "nhưng", "bởi", "vì", "do", "từ", "lên", "xuống", "ra", "vào", "về"
}

def clean_word_token(text):
    """Loại bỏ dấu câu và chuẩn hóa thành chữ thường để so khớp."""
    return re.sub(r'[^\w\s]', '', str(text)).strip().lower()

def is_compound_pair(w1, w2):
    """Kiểm tra xem 2 từ liên tiếp có tạo thành từ ghép hoặc cụm nghĩa không được tách rời."""
    t1 = clean_word_token(w1)
    t2 = clean_word_token(w2)
    if not t1 or not t2:
        return False
    return (t1, t2) in VIETNAMESE_COMPOUND_PAIRS

def clean_and_check_emphasis(word_str):
    """
    Phát hiện cú pháp *từ nhấn mạnh* kiểu JIZURA.
    Trả về: (display_word, is_emphasis)
    """
    s = word_str.strip()
    if s.startswith('*') and s.endswith('*') and len(s) > 2:
        return s[1:-1], True
    elif s.startswith('*'):
        return s[1:], True
    elif s.endswith('*'):
        return s[:-1], True
    return s, False

def create_smart_rhythm_chunks(words, max_words=4, max_chars=24, silence_threshold=0.35, max_duration=2.8):
    """
    Chia dòng phụ đề thông minh bảo toàn cụm từ ghép tiếng Việt (Compound-Aware Chunking).
    Không ngắt giữa 'kế hoạch', 'lập trình', 'browse web' v.v.
    Hỗ trợ dấu gạch chéo '/' để ngắt nhịp chủ động kiểu JIZURA.
    """
    if not words:
        return []
    
    chunks = []
    current_chunk = []
    
    for i, w in enumerate(words):
        raw_word = w.get('word', '').strip()
        
        # Nếu từ chứa dấu ngắt chủ động '/' (JIZURA slash cut)
        if raw_word == '/' or raw_word == '//':
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
            continue
            
        clean_w_text, is_emph = clean_and_check_emphasis(raw_word)
        # Giữ lại metadata emphasis
        w_copy = dict(w)
        w_copy['word'] = clean_w_text
        if is_emph:
            w_copy['is_emphasis'] = True
            
        current_chunk.append(w_copy)
        
        # Nếu là từ cuối cùng, kết thúc vòng lặp
        if i == len(words) - 1:
            break
            
        next_w = words[i + 1]
        should_split = False
        
        silence_gap = next_w.get('start', 0) - w.get('end', 0)
        word_text = clean_w_text
        
        # Điều kiện 1: Khoảng lặng tự nhiên khi lấy hơi (người nói dừng rõ ràng)
        if silence_gap >= silence_threshold:
            should_split = True
            
        # Điều kiện 2: Dấu câu ngắt câu (. ! ? ...)
        elif any(word_text.endswith(p) for p in ['.', '!', '?', '...']):
            should_split = True
            
        # Điều kiện 3: Dấu phẩy / ngắt mệnh đề (, ; : -) nếu câu đã có từ 2 từ trở lên
        elif any(word_text.endswith(p) for p in [',', ';', ':', ' - ']) and len(current_chunk) >= 2:
            should_split = True
            
        # Điều kiện 4: Vượt giới hạn số từ hoặc độ dài ký tự
        else:
            chunk_text_len = sum(len(x.get('word', '')) for x in current_chunk) + len(current_chunk) - 1
            chunk_dur = w.get('end', 0) - current_chunk[0].get('start', 0)
            
            if len(current_chunk) >= max_words or chunk_text_len >= max_chars or (chunk_dur >= max_duration and len(current_chunk) >= 2):
                # KIỂM TRA TỪ GHÉP: Nếu ngắt ở đây sẽ xé đôi từ ghép (ví dụ: 'kế' | 'hoạch')
                next_clean, _ = clean_and_check_emphasis(next_w.get('word', ''))
                if is_compound_pair(clean_w_text, next_clean) and silence_gap < 0.45:
                    # Cho phép co giãn linh hoạt +1 từ nếu chunk chưa quá dài
                    if len(current_chunk) <= max_words and chunk_text_len < max_chars + 12:
                        should_split = False  # Giữ lại để nhận thêm next_w ở lượt tiếp theo
                    else:
                        # Chunk đã quá dài, ngắt TRƯỚC từ hiện tại để cả cụm đi chung vào chunk mới
                        if len(current_chunk) >= 2:
                            current_chunk.pop() # Bỏ w ra khỏi chunk hiện tại
                            chunks.append(current_chunk)
                            current_chunk = [w_copy] # w bắt đầu chunk mới cùng next_w
                            should_split = False
                        else:
                            should_split = False
                elif clean_word_token(word_text) in DANGLING_PARTICLES and silence_gap < 0.4:
                    # Tránh để từ treo (để, với, cho, của) đứng cuối chunk nếu không nghỉ thở
                    if len(current_chunk) <= max_words:
                        should_split = False
                    else:
                        should_split = True
                else:
                    should_split = True

        if should_split:
            chunks.append(current_chunk)
            current_chunk = []
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def ai_optimize_subtitle_chunks(chunks):
    """
    AI Subtitle Inspector: Quét toàn bộ danh sách phân đoạn hiện có, phát hiện và
    tự động hàn gắn các cụm từ ghép bị cắt rời giữa 2 câu liền kề (như 'kế' -> 'hoạch').
    Trả về: (new_chunks, fixes_applied)
    """
    if not chunks or len(chunks) < 2:
        return chunks, []
        
    new_chunks = [list(c) for c in chunks]
    fixes_applied = []
    
    modified = True
    passes = 0
    while modified and passes < 3:
        modified = False
        passes += 1
        i = 0
        while i < len(new_chunks) - 1:
            c1 = new_chunks[i]
            c2 = new_chunks[i + 1]
            if not c1 or not c2:
                i += 1
                continue
                
            last_w1 = c1[-1]['word']
            first_w2 = c2[0]['word']
            
            # Kiểm tra xem từ cuối câu trước và từ đầu câu sau có phải từ ghép bị cắt đôi không
            if is_compound_pair(last_w1, first_w2):
                pair_name = f"{clean_word_token(last_w1)} {clean_word_token(first_w2)}"
                if len(c1) <= 3 or len(c2) >= 3:
                    moved_word = c2.pop(0)
                    c1.append(moved_word)
                    fixes_applied.append(f"Gộp cụm từ ghép '{pair_name}' vào câu #{i+1}")
                    modified = True
                else:
                    moved_word = c1.pop()
                    c2.insert(0, moved_word)
                    fixes_applied.append(f"Chuyển cụm từ ghép '{pair_name}' sang câu #{i+2}")
                    modified = True
            elif clean_word_token(last_w1) in DANGLING_PARTICLES and len(c1) > 1 and len(c2) <= 3:
                moved_word = c1.pop()
                c2.insert(0, moved_word)
                fixes_applied.append(f"Chuyển từ liên kết '{clean_word_token(last_w1)}' sang đầu câu #{i+2}")
                modified = True
                
            if not c1:
                new_chunks.pop(i)
                continue
            if not c2:
                new_chunks.pop(i + 1)
                continue
                
            i += 1
            
    new_chunks = [c for c in new_chunks if c]
    return new_chunks, fixes_applied

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

def align_user_script_to_audio(script_text, whisper_words, audio_duration=10.0):
    """
    Forced alignment: Maps user-provided exact script onto Whisper's audio timestamps.
    Ensures 100% correct spelling, punctuation, and wording while preserving *emphasis* flags.
    """
    if not script_text or not script_text.strip():
        return whisper_words
        
    user_words_raw = re.findall(r'\S+', script_text.strip())
    if not user_words_raw:
        return whisper_words
        
    aligned_words = []
    n_user = len(user_words_raw)
    
    if not whisper_words:
        dur_per_word = audio_duration / n_user if n_user > 0 else 0.5
        for i, uw in enumerate(user_words_raw):
            clean_uw, is_emph = clean_and_check_emphasis(uw)
            aligned_words.append({
                "word": clean_uw,
                "is_emphasis": is_emph,
                "start": i * dur_per_word,
                "end": (i + 1) * dur_per_word
            })
        return aligned_words
        
    def norm(w):
        clean_w, _ = clean_and_check_emphasis(w)
        return re.sub(r'[^\w\s]', '', clean_w).lower()
        
    norm_user = [norm(w) for w in user_words_raw]
    norm_whisper = [norm(w.get('word', '')) for w in whisper_words]
    
    matcher = difflib.SequenceMatcher(None, norm_user, norm_whisper)
    matching_blocks = matcher.get_matching_blocks()
    
    user_timestamps = [None] * n_user
    
    for block in matching_blocks:
        u_idx = block.a
        w_idx = block.b
        size = block.size
        for k in range(size):
            if u_idx + k < n_user and w_idx + k < len(whisper_words):
                w_obj = whisper_words[w_idx + k]
                user_timestamps[u_idx + k] = (w_obj['start'], w_obj['end'])
                
    last_known_end = 0.0
    i = 0
    while i < n_user:
        if user_timestamps[i] is not None:
            last_known_end = user_timestamps[i][1]
            i += 1
        else:
            j = i
            while j < n_user and user_timestamps[j] is None:
                j += 1
            if j < n_user:
                next_known_start = user_timestamps[j][0]
            else:
                next_known_start = max(last_known_end + (j - i) * 0.4, audio_duration)
                
            gap_dur = max(0.1, next_known_start - last_known_end)
            step = gap_dur / (j - i)
            for k in range(i, j):
                s = last_known_end + (k - i) * step
                e = s + step
                user_timestamps[k] = (s, e)
            last_known_end = next_known_start
            i = j
            
    for idx, uw in enumerate(user_words_raw):
        t_start, t_end = user_timestamps[idx]
        clean_uw, is_emph = clean_and_check_emphasis(uw)
        aligned_words.append({
            "word": clean_uw,
            "is_emphasis": is_emph,
            "start": t_start,
            "end": t_end
        })
        
    return aligned_words

# ==============================================================================
# HỆ THỐNG HIỆU ỨNG CHỮ ĐỘNG (KINETIC MOTION ENGINE - CẢM HỨNG JIZURA)
# ==============================================================================
def get_kinetic_motion_tags(animation_mode, is_emphasis, highlight_color, emphasis_color):
    """
    Tạo các thẻ ASS tags chuyển động mô phỏng vật lý (Damped Spring, Tilt, Squash, Glitch)
    chuẩn phong cách Kinetic Typography chuyên nghiệp.
    """
    target_color = emphasis_color if (is_emphasis and emphasis_color) else highlight_color
    
    if animation_mode == "elastic_spring":
        # JIZURA Damped Spring Physics: Nảy vượt ngưỡng (overshoot) rồi co lại cân bằng
        if is_emphasis:
            # Từ nhấn mạnh: Nảy cực đại 140% -> 94% -> 105%
            anim_tag = r"\t(0,70,\fscx140\fscy140)\t(70,140,\fscx94\fscy94)\t(140,210,\fscx105\fscy105)"
            reset_tag = r"\fscx100\fscy100"
        else:
            anim_tag = r"\t(0,70,\fscx125\fscy125)\t(70,140,\fscx96\fscy96)\t(140,200,\fscx100\fscy100)"
            reset_tag = r"\fscx100\fscy100"
    elif animation_mode == "kinetic_tilt":
        # MrBeast Kinetic Punch: Lắc nghiêng góc trục Z (-4° -> +3° -> 0°) giật mắt dồn dập
        if is_emphasis:
            anim_tag = r"\t(0,60,\frz-6\fscx135\fscy135)\t(60,130,\frz4)\t(130,200,\frz0\fscx105\fscy105)"
            reset_tag = r"\frz0\fscx100\fscy100"
        else:
            anim_tag = r"\t(0,60,\frz-4\fscx118\fscy118)\t(60,130,\frz3)\t(130,190,\frz0\fscx100\fscy100)"
            reset_tag = r"\frz0\fscx100\fscy100"
    elif animation_mode == "squash_stretch":
        # Cartoon Squash & Stretch: Co dẹp chiều cao khi chạm đất rồi bung dài nảy lên
        if is_emphasis:
            anim_tag = r"\t(0,60,\fscx142\fscy70)\t(60,130,\fscx82\fscy130)\t(130,200,\fscx100\fscy100)"
            reset_tag = r"\fscx100\fscy100"
        else:
            anim_tag = r"\t(0,60,\fscx128\fscy78)\t(60,130,\fscx88\fscy120)\t(130,190,\fscx100\fscy100)"
            reset_tag = r"\fscx100\fscy100"
    elif animation_mode == "pop_strong":
        scale = 135 if is_emphasis else 125
        anim_tag = f"\\fscx{scale}\\fscy{scale}"
        reset_tag = r"\fscx100\fscy100"
    elif animation_mode == "pop":
        scale = 130 if is_emphasis else 115
        anim_tag = f"\\fscx{scale}\\fscy{scale}"
        reset_tag = r"\fscx100\fscy100"
    elif animation_mode == "smooth_fade":
        scale = 112 if is_emphasis else 105
        anim_tag = f"\\t(0,100,\\fscx{scale}\\fscy{scale})"
        reset_tag = r"\fscx100\fscy100"
    else:
        anim_tag = ""
        reset_tag = ""
        
    return target_color, anim_tag, reset_tag

def generate_ass_subtitle(
    transcript_json, 
    output_path, 
    video_width=1080, 
    video_height=1920, 
    margin_v=220, 
    highlight_color="&H0000E6FF", 
    emphasis_color="&H000033FF",
    correct_text=None, 
    audio_duration=10.0, 
    font_name="UVN Ban Tay", 
    font_size=65, 
    sub_style="🔥 Alex Hormozi (Titan Viral)", 
    sub_offset_ms=0,
    animation_mode="elastic_spring",
    text_transform="uppercase",
    max_words_per_chunk=4,
    pre_chunked_data=None
):
    """
    Sinh file phụ đề .ASS chuyên nghiệp chuẩn Kinetic Typography (JIZURA-inspired):
    - Hỗ trợ 6 Motion FX: Elastic Spring, Kinetic Tilt, Squash & Stretch, Chromatic Glitch, Pop, Smooth Fade.
    - Hỗ trợ Dual-Accent Karaoke (màu active riêng cho từ thường vs từ nhấn mạnh *từ*).
    - Hỗ trợ phân tầng 3D Chromatic Anaglyph Glitch (Cyan & Magenta offset layers).
    """
    # 1. Định nghĩa Style ASS cho các Presets Studio Độc Quyền
    if "Alex Hormozi" in sub_style:
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,"
            f"-1,0,0,0,100,100,0,0,1,10,3,2,20,20,{margin_v},1"
        )
    elif "MrBeast" in sub_style:
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00110022,&HA0000088,"
            f"-1,-1,0,0,105,100,0,0,1,8,4,2,20,20,{margin_v},1"
        )
    elif "Ali Abdaal" in sub_style:
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00F8FAFC,&H00F8FAFC,&H001E293B,&H40000000,"
            f"0,0,0,0,100,100,1,0,1,2,1,2,20,20,{margin_v},1"
        )
    elif "Submagic Pill" in sub_style or "TikTok Karaoke" in sub_style:
        styles_str = (
            f"Style: MaskStyle,{font_name},{font_size},"
            f"&HFF000000,&HFF000000,&HA0000000,&HA0000000,"
            f"-1,0,0,0,100,100,0,0,3,10,0,2,20,20,{margin_v},1\n"
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
            f"-1,0,0,0,100,100,0,0,1,4,1,2,20,20,{margin_v},1"
        )
    elif "YouTube Vlog" in sub_style:
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,"
            f"-1,0,0,0,100,100,0,0,1,6,2,2,20,20,{margin_v},1"
        )
    elif "Cyberpunk" in sub_style:
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00550055,&H80FF00FF,"
            f"-1,0,0,0,100,100,0,0,1,6,4,2,20,20,{margin_v},1"
        )
    else:
        # Netflix Documentary
        styles_str = (
            f"Style: TextStyle,{font_name},{font_size},"
            f"&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,"
            f"0,0,0,0,100,100,0,0,1,3,1,2,20,20,{margin_v},1"
        )

    # Thêm Ghost Styles nếu kích hoạt Chromatic 3D Glitch
    if animation_mode == "chromatic_glitch":
        styles_str += (
            f"\nStyle: GhostCyan,{font_name},{font_size},"
            f"&H80FFFF00,&H80FFFF00,&H00000000,&H00000000,"
            f"-1,0,0,0,100,100,0,0,1,0,0,2,17,23,{margin_v+2},1"
            f"\nStyle: GhostMagenta,{font_name},{font_size},"
            f"&H80FF00FF,&H80FF00FF,&H00000000,&H00000000,"
            f"-1,0,0,0,100,100,0,0,1,0,0,2,23,17,{max(0, margin_v-2)},1"
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
    
    # 2. Xử lý chunks phụ đề
    if pre_chunked_data:
        chunks = pre_chunked_data
    else:
        whisper_words = extract_flat_words_from_transcript(transcript_json)
        
        if correct_text and correct_text.strip():
            words_to_chunk = align_user_script_to_audio(correct_text, whisper_words, audio_duration=audio_duration)
        else:
            words_to_chunk = whisper_words
            
        offset_sec = sub_offset_ms / 1000.0
        for w in words_to_chunk:
            w['start'] = max(0.0, w['start'] + offset_sec)
            w['end'] = max(0.0, w['end'] + offset_sec)
            
        chunks = create_smart_rhythm_chunks(words_to_chunk, max_words=max_words_per_chunk)

    # 3. Xuất các dòng sự kiện Dialogue
    for chunk in chunks:
        if not chunk: 
            continue
        chunk_start = chunk[0]['start']
        chunk_end = chunk[-1]['end']
        
        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)
        
        # Xử lý định dạng chữ & phát hiện emphasis *từ*
        formatted_words = []
        word_emph_flags = []
        for w in chunk:
            raw_w = w['word'].replace('\n', '')
            clean_w, is_emph = clean_and_check_emphasis(raw_w)
            is_emph = is_emph or w.get('is_emphasis', False)
            word_emph_flags.append(is_emph)
            formatted_words.append(clean_w.upper() if text_transform == "uppercase" else clean_w)
            
        full_text = ' '.join(formatted_words)
        
        # Layer 0: Mask background box (Submagic Pill Badge)
        if "Submagic Pill" in sub_style or "TikTok Karaoke" in sub_style:
            ass_content += f"Dialogue: 0,{start_str},{end_str},MaskStyle,,0,0,0,,{{\\alpha&HFF&}}{full_text}\n"
            
        # Layer 0: Chromatic Glitch Cyan & Magenta Ghost Layers
        if animation_mode == "chromatic_glitch":
            ass_content += f"Dialogue: 0,{start_str},{end_str},GhostCyan,,0,0,0,,{full_text}\n"
            ass_content += f"Dialogue: 0,{start_str},{end_str},GhostMagenta,,0,0,0,,{full_text}\n"

        # Netflix Cinematic: Hiển thị nguyên câu tĩnh
        if "Netflix" in sub_style:
            ass_content += f"Dialogue: 1,{start_str},{end_str},TextStyle,,0,0,0,,{full_text}\n"
            continue
        
        # Layer 1: Karaoke word highlight tracking kèm Kinetic Motion FX
        last_time = chunk_start
        for i, target_word in enumerate(chunk):
            w_start = max(target_word['start'], last_time)
            
            if i < len(chunk) - 1:
                w_end = min(target_word['end'], chunk[i+1]['start'])
            else:
                w_end = target_word['end']
                
            w_end = max(w_start + 0.01, w_end)
            
            # Khoảng nghỉ trước từ: in câu trung tính
            if w_start > last_time + 0.01:
                gap_start = format_ass_time(last_time)
                gap_end = format_ass_time(w_start)
                ass_content += f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{full_text}\n"
                
            # Tạo kinetic animation tags cho từ đang active
            is_emph = word_emph_flags[i]
            target_color, anim_tag, reset_tag = get_kinetic_motion_tags(
                animation_mode, 
                is_emph, 
                highlight_color, 
                emphasis_color
            )
            
            word_start_str = format_ass_time(w_start)
            word_end_str = format_ass_time(w_end)
            
            parts = []
            for j, w_text in enumerate(formatted_words):
                if j == i:
                    parts.append(f"{{\\c{target_color}&{anim_tag}}}{w_text}{{\\c&H00FFFFFF&{reset_tag}}}")
                else:
                    parts.append(w_text)
            line_text = ' '.join(parts)
            ass_content += f"Dialogue: 1,{word_start_str},{word_end_str},TextStyle,,0,0,0,,{line_text}\n"
            
            last_time = w_end
            
        # Khoảng nghỉ cuối câu
        if chunk_end > last_time + 0.01:
            gap_start = format_ass_time(last_time)
            gap_end = format_ass_time(chunk_end)
            ass_content += f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{full_text}\n"
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
        
    return output_path
