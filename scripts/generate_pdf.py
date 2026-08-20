#!/usr/bin/env python3
"""Generate a printable storybook PDF from a Fábula story — images only.

Reads overlaid images from scenes/<n>/pages/01.png if they exist
(produced by scripts/overlay_text.py), else falls back to clean scene.png.
Cover and back-cover logic unchanged.
"""

import argparse
import hashlib
import os
import re
from pathlib import Path
from fpdf import FPDF
from PIL import Image

# A4 landscape: 297mm × 210mm
PAGE_W, PAGE_H = 297, 210
TMP_DIR = "/tmp/fabula_pdf"


def optimize_image(img_path, max_w=4000, max_h=2250):
    """Resize and convert to JPEG. Cache key is the full path hash to avoid
    collisions between scene.png and pages/01.png in the same scene dir.
    Regenerates if source is newer than cached file.
    """
    os.makedirs(TMP_DIR, exist_ok=True)
    key = hashlib.md5(img_path.encode()).hexdigest()[:12]
    out_path = os.path.join(TMP_DIR, f"{key}.jpg")

    # Invalidate cache if source is newer than cached version
    if os.path.exists(out_path) and os.path.exists(img_path):
        if os.path.getmtime(img_path) > os.path.getmtime(out_path):
            os.remove(out_path)

    if not os.path.exists(out_path):
        img = Image.open(img_path).convert("RGB")
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        img.save(out_path, "JPEG", quality=92)
    return out_path


class Storybook(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=0)

    def image_page(self, img_path):
        self.add_page()
        if img_path and os.path.exists(img_path):
            # Full-bleed landscape image
            self.image(img_path, x=0, y=0, w=PAGE_W, h=PAGE_H)

    def cover_page(self, img_path):
        self.add_page()
        if img_path and os.path.exists(img_path):
            self.image(img_path, x=0, y=0, w=PAGE_W, h=PAGE_H)

    def generate(self, story_dir, output_path):
        story_dir = Path(story_dir)
        scene_dirs = sorted([d for d in (story_dir / "scenes").iterdir() if d.is_dir()])

        # Cover: use AI-generated cover.png if present, else fall back to protagonist image
        cover_path = story_dir / "cover.png"
        if cover_path.exists():
            opt_cover = optimize_image(str(cover_path), 4000, 2250)
        else:
            # Try multi-character cast.json first
            cast_json = story_dir / "cast.json"
            protagonist_img = None
            if cast_json.exists():
                import json
                cast = json.loads(cast_json.read_text())
                for c in cast.get("cast", []):
                    if c.get("role") == "protagonist":
                        img = story_dir / c["char_dir"] / "character.png"
                        if img.exists():
                            protagonist_img = img
                            break
                if not protagonist_img and cast.get("cast"):
                    img = story_dir / cast["cast"][0]["char_dir"] / "character.png"
                    if img.exists():
                        protagonist_img = img
            # Fall back to single-character
            if not protagonist_img:
                protagonist_img = story_dir / "character" / "character.png"
            opt_cover = optimize_image(str(protagonist_img), 2000, 2000) if protagonist_img and protagonist_img.exists() else ""
        self.cover_page(opt_cover)

        # Scene pages — use overlaid image (with text) if it exists, else clean scene.png
        for sdir in scene_dirs:
            overlaid = sdir / "pages" / "01.png"
            scene_png = sdir / "scene.png"
            img_to_use = overlaid if overlaid.exists() else scene_png
            if img_to_use.exists():
                opt_img = optimize_image(str(img_to_use), 4000, 2250)
                self.image_page(opt_img)

        self.output(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate a storybook PDF from a Fábula story")
    parser.add_argument("story_dir", help="Path to story directory")
    parser.add_argument("--output", "-o", help="Output PDF path (default: <story_dir>/storybook.pdf)")
    args = parser.parse_args()

    story_dir = Path(args.story_dir)
    if not story_dir.exists():
        print(f"ERROR: directory not found: {story_dir}")
        return 1

    output = args.output or str(story_dir / "storybook.pdf")

    pdf = Storybook()
    pdf.generate(str(story_dir), output)

    size_mb = os.path.getsize(output) / (1024 * 1024)
    pages = pdf.pages_count if hasattr(pdf, 'pages_count') else pdf.page
    print(f"Storybook: {output} ({size_mb:.1f} MB, {pages} pages)")


if __name__ == "__main__":
    exit(main())
