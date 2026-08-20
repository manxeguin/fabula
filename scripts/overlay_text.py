#!/usr/bin/env python3
"""Overlay short labels onto scene images for the PDF storybook.

Reads `## Label` and `## Visual Prompt` from each scene.md, decides a
layout (heuristic + optional Moondream 2 refinement), and renders text
onto a copy of scene.png. Writes to scenes/<n>/pages/01.png.

The original scene.png is NEVER modified.

Usage:
    python3 overlay_text.py <story_dir> [--force] [--strategy hybrid|heuristic|vision] [--style storybook|handwritten|movie|whimsical]
"""

import argparse
import json
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from text_layout import decide_layout, Layout
from text_render import render_label
from text_styles import list_styles


GENERATION_LOG = "generation_log.jsonl"


def parse_scene_md(scene_md_path: Path):
    """Extract ## Label and ## Visual Prompt from scene.md.

    Returns (label_or_None, visual_prompt_text).
    """
    content = scene_md_path.read_text()
    label_match = re.search(r"## Label\s*\n+(.+?)(?:\n##|\Z)", content, re.DOTALL)
    vp_match = re.search(r"## Visual Prompt\s*\n+(.+?)(?:\n##|\Z)", content, re.DOTALL)
    label = label_match.group(1).strip() if label_match else None
    visual_prompt = vp_match.group(1).strip() if vp_match else ""
    return label, visual_prompt


def derive_label_from_title(scene_md_path: Path) -> str:
    """Fallback: derive label from # Scene N: <Title> in sentence case."""
    content = scene_md_path.read_text()
    m = re.search(r"# Scene \d+:\s*(.+)", content)
    if m:
        title = m.group(1).strip()
        words = title.split()
        if words:
            return words[0].capitalize() + " " + " ".join(w.lower() for w in words[1:])
    return "Sin título"


def log_overlay_entry(
    story_dir: Path,
    scene_name: str,
    layout: Layout,
    label: str,
    model_used: str,
    cost: float = 0.0,
    style: str = "storybook",
):
    """Append an entry to the story's generation_log.jsonl."""
    log_path = story_dir / GENERATION_LOG
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "asset": "text_overlay",
        "path": f"scenes/{scene_name}/pages/01.png",
        "model": model_used,
        "params": {
            "label": label,
            "style": style,
            "layout": layout.to_dict(),
        },
        "cost": {"unit": "image", "price": cost} if cost > 0 else {"unit": "image", "price": 0.0},
        "preset": "overlay",
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def has_multi_char_cast(story_dir: Path) -> bool:
    """Check if cast.json has more than one character."""
    cast_json = story_dir / "cast.json"
    if not cast_json.exists():
        return False
    try:
        cast = json.loads(cast_json.read_text())
        return len(cast.get("cast", [])) > 1
    except Exception:
        return False


def should_use_moondream(
    strategy: str,
    has_multi_char: bool,
    visual_prompt: str,
    label: str,
) -> bool:
    """Decide whether to call Moondream 2 for refinement.

    NOTE: Moondream 2 object-detection ($0.02/image, single object per call)
    is not cost-effective for detecting multiple object types per scene.
    We use local luminance-based quadrant selection instead.

    Kept as a hook for future vision-based refinement, but disabled by default.
    """
    if strategy == "vision":
        return True
    return False


def overlay_scene(
    scene_dir: Path,
    story_dir: Path,
    strategy: str = "hybrid",
    force: bool = False,
    style: str = "storybook",
) -> tuple[bool, str, dict]:
    """Overlay text on a single scene. Returns (success, message, stats)."""
    scene_md = scene_dir / "scene.md"
    scene_png = scene_dir / "scene.png"
    output_png = scene_dir / "pages" / "01.png"

    if not scene_png.exists():
        return False, "no scene.png", {}
    if output_png.exists() and not force:
        return True, "skipped (already exists)", {}

    label, visual_prompt = parse_scene_md(scene_md)
    if not label:
        label = derive_label_from_title(scene_md)
        print(f"  WARN: {scene_md.name} has no ## Label, derived: {label!r}")

    from PIL import Image
    img = Image.open(scene_png)
    w, h = img.size

    has_multi_char = has_multi_char_cast(story_dir)
    layout = decide_layout(w, h, visual_prompt, preset="quality")
    model_used = "heuristic"
    cost = 0.0

    # For default (medium-shot) layouts, refine by sampling both bottom
    # quadrants and picking the one with lower variance (less busy).
    from text_layout import _detect_framing, pick_better_quadrant
    if _detect_framing(visual_prompt) is None and strategy != "vision":
        # Default quadrant — pick the better side
        layout = pick_better_quadrant(w, h, str(scene_png))
        model_used = "luminance-heuristic"

    if should_use_moondream(strategy, has_multi_char, visual_prompt, label):
        try:
            from text_moondream import refine_layout
            layout = refine_layout(str(scene_png), layout, visual_prompt)
            model_used = "moondream2+heuristic"
            cost = 0.02
        except Exception as e:
            print(f"  WARN: Moondream failed: {e}, using heuristic")

    output_png.parent.mkdir(parents=True, exist_ok=True)
    stats = render_label(str(scene_png), str(output_png), label, layout, style_name=style)
    log_overlay_entry(story_dir, scene_dir.name, layout, label, model_used, cost, style=style)
    return True, "ok", stats


def main():
    parser = argparse.ArgumentParser(description="Overlay text labels onto scene images")
    parser.add_argument("story_dir", help="Path to story directory")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing overlays")
    parser.add_argument("--strategy", choices=["hybrid", "heuristic", "vision"],
                        default="hybrid", help="Layout strategy (default: hybrid)")
    parser.add_argument("--style", choices=list_styles(),
                        default="storybook",
                        help=f"Typography style (default: storybook). Available: {', '.join(list_styles())}")
    args = parser.parse_args()

    story_dir = Path(args.story_dir)
    if not story_dir.exists():
        print(f"ERROR: directory not found: {story_dir}")
        return 1

    scenes_dir = story_dir / "scenes"
    if not scenes_dir.exists():
        print(f"ERROR: no scenes/ directory in {story_dir}")
        return 1

    print(f"Overlaying labels for {story_dir.name} (strategy={args.strategy}, style={args.style})")

    overlay_count = 0
    skip_count = 0
    for scene_dir in sorted(scenes_dir.iterdir()):
        if not scene_dir.is_dir():
            continue
        ok, msg, stats = overlay_scene(scene_dir, story_dir,
                                        strategy=args.strategy, force=args.force,
                                        style=args.style)
        status = "OK  " if ok else "SKIP"
        if "luminance" in stats:
            extra = f" (lum={stats['luminance']}, var={stats['variance']}, style={stats.get('style')})"
        else:
            extra = ""
        print(f"  [{status}] {scene_dir.name}: {msg}{extra}")
        if ok and msg == "ok":
            overlay_count += 1
        elif msg.startswith("skipped"):
            skip_count += 1

    print(f"\nDone: {overlay_count} overlaid, {skip_count} skipped")
    return 0


if __name__ == "__main__":
    exit(main())
