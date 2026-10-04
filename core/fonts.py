"""
core/fonts.py - Font Inspector and Typography Metadata System
Safely inspects TTF/OTF files, extracts clean font family names, and provides studio defaults.
"""

import os
from fontTools.ttLib import TTFont

RECOMMENDED_CREATOR_FONTS = [
    {"name": "Arial", "category": "Universal / High-Legibility"},
    {"name": "Impact", "category": "Heavy / Viral Short-Form"},
    {"name": "Trebuchet MS", "category": "Modern / Humanist"},
    {"name": "Helvetica Neue", "category": "Lifestyle / Minimalist"},
    {"name": "UVN Ban Tay", "category": "Casual / Friendly Accent"}
]

def inspect_font_file(file_path: str) -> dict:
    """
    Parses a TTF or OTF font file using fontTools.ttLib and extracts clean typography metadata.
    Returns:
        dict: {
            "family": str,
            "style": str,
            "display_name": str,
            "is_valid": bool,
            "error": str | None
        }
    """
    if not os.path.exists(file_path):
        return {
            "family": "Arial",
            "style": "Regular",
            "display_name": "Arial (Fallback)",
            "is_valid": False,
            "error": "File does not exist"
        }
        
    try:
        font = TTFont(file_path)
        family = None
        style = None
        
        # Scan font naming records
        for record in font['name'].names:
            # 16 = Typographic Family, 1 = Font Family
            if record.nameID == 16 and not family:
                try:
                    family = record.toUnicode()
                except Exception:
                    pass
            elif record.nameID == 1 and not family:
                try:
                    family = record.toUnicode()
                except Exception:
                    pass
            # 17 = Typographic Subfamily, 2 = Font Subfamily
            elif record.nameID == 2 and not style:
                try:
                    style = record.toUnicode()
                except Exception:
                    pass
                    
        clean_family = family.strip() if family else os.path.splitext(os.path.basename(file_path))[0]
        clean_style = style.strip() if style else "Regular"
        display_name = f"{clean_family} {clean_style}".strip()
        
        return {
            "family": clean_family,
            "style": clean_style,
            "display_name": display_name,
            "is_valid": True,
            "error": None
        }
    except Exception as e:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        return {
            "family": base_name,
            "style": "Regular",
            "display_name": f"{base_name} (Unverified)",
            "is_valid": False,
            "error": str(e)
        }

def get_creator_font_catalog():
    """Returns catalog of verified creator fonts."""
    return RECOMMENDED_CREATOR_FONTS
