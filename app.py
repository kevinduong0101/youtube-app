import streamlit as st
import tempfile
import os
import shutil

from core.media_utils import get_audio_duration, process_video, extract_video_audio
from core.subtitle_engine import call_nvidia_whisper, generate_ass_subtitle

# Thiết lập giao diện trang
st.set_page_config(page_title="Công cụ Video Tự động hoá", page_icon="🎥", layout="wide")

st.title("🎥 Công Cụ Cắt Ghép Video & Tạo Phụ Đề Tự Động")
st.markdown("Cắt video, thay thế âm thanh tiếng Việt, tự động tạo phụ đề và hộp che phụ đề thông minh.")

# Cột giao diện
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Tải lên Media")
    video_file = st.file_uploader("Tải lên File Video Gốc (.mp4, .mov)", type=["mp4", "mov"])
    audio_file = st.file_uploader("Tải lên File Âm Thanh Tiếng Việt (.mp3, .wav) - [Không bắt buộc nếu Video đã có tiếng]", type=["mp3", "wav"])
    
    st.subheader("2. Tùy chỉnh Phụ Đề Nâng Cao")
    sub_style = st.selectbox("Style Phụ Đề", ["TikTok Karaoke", "YouTube Vlog", "Netflix Style"])
    sub_offset_ms = st.slider("Độ trễ Phụ đề (ms) - Kéo âm (-) để chữ hiện sớm hơn", min_value=-1000, max_value=1000, value=0, step=50)
    font_file = st.file_uploader("Tải lên Font chữ tuỳ chỉnh (.ttf, .otf) - Tùy chọn", type=["ttf", "otf"])
    font_size = st.slider("Kích cỡ chữ (Font Size)", min_value=20, max_value=150, value=75, step=5)
    margin_v = st.slider("Vị trí phụ đề (Từ dưới lên)", min_value=0, max_value=500, value=80, step=5)
    
    highlight_colors = {
        "Vàng Tiktok (Rực rỡ)": "&H0000FFFF",
        "Xanh lá (Nổi bật)": "&H0000FF00",
        "Trắng (Cổ điển)": "&H00FFFFFF",
        "Xanh Cyan (Công nghệ)": "&H00FFFF00"
    }
    selected_color_name = st.selectbox("Màu chữ nhấn mạnh (Karaoke)", options=list(highlight_colors.keys()))
    highlight_color_hex = highlight_colors[selected_color_name]
    
    st.subheader("2.1. Phụ Đề Chính Xác (Tùy chọn)")
    correct_text = st.text_area("Văn bản phụ đề", help="Dán phần dịch chính xác vào đây. Hệ thống sẽ tự động khớp văn bản này với âm thanh gốc thay vì dùng AI nhận dạng.")

