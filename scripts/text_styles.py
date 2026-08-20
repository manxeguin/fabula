#!/usr/bin/env python3
"""Style loader for text overlay.

Loads style definitions from assets/text_styles.json and provides
helpers to:
- Resolve font path (bundled in assets/fonts/)
- Apply variable font weight axis
- Get a font for a given style and size
- Validate a style name

Usage:
    from text_styles import load_style, load_style_font, list_styles
    style = load_style("storybook")
    font = load_style_font(style, 80)
"""

import json
import sys
from pathlib import Path
from PIL import ImageFont


ASSETS_DIR = Path(__file__).parent.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
STYLES_FILE = ASSETS_DIR / "text_styles.json"


_styles_cache = None


def _load_styles_file():
    """Load the styles JSON (cached)."""
    global _styles_cache
    if _styles_cache is None:
        with open(STYLES_FILE) as f:
            data = json.load(f)
        # Strip the _comment key
        _styles_cache = {k: v for k, v in data.items() if not k.startswith("_")}
    return _styles_cache


def list_styles() -> list:
    """Return list of available style names."""
    return list(_load_styles_file().keys())


def load_style(name: str) -> dict:
    """Return the style dict for the given name. Raises ValueError if unknown."""
    styles = _load_styles_file()
    if name not in styles:
        raise ValueError(
            f"Unknown style: {name!r}. Available: {list(styles.keys())}"
        )
    return styles[name]


def resolve_font_path(font_filename: str) -> Path:
    """Resolve a font filename to its absolute path in assets/fonts/.
    Raises FileNotFoundError if the file doesn't exist.
    """
    path = FONTS_DIR / font_filename
    if not path.exists():
        raise FileNotFoundError(
            f"Font file not found: {path}\n"
            f"Download from Google Fonts: search for {font_filename}"
        )
    return path


def load_style_font(style: dict, size: int) -> ImageFont.FreeTypeFont:
    """Load the font for a style at the given size, applying weight axis if needed.

    Variable fonts (Fredoka, Quicksand) need set_variation_by_axes() to set
    the weight. Static fonts (Caveat Brush, Bungee) ignore the weight value.
    """
    path = resolve_font_path(style["font"])
    font = ImageFont.truetype(str(path), size)

    weight = style.get("font_weight", 400)
    if weight and weight != 400:
        # Variable font — set the weight axis
        try:
            # Quicksand has wght axis (single)
            # Fredoka has wght + wdth axes (two)
            if "fredoka" in style["font"].lower():
                # wght 100-900, wdth 75-125 (default 100 = normal width)
                font.set_variation_by_axes([weight, 100])
            else:
                # Single wght axis
                font.set_variation_by_axes([weight])
        except (AttributeError, Exception) as e:
            # Not a variable font, or axes not supported — silent fallback
            pass

    return font


def get_style_description(name: str) -> str:
    """Return the human-readable description for a style."""
    style = load_style(name)
    return style.get("description", "")


if __name__ == "__main__":
    # Quick test
    for s in list_styles():
        style = load_style(s)
        print(f"  {s:12} — {style['description'][:80]}")
        try:
            font = load_style_font(style, 40)
            print(f"    font OK: {font.font.family}")
        except Exception as e:
            print(f"    font ERR: {e}")
