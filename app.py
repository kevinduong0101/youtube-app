import streamlit as st
import tempfile
import os
import shutil
from fontTools.ttLib import TTFont

from core.media_utils import (
    get_audio_duration, 
    get_video_dimensions,
    extract_video_audio, 
    generate_preview_frame,
    process_video_subtitles_only, 
    process_video_with_audio_replace
)
from core.subtitle_engine import (
    transcribe_audio, 
    align_user_script_to_audio,
    create_smart_rhythm_chunks,
    extract_flat_words_from_transcript,
    generate_ass_subtitle
)

# 1. Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="AutoSub Studio Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Design System Tokens & CSS Glassmorphism Studio
st.markdown("""
<style>
/* Nền tối sâu & typography */
.stApp {
    background-color: #0b0e14;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}

/* Ẩn bớt khoảng trắng mặc định phía trên */
.block-container {
    padding-top: 1.8rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Header thương hiệu */
.brand-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background: linear-gradient(135deg, rgba(22, 27, 34, 0.95), rgba(13, 17, 23, 0.95));
    border: 1px solid #30363d;
    border-radius: 14px;
    margin-bottom: 24px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.brand-title {
    font-size: 1.45rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60a5fa, #a855f7, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: flex;
    align-items: center;
    gap: 10px;
}
.brand-badge {
    background: #1f2937;
    border: 1px solid #374151;
    color: #9ca3af;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
}

/* Card container chuẩn studio */
.studio-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}
.studio-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f0f6fc;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Stat pill */
.stat-pill {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #58a6ff;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-right: 8px;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background-color: #161b22;
    padding: 6px;
    border-radius: 12px;
    border: 1px solid #30363d;
}
.stTabs [data-baseweb="tab"] {
    height: 42px;
    border-radius: 8px;
    color: #8b949e;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0 18px;
}
.stTabs [aria-selected="true"] {
    background-color: #21262d !important;
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
}

/* Nút bấm CTA lớn */
div.stButton > button:first-child[type="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    padding: 12px 24px !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.35) !important;
    transition: all 0.2s ease !important;
}
div.stButton > button:first-child[type="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
}

/* Khung mô phỏng Smartphone Studio Mockup */
.mockup-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 15px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 16px;
}
.mockup-phone {
    width: 210px;
    height: 380px;
    background: #000000;
    border: 3.5px solid #484f58;
    border-radius: 32px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 16px 36px rgba(0, 0, 0, 0.6);
}
.mockup-notch {
    position: absolute;
    top: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 60px;
    height: 12px;
    background: #161b22;
    border-radius: 10px;
    z-index: 10;
}
.mockup-guide {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: #30363d;
    pointer-events: none;
    letter-spacing: 1px;
}
</style>

<div class="brand-bar">
    <div class="brand-title">
        <span>🎬 AutoSub Studio Pro</span>
    </div>
    <div class="brand-badge">✨ Senior Studio Engine • v2.5</div>
</div>
""", unsafe_allow_html=True)

# 3. Khởi tạo Session State
if "transcribed_video_name" not in st.session_state:
    st.session_state.transcribed_video_name = None
if "transcript_raw" not in st.session_state:
    st.session_state.transcript_raw = None
if "chunks_data" not in st.session_state:
    st.session_state.chunks_data = None
if "rendered_video_bytes" not in st.session_state:
    st.session_state.rendered_video_bytes = None

def helper_update_chunk_text(chunk, new_text):
    words_raw = new_text.strip().split()
    if not words_raw:
        return chunk
    start_t = chunk[0]['start']
    end_t = chunk[-1]['end']
    total_dur = max(0.1, end_t - start_t)
    dur_per_word = total_dur / len(words_raw)
    
    new_chunk = []
    for i, w in enumerate(words_raw):
        new_chunk.append({
            "word": w,
            "start": start_t + i * dur_per_word,
            "end": start_t + (i + 1) * dur_per_word
        })
    return new_chunk

# 4. Kiến trúc Studio Tabbed Workflow
tab_ingest, tab_transcript, tab_style, tab_export = st.tabs([
    "📥 1. Nhập Media & Kịch Bản",
    "📝 2. Soát Lời Thoại",
    "🎨 3. Studio Styling & Mockup",
    "🚀 4. Xuất Video Hoàn Chỉnh"
])

