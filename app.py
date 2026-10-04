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
    create_smart_rhythm_chunks,
    extract_flat_words_from_transcript,
    generate_ass_subtitle
)

# Thiết lập giao diện trang
st.set_page_config(page_title="AutoSub Pro", page_icon="🎬", layout="wide")

# CSS giao diện hiện đại, tinh giản
st.markdown("""
<style>
.main-header {
    text-align: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #FF4B4B;
    margin-top: -25px;
    margin-bottom: 2px;
    font-weight: 800;
}
.sub-header {
    text-align: center;
    font-size: 1.05em;
    color: #888888;
    margin-bottom: 25px;
}
.badge-style {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: bold;
    margin-right: 5px;
}
</style>
<h1 class="main-header">🎬 AutoSub Pro</h1>
<p class="sub-header">Hệ Thống Typography Phụ Đề Chuẩn Studio & Hiệu Ứng Nảy Chữ Viral</p>
""", unsafe_allow_html=True)

# Khởi tạo session state lưu dữ liệu bóc băng
if "transcribed_video_name" not in st.session_state:
    st.session_state.transcribed_video_name = None
if "transcript_raw" not in st.session_state:
    st.session_state.transcript_raw = None
if "chunks_data" not in st.session_state:
    st.session_state.chunks_data = None

def helper_update_chunk_text(chunk, new_text):
    """
    Cập nhật lại văn bản của 1 chunk và phân bổ thời gian đều cho các từ mới.
    """
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

# ==========================================
# BƯỚC 1: TẢI LÊN MEDIA & CHỌN MÔ HÌNH AI
# ==========================================
st.markdown("### 📥 Bước 1: Tải Lên Video & Bóc Băng AI")

col_upload_1, col_upload_2 = st.columns([1.5, 1])
with col_upload_1:
    video_file = st.file_uploader("Tải lên File Video Gốc (.mp4, .mov) 🎬", type=["mp4", "mov"])
    audio_file = st.file_uploader("Tải lên File Âm Thanh Thay Thế (.mp3, .wav) 🎙️ [Tùy chọn]", type=["mp3", "wav"])

with col_upload_2:
    whisper_model_choice = st.selectbox(
        "Mô hình nhận diện giọng nói (Whisper Model)",
        options=["base", "small"],
        index=0,
        help="Base: Siêu nhanh (khuyên dùng). Small: Bóc băng tiếng Việt chuẩn xác hơn và ít lỗi chính tả hơn."
    )
    
    # Nút bắt đầu bóc băng
    btn_transcribe = st.button("🎙️ Bóc Băng & Phân Tích Phụ Đề", use_container_width=True, type="secondary")

# Reset transcript nếu người dùng chọn video mới
if video_file and st.session_state.transcribed_video_name != video_file.name:
    st.session_state.transcribed_video_name = None
    st.session_state.transcript_raw = None
    st.session_state.chunks_data = None

# Thực hiện bóc băng khi bấm nút
if btn_transcribe:
    if not video_file:
        st.error("⚠️ Vui lòng tải lên file Video trước khi bóc băng!")
    else:
        with st.spinner("⏳ Đang trích xuất âm thanh và bóc băng bằng Whisper AI..."):
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
                    
                transcript = transcribe_audio(temp_audio_path, model_name=whisper_model_choice, language="vi")
                flat_words = extract_flat_words_from_transcript(transcript)
                smart_chunks = create_smart_rhythm_chunks(flat_words, max_words=3)
                
                st.session_state.transcribed_video_name = video_file.name
                st.session_state.transcript_raw = transcript
                st.session_state.chunks_data = smart_chunks
                st.success(f"🎉 Bóc băng thành công! AI đã phân đoạn thành {len(smart_chunks)} cụm nhịp thở tự nhiên.")
            except Exception as e:
                st.error(f"Lỗi khi bóc băng: {e}")
            finally:
                shutil.rmtree(temp_dir_transcribe, ignore_errors=True)

# ==========================================
# BƯỚC 2: XEM & SỬA LỖI CHÍNH TẢ TRỰC TIẾP
# ==========================================
if st.session_state.chunks_data:
    st.markdown("---")
    st.markdown("### 📝 Bước 2: Soát & Chỉnh Sửa Phụ Đề Trực Tiếp")
    with st.expander(f"📋 Danh sách {len(st.session_state.chunks_data)} câu phụ đề (Bấm để xem và sửa nếu AI nghe nhầm từ)", expanded=False):
        st.caption("Mẹo: Sửa chữ tại đây sẽ cập nhật trực tiếp lên video thành phẩm mà không làm lệch nhịp âm thanh!")
        
        for c_idx, chunk in enumerate(st.session_state.chunks_data):
            c_text = " ".join(w['word'] for w in chunk)
            c_start = chunk[0]['start']
            c_end = chunk[-1]['end']
            
            new_text = st.text_input(
                f"[{c_start:.1f}s -> {c_end:.1f}s] Câu #{c_idx+1}:", 
                value=c_text, 
                key=f"chunk_edit_{c_idx}"
            )
            if new_text != c_text:
                st.session_state.chunks_data[c_idx] = helper_update_chunk_text(chunk, new_text)