with col2:
    st.subheader("3. Cấu hình Thời gian")
    auto_sync = st.checkbox("🤖 Tự động tìm vị trí khớp (Sử dụng AI phân tích kịch bản)", value=True)
    start_time_offset = st.number_input(
        "Thời điểm bắt đầu cắt thủ công (Giây)", 
        min_value=0.0, value=0.0, step=1.0, 
        disabled=auto_sync,
        help="Bỏ tick chọn 'Tự động tìm vị trí khớp' để nhập thời gian thủ công."
    )
    audio_delay_ms = st.slider(
        "Độ trễ âm thanh siêu nhỏ (milliseconds)", 
        min_value=-1000, max_value=1000, value=0, step=50,
        help="Sử dụng thanh này để tinh chỉnh âm thanh sớm hoặc trễ hơn (âm số là phát sớm hơn, dương là phát trễ hơn)."
    )
    # API key đã được nhúng sẵn cho sử dụng cá nhân
    api_key = "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"
    
    bgm_dir = "/Users/kevinduong/Downloads/Media/Audio"
    bgm_files = []
    if os.path.exists(bgm_dir):
        bgm_files = [f for f in os.listdir(bgm_dir) if f.lower().endswith('.mp3')]
        bgm_files.sort()
        
    st.subheader("3. Nhạc nền (BGM)")
    bg_options = ["Không sử dụng nhạc nền"] + bgm_files
    
    # We use session state to hold the selected BGM so the AI button can update it
    if "selected_bgm" not in st.session_state:
        st.session_state.selected_bgm = "Không sử dụng nhạc nền"
        
    selected_bgm = st.selectbox("Chọn file nhạc nền:", options=bg_options, index=bg_options.index(st.session_state.selected_bgm) if st.session_state.selected_bgm in bg_options else 0)
    st.session_state.selected_bgm = selected_bgm
    
    if selected_bgm != "Không sử dụng nhạc nền":
        st.audio(os.path.join(bgm_dir, selected_bgm))
        
    if st.button("🤖 AI Gợi Ý Nhạc Nền"):
        if not video_file and not audio_file:
            st.warning("Vui lòng tải lên Video hoặc Âm thanh trước để AI nghe và phân tích mood!")
        elif not bgm_files:
            st.warning("Không tìm thấy nhạc trong thư mục Downloads/Media/Audio")
        else:
            with st.spinner("AI đang nghe và phân tích..."):
                from core.subtitle_engine import call_nvidia_whisper, recommend_bgm
                temp_dir2 = tempfile.mkdtemp()
                temp_audio_path = os.path.join(temp_dir2, "temp_audio.mp3")
                
                if audio_file:
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_file.getvalue())
                else:
                    # Extract from video
                    temp_vid_path = os.path.join(temp_dir2, "temp_vid.mp4")
                    with open(temp_vid_path, "wb") as f:
                        f.write(video_file.getvalue())
                    extract_video_audio(temp_vid_path, temp_audio_path)

                
                # Transcribe briefly to get text
                aud_transcript = call_nvidia_whisper(temp_audio_path, api_key, language="vi")
                recommended = recommend_bgm(aud_transcript, bgm_files, api_key)
                
                if recommended:
                    st.session_state.selected_bgm = recommended
                    st.success(f"AI đề xuất nhạc: **{recommended}**. Đã tự động chọn!")
                    st.rerun()
                else:
                    st.warning("AI không thể gợi ý bài nào.")
                shutil.rmtree(temp_dir2, ignore_errors=True)
                
    st.markdown("---")