# ==============================================================================
# TAB 1: NHẬP MEDIA & ĐỒNG BỘ KỊCH BẢN
# ==============================================================================
with tab_ingest:
    col_ingest_left, col_ingest_right = st.columns([1.2, 1], gap="large")
    
    with col_ingest_left:
        st.markdown("""
        <div class="studio-card-title">📹 Tải Lên Video & Audio Gốc</div>
        """, unsafe_allow_html=True)
        video_file = st.file_uploader(
            "Video nguồn (.mp4, .mov)", 
            type=["mp4", "mov"],
            help="Hệ thống sẽ giữ nguyên vẹn 100% âm thanh của video gốc này khi xuất."
        )
        audio_file = st.file_uploader(
            "Âm thanh thay thế (.mp3, .wav) [Tùy chọn]", 
            type=["mp3", "wav"],
            help="Chỉ tải nếu bạn muốn thay đổi âm thanh gốc bằng file lồng tiếng/nhạc riêng."
        )
        
    with col_ingest_right:
        st.markdown("""
        <div class="studio-card-title">⚙️ Phương Thức Đồng Bộ</div>
        """, unsafe_allow_html=True)
        sync_mode = st.radio(
            "Chế độ tạo phụ đề:",
            options=[
                "🤖 AI Whisper Bóc Băng & Căn Nhịp (Khuyên dùng)",
                "⚡ Khớp Nhanh Kịch Bản (Không cần AI - <1s)"
            ],
            index=0,
            label_visibility="collapsed"
        )
        
        whisper_model_choice = st.selectbox(
            "Mô hình nhận diện giọng nói (Whisper)",
            options=["base", "small"],
            index=0,
            disabled=("Không cần AI" in sync_mode),
            help="Base: Nhanh nhẹ. Small: Nhận diện tiếng Việt và từ khó chính xác hơn."
        )
        
        st.caption("💡 Mẹo: Dán kịch bản vào bên dưới để AI tự động sửa chuẩn 100% từng chữ và dấu câu theo lời thoại của bạn.")

    st.markdown("---")
    st.markdown("""
    <div class="studio-card-title">📜 Kịch Bản / Lời Thoại Chính Xác (Khuyên dùng để chuẩn 100% từng từ)</div>
    """, unsafe_allow_html=True)
    custom_script = st.text_area(
        "Dán toàn bộ lời thoại đã thu âm vào đây:",
        placeholder="Dán kịch bản có dấu của bạn vào đây... AI sẽ tự động so khớp để giữ đúng từng chữ của bạn mà không lo Whisper nghe nhầm!",
        height=120,
        label_visibility="collapsed"
    )

    btn_transcribe = st.button("⚡ BẮT ĐẦU ĐỒNG BỘ PHỤ ĐỀ", use_container_width=True, type="primary")

    if video_file and st.session_state.transcribed_video_name != video_file.name:
        st.session_state.transcribed_video_name = None
        st.session_state.transcript_raw = None
        st.session_state.chunks_data = None
        st.session_state.rendered_video_bytes = None

    if btn_transcribe:
        if not video_file:
            st.error("⚠️ Vui lòng tải lên file Video trước!")
        else:
            temp_dir_transcribe = tempfile.mkdtemp()
            try:
                temp_vid_path = os.path.join(temp_dir_transcribe, "temp_video.mp4")
                with open(temp_vid_path, "wb") as f:
                    f.write(video_file.getvalue())
                    
                if audio_file:
                    temp_audio_path = os.path.join(temp_dir_transcribe, "temp_audio.mp3")
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_file.getvalue())
                else:
                    temp_audio_path = os.path.join(temp_dir_transcribe, "extracted_audio.mp3")
                    extract_video_audio(temp_vid_path, temp_audio_path)
                    
                audio_dur = get_audio_duration(temp_audio_path)
                
                if "Không cần AI" in sync_mode:
                    if not custom_script or not custom_script.strip():
                        st.warning("⚠️ Chế độ không dùng AI yêu cầu bạn phải dán Kịch bản vào ô bên trên!")
                    else:
                        aligned_words = align_user_script_to_audio(custom_script, [], audio_duration=audio_dur)
                        smart_chunks = create_smart_rhythm_chunks(aligned_words, max_words=3)
                        st.session_state.transcribed_video_name = video_file.name
                        st.session_state.chunks_data = smart_chunks
                        st.success(f"⚡ Đã khớp kịch bản thành công trong 0.1s! Tạo ra {len(smart_chunks)} phân đoạn.")
                else:
                    with st.spinner("⏳ Đang phân tích âm thanh và căn nhịp phụ đề..."):
                        transcript = transcribe_audio(temp_audio_path, model_name=whisper_model_choice, language="vi")
                        flat_words = extract_flat_words_from_transcript(transcript)
                        
                        if custom_script and custom_script.strip():
                            aligned_words = align_user_script_to_audio(custom_script, flat_words, audio_duration=audio_dur)
                            smart_chunks = create_smart_rhythm_chunks(aligned_words, max_words=3)
                            msg = f"🎉 Đã khớp kịch bản với giọng nói chuẩn 100%! Tạo ra {len(smart_chunks)} phân đoạn nhịp thở."
                        else:
                            smart_chunks = create_smart_rhythm_chunks(flat_words, max_words=3)
                            msg = f"🎉 Bóc băng thành công! AI đã phân đoạn thành {len(smart_chunks)} cụm nhịp thở tự nhiên."
                            
                        st.session_state.transcribed_video_name = video_file.name
                        st.session_state.transcript_raw = transcript
                        st.session_state.chunks_data = smart_chunks
                        st.success(msg)
            except Exception as e:
                st.error(f"Lỗi khi xử lý: {e}")
            finally:
                shutil.rmtree(temp_dir_transcribe, ignore_errors=True)

