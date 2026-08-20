#!/usr/bin/env python3
"""Font loader for text overlay.

Tries bundled font (assets/fonts/CormorantGaramond-Italic.ttf) first,
then falls back to system fonts. Caches loaded fonts for performance.

Usage:
    from text_fonts import load_font
    font = load_font(size=80, italic=True)
"""

from pathlib import Path
from PIL import ImageFont


ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"


# System fallbacks (macOS first, Linux as backup). Order matters — first existing wins.
SYSTEM_FALLBACKS = {
    "italic": [
        "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
        "/System/Library/Fonts/Supplemental/Optima Italic.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    ],
    "regular": [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    ],
}


_font_cache = {}


def _bundled_font_path(italic: bool) -> Path:
    """Return path to bundled font if it exists, else None."""
    name = "CormorantGaramond-Italic.ttf" if italic else "CormorantGaramond-Regular.ttf"
    path = FONTS_DIR / name
    return path if path.exists() else None


def _first_existing(paths):
    for p in paths:
        if Path(p).exists():
            return p
    return None


def load_font(size: int, italic: bool = True) -> ImageFont.FreeTypeFont:
    """Load a font at the given size. Cached for performance.

    Priority:
    1. Bundled font in assets/fonts/ (Cormorant Garamond)
    2. System font (Georgia Italic on macOS, DejaVu/Liberation on Linux)
    3. Pillow's default font (last resort, no kerning)
    """
    key = (size, italic)
    if key in _font_cache:
        return _font_cache[key]

    # 1. Bundled
    bundled = _bundled_font_path(italic)
    if bundled:
        try:
            font = ImageFont.truetype(str(bundled), size)
            _font_cache[key] = font
            return font
        except Exception:
            pass  # fall through to system

    # 2. System fallback
    fallbacks = SYSTEM_FALLBACKS["italic" if italic else "regular"]
    system_path = _first_existing(fallbacks)
    if system_path:
        try:
            font = ImageFont.truetype(system_path, size)
            _font_cache[key] = font
            return font
        except Exception as e:
            print(f"  WARN: failed to load {system_path}: {e}")

    # 3. Default (Pillow's bitmap font, no kerning — looks bad but works)
    print("  WARN: no serif font found, using Pillow default (will look basic)")
    font = ImageFont.load_default()
    _font_cache[key] = font
    return font


def get_active_font_name() -> str:
    """Return human-readable name of the font that will be used."""
    bundled = _bundled_font_path(italic=True)
    if bundled:
        return bundled.name
    system_path = _first_existing(SYSTEM_FALLBACKS["italic"])
    if system_path:
        return Path(system_path).name
    return "default"


if __name__ == "__main__":
    # Quick test
    print(f"Active italic font: {get_active_font_name()}")
    font = load_font(80, italic=True)
    print(f"Loaded: {font}")
