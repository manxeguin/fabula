#!/usr/bin/env python3
"""Decorative shape drawer for text overlay.

Draws small shapes (star, sparkle, dot, heart) onto a transparent RGBA layer.
Used by the 'whimsical' style to add picture-book decoration next to the text.

All shapes are drawn at a given center (x, y) with a given size (radius in px)
in the given RGBA color. The result is a separate RGBA image that the caller
composites onto the main scene.

Usage:
    from text_decorations import draw_decoration
    layer = draw_decoration('star', center_x=100, center_y=200,
                             size=20, color=(255, 220, 130, 255),
                             canvas_size=(300, 300))
    # layer is a PIL Image (RGBA) with the star centered
"""

import math
from PIL import Image, ImageDraw


def _star_points(cx, cy, outer_r, inner_r, num_points=5):
    """Compute 10 points (5 outer + 5 inner) for a star polygon."""
    pts = []
    for i in range(num_points * 2):
        angle = math.pi / 2 + i * math.pi / num_points  # start at top
        r = outer_r if i % 2 == 0 else inner_r
        x = cx + r * math.cos(angle)
        y = cy - r * math.sin(angle)  # negative because y is inverted in PIL
        pts.append((x, y))
    return pts


def _sparkle_points(cx, cy, outer_r, inner_r, num_points=4):
    """Compute points for a 4-pointed sparkle (concave diamond)."""
    return _star_points(cx, cy, outer_r, inner_r, num_points)


def _star(canvas_size, cx, cy, size, color, num_points=5):
    """Draw a 5-pointed star centered at (cx, cy) with given size (radius)."""
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    inner_r = size * 0.4  # classic star ratio
    pts = _star_points(cx, cy, size, inner_r, num_points)
    d.polygon(pts, fill=color)
    return img


def _sparkle(canvas_size, cx, cy, size, color):
    """Draw a 4-pointed sparkle (concave star) with a small center dot.

    The 4-pointed sparkle is the classic Disney/Pixar "magic" shape:
    - 4 thin points (top, bottom, left, right)
    - small filled center
    """
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Long thin arms
    inner_r = size * 0.15  # very thin
    pts = _sparkle_points(cx, cy, size, inner_r, 4)
    d.polygon(pts, fill=color)
    # Center dot (slightly smaller, brighter)
    center_color = (
        min(color[0] + 30, 255),
        min(color[1] + 30, 255),
        min(color[2] + 30, 255),
        color[3],
    )
    d.ellipse(
        (cx - size * 0.12, cy - size * 0.12, cx + size * 0.12, cy + size * 0.12),
        fill=center_color,
    )
    return img


def _dot(canvas_size, cx, cy, size, color):
    """Draw a filled circle (dot)."""
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse(
        (cx - size, cy - size, cx + size, cy + size),
        fill=color,
    )
    return img


def _heart(canvas_size, cx, cy, size, color):
    """Draw a heart shape using two circles + a triangle."""
    img = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Two top circles
    r = size * 0.55
    d.ellipse((cx - size, cy - size * 0.5, cx, cy + size * 0.5), fill=color)
    d.ellipse((cx, cy - size * 0.5, cx + size, cy + size * 0.5), fill=color)
    # Bottom triangle (V shape)
    d.polygon(
        [
            (cx - size * 0.95, cy + size * 0.1),
            (cx + size * 0.95, cy + size * 0.1),
            (cx, cy + size * 1.3),
        ],
        fill=color,
    )
    return img


_DECORATION_FUNCS = {
    "star": _star,
    "sparkle": _sparkle,
    "dot": _dot,
    "heart": _heart,
}


def draw_decoration(kind, size, color):
    """Draw a decoration centered on a small transparent canvas.

    Args:
        kind: one of "star", "sparkle", "dot", "heart"
        size: radius in pixels
        color: RGBA tuple

    Returns:
        PIL.Image (RGBA) with the decoration centered. The caller composites
        this at the desired position using alpha_composite(layer, (x, y))
        where (x, y) is the top-left corner such that the decoration center
        lands at (x + w/2, y + h/2).
    """
    if kind not in _DECORATION_FUNCS:
        raise ValueError(
            f"Unknown decoration: {kind!r}. Available: {list(_DECORATION_FUNCS.keys())}"
        )

    margin = max(4, int(size * 0.4))
    s = int(size * 2 + margin * 2)
    canvas_size = (s, s)
    center_x = s // 2
    center_y = s // 2

    return _DECORATION_FUNCS[kind](canvas_size, center_x, center_y, size, color)


def composite_decoration(target, kind, center_x, center_y, size, color):
    """Helper: draw a decoration and composite it onto target so its center is at (center_x, center_y).

    Args:
        target: PIL.Image (RGBA) to composite onto
        kind: decoration name
        center_x, center_y: pixel position for the decoration CENTER in target
        size: radius in pixels
        color: RGBA tuple

    Returns:
        target (mutated in place, also returned)
    """
    layer = draw_decoration(kind, size, color)
    lw, lh = layer.size
    target.alpha_composite(layer, (int(center_x - lw // 2), int(center_y - lh // 2)))
    return target


def draw_underline(canvas_size, x0, x1, y, color, wave_amplitude=4, wave_period=40, thickness=3):
    """Draw a wavy underline below text from (x0, y) to (x1, y).

    Args:
        canvas_size: (width, height) of the canvas
        x0, x1: horizontal range
        y: vertical baseline
        color: RGBA tuple
        wave_amplitude: how far the wave dips (px)
        wave_period: distance between wave peaks (px)
        thickness: stroke width in px

    Returns:
        PIL.Image (RGBA) with the wavy line drawn
    """
    import math
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # Draw the wave as a series of small line segments
    step = 2  # smaller = smoother
    points = []
    for x in range(int(x0), int(x1) + 1, step):
        # Sine wave
        dy = wave_amplitude * math.sin(2 * math.pi * (x - x0) / wave_period)
        points.append((x, y + dy))
    if len(points) >= 2:
        d.line(points, fill=color, width=thickness, joint="curve")
    return layer


def draw_circle_background(canvas_size, cx, cy, radius, color):
    """Draw a filled circle (ellipse) at the given position.

    Useful as a "spotlight" or "highlight" behind text.
    """
    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=color,
    )
    return layer


def list_decorations():
    """Return list of available decoration names."""
    return list(_DECORATION_FUNCS.keys())


if __name__ == "__main__":
    # Quick test: render all 4 decorations on a 200x400 strip
    img = Image.new("RGBA", (200, 400), (255, 255, 255, 255))
    for i, kind in enumerate(list_decorations()):
        composite_decoration(img, kind, 100, 50 + i * 100, 30, (255, 180, 50, 255))
    img.convert("RGB").save("/tmp/decorations_test.png")
    print("Saved /tmp/decorations_test.png")