# ==============================================================================
# TAB 2: SOÁT & CHỈNH SỬA PHỤ ĐỀ
# ==============================================================================
with tab_transcript:
    if not st.session_state.chunks_data:
        st.info("ℹ️ Chưa có dữ liệu phụ đề. Vui lòng tải video và bấm 'Bắt Đầu Đồng Bộ Phụ Đề' ở Tab 1.")
    else:
        chunks = st.session_state.chunks_data
        total_chunks = len(chunks)
        total_words = sum(len(c) for c in chunks)
        dur = chunks[-1][-1]['end'] if chunks else 0
        wpm = int((total_words / (dur / 60))) if dur > 0 else 0
        
        st.markdown(f"""
        <div style="margin-bottom: 16px;">
            <span class="stat-pill">📊 {total_chunks} phân đoạn</span>
            <span class="stat-pill">⏱️ Thời lượng: {dur:.1f}s</span>
            <span class="stat-pill">⚡ Nhịp đọc: {wpm} wpm</span>
        </div>
        """, unsafe_allow_html=True)

        col_search, col_info = st.columns([1.5, 1])
        with col_search:
            search_query = st.text_input("🔍 Tìm kiếm cụm từ trong phụ đề:", placeholder="Gõ từ cần tìm...")
        with col_info:
            st.caption("Mẹo: Sửa chữ tại đây sẽ cập nhật trực tiếp lên video mà không làm lệch nhịp âm thanh gốc.")

        st.markdown("---")
        
        # Danh sách thẻ chỉnh sửa câu gọn gàng
        for c_idx, chunk in enumerate(chunks):
            c_text = " ".join(w['word'] for w in chunk)
            c_start = chunk[0]['start']
            c_end = chunk[-1]['end']
            
            if search_query and search_query.lower() not in c_text.lower():
                continue
                
            c_col_time, c_col_input = st.columns([1, 4])
            with c_col_time:
                st.markdown(f"""
                <div style="background: #21262d; border-radius: 6px; padding: 6px 10px; font-size: 0.82rem; color: #58a6ff; font-weight: 600; text-align: center; margin-top: 4px;">
                    #{c_idx+1} &nbsp; {c_start:.1f}s ➔ {c_end:.1f}s
                </div>
                """, unsafe_allow_html=True)
            with c_col_input:
                new_text = st.text_input(
                    label=f"chunk_{c_idx}",
                    value=c_text,
                    key=f"chunk_edit_{c_idx}",
                    label_visibility="collapsed"
                )
                if new_text != c_text:
                    st.session_state.chunks_data[c_idx] = helper_update_chunk_text(chunk, new_text)

