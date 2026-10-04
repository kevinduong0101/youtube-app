import streamlit as st
import tempfile
import os
import shutil

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
from core.presets import list_presets, get_preset, STUDIO_PALETTES
from core.fonts import inspect_font_file, RECOMMENDED_CREATOR_FONTS

# Thiết lập cấu hình trang
st.set_page_config(
    page_title="AutoSub Pro Studio", 
    page_icon="■", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark Studio Design System CSS (#0B0C0F, #13151A, #191C22)
st.markdown("""
<style>
/* Reset & Background */
.stApp {
    background-color: #0B0C0F;
    color: #EDEDED;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Header */
.studio-brand {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-top: -30px;
    margin-bottom: 20px;
    border-bottom: 1px solid #1E222B;
    padding-bottom: 12px;
}
.brand-title {
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #EDEDED;
    margin: 0;
}
.brand-badge {
    background-color: #191C22;
    border: 1px solid #2B303C;
    color: #FF4B4B;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.5px;
}
.brand-meta {
    margin-left: auto;
    font-size: 0.8rem;
    color: #7A8194;
    font-variant-numeric: tabular-nums;
}

/* Panel Containers */
.studio-card {
    background-color: #13151A;
    border: 1px solid #1F232D;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
}
.card-header {
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #8E95A5;
    margin-bottom: 12px;
}

/* Preview Stage Container */
.preview-stage {
    background-color: #0E1015;
    border: 1px solid #1F232D;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 480px;
    padding: 12px;
    position: relative;
}

/* Buttons */
.stButton > button {
    border-radius: 6px;
    font-weight: 600;
    transition: all 0.15s ease;
}
</style>
""", unsafe_allow_html=True)

# Khởi tạo session state lưu trữ
if "transcribed_video_name" not in st.session_state:
    st.session_state.transcribed_video_name = None
if "transcript_raw" not in st.session_state:
    st.session_state.transcript_raw = None
if "chunks_data" not in st.session_state:
    st.session_state.chunks_data = None
if "preview_frame_path" not in st.session_state:
    st.session_state.preview_frame_path = None
if "rendered_video_path" not in st.session_state:
    st.session_state.rendered_video_path = None
if "video_meta" not in st.session_state:
    st.session_state.video_meta = None

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

# Top Studio Brand Bar
meta_text = ""
if st.session_state.video_meta:
    meta = st.session_state.video_meta
    meta_text = f"{meta['width']}×{meta['height']}  •  {meta['duration']:.1f}s  •  {meta['chunks_count']} segments"

st.markdown(f"""
<div class="studio-brand">
    <h1 class="brand-title">AUTOSUB PRO</h1>
    <span class="brand-badge">STUDIO</span>
    <span class="brand-meta">{meta_text}</span>
</div>
""", unsafe_allow_html=True)

# Main Studio Layout: 2 Columns (Left: Visual Canvas Stage, Right: Studio Inspector)
col_stage, col_inspector = st.columns([1.1, 1.0], gap="large")

# =========================================================================
# RIGHT COLUMN: STUDIO INSPECTOR (Controls & Orchestration)
# =========================================================================
with col_inspector:
    st.markdown('<div class="card-header">MEDIA & INGESTION</div>', unsafe_allow_html=True)
    
    col_up_vid, col_up_aud = st.columns(2)
    with col_up_vid:
        video_file = st.file_uploader("Video Source (.mp4, .mov)", type=["mp4", "mov"], label_visibility="collapsed")
    with col_up_aud:
        audio_file = st.file_uploader("Replace Audio (.mp3, .wav)", type=["mp3", "wav"], label_visibility="collapsed")

    # Ingestion Controls
    col_model, col_btn_trans = st.columns([1, 1.2])
    with col_model:
        whisper_model = st.selectbox(
            "Speech Engine",
            options=["base", "small"],
            index=0,
            help="Base: Fast (recommended). Small: High accuracy for Vietnamese dialects.",
            label_visibility="collapsed"
        )
    with col_btn_trans:
        btn_transcribe = st.button("Transcribe Subtitles", use_container_width=True, type="secondary")

    # Reset transcript upon new video
    if video_file and st.session_state.transcribed_video_name != video_file.name:
        st.session_state.transcribed_video_name = None
        st.session_state.transcript_raw = None
        st.session_state.chunks_data = None
        st.session_state.preview_frame_path = None
        st.session_state.rendered_video_path = None
        st.session_state.video_meta = None

    # Handle Transcription Execution
    if btn_transcribe:
        if not video_file:
            st.error("Please select a video file before transcribing.")
        else:
            with st.spinner("Extracting audio and analyzing rhythm with Whisper AI..."):
                temp_trans = tempfile.mkdtemp()
                try:
                    temp_vid = os.path.join(temp_trans, "in.mp4")
                    with open(temp_vid, "wb") as f:
                        f.write(video_file.getvalue())
                        
                    if audio_file:
                        temp_aud = os.path.join(temp_trans, "in.mp3")
                        with open(temp_aud, "wb") as f:
                            f.write(audio_file.getvalue())
                    else:
                        temp_aud = os.path.join(temp_trans, "extracted.mp3")
                        extract_video_audio(temp_vid, temp_aud)
                        
                    transcript = transcribe_audio(temp_aud, model_name=whisper_model, language="vi")
                    flat_words = extract_flat_words_from_transcript(transcript)
                    smart_chunks = create_smart_rhythm_chunks(flat_words, max_words=3)
                    
                    vw, vh = get_video_dimensions(temp_vid)
                    vdur = get_audio_duration(temp_aud)
                    
                    st.session_state.transcribed_video_name = video_file.name
                    st.session_state.transcript_raw = transcript
                    st.session_state.chunks_data = smart_chunks
                    st.session_state.video_meta = {
                        "width": vw,
                        "height": vh,
                        "duration": vdur,
                        "chunks_count": len(smart_chunks)
                    }
                    st.rerun()
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                finally:
                    shutil.rmtree(temp_trans, ignore_errors=True)

    st.markdown('<hr style="border: 0; border-top: 1px solid #1F232D; margin: 16px 0;">', unsafe_allow_html=True)
    
    # Inspector Tabs: Studio Controls
    tab_presets, tab_typo, tab_motion, tab_editor, tab_adv = st.tabs([
        "PRESETS", "TYPOGRAPHY", "MOTION & COLOR", "TRANSCRIPT", "ADVANCED"
    ])

    # 1. TAB: PRESETS
    with tab_presets:
        presets_list = list_presets()
        preset_names = [f"{p['name']}  —  {p['tagline']}" for p in presets_list]
        selected_preset_idx = st.selectbox(
            "Design Preset",
            range(len(preset_names)),
            format_func=lambda i: preset_names[i],
            label_visibility="collapsed"
        )
        active_preset = presets_list[selected_preset_idx]
        st.caption(f"Category: **{active_preset['badge']}** • Base Font: **{active_preset['font_family']}**")

    # 2. TAB: TYPOGRAPHY
    with tab_typo:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            rec_font_names = [f["name"] for f in RECOMMENDED_CREATOR_FONTS]
            selected_font_family = st.selectbox(
                "Font Family",
                options=rec_font_names,
                index=rec_font_names.index(active_preset["font_family"]) if active_preset["font_family"] in rec_font_names else 0
            )
        with col_f2:
            custom_font_file = st.file_uploader("Upload TTF/OTF", type=["ttf", "otf"])
            if custom_font_file:
                temp_font_dir = tempfile.mkdtemp()
                temp_font_path = os.path.join(temp_font_dir, custom_font_file.name)
                with open(temp_font_path, "wb") as f:
                    f.write(custom_font_file.getvalue())
                font_meta = inspect_font_file(temp_font_path)
                selected_font_family = font_meta["family"]
                st.caption(f"Detected: **{font_meta['display_name']}**")
                
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            font_size = st.slider("Font Size", min_value=30, max_value=120, value=active_preset["font_size"], step=2)
        with col_t2:
            all_caps = st.checkbox("ALL CAPS (Shorts/TikTok)", value=active_preset["all_caps"])
            
        words_per_line = st.slider(
            "Pacing (Words per Line)",
            min_value=1, max_value=6, value=active_preset["words_per_line"], step=1,
            help="1-2 words: Rapid punchy hook (Alex Hormozi). 3-4 words: Standard TikTok. 5-6 words: Vlog / Editorial."
        )

    # 3. TAB: MOTION & COLOR
    with tab_motion:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            anim_options = {
                "pop_bounce": "Elastic Bounce (112% motion curve)",
                "pop_subtle": "Subtle Lift (108%)",
                "pop_strong": "Impact Punch (120%)",
                "none": "Static Highlight (No scale)"
            }
            selected_anim = st.selectbox(
                "Active Word Animation",
                options=list(anim_options.keys()),
                format_func=lambda k: anim_options[k],
                index=list(anim_options.keys()).index(active_preset["animation_mode"]) if active_preset["animation_mode"] in anim_options else 0
            )
        with col_m2:
            palette_names = list(STUDIO_PALETTES.keys())
            selected_color_name = st.selectbox("Highlight Palette", options=palette_names, index=0)
            highlight_color = STUDIO_PALETTES[selected_color_name]
            
        margin_v = st.slider(
            "Vertical Position (Margin Bottom)",
            min_value=40, max_value=600, value=active_preset["margin_v"], step=10,
            help="Height in pixels from bottom edge. Default 200-240px leaves room for TikTok caption & action bar."
        )

    # 4. TAB: TRANSCRIPT EDITOR
    with tab_editor:
        if st.session_state.chunks_data:
            st.caption(f"Editing {len(st.session_state.chunks_data)} spoken segments (Timestamps auto-aligned):")
            for c_idx, chunk in enumerate(st.session_state.chunks_data):
                c_text = " ".join(w.get('word', '') for w in chunk)
                c_start = chunk[0].get('start', 0.0)
                c_end = chunk[-1].get('end', 0.0)
                
                new_text = st.text_input(
                    f"{c_start:.1f}s – {c_end:.1f}s",
                    value=c_text,
                    key=f"editor_chunk_{c_idx}"
                )
                if new_text != c_text:
                    st.session_state.chunks_data[c_idx] = helper_update_chunk_text(chunk, new_text)
        else:
            st.info("Upload a video and transcribe to edit subtitle lines.")

    # 5. TAB: ADVANCED
    with tab_adv:
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            timing_offset = st.slider("Timing Offset (ms)", min_value=-500, max_value=500, value=0, step=25)
        with col_a2:
            aspect_choice = st.selectbox("Export Framing", ["Original Aspect Ratio", "Crop/Fit 9:16 (Shorts/TikTok)"], index=0)
            aspect_mode = "vertical_9_16" if "9:16" in aspect_choice else "original"

    st.markdown('<hr style="border: 0; border-top: 1px solid #1F232D; margin: 16px 0;">', unsafe_allow_html=True)
    
    # Export Button in Inspector
    btn_export = st.button("RENDER & EXPORT MASTER MP4", use_container_width=True, type="primary")

# =========================================================================
# LEFT COLUMN: VISUAL CANVAS STAGE (Centerpiece Experience)
# =========================================================================
with col_stage:
    st.markdown('<div class="card-header">VISUAL CANVAS STAGE</div>', unsafe_allow_html=True)
    
    # Preview Controls Bar
    col_p_btn, col_p_guide, col_p_seek = st.columns([1.2, 1.2, 1.6])
    with col_p_btn:
        btn_preview = st.button("Preview Frame", use_container_width=True)
    with col_p_guide:
        show_safe_area = st.checkbox("Safe Area Guide", value=False, help="Displays TikTok/Reels UI overlay boundaries.")
    with col_p_seek:
        total_d = st.session_state.video_meta["duration"] if st.session_state.video_meta else 10.0
        seek_sec = st.slider("Time", min_value=0.0, max_value=float(total_d), value=min(1.5, float(total_d)), step=0.1, label_visibility="collapsed")

    # Render Preview Frame Action
    if btn_preview:
        if not video_file:
            st.warning("Please upload a video file to generate preview.")
        else:
            with st.spinner("Rendering single-frame typography..."):
                t_prev_dir = tempfile.mkdtemp()
                try:
                    p_vid = os.path.join(t_prev_dir, "p_in.mp4")
                    with open(p_vid, "wb") as f:
                        f.write(video_file.getvalue())
                        
                    vw, vh = get_video_dimensions(p_vid)
                    if aspect_mode == "vertical_9_16":
                        vw, vh = 1080, 1920
                        
                    p_ass = os.path.join(t_prev_dir, "p_sub.ass")
                    
                    if st.session_state.chunks_data:
                        render_chunks = st.session_state.chunks_data
                    else:
                        render_chunks = [[
                            {"word": "CREATING", "start": 0.5, "end": 1.0},
                            {"word": "VIRAL", "start": 1.0, "end": 1.5},
                            {"word": "CONTENT", "start": 1.5, "end": 2.2}
                        ]]
                        
                    overrides = {
                        "font_family": selected_font_family,
                        "font_size": font_size,
                        "all_caps": all_caps,
                        "words_per_line": words_per_line,
                        "animation_mode": selected_anim,
                        "highlight_color": highlight_color,
                        "margin_v": margin_v
                    }
                    
                    generate_ass_subtitle(
                        transcript_json={},
                        output_path=p_ass,
                        video_width=vw,
                        video_height=vh,
                        margin_v=margin_v,
                        highlight_color=highlight_color,
                        font_name=selected_font_family,
                        font_size=font_size,
                        sub_style=active_preset["id"],
                        sub_offset_ms=timing_offset,
                        animation_mode=selected_anim,
                        text_transform="uppercase" if all_caps else "original",
                        max_words_per_chunk=words_per_line,
                        pre_chunked_data=render_chunks
                    )
                    
                    p_img = os.path.join(t_prev_dir, "preview.jpg")
                    generate_preview_frame(
                        video_in=p_vid,
                        subtitle_ass=p_ass,
                        timestamp_sec=seek_sec,
                        output_img_path=p_img,
                        aspect_mode=aspect_mode,
                        show_safe_area=show_safe_area
                    )
                    
                    # Store image in memory or persistent location
                    with open(p_img, "rb") as img_f:
                        st.session_state.preview_frame_path = img_f.read()
                except Exception as e:
                    st.error(f"Preview render failed: {e}")
                finally:
                    shutil.rmtree(t_prev_dir, ignore_errors=True)

    # Visual Display Box
    if st.session_state.rendered_video_path and os.path.exists(st.session_state.rendered_video_path):
        st.success("Master Render Complete")
        st.video(st.session_state.rendered_video_path)
        with open(st.session_state.rendered_video_path, "rb") as f:
            v_data = f.read()
        st.download_button(
            label="DOWNLOAD COMPLETED MP4",
            data=v_data,
            file_name="autosub_master_export.mp4",
            mime="video/mp4",
            type="primary",
            use_container_width=True
        )
    elif st.session_state.preview_frame_path:
        st.image(st.session_state.preview_frame_path, use_container_width=True)
    else:
        # Default placeholder canvas
        st.markdown("""
        <div class="preview-stage">
            <div style="font-size: 2.2rem; color: #2C3240; margin-bottom: 8px;">■</div>
            <div style="font-size: 0.9rem; font-weight: 600; color: #6D7588;">PREVIEW STAGE READY</div>
            <div style="font-size: 0.75rem; color: #4B5263; margin-top: 4px;">Click "Preview Frame" above to render instant typography</div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================================
# FINAL EXPORT LOGIC
# =========================================================================
if btn_export:
    if not video_file:
        st.error("Please provide a source video before exporting.")
    else:
        t_export = tempfile.mkdtemp()
        try:
            progress_bar = st.progress(0, text="Preparing master export pipeline...")
            export_vid = os.path.join(t_export, "export_in.mp4")
            with open(export_vid, "wb") as f:
                f.write(video_file.getvalue())
                
            export_aud = None
            if audio_file:
                export_aud = os.path.join(t_export, "export_aud.mp3")
                with open(export_aud, "wb") as f:
                    f.write(audio_file.getvalue())
                    
            progress_bar.progress(25, text="Synchronizing speech rhythm & alignment...")
            if st.session_state.chunks_data and st.session_state.transcribed_video_name == video_file.name:
                final_chunks = st.session_state.chunks_data
            else:
                target_aud = export_aud
                if not target_aud:
                    target_aud = os.path.join(t_export, "extracted_aud.mp3")
                    extract_video_audio(export_vid, target_aud)
                t_res = transcribe_audio(target_aud, model_name=whisper_model, language="vi")
                t_words = extract_flat_words_from_transcript(t_res)
                final_chunks = create_smart_rhythm_chunks(t_words, max_words=words_per_line)
                st.session_state.chunks_data = final_chunks

            progress_bar.progress(50, text="Generating master Advanced SubStation Alpha script...")
            vw, vh = get_video_dimensions(export_vid)
            if aspect_mode == "vertical_9_16":
                vw, vh = 1080, 1920
                
            final_ass = os.path.join(t_export, "final_sub.ass")
            generate_ass_subtitle(
                transcript_json={},
                output_path=final_ass,
                video_width=vw,
                video_height=vh,
                margin_v=margin_v,
                highlight_color=highlight_color,
                font_name=selected_font_family,
                font_size=font_size,
                sub_style=active_preset["id"],
                sub_offset_ms=timing_offset,
                animation_mode=selected_anim,
                text_transform="uppercase" if all_caps else "original",
                max_words_per_chunk=words_per_line,
                pre_chunked_data=final_chunks
            )

            progress_bar.progress(70, text="Burning subtitles with libass & passthrough audio...")
            final_out = os.path.join(tempfile.gettempdir(), "autosub_pro_finished.mp4")
            
            if export_aud:
                process_video_with_audio_replace(
                    video_in=export_vid,
                    audio_in=export_aud,
                    subtitle_ass=final_ass,
                    output_path=final_out,
                    aspect_mode=aspect_mode,
                    enhance_quality=False
                )
            else:
                process_video_subtitles_only(
                    video_in=export_vid,
                    subtitle_ass=final_ass,
                    output_path=final_out,
                    aspect_mode=aspect_mode,
                    enhance_quality=False
                )

            progress_bar.progress(100, text="Export complete!")
            st.session_state.rendered_video_path = final_out
            st.rerun()
        except Exception as e:
            st.error(f"Export processing failed: {e}")
        finally:
            shutil.rmtree(t_export, ignore_errors=True)
