#!/usr/bin/env python3
"""Moondream 2 object detection for layout refinement.

Detects things we want to AVOID covering with text (faces, hands, persons)
in the scene image, and computes the largest empty zone from the candidates.
Falls back to the original heuristic layout if the API fails.

Cost: ~$0.0001 per call. Only used when:
- cast.json has >1 character
- visual prompt has no clear framing keyword
- preset is 'quality'
- user explicitly asked for vision strategy
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from text_layout import Layout, _quadrant, _wide_band, _narrow_bottom, _top_band


MOONDREAM_ENDPOINT = "https://fal.run/fal-ai/moondream2/object-detection"
AVOID_OBJECTS = "face, hand, person"


def _get_fal_key() -> str:
    """Resolve FAL_KEY from env or ~/.zshrc."""
    key = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY", "")
    if not key:
        try:
            content = Path.home() / ".zshrc"
            if content.exists():
                for line in content.read_text().splitlines():
                    if line.startswith("FAL_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("'\"")
                        break
        except Exception:
            pass
    return key


def _upload_file(path: str) -> str:
    """Upload a file via fal_upload.py and return the public URL."""
    script = Path(__file__).parent / "fal_upload.py"
    r = subprocess.run(["python3", str(script), path],
                       capture_output=True, text=True)
    url = r.stdout.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"upload failed: {r.stdout[:200]} {r.stderr[:200]}")
    return url


def _call_moondream(image_url: str, prompt: str = AVOID_OBJECTS, threshold: float = 0.3) -> List[dict]:
    """Call Moondream 2 object detection. Returns list of detected objects with bboxes."""
    key = _get_fal_key()
    if not key:
        raise RuntimeError("FAL_KEY not set")

    payload = {
        "image_url": image_url,
        "prompt": prompt,
        "threshold": threshold,
    }
    r = subprocess.run(
        ["curl", "-s", "--max-time", "30", MOONDREAM_ENDPOINT,
         "-H", f"Authorization: Key {key}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Moondream returned non-JSON: {r.stdout[:200]}")

    if "objects" not in data:
        # Moondream 2 can return a single object via "object" or different schema
        # Try a few shapes
        if "object" in data:
            obj = data["object"]
            return [obj] if obj else []
        if "boxes" in data:
            return data.get("boxes", [])
        # No detections is valid
        return []
    return data.get("objects", [])


def _bbox_overlap_area(b1: dict, b2: dict) -> float:
    """Compute overlap area between two bounding boxes.

    Bounding box format: {"x_min": 0.0, "y_min": 0.0, "x_max": 1.0, "y_max": 1.0}
    All values normalized to [0, 1] for image coordinates.
    """
    x1 = max(b1.get("x_min", 0), b2.get("x_min", 0))
    y1 = max(b1.get("y_min", 0), b2.get("y_min", 0))
    x2 = min(b1.get("x_max", 1), b2.get("x_max", 1))
    y2 = min(b1.get("y_max", 1), b2.get("y_max", 1))
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _layout_to_normalized_bbox(layout: Layout, image_w: int, image_h: int) -> dict:
    """Convert a Layout (pixel coords) to a normalized bbox dict."""
    return {
        "x_min": layout.x / image_w,
        "y_min": layout.y / image_h,
        "x_max": (layout.x + layout.width) / image_w,
        "y_max": (layout.y + layout.height) / image_h,
    }


def _score_layout(layout: Layout, detected: List[dict], image_w: int, image_h: int) -> float:
    """Score a layout: lower is better (less overlap with detected objects)."""
    if not detected:
        return 0.0
    layout_bbox = _layout_to_normalized_bbox(layout, image_w, image_h)
    total_overlap = 0.0
    for obj in detected:
        bbox = obj.get("bounding_box", obj)
        total_overlap += _bbox_overlap_area(layout_bbox, bbox)
    return total_overlap


def _generate_candidates(image_w: int, image_h: int, visual_prompt: str) -> List[Layout]:
    """Generate a set of candidate layouts to score against Moondream's detections."""
    # Generate all 4 main candidates
    candidates = [
        _wide_band(image_w, image_h),
        _narrow_bottom(image_w, image_h),
        _top_band(image_w, image_h),
        _quadrant(image_w, image_h, "bottom-left"),
        _quadrant(image_w, image_h, "bottom-right"),
    ]
    return candidates


def refine_layout(image_path: str, heuristic_layout: Layout, visual_prompt: str) -> Layout:
    """Call Moondream 2 to refine the heuristic layout.

    Detects faces/hands/persons in the image, then scores candidate layouts
    by overlap. Returns the candidate with the least overlap. If Moondream
    fails for any reason, returns the heuristic layout unchanged.

    Cost: ~$0.0001 per call.
    """
    try:
        from PIL import Image
        img = Image.open(image_path)
        w, h = img.size
    except Exception as e:
        print(f"  WARN: cannot open image for Moondream: {e}")
        return heuristic_layout

    try:
        image_url = _upload_file(image_path)
    except Exception as e:
        print(f"  WARN: Moondream upload failed: {e}")
        return heuristic_layout

    try:
        detected = _call_moondream(image_url)
    except Exception as e:
        print(f"  WARN: Moondream call failed: {e}")
        return heuristic_layout

    if not detected:
        return heuristic_layout

    candidates = _generate_candidates(w, h, visual_prompt)
    scored = [(_score_layout(c, detected, w, h), c) for c in candidates]
    scored.sort(key=lambda t: t[0])
    best_score, best_layout = scored[0]
    return best_layout


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Moondream refinement on an image")
    parser.add_argument("image", help="Path to scene image")
    parser.add_argument("--visual-prompt", default="", help="Visual prompt text")
    args = parser.parse_args()

    from text_layout import decide_layout
    img = Image.open(args.image)
    heuristic = decide_layout(img.size[0], img.size[1], args.visual_prompt)
    print(f"Heuristic: x={heuristic.x} y={heuristic.y} w={heuristic.width} h={heuristic.height}")
    refined = refine_layout(args.image, heuristic, args.visual_prompt)
    print(f"Refined:   x={refined.x} y={refined.y} w={refined.width} h={refined.height}")
