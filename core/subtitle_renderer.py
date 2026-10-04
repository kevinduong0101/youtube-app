"""
core/subtitle_renderer.py - Advanced ASS Subtitle Renderer & Motion Typography Engine
Renders studio-grade .ass files supporting preset design systems, elastic pop animations,
letter-spacing, blur outlines, and anti-flicker continuous layers.
"""

import os
from core.presets import get_preset

def format_ass_time(seconds: float) -> str:
    """Converts seconds (float) to ASS timestamp format: H:MM:SS.cs"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def render_ass_script(
    chunks: list,
    output_path: str,
    preset_id: str = "hormozi",
    custom_overrides: dict = None,
    video_width: int = 1080,
    video_height: int = 1920
) -> str:
    """
    Renders an Advanced SubStation Alpha (.ass v4.00+) script from structured chunks.
    
    Args:
        chunks: List of word chunks (each is a list of dicts with 'word', 'start', 'end')
        output_path: Target path to write the .ass file
        preset_id: Key of the studio preset ("hormozi", "vlog_pro", "pill_badge", "neon_glow", "cinematic")
        custom_overrides: Optional user overrides (e.g. font_family, font_size, margin_v, highlight_color)
        video_width: Video resolution width (PlayResX)
        video_height: Video resolution height (PlayResY)
    """
    preset = get_preset(preset_id)
    if custom_overrides:
        for k, v in custom_overrides.items():
            if v is not None:
                preset[k] = v
                
    font_family = preset.get("font_family", "Arial")
    font_size = int(preset.get("font_size", 65))
    bold_flag = -1 if preset.get("bold", True) else 0
    italic_flag = -1 if preset.get("italic", False) else 0
    letter_spacing = float(preset.get("letter_spacing", 0.0))
    outline_width = float(preset.get("outline_width", 6.0))
    shadow_depth = float(preset.get("shadow_depth", 2.0))
    margin_v = int(preset.get("margin_v", 200))
    border_style = int(preset.get("border_style", 1))
    
    primary_color = preset.get("primary_color", "&H00FFFFFF")
    highlight_color = preset.get("highlight_color", "&H0000E6FF")
    outline_color = preset.get("outline_color", "&H00000000")
    shadow_color = preset.get("shadow_color", "&H80000000")
    
    all_caps = preset.get("all_caps", False)
    animation_mode = preset.get("animation_mode", "pop_bounce")
    pop_scale = int(preset.get("pop_scale", 112))
    
    # 1. Styles Definition
    # TextStyle: Main typographic dialogue layer
    text_style_line = (
        f"Style: TextStyle,{font_family},{font_size},"
        f"{primary_color},{primary_color},{outline_color},{shadow_color},"
        f"{bold_flag},{italic_flag},0,0,100,100,{letter_spacing},0,"
        f"{border_style},{outline_width},{shadow_depth},2,20,20,{margin_v},1"
    )
    
    styles_block = text_style_line
    
    # MaskStyle: Pill Badge translucent container backing (Layer 0)
    if border_style == 3 or preset.get("id") == "pill_badge":
        box_color = preset.get("box_color", "&HB014161C")
        box_padding = float(preset.get("box_padding", 10.0))
        mask_style_line = (
            f"Style: MaskStyle,{font_family},{font_size},"
            f"&HFF000000,&HFF000000,{box_color},{box_color},"
            f"{bold_flag},0,0,0,100,100,{letter_spacing},0,"
            f"3,{box_padding},0,2,20,20,{margin_v},1"
        )
        styles_block = f"{mask_style_line}\n{text_style_line}"

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles_block}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    events_lines = []
    
    # Motion Tag Generator
    if animation_mode == "pop_bounce":
        # Elastic bounce curve: expand to pop_scale in 70ms, return to 100% in 160ms
        active_anim_tag = f"\\t(0,70,\\fscx{pop_scale}\\fscy{pop_scale})\\t(70,160,\\fscx100\\fscy100)"
        reset_anim_tag = "\\fscx100\\fscy100"
    elif animation_mode == "pop_subtle":
        active_anim_tag = "\\fscx108\\fscy108"
        reset_anim_tag = "\\fscx100\\fscy100"
    elif animation_mode == "pop_strong":
        active_anim_tag = f"\\t(0,80,\\fscx{pop_scale + 8}\\fscy{pop_scale + 8})\\t(80,180,\\fscx100\\fscy100)"
        reset_anim_tag = "\\fscx100\\fscy100"
    else:
        active_anim_tag = ""
        reset_anim_tag = ""

    # 2. Events Generation
    for chunk in chunks:
        if not chunk:
            continue
        chunk_start = chunk[0]['start']
        chunk_end = chunk[-1]['end']
        
        start_str = format_ass_time(chunk_start)
        end_str = format_ass_time(chunk_end)
        
        formatted_words = []
        for w in chunk:
            raw_w = w.get('word', '').replace('\n', '').strip()
            formatted_words.append(raw_w.upper() if all_caps else raw_w)
            
        full_text = ' '.join(formatted_words)
        
        # Layer 0: Mask Container Backing (Pill Badge)
        if border_style == 3 or preset.get("id") == "pill_badge":
            events_lines.append(f"Dialogue: 0,{start_str},{end_str},MaskStyle,,0,0,0,,{{\\alpha&HFF&}}{full_text}")
            
        # Cinematic Preset: Pure static subtitle line without word-by-word highlight
        if preset.get("id") == "cinematic" or animation_mode == "static_chunk":
            events_lines.append(f"Dialogue: 1,{start_str},{end_str},TextStyle,,0,0,0,,{full_text}")
            continue
            
        # Layer 1: Motion Typography & Word Karaoke Tracking
        last_time = chunk_start
        for i, target_word in enumerate(chunk):
            w_start = max(target_word.get('start', 0.0), last_time)
            
            # Anti-overlap end boundary
            if i < len(chunk) - 1:
                w_end = min(target_word.get('end', 0.0), chunk[i+1].get('start', 0.0))
            else:
                w_end = target_word.get('end', 0.0)
                
            w_end = max(w_start + 0.01, w_end)
            
            # Pre-word gap: Render resting neutral text (Anti-flicker continuous layer)
            if w_start > last_time + 0.01:
                gap_start = format_ass_time(last_time)
                gap_end = format_ass_time(w_start)
                events_lines.append(f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{full_text}")
                
            # Active Word Dialogue Event
            word_start_str = format_ass_time(w_start)
            word_end_str = format_ass_time(w_end)
            
            parts = []
            for j, w_text in enumerate(formatted_words):
                if j == i:
                    anim_prefix = f"\\{active_anim_tag}" if active_anim_tag else ""
                    anim_suffix = f"\\{reset_anim_tag}" if reset_anim_tag else ""
                    parts.append(f"{{\\c{highlight_color}&{anim_prefix}}}{w_text}{{\\c{primary_color}&{anim_suffix}}}")
                else:
                    parts.append(w_text)
            line_text = ' '.join(parts)
            events_lines.append(f"Dialogue: 1,{word_start_str},{word_end_str},TextStyle,,0,0,0,,{line_text}")
            
            last_time = w_end
            
        # Post-word trailing gap inside chunk
        if chunk_end > last_time + 0.01:
            gap_start = format_ass_time(last_time)
            gap_end = format_ass_time(chunk_end)
            events_lines.append(f"Dialogue: 1,{gap_start},{gap_end},TextStyle,,0,0,0,,{full_text}")

    full_ass_content = ass_header + "\n".join(events_lines) + "\n"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_ass_content)
        
    return output_path