# ==========================================
# BƯỚC 3: TÙY CHỈNH THẨM MỸ & STYLE VIRAL
# ==========================================
st.markdown("---")
st.markdown("### 🎨 Bước 3: Tùy Chỉnh Thẩm Mỹ & Style Phụ Đề Viral")

col_style_left, col_style_right = st.columns(2)

with col_style_left:
    sub_style = st.selectbox(
        "Style Phụ Đề (Studio Presets)", 
        [
            "🔥 Alex Hormozi (Chữ In Hoa, Viền Đen Siêu Dày, Pop Nảy Chữ)",
            "✨ YouTube Vlog Pro (Viền Nét Đậm, Shadow 3D Mềm Mại)",
            "🏷️ Submagic Pill Badge (Hộp Bo Tròn Che Nền Sang Trọng)",
            "⚡ Cyberpunk Neon Glow (Viền Dạ Quang Phát Sáng Điện Tử)",
            "🍿 Netflix Cinematic (Thanh Lịch Tối Giản Điện Ảnh)"
        ], 
        index=0,
        help="Chọn phong cách phù hợp với định dạng kênh của bạn: Alex Hormozi cho Shorts/Reels triệu view, Vlog Pro cho du lịch/lifestyle, Submagic cho podcast."
    )
    
    col_anim_1, col_anim_2 = st.columns(2)
    with col_anim_1:
        anim_choice = st.selectbox(
            "Hiệu ứng nảy chữ (Word Animation)",
            options=[
                "Nảy chữ phóng to (Pop 115% - Khuyên dùng)",
                "Nảy chữ mạnh mẽ (Pop 125%)",
                "Chỉ đổi màu tĩnh (Không nảy)"
            ],
            index=0,
            help="Tạo chuyển động thị giác giật mắt khi từng từ được cất lên, giữ chân người xem lâu hơn."
        )
        if "125%" in anim_choice:
            animation_mode = "pop_strong"
        elif "115%" in anim_choice:
            animation_mode = "pop"
        else:
            animation_mode = "none"
            
    with col_anim_2:
        text_transform_choice = st.checkbox(
            "🔤 VIẾT HOA TOÀN BỘ (Shorts/TikTok)", 
            value=True,
            help="Tự động viết hoa toàn bộ chữ, phong cách đặc trưng giúp video dễ đọc khi lướt nhanh."
        )
        text_transform = "uppercase" if text_transform_choice else "original"

    highlight_colors = {
        "Vàng Chanh Hormozi (#FFE600)": "&H0000E6FF",
        "Xanh Lá Neon (#00FF66)": "&H0066FF00",
        "Xanh Cyan Công Nghệ (#00FFFF)": "&H00FFFF00",
        "Hồng Neon TikTok (#FF007F)": "&H007F00FF",
        "Đỏ Cam Rực Rỡ (#FF5500)": "&H000055FF",
        "Trắng Tinh Khôi (#FFFFFF)": "&H00FFFFFF"
    }
    selected_color_name = st.selectbox("Màu chữ nổi bật (Active Karaoke Word)", options=list(highlight_colors.keys()), index=0)
    highlight_color_hex = highlight_colors[selected_color_name]
    
    max_words_per_chunk = st.slider(
        "Mật độ từ mỗi dòng (Words per line)", 
        min_value=1, max_value=6, value=3, step=1,
        help="1-2 từ: Siêu nhanh kích thích thị giác kiểu Alex Hormozi. 3-4 từ: Chuẩn TikTok. 5-6 từ: Kiểu Vlog/Podcast."
    )

