#!/usr/bin/env python3
"""Style-aware text overlay renderer.

Renders a label onto a copy of an image using a typography style from
text_styles.json. Supports:
- 4 bundled styles (storybook, handwritten, movie, whimsical)
- Text outline (stroke)
- Multi-layer drop shadow (stacked shadows for 3D effect)
- Soft glow (whimsical)
- Background panel (rounded rect)
- Letter spacing
- Rotation
- Decorative shapes (stars, sparkles, dots, hearts)

The original image is NEVER modified — we work on a copy.

Usage:
    from text_render import render_label
    render_label(image_path, output_path, "El abrazo",
                 layout, style_name="storybook")
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from text_layout import Layout
from text_styles import load_style, load_style_font
from text_decorations import composite_decoration


# ---------------------------------------------------------------------------
# Helpers: color, panel, rotation
# ---------------------------------------------------------------------------

def _apply_shadow_to_layer(layer, shadow_def):
    """Apply a shadow to a text layer. Returns a new RGBA layer with shadow.

    If shadow_def has a 'stack' key, draws multiple stacked shadows.
    """
    if not shadow_def:
        return layer

    if "stack" in shadow_def:
        # Multi-layer shadow (3D effect)
        result = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        for s in shadow_def["stack"]:
            offset = s.get("offset", [2, 2])
            blur = s.get("blur", 0)
            color = tuple(s.get("color", [0, 0, 0, 200]))
            shadow_layer = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow_layer)
            sd.bitmap((offset[0], offset[1]), layer.split()[0].point(lambda v: 255 if v > 0 else 0), fill=color)
            if blur > 0:
                shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur))
            result = Image.alpha_composite(result, shadow_layer)
        return result

    # Single shadow
    color = tuple(shadow_def.get("color", [0, 0, 0, 128]))
    offset = shadow_def.get("offset", [2, 2])
    blur = shadow_def.get("blur", 4)

    shadow_layer = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    # Use the alpha channel of the text as a mask
    alpha = layer.split()[3]
    sd = ImageDraw.Draw(shadow_layer)
    sd.bitmap((offset[0], offset[1]), alpha, fill=color)
    if blur > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur))
    return shadow_layer


def _apply_glow(layer, glow_def):
    """Apply a soft glow halo around the text. Returns a new RGBA layer with glow."""
    if not glow_def:
        return None
    color = tuple(glow_def.get("color", [255, 255, 255, 80]))
    blur = glow_def.get("blur", 10)

    glow_layer = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    alpha = layer.split()[3]
    gd = ImageDraw.Draw(glow_layer)
    gd.bitmap((0, 0), alpha, fill=color)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=blur))
    return glow_layer


def _draw_background_panel(canvas_size, layout, panel_def):
    """Draw the background panel (rounded rect). Returns a new RGBA layer."""
    if not panel_def:
        return None
    color = tuple(panel_def.get("color", [0, 0, 0, 100]))
    radius_pct = panel_def.get("corner_radius_pct", 12)
    pad = int(layout.font_size * 0.35)

    px0 = layout.x + pad // 2
    py0 = layout.y + pad // 2
    px1 = layout.x + layout.width - pad // 2
    py1 = layout.y + layout.height - pad // 2
    radius = max(4, int((px1 - px0) * radius_pct / 100))

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([px0, py0, px1, py1], radius=radius, fill=color)
    return layer


def _rotate_layer(layer, angle_deg):
    """Rotate a layer around its center. Returns a new RGBA layer (same size)."""
    if not angle_deg:
        return layer
    return layer.rotate(angle_deg, resample=Image.BICUBIC, expand=False, center=(layer.size[0] // 2, layer.size[1] // 2))


# ---------------------------------------------------------------------------
# Text drawing with letter spacing
# ---------------------------------------------------------------------------

def _draw_text_with_spacing(d, text, font, x, y, fill, spacing_pct=0):
    """Draw text with custom letter spacing. Returns list of char positions drawn."""
    if not spacing_pct:
        d.text((x, y), text, font=font, fill=fill)
        return

    # Draw character by character with custom spacing
    spacing_factor = 1.0 + (spacing_pct / 100.0)
    cur_x = x
    for ch in text:
        bbox = d.textbbox((0, 0), ch, font=font)
        ch_w = bbox[2] - bbox[0]
        d.text((cur_x - bbox[0], y), ch, font=font, fill=fill)
        cur_x += int(ch_w * spacing_factor)


def _measure_text(text, font, spacing_pct=0):
    """Measure text width/height with custom spacing. Returns (width, height, offset_x, offset_y)."""
    dummy = Image.new("RGBA", (1, 1))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    if spacing_pct:
        spacing_factor = 1.0 + (spacing_pct / 100.0)
        # Per-character width
        char_widths = []
        for ch in text:
            cb = d.textbbox((0, 0), ch, font=font)
            char_widths.append(cb[2] - cb[0])
        w = int(sum(cw * spacing_factor for cw in char_widths) - char_widths[-1] * (spacing_factor - 1))

    return w, h, bbox[0], bbox[1]


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_label(image_path, output_path, text, layout, style_name="storybook"):
    """Render a label onto a copy of the image, save to output_path.

    Args:
        image_path: path to source image
        output_path: path to save the overlaid image
        text: the label string
        layout: Layout object (from text_layout.py)
        style_name: one of "storybook", "handwritten", "movie", "whimsical"

    Returns:
        dict with stats (luminance, variance, style, etc.)
    """
    style = load_style(style_name)

    # 1. Open image as RGBA copy
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size

    # 2. Sample luminance in the layout zone
    zone_x0 = max(0, layout.x)
    zone_y0 = max(0, layout.y)
    zone_x1 = min(w, layout.x + layout.width)
    zone_y1 = min(h, layout.y + layout.height)
    if zone_x1 <= zone_x0 or zone_y1 <= zone_y0:
        zone_x0, zone_y0, zone_x1, zone_y1 = 0, 0, w, h
    zone = img.crop((zone_x0, zone_y0, zone_x1, zone_y1))
    pixels = list(zone.convert("L").getdata())
    luminance = sum(pixels) / (len(pixels) * 255.0) if pixels else 0.5
    var = 0.0
    if pixels:
        mean = sum(pixels) / len(pixels)
        var = (sum((p - mean) ** 2 for p in pixels) / len(pixels)) ** 0.5 / 128.0

    # 3. Load font with style-specific size multiplier
    font_size = int(layout.font_size * style.get("font_size_multiplier", 1.0))
    font = load_style_font(style, font_size)

    # 4. Measure text
    text_w, text_h, bbox_x, bbox_y = _measure_text(
        text, font, style.get("letter_spacing_pct", 0)
    )
    if text_w <= 0 or text_h <= 0:
        img.convert("RGB").save(output_path, "PNG", optimize=True)
        return {"luminance": round(luminance, 3), "variance": round(var, 3), "style": style_name, "rendered": "empty"}

    # 5. Compute text position (center in layout zone)
    alignment = layout.alignment
    if alignment == "left":
        tx = layout.x + int(layout.width * 0.05)
    elif alignment == "right":
        tx = layout.x + layout.width - text_w - int(layout.width * 0.05)
    else:  # center
        tx = layout.x + (layout.width - text_w) // 2
    ty = layout.y + (layout.height - text_h) // 2

    # 6. Build layers
    # 6a. Foreground text layer
    text_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(text_layer)
    text_color = tuple(style["text_color"])
    spacing_pct = style.get("letter_spacing_pct", 0)
    _draw_text_with_spacing(td, text, font, tx, ty, text_color, spacing_pct)

    # 6b. Outline layer (drawn at +N px in outline color via stroke_width)
    outline_w = style.get("outline_width", 0)
    if outline_w > 0:
        outline_color = tuple(style["outline_color"])
        # Draw text again with stroke as the outline (Pillow 6.2+)
        # We draw the outline first, then the text on top
        for dx in range(-outline_w, outline_w + 1):
            for dy in range(-outline_w, outline_w + 1):
                if dx * dx + dy * dy <= outline_w * outline_w:
                    _draw_text_with_spacing(td, text, font, tx + dx, ty + dy, outline_color, spacing_pct)
        # Redraw the text on top to ensure it's on top of the outline
        _draw_text_with_spacing(td, text, font, tx, ty, text_color, spacing_pct)

    # 6c. Apply rotation if specified
    rotation = style.get("rotation_deg", 0)
    if rotation:
        text_layer = _rotate_layer(text_layer, rotation)

    # 7. Build composite
    composed = img

    # 7a. Background panel
    bg_panel = _draw_background_panel(img.size, layout, style.get("background"))
    if bg_panel is not None:
        composed = Image.alpha_composite(composed, bg_panel)

    # 7b. Decorations (drawn behind text)
    deco_def = style.get("decorations")
    if deco_def:
        deco_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        # Text is at tx..tx+text_w vertically centered at ty+text_h/2
        text_center_y = ty + text_h // 2

        # Circle background (drawn first, behind everything)
        if deco_def.get("circle_background"):
            from text_decorations import draw_circle_background
            circle_color = tuple(deco_def.get("circle_color", [255, 220, 130, 230]))
            # Circle radius = max of text_w or text_h / 2 + padding
            radius = int(max(text_w, text_h) * 0.65)
            circle_layer = draw_circle_background(
                img.size, tx + text_w // 2, text_center_y, radius, circle_color,
            )
            composed = Image.alpha_composite(composed, circle_layer)

        # Underline (drawn after circle, before side decorations)
        if deco_def.get("underline"):
            from text_decorations import draw_underline
            underline_color = tuple(deco_def.get("underline_color", [255, 200, 100, 255]))
            # Underline goes 20% of font size below text
            underline_y = ty + text_h + int(layout.font_size * 0.20)
            underline_layer = draw_underline(
                img.size,
                tx, tx + text_w, underline_y,
                underline_color,
                wave_amplitude=max(2, int(layout.font_size * 0.04)),
                wave_period=max(30, int(layout.font_size * 0.5)),
                thickness=max(2, int(layout.font_size * 0.04)),
            )
            composed = Image.alpha_composite(composed, underline_layer)

        # Side decorations (stars, sparkles, dots, hearts)
        if deco_def.get("left") or deco_def.get("right"):
            deco_color = tuple(deco_def.get("color", [255, 220, 130, 255]))
            deco_size = int(layout.font_size * deco_def.get("size_pct", 60) / 100.0)
            spacing = deco_def.get("spacing_px", 30)
            if deco_def.get("left"):
                composite_decoration(
                    deco_layer, deco_def["left"],
                    tx - spacing, text_center_y,
                    deco_size, deco_color,
                )
            if deco_def.get("right"):
                composite_decoration(
                    deco_layer, deco_def["right"],
                    tx + text_w + spacing, text_center_y,
                    deco_size, deco_color,
                )
            composed = Image.alpha_composite(composed, deco_layer)

    # 7c. Glow (behind shadow, behind text)
    glow_def = style.get("glow")
    if glow_def:
        glow_layer = _apply_glow(text_layer, glow_def)
        if glow_layer is not None:
            composed = Image.alpha_composite(composed, glow_layer)

    # 7d. Shadow (behind text)
    shadow_def = style.get("shadow")
    if shadow_def:
        shadow_layer = _apply_shadow_to_layer(text_layer, shadow_def)
        composed = Image.alpha_composite(composed, shadow_layer)

    # 7e. Text foreground
    composed = Image.alpha_composite(composed, text_layer)

    # 8. Save
    composed.convert("RGB").save(output_path, "PNG", optimize=True)

    return {
        "luminance": round(luminance, 3),
        "variance": round(var, 3),
        "style": style_name,
        "text_position": (tx, ty),
        "text_size": (text_w, text_h),
        "rendered": "ok",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    from text_layout import Layout

    parser = argparse.ArgumentParser(description="Render a label onto an image using a named style")
    parser.add_argument("image", help="Input image path")
    parser.add_argument("output", help="Output image path")
    parser.add_argument("text", help="Label text")
    parser.add_argument("--style", default="storybook",
                        choices=["storybook", "handwritten", "movie", "whimsical"],
                        help="Typography style (default: storybook)")
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--width", type=int, default=1000)
    parser.add_argument("--height", type=int, default=200)
    parser.add_argument("--font-size", type=int, default=80)
    args = parser.parse_args()

    layout = Layout(
        x=args.x, y=args.y,
        width=args.width, height=args.height,
        font_size=args.font_size,
        alignment="center", needs_panel=False, style="narration",
    )
    stats = render_label(args.image, args.output, args.text, layout, args.style)
    print(f"Stats: {stats}")