# ==============================================================================
# TAB 3: STUDIO STYLING & LIVE MOCKUP
# ==============================================================================
with tab_style:
    col_style_left, col_style_right = st.columns([1.3, 1], gap="large")
    
    with col_style_left:
        st.markdown("""
        <div class="studio-card-title">🎨 Studio Presets Độc Quyền</div>
        """, unsafe_allow_html=True)
        
        sub_style = st.selectbox(
            "Phong cách phụ đề:", 
            [
                "🔥 Alex Hormozi (Chữ In Hoa, Viền Đen Siêu Dày, Pop Nảy Chữ)",
                "✨ YouTube Vlog Pro (Viền Nét Đậm, Shadow 3D Mềm Mại)",
                "🏷️ Submagic Pill Badge (Hộp Bo Tròn Che Nền Sang Trọng)",
                "⚡ Cyberpunk Neon Glow (Viền Dạ Quang Phát Sáng Điện Tử)",
                "🍿 Netflix Cinematic (Thanh Lịch Tối Giản Điện Ảnh)"
            ], 
            index=0,
            label_visibility="collapsed",
            help="Chọn phong cách phù hợp với định dạng kênh của bạn."
        )

        with st.expander("🔤 Typography & Điểm Nhấn Màu Sắc", expanded=True):
            col_typo_1, col_typo_2 = st.columns(2)
            with col_typo_1:
                font_file = st.file_uploader("Font chữ tuỳ chỉnh (.ttf, .otf)", type=["ttf", "otf"])
                font_size = st.slider("Cỡ chữ (Font Size)", min_value=25, max_value=130, value=75, step=5)
            with col_typo_2:
                highlight_colors = {
                    "Vàng Chanh Hormozi (#FFE600)": ("#FFE600", "&H0000E6FF"),
                    "Xanh Lá Neon (#00FF66)": ("#00FF66", "&H0066FF00"),
                    "Xanh Cyan Công Nghệ (#00FFFF)": ("#00FFFF", "&H00FFFF00"),
                    "Hồng Neon TikTok (#FF007F)": ("#FF007F", "&H007F00FF"),
                    "Đỏ Cam Rực Rỡ (#FF5500)": ("#FF5500", "&H000055FF"),
                    "Trắng Tinh Khôi (#FFFFFF)": ("#FFFFFF", "&H00FFFFFF")
                }
                selected_color_name = st.selectbox("Màu Active Karaoke:", options=list(highlight_colors.keys()), index=0)
                active_hex_css, highlight_color_hex = highlight_colors[selected_color_name]
                
                text_transform_choice = st.checkbox(
                    "🔤 VIẾT HOA TOÀN BỘ (Shorts/TikTok)", 
                    value=True,
                    help="Tự động viết hoa toàn bộ chữ để tăng tỷ lệ đọc khi lướt nhanh."
                )
                text_transform = "uppercase" if text_transform_choice else "original"

        with st.expander("⚙️ Chuyển Động & Căn Chỉnh Vị Trí", expanded=True):
            col_anim_1, col_anim_2 = st.columns(2)
            with col_anim_1:
                anim_choice = st.selectbox(
                    "Hiệu ứng nảy chữ:",
                    options=[
                        "Nảy chữ phóng to (Pop 115% - Khuyên dùng)",
                        "Nảy chữ mạnh mẽ (Pop 125%)",
                        "Chỉ đổi màu tĩnh (Không nảy)"
                    ],
                    index=0
                )
                if "125%" in anim_choice:
                    animation_mode = "pop_strong"
                elif "115%" in anim_choice:
                    animation_mode = "pop"
                else:
                    animation_mode = "none"

                max_words_per_chunk = st.slider("Mật độ từ mỗi dòng", min_value=1, max_value=6, value=3, step=1)

            with col_anim_2:
                margin_v = st.slider("Vị trí từ dưới lên (Margin V)", min_value=20, max_value=800, value=200, step=10)
                sub_offset_ms = st.slider("Độ trễ nhịp (ms) [Âm là sớm hơn]", min_value=-500, max_value=500, value=0, step=25)

        aspect_choice = st.selectbox(
            "Tỷ lệ khung hình xuất ra:",
            options=["Giữ nguyên tỷ lệ gốc (Khuyên dùng)", "Ép chuẩn dọc 9:16 (Shorts/TikTok/Reels)"],
            index=0
        )
        aspect_mode = "vertical_9_16" if "9:16" in aspect_choice else "original"

    with col_style_right:
        st.markdown("""
        <div class="studio-card-title">📱 Mô Phỏng Khung Hình Trực Quan</div>
        """, unsafe_allow_html=True)
        
        # Tính toán vị trí tương đối
        bottom_pct = max(5, min(80, int((margin_v / 1920) * 100 * 2.2)))
        sample_title = "HỌC LẬP TRÌNH" if text_transform == "uppercase" else "Học lập trình"
        sample_words = sample_title.split()
        first_word = sample_words[0] if sample_words else "HỌC"
        rest_words = " ".join(sample_words[1:]) if len(sample_words) > 1 else "LẬP TRÌNH"
        
        # Mô phỏng style bằng CSS
        style_box_css = "background: rgba(0,0,0,0.7); border-radius: 6px; padding: 5px 8px;"
        if "Submagic" in sub_style:
            style_box_css = "background: rgba(0, 0, 0, 0.88); border-radius: 14px; padding: 6px 12px; border: 1.5px solid #ffffff;"
        elif "Cyberpunk" in sub_style:
            style_box_css = "background: rgba(10, 10, 25, 0.8); border-radius: 4px; padding: 5px 8px; box-shadow: 0 0 10px #00ffff;"
        elif "Netflix" in sub_style:
            style_box_css = "background: transparent; padding: 4px 6px;"

        st.markdown(f"""
        <div class="mockup-wrapper">
            <div class="mockup-phone">
                <div class="mockup-notch"></div>
                <div class="mockup-guide">KHUNG 9:16 MOBILE</div>
                <div style="position: absolute; bottom: {bottom_pct}%; left: 8%; right: 8%; text-align: center; {style_box_css}">
                    <span style="color: {active_hex_css}; font-weight: 900; font-size: 13px; text-shadow: 0 2px 4px rgba(0,0,0,0.8);">{first_word}</span>
                    <span style="color: #FFFFFF; font-weight: 800; font-size: 12px; text-shadow: 0 2px 4px rgba(0,0,0,0.8); margin-left: 4px;">{rest_words}</span>
                </div>
            </div>
            <div style="font-size: 0.78rem; color: #8b949e; margin-top: 10px; text-align: center;">
                Kéo thanh <b>Margin V</b> để canh vị trí không che mặt và tránh thanh công cụ TikTok.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        btn_preview_frame = st.button("👁️ XEM TRƯỚC 1 FRAME THỰC TẾ (<1s)", use_container_width=True)

        if btn_preview_frame:
            if not video_file:
                st.warning("⚠️ Vui lòng tải lên video ở Tab 1 trước!")
            else:
                with st.spinner("Đang kết xuất khung hình mẫu bằng FFmpeg..."):
                    temp_dir_prev = tempfile.mkdtemp()
                    try:
                        prev_vid_path = os.path.join(temp_dir_prev, "prev_vid.mp4")
                        with open(prev_vid_path, "wb") as f:
                            f.write(video_file.getvalue())
                            
                        prev_font_dir = None
                        prev_font_name = "UVN Ban Tay"
                        if font_file:
                            prev_font_dir = os.path.join(temp_dir_prev, "fonts")
                            os.makedirs(prev_font_dir, exist_ok=True)
                            prev_font_path = os.path.join(prev_font_dir, font_file.name)
                            with open(prev_font_path, "wb") as f:
                                f.write(font_file.getvalue())
                            try:
                                font_obj = TTFont(prev_font_path)
                                for record in font_obj['name'].names:
                                    if record.nameID == 1:
                                        prev_font_name = record.toUnicode()
                                        break
                            except Exception:
                                prev_font_name = os.path.splitext(font_file.name)[0]
                        else:
                            if os.path.exists("/Users/kevinduong/Downloads/font"):
                                prev_font_dir = "/Users/kevinduong/Downloads/font"
                                
                        vid_w, vid_h = get_video_dimensions(prev_vid_path)
                        if aspect_mode == "vertical_9_16":
                            vid_w, vid_h = 1080, 1920
                            
                        prev_sub_path = os.path.join(temp_dir_prev, "prev.ass")
                        
                        if st.session_state.chunks_data:
                            preview_chunks = st.session_state.chunks_data
                            seek_t = preview_chunks[0][0]['start'] + 0.2 if preview_chunks else 1.5
                        else:
                            preview_chunks = [[
                                {"word": "XEM", "start": 1.0, "end": 1.4},
                                {"word": "TRƯỚC", "start": 1.4, "end": 1.8},
                                {"word": "PHỤ", "start": 1.8, "end": 2.2},
                                {"word": "ĐỀ", "start": 2.2, "end": 2.6}
                            ]]
                            seek_t = 1.6
                            
                        generate_ass_subtitle(
                            transcript_json={},
                            output_path=prev_sub_path,
                            video_width=vid_w,
                            video_height=vid_h,
                            margin_v=margin_v,
                            highlight_color=highlight_color_hex,
                            font_name=prev_font_name,
                            font_size=font_size,
                            sub_style=sub_style,
                            sub_offset_ms=sub_offset_ms,
                            animation_mode=animation_mode,
                            text_transform=text_transform,
                            max_words_per_chunk=max_words_per_chunk,
                            pre_chunked_data=preview_chunks
                        )
                        
                        prev_img_path = os.path.join(temp_dir_prev, "preview.jpg")
                        generate_preview_frame(
                            video_in=prev_vid_path,
                            subtitle_ass=prev_sub_path,
                            timestamp_sec=seek_t,
                            output_img_path=prev_img_path,
                            font_dir=prev_font_dir,
                            aspect_mode=aspect_mode
                        )
                        
                        st.image(prev_img_path, caption=f"Frame Thực Tế (Font: {prev_font_name}, Size: {font_size})", use_container_width=True)
                    except Exception as e:
                        st.error(f"Không thể tạo ảnh xem trước: {e}")
                    finally:
                        shutil.rmtree(temp_dir_prev, ignore_errors=True)

# ==============================================================================
# TAB 4: XUẤT VIDEO HOÀN CHỈNH
# ==============================================================================
with tab_export:
    st.markdown("""
    <div class="studio-card-title">🚀 Trung Tâm Xuất Bản Video</div>
    """, unsafe_allow_html=True)
    
    col_exp_info, col_exp_action = st.columns([1.2, 1], gap="large")
    with col_exp_info:
        st.markdown(f"""
        <div class="studio-card" style="margin-bottom: 0;">
            <div style="font-weight: 700; color: #58a6ff; margin-bottom: 8px;">📋 Tóm Tắt Thông Số Xuất Bản:</div>
            <div style="font-size: 0.88rem; line-height: 1.8; color: #c9d1d9;">
                • <b>Style:</b> {sub_style.split('(')[0]}<br/>
                • <b>Hiệu ứng nảy:</b> {anim_choice}<br/>
                • <b>Định dạng chữ:</b> {'Chữ In Hoa' if text_transform == 'uppercase' else 'Nguyên Bản'}<br/>
                • <b>Tỷ lệ xuất:</b> {'9:16 Vertical' if aspect_mode == 'vertical_9_16' else 'Giữ nguyên gốc'}<br/>
                • <b>Âm thanh:</b> Giữ nguyên 100% Bitrate & Codec gốc (-c:a copy)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_exp_action:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        btn_render = st.button("⚡ BẮT ĐẦU XUẤT VIDEO", use_container_width=True, type="primary")

    if btn_render:
        if not video_file:
            st.error("⚠️ Vui lòng tải lên file Video gốc ở Tab 1!")
        else:
            temp_dir = tempfile.mkdtemp()
            try:
                progress_bar = st.progress(0, text="Chuẩn bị dữ liệu đầu vào...")
                video_path = os.path.join(temp_dir, "input_video.mp4")
                output_video_path = os.path.join(temp_dir, "output_video.mp4")
                subtitle_path = os.path.join(temp_dir, "subtitles.ass")
                
                with open(video_path, "wb") as f:
                    f.write(video_file.getvalue())
                    
                audio_path = None
                if audio_file:
                    audio_path = os.path.join(temp_dir, "input_audio.mp3")
                    with open(audio_path, "wb") as f:
                        f.write(audio_file.getvalue())
                        
                font_dir = None
                font_name = "UVN Ban Tay"
                if font_file:
                    font_dir = os.path.join(temp_dir, "fonts")
                    os.makedirs(font_dir, exist_ok=True)
                    font_path = os.path.join(font_dir, font_file.name)
                    with open(font_path, "wb") as f:
                        f.write(font_file.getvalue())
                    try:
                        font_obj = TTFont(font_path)
                        for record in font_obj['name'].names:
                            if record.nameID == 1:
                                font_name = record.toUnicode()
                                break
                    except Exception:
                        font_name = os.path.splitext(font_file.name)[0]
                else:
                    if os.path.exists("/Users/kevinduong/Downloads/font"):
                        font_dir = "/Users/kevinduong/Downloads/font"

                progress_bar.progress(25, text="Phân tích nhịp phụ đề và đồng bộ lời thoại...")
                
                if st.session_state.chunks_data and st.session_state.transcribed_video_name == video_file.name:
                    active_chunks = st.session_state.chunks_data
                else:
                    target_audio_for_transcribe = audio_path
                    if not target_audio_for_transcribe:
                        extracted_path = os.path.join(temp_dir, "extracted_audio.mp3")
                        extract_video_audio(video_path, extracted_path)
                        target_audio_for_transcribe = extracted_path
                    audio_dur = get_audio_duration(target_audio_for_transcribe)
                    if "Không cần AI" in sync_mode and custom_script and custom_script.strip():
                        aligned_words = align_user_script_to_audio(custom_script, [], audio_duration=audio_dur)
                    else:
                        transcript = transcribe_audio(target_audio_for_transcribe, model_name=whisper_model_choice, language="vi")
                        flat_words = extract_flat_words_from_transcript(transcript)
                        if custom_script and custom_script.strip():
                            aligned_words = align_user_script_to_audio(custom_script, flat_words, audio_duration=audio_dur)
                        else:
                            aligned_words = flat_words
                            
                    active_chunks = create_smart_rhythm_chunks(aligned_words, max_words=max_words_per_chunk)
                    st.session_state.chunks_data = active_chunks
                    st.session_state.transcribed_video_name = video_file.name

                progress_bar.progress(55, text="Biên soạn tập tin phụ đề Studio ASS...")
                vid_w, vid_h = get_video_dimensions(video_path)
                if aspect_mode == "vertical_9_16":
                    vid_w, vid_h = 1080, 1920
                    
                generate_ass_subtitle(
                    transcript_json={},
                    output_path=subtitle_path,
                    video_width=vid_w,
                    video_height=vid_h,
                    margin_v=margin_v,
                    highlight_color=highlight_color_hex,
                    font_name=font_name,
                    font_size=font_size,
                    sub_style=sub_style,
                    sub_offset_ms=sub_offset_ms,
                    animation_mode=animation_mode,
                    text_transform=text_transform,
                    max_words_per_chunk=max_words_per_chunk,
                    pre_chunked_data=active_chunks
                )

                progress_bar.progress(75, text="Render FFmpeg (Bọc phụ đề & Passthrough âm thanh gốc)...")
                if audio_path:
                    process_video_with_audio_replace(
                        video_in=video_path,
                        audio_in=audio_path,
                        subtitle_ass=subtitle_path,
                        output_path=output_video_path,
                        font_dir=font_dir,
                        aspect_mode=aspect_mode,
                        enhance_quality=False
                    )
                else:
                    process_video_subtitles_only(
                        video_in=video_path,
                        subtitle_ass=subtitle_path,
                        output_path=output_video_path,
                        font_dir=font_dir,
                        aspect_mode=aspect_mode,
                        enhance_quality=False
                    )

                progress_bar.progress(100, text="Hoàn tất!")
                st.success("🎉 Xuất Video thành công! Âm thanh giữ nguyên 100% chất lượng gốc.")
                
                with open(output_video_path, "rb") as f:
                    st.session_state.rendered_video_bytes = f.read()

            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong quá trình xuất: {e}")
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    # Hiển thị video sau render
    if st.session_state.rendered_video_bytes:
        st.markdown("---")
        st.markdown("""
        <div class="studio-card-title">🍿 Video Thành Phẩm</div>
        """, unsafe_allow_html=True)
        col_out_l, col_out_c, col_out_r = st.columns([1, 1.8, 1])
        with col_out_c:
            st.video(st.session_state.rendered_video_bytes)
            st.download_button(
                label="⬇️ TẢI XUỐNG VIDEO (.MP4)",
                data=st.session_state.rendered_video_bytes,
                file_name="autosub_studio_finished.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