with col_style_right:
    font_file = st.file_uploader("Tải lên Font chữ tuỳ chỉnh (.ttf, .otf) - Tùy chọn", type=["ttf", "otf"])
    font_size = st.slider("Kích cỡ chữ (Font Size)", min_value=25, max_value=130, value=75, step=5)
    margin_v = st.slider("Vị trí phụ đề (Pixel tính từ dưới màn hình lên)", min_value=20, max_value=800, value=200, step=10)
    
    col_sub_sub1, col_sub_sub2 = st.columns(2)
    with col_sub_sub1:
        sub_offset_ms = st.slider(
            "Độ trễ Phụ đề (ms) [Âm là sớm hơn]", 
            min_value=-500, max_value=500, value=0, step=25
        )
    with col_sub_sub2:
        aspect_choice = st.selectbox(
            "Tỷ lệ khung hình xuất ra",
            options=["Giữ nguyên tỷ lệ gốc (Khuyên dùng)", "Ép chuẩn dọc 9:16 (Shorts/TikTok/Reels)"],
            index=0
        )
        aspect_mode = "vertical_9_16" if "9:16" in aspect_choice else "original"

    # CSS Visualizer
    bottom_pct = (margin_v / 1920) * 100
    sample_text = "HỌC LẬP TRÌNH" if text_transform == "uppercase" else "Học lập trình"
    st.markdown(f"""
    <div style="display: flex; gap: 15px; align-items: center; margin-top: 10px;">
        <div style="width: 85px; height: 150px; background-color: #1e1e24; border-radius: 8px; position: relative; border: 2px solid #555; overflow: hidden; flex-shrink: 0;">
            <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; opacity: 0.2; font-size: 8px;">Màn hình</div>
            <div style="position: absolute; bottom: {bottom_pct}%; left: 5%; right: 5%; background: rgba(0,0,0,0.7); color: white; text-align: center; border-radius: 4px; font-size: 8px; padding: 3px; font-weight: bold;">
                <span style="color: #00E6FF; font-size: 9px;">{sample_text.split()[0]}</span> {' '.join(sample_text.split()[1:])}
            </div>
        </div>
        <div style="font-size: 12px; color: #aaa;">
            <b>Khung mô phỏng trực quan:</b><br/>
            Kéo thanh trượt vị trí để canh né thanh công cụ TikTok/Reels mà không che khuôn mặt.
        </div>
    </div>
    """, unsafe_allow_html=True)

# Nút Xem Trước Frame Tức Thì
btn_preview_frame = st.button("👁️ Xem Trước 1 Khung Hình (Instant Preview)", use_container_width=True)

if btn_preview_frame:
    if not video_file:
        st.warning("⚠️ Vui lòng tải lên video để xem trước khung hình!")
    else:
        with st.spinner("Đang kết xuất khung hình xem trước..."):
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
                
                col_prev_l, col_prev_c, col_prev_r = st.columns([1, 1.6, 1])
                with col_prev_c:
                    st.image(prev_img_path, caption=f"Khung hình mẫu (Font: {prev_font_name}, Size: {font_size}, Preset: {sub_style.split()[1]})", use_container_width=True)
            except Exception as e:
                st.error(f"Không thể tạo ảnh xem trước: {e}")
            finally:
                shutil.rmtree(temp_dir_prev, ignore_errors=True)

# ==========================================
# BƯỚC 4: XUẤT VIDEO HOÀN CHỈNH
# ==========================================
st.markdown("---")
st.markdown("### 🚀 Bước 4: Xuất Video Hoàn Chỉnh")

btn_render = st.button("⚡ XUẤT VIDEO HOÀN TẤT", use_container_width=True, type="primary")

if btn_render:
    if not video_file:
        st.error("⚠️ Vui lòng tải lên file Video gốc!")
    else:
        temp_dir = tempfile.mkdtemp()
        try:
            progress_bar = st.progress(0, text="Bước 1/4: Đang chuẩn bị dữ liệu...")
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

            progress_bar.progress(25, text="Bước 2/4: Đang bóc băng và đồng bộ nhịp phụ đề...")
            
            if st.session_state.chunks_data and st.session_state.transcribed_video_name == video_file.name:
                active_chunks = st.session_state.chunks_data
            else:
                target_audio_for_transcribe = audio_path
                if not target_audio_for_transcribe:
                    extracted_path = os.path.join(temp_dir, "extracted_audio.mp3")
                    extract_video_audio(video_path, extracted_path)
                    target_audio_for_transcribe = extracted_path
                    
                transcript = transcribe_audio(target_audio_for_transcribe, model_name=whisper_model_choice, language="vi")
                flat_words = extract_flat_words_from_transcript(transcript)
                active_chunks = create_smart_rhythm_chunks(flat_words, max_words=max_words_per_chunk)
                st.session_state.chunks_data = active_chunks
                st.session_state.transcribed_video_name = video_file.name

            progress_bar.progress(50, text="Bước 3/4: Đang tạo file phụ đề ASS...")
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

            progress_bar.progress(70, text="Bước 4/4: Đang xử lý Video và bọc phụ đề bằng FFmpeg...")
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
            
            st.markdown("### 🍿 Video Hoàn Chỉnh Của Bạn")
            col_l, col_c, col_r = st.columns([1, 1.6, 1])
            with col_c:
                with open(output_video_path, "rb") as f:
                    v_bytes = f.read()
                st.video(v_bytes)
                st.download_button(
                    label="⬇️ TẢI XUỐNG VIDEO (.MP4)",
                    data=v_bytes,
                    file_name="autosub_pro_finished.mp4",
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