# Nút bắt đầu xử lý
if st.button("BẮT ĐẦU XỬ LÝ", use_container_width=True, type="primary"):
    if not video_file:
        st.error("Vui lòng tải ít nhất Video gốc!")
    else:
        temp_dir = tempfile.mkdtemp()
        
        try:
            with st.spinner("Đang lưu file tạm..."):
                video_path = os.path.join(temp_dir, "input_video.mp4")
                audio_path = os.path.join(temp_dir, "input_audio.mp3")
                output_video_path = os.path.join(temp_dir, "output_video.mp4")
                subtitle_path = os.path.join(temp_dir, "subtitles.ass")
                
                with open(video_path, "wb") as f:
                    f.write(video_file.read())
                    
                if audio_file:
                    with open(audio_path, "wb") as f:
                        f.write(audio_file.read())
                        
                font_dir = None
                font_name = "UVN Ban Tay" # Font mặc định
                
                if font_file:
                    font_dir = os.path.join(temp_dir, "fonts")
                    os.makedirs(font_dir, exist_ok=True)
                    font_path = os.path.join(font_dir, font_file.name)
                    with open(font_path, "wb") as f:
                        f.write(font_file.read())
                        
                    # Extract true font family name
                    try:
                        from fontTools.ttLib import TTFont
                        font = TTFont(font_path)
                        for record in font['name'].names:
                            if record.nameID == 1:
                                font_name = record.toUnicode()
                                break
                    except Exception as e:
                        print("Error reading font name:", e)
                        font_name = os.path.splitext(font_file.name)[0]
                else:
                    # Sử dụng font mặc định
                    font_dir = "/Users/kevinduong/Downloads/font"
            
            cuts = []
            
            bg_audio_path = None
            if st.session_state.selected_bgm != "Không sử dụng nhạc nền":
                bg_audio_path = os.path.join(bgm_dir, st.session_state.selected_bgm)
            
            if audio_file:
                # DUBBING MODE: Video + Audio File
                progress_bar = st.progress(0, text="Bước 1/4: Đang phân tích thời lượng âm thanh...")
                duration = get_audio_duration(audio_path)
                
                if auto_sync:
                    from core.subtitle_engine import auto_sync_scenes
                    progress_bar.progress(20, text="Bước 2/4: [AI Auto-sync] Đang trích xuất và bóc băng âm thanh Video gốc...")
                    vid_audio_path = os.path.join(temp_dir, "vid_audio.mp3")
                    extract_video_audio(video_path, vid_audio_path)
                    vid_transcript = call_nvidia_whisper(vid_audio_path, api_key)
                    
                    progress_bar.progress(40, text="Bước 2/4: [AI Auto-sync] Đang bóc băng âm thanh Tiếng Việt...")
                    aud_transcript = call_nvidia_whisper(audio_path, api_key, language="vi")
                    
                    progress_bar.progress(60, text="Bước 2/4: [AI Auto-sync] LLM đang tìm và phân tích các phân cảnh khớp...")
                    cuts = auto_sync_scenes(vid_transcript, aud_transcript, api_key, duration)
                    
                    info_msg = "🤖 AI đã hoàn tất cắt ghép: Ghép nối " + str(len(cuts)) + " phân cảnh."
                    if len(cuts) > 0:
                        info_msg += f" (Cảnh 1 bắt đầu từ {cuts[0]['vid_start']}s)"
                    st.info(info_msg)
                else:
                    progress_bar.progress(40, text="Bước 2/4: Đang gọi NVIDIA API để tạo phụ đề...")
                    aud_transcript = call_nvidia_whisper(audio_path, api_key, language="vi")
                    cuts = [{"vid_start": start_time_offset, "duration": duration}]
                    
                progress_bar.progress(80, text="Bước 3/4: Đang tạo file phụ đề ASS...")
                generate_ass_subtitle(
                    aud_transcript, 
                    subtitle_path, 
                    margin_v=margin_v, 
                    highlight_color=highlight_color_hex, 
                    correct_text=correct_text,
                    audio_duration=duration,
                    font_name=font_name,
                    font_size=font_size,
                    sub_style=sub_style,
                    sub_offset_ms=sub_offset_ms
                )
                    
                progress_bar.progress(90, text="Bước 4/4: Đang nối cảnh và xử lý Video bằng FFmpeg (Có thể mất vài phút)...")
                process_video(
                    video_in=video_path,
                    audio_in=audio_path,
                    subtitle_ass=subtitle_path,
                    cuts=cuts,
                    output_path=output_video_path,
                    audio_delay_ms=audio_delay_ms,
                    total_audio_duration=duration,
                    bg_audio_path=bg_audio_path,
                    font_dir=font_dir
                )
            else:
                # SUBTITLE ONLY MODE: Video Only
                progress_bar = st.progress(0, text="Bước 1/3: Trích xuất âm thanh từ Video...")
                from core.media_utils import process_video_subtitles_only
                
                vid_audio_path = os.path.join(temp_dir, "vid_audio.mp3")
                extract_video_audio(video_path, vid_audio_path)
                duration = get_audio_duration(vid_audio_path)
                
                progress_bar.progress(30, text="Bước 2/3: Đang gọi NVIDIA API để nhận diện giọng nói và tạo phụ đề...")
                aud_transcript = call_nvidia_whisper(vid_audio_path, api_key, language="vi")
                
                generate_ass_subtitle(
                    aud_transcript, 
                    subtitle_path, 
                    margin_v=margin_v, 
                    highlight_color=highlight_color_hex, 
                    correct_text=correct_text,
                    audio_duration=duration,
                    font_name=font_name,
                    font_size=font_size,
                    sub_style=sub_style,
                    sub_offset_ms=sub_offset_ms
                )
                
                progress_bar.progress(70, text="Bước 3/3: Bọc phụ đề vào Video...")
                process_video_subtitles_only(
                    video_in=video_path,
                    subtitle_ass=subtitle_path,
                    output_path=output_video_path,
                    bg_audio_path=bg_audio_path,
                    font_dir=font_dir
                )
            
            progress_bar.progress(100, text="Hoàn tất!")
            st.success("🎉 Xử lý Video thành công!")
            
            st.subheader("4. Kết quả")
            with open(output_video_path, "rb") as f:
                video_bytes = f.read()
                
            st.video(video_bytes)
            
            st.download_button(
                label="⬇️ TẢI XUỐNG VIDEO",
                data=video_bytes,
                file_name="video_da_xu_ly.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
            
        except Exception as e:
            st.error(f"Đã xảy ra lỗi trong quá trình xử lý: {e}")
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
