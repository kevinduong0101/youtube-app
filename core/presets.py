"""
core/presets.py - Studio Subtitle Presets & Design Systems
Defines complete typography, layout, and motion specifications for each visual style.
"""

STUDIO_PRESETS = {
    "hormozi": {
        "id": "hormozi",
        "name": "HORMOZI",
        "tagline": "Bold / Punchy / High-Retention",
        "badge": "VIRAL SHORT",
        "font_family": "Impact",
        "fallback_fonts": ["Arial", "Trebuchet MS", "Helvetica Neue"],
        "font_size": 75,
        "bold": True,
        "italic": False,
        "all_caps": True,
        "letter_spacing": 1.0,
        "words_per_line": 3,
        "primary_color": "&H00FFFFFF",        # Pure White
        "highlight_color": "&H0000E6FF",      # Hormozi Neon Yellow (#FFE600)
        "outline_color": "&H00000000",        # Deep Black
        "outline_width": 9.0,
        "shadow_color": "&H90000000",         # Hard Drop Shadow
        "shadow_depth": 3.0,
        "border_style": 1,                    # Outline + Drop Shadow
        "blur_edges": 0.5,
        "margin_v": 230,                      # Elevated above TikTok bottom nav
        "animation_mode": "pop_bounce",
        "pop_scale": 112                      # 112% elastic bounce
    },
    "vlog_pro": {
        "id": "vlog_pro",
        "name": "VLOG PRO",
        "tagline": "Clean / Natural / Lifestyle",
        "badge": "LIFESTYLE",
        "font_family": "Helvetica Neue",
        "fallback_fonts": ["Arial", "Trebuchet MS", "sans-serif"],
        "font_size": 65,
        "bold": True,
        "italic": False,
        "all_caps": False,
        "letter_spacing": 0.5,
        "words_per_line": 4,
        "primary_color": "&H00FFFFFF",        # Clean White
        "highlight_color": "&H0000D0FF",      # Warm Amber Gold (#FFD000)
        "outline_color": "&H00000000",        # Soft Charcoal Black
        "outline_width": 5.0,
        "shadow_color": "&H60000000",         # Soft Ambient Shadow
        "shadow_depth": 2.0,
        "border_style": 1,
        "blur_edges": 1.0,
        "margin_v": 200,
        "animation_mode": "pop_subtle",
        "pop_scale": 108                      # 108% subtle lift
    },
    "pill_badge": {
        "id": "pill_badge",
        "name": "PILL BADGE",
        "tagline": "Modern Caption Bubble / Dark Glass",
        "badge": "POPULAR",
        "font_family": "Arial",
        "fallback_fonts": ["Helvetica Neue", "Trebuchet MS"],
        "font_size": 60,
        "bold": True,
        "italic": False,
        "all_caps": True,
        "letter_spacing": 0.5,
        "words_per_line": 3,
        "primary_color": "&H00FFFFFF",        # Crisp White
        "highlight_color": "&H00FFFF00",      # Cyan Blue Accent (#00FFFF)
        "outline_color": "&H00000000",        # Thin separator
        "outline_width": 3.0,
        "shadow_color": "&H00000000",
        "shadow_depth": 0.0,
        "border_style": 3,                    # Opaque box backing (Pill Badge)
        "box_color": "&HB014161C",            # Translucent Studio Glass
        "box_padding": 12.0,
        "blur_edges": 0.0,
        "margin_v": 220,
        "animation_mode": "pop_bounce",
        "pop_scale": 110
    },
    "neon_glow": {
        "id": "neon_glow",
        "name": "NEON GLOW",
        "tagline": "Cyberpunk / Tech / High Voltage",
        "badge": "CREATIVE",
        "font_family": "Trebuchet MS",
        "fallback_fonts": ["Arial", "Impact"],
        "font_size": 68,
        "bold": True,
        "italic": False,
        "all_caps": True,
        "letter_spacing": 1.2,
        "words_per_line": 3,
        "primary_color": "&H00FFFFFF",        # Electric White
        "highlight_color": "&H007F00FF",      # TikTok Neon Pink (#FF007F)
        "outline_color": "&H00550055",        # Deep Ultraviolet
        "outline_width": 6.0,
        "shadow_color": "&H80FF00FF",         # Neon Ambient Glow
        "shadow_depth": 3.5,
        "border_style": 1,
        "blur_edges": 2.0,
        "margin_v": 230,
        "animation_mode": "pop_bounce",
        "pop_scale": 112
    },
    "cinematic": {
        "id": "cinematic",
        "name": "CINEMATIC",
        "tagline": "Editorial / Film / Minimalist",
        "badge": "EDITORIAL",
        "font_family": "Arial",
        "fallback_fonts": ["Helvetica Neue", "Geneva"],
        "font_size": 55,
        "bold": False,
        "italic": False,
        "all_caps": False,
        "letter_spacing": 1.5,
        "words_per_line": 5,
        "primary_color": "&H00F0F0F0",        # Warm Ivory
        "highlight_color": "&H00C0E0FF",      # Subtle Pale Gold
        "outline_color": "&H00000000",        # Fine Line
        "outline_width": 2.5,
        "shadow_color": "&H50000000",         # Very light cinematic shadow
        "shadow_depth": 1.2,
        "border_style": 1,
        "blur_edges": 0.5,
        "margin_v": 170,
        "animation_mode": "none",             # Pure static elegance
        "pop_scale": 100
    }
}

STUDIO_PALETTES = {
    "Vàng Chanh Hormozi": "&H0000E6FF",
    "Xanh Lá Neon": "&H0066FF00",
    "Xanh Cyan Công Nghệ": "&H00FFFF00",
    "Hồng Neon TikTok": "&H007F00FF",
    "Đỏ Cam Rực Rỡ": "&H000055FF",
    "Trắng Tinh Khôi": "&H00FFFFFF"
}

def get_preset(preset_id: str) -> dict:
    """Returns the preset configuration dict by id, falling back to 'hormozi'."""
    # Handle cases where full name or legacy id was passed
    clean_id = preset_id.lower()
    for key in STUDIO_PRESETS:
        if key in clean_id or STUDIO_PRESETS[key]["name"].lower() in clean_id:
            return STUDIO_PRESETS[key].copy()
    return STUDIO_PRESETS["hormozi"].copy()

def list_presets() -> list:
    """Returns list of preset dictionaries ordered for the studio UI."""
    return list(STUDIO_PRESETS.values())

def get_available_presets() -> dict:
    """Returns mapping of all studio presets."""
    return STUDIO_PRESETS
