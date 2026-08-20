#!/usr/bin/env python3
"""Layout engine for text overlay on scene images.

Given image dimensions and the visual prompt text, decide where the label
should go. Heuristic-only in this version — Moondream fallback is in
text_moondream.py and called from overlay_text.py.

Layout strategies:
- wide establishing shot / wide shot → wide band, full width, 15% height, 8% from bottom
- close-up / extreme close-up → narrow bottom, 50% width, 18% height
- over-the-shoulder / POV → top band, 15% height, 8% from top
- default (medium shot, full shot) → bottom-left quadrant, 55% width, 20% height
"""

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Layout:
    x: int
    y: int
    width: int
    height: int
    font_size: int
    alignment: str  # "left" | "center" | "right"
    needs_panel: bool  # whether a background panel is recommended
    style: str  # "narration" — only one for v1

    def to_dict(self):
        return asdict(self)


def _wide_band(w: int, h: int) -> Layout:
    margin_x = int(w * 0.05)
    return Layout(
        x=margin_x,
        y=int(h * 0.77),
        width=w - 2 * margin_x,
        height=int(h * 0.15),
        font_size=int(h * 0.085),
        alignment="center",
        needs_panel=True,
        style="narration",
    )


def _narrow_bottom(w: int, h: int) -> Layout:
    margin_x = int(w * 0.20)
    return Layout(
        x=margin_x,
        y=int(h * 0.74),
        width=w - 2 * margin_x,
        height=int(h * 0.18),
        font_size=int(h * 0.095),
        alignment="center",
        needs_panel=False,
        style="narration",
    )


def _top_band(w: int, h: int) -> Layout:
    margin_x = int(w * 0.05)
    return Layout(
        x=margin_x,
        y=int(h * 0.06),
        width=w - 2 * margin_x,
        height=int(h * 0.15),
        font_size=int(h * 0.085),
        alignment="center",
        needs_panel=True,
        style="narration",
    )


def _quadrant(w: int, h: int, corner: str = "bottom-left") -> Layout:
    """Bottom-left or bottom-right quadrant. For default medium shots."""
    if corner == "bottom-left":
        return Layout(
            x=int(w * 0.04),
            y=int(h * 0.72),
            width=int(w * 0.55),
            height=int(h * 0.20),
            font_size=int(h * 0.10),
            alignment="left",
            needs_panel=False,
            style="narration",
        )
    # bottom-right
    return Layout(
        x=int(w * 0.41),
        y=int(h * 0.72),
        width=int(w * 0.55),
        height=int(h * 0.20),
        font_size=int(h * 0.10),
        alignment="right",
        needs_panel=False,
        style="narration",
    )


def _detect_framing(visual_prompt: str) -> Optional[str]:
    """Return framing key if recognized, else None.

    Checks for explicit framing keywords in the visual prompt text.
    """
    lower = visual_prompt.lower()
    if re.search(r"wide[\s-]?(?:establishing[\s-]?)?shot|establishing[\s-]?shot", lower):
        return "wide"
    if re.search(r"close[\s-]?up|extreme[\s-]?close[\s-]?up", lower):
        return "close"
    if re.search(r"over[\s-]?the[\s-]?shoulder|point[\s-]?of[\s-]?view|\bpov\b", lower):
        return "top"
    return None


def decide_layout(
    image_w: int,
    image_h: int,
    visual_prompt: str,
    preset: str = "quality",
) -> Layout:
    """Decide the layout for the label based on the visual prompt.

    Args:
        image_w: image width in pixels
        image_h: image height in pixels
        visual_prompt: the contents of the `## Visual Prompt` section
        preset: generation preset (debug | testing | budget | quality)

    Returns:
        Layout with x, y, width, height, font_size, alignment, needs_panel, style
    """
    framing = _detect_framing(visual_prompt)

    if framing == "wide":
        return _wide_band(image_w, image_h)
    if framing == "close":
        return _narrow_bottom(image_w, image_h)
    if framing == "top":
        return _top_band(image_w, image_h)

    # Default: medium/full shot → bottom-left quadrant
    return _quadrant(image_w, image_h, corner="bottom-left")


def pick_better_quadrant(image_w: int, image_h: int, image_path: str = None) -> Layout:
    """For default (medium-shot) scenes, pick the bottom quadrant with the
    lower variance (less busy). Local, no API call.

    Reads the image at image_path, samples both bottom quadrants, returns
    the one with lower standard deviation. If image_path is None, returns
    bottom-left.
    """
    if not image_path:
        return _quadrant(image_w, image_h, "bottom-left")

    try:
        from PIL import Image
        img = Image.open(image_path).convert("L")
        left_box = (
            int(image_w * 0.04),
            int(image_h * 0.72),
            int(image_w * 0.04) + int(image_w * 0.55),
            int(image_h * 0.72) + int(image_h * 0.20),
        )
        right_box = (
            int(image_w * 0.41),
            int(image_h * 0.72),
            int(image_w * 0.41) + int(image_w * 0.55),
            int(image_h * 0.72) + int(image_h * 0.20),
        )
        left_zone = img.crop(left_box)
        right_zone = img.crop(right_box)
        left_pixels = list(left_zone.getdata())
        right_pixels = list(right_zone.getdata())
        left_var = _std(left_pixels)
        right_var = _std(right_pixels)
        # Lower variance = more uniform = better place for text
        if right_var < left_var:
            return _quadrant(image_w, image_h, "bottom-right")
        return _quadrant(image_w, image_h, "bottom-left")
    except Exception:
        return _quadrant(image_w, image_h, "bottom-left")


def _std(values):
    """Standard deviation of a list of numbers."""
    if not values:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return var ** 0.5


if __name__ == "__main__":
    # Quick test
    layouts = {
        "wide": "A wide establishing shot of the classroom at dawn.",
        "close": "Extreme close-up of Claudia's pouting face.",
        "top": "Over-the-shoulder POV looking down at the toy.",
        "default": "Medium shot, 50mm lens, soft morning light.",
    }
    for name, vp in layouts.items():
        layout = decide_layout(1376, 768, vp)
        print(f"  [{name:8}] x={layout.x:4} y={layout.y:4} w={layout.width:4} h={layout.height:3} font={layout.font_size:3} panel={layout.needs_panel}")


if __name__ == "__main__":
    # Quick test
    layouts = {
        "wide": "A wide establishing shot of the classroom at dawn.",
        "close": "Extreme close-up of Claudia's pouting face.",
        "top": "Over-the-shoulder POV looking down at the toy.",
        "default": "Medium shot, 50mm lens, soft morning light.",
    }
    for name, vp in layouts.items():
        layout = decide_layout(1376, 768, vp)
        print(f"  [{name:8}] x={layout.x:4} y={layout.y:4} w={layout.width:4} h={layout.height:3} font={layout.font_size:3} panel={layout.needs_panel}")
