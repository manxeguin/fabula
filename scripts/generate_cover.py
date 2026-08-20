#!/usr/bin/env python3
"""Generate a Pixar storybook cover using actual character reference images.
Uses image-to-image (edit) with characters + backgrounds from the story.
No text on cover — user adds titles manually."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


FAL_KEY = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY", "")
NB2_EDIT_ENDPOINT = "https://fal.run/fal-ai/nano-banana-2/edit"


def get_char_anchor(character_md):
    """Extract CHARACTER ANCHOR fields from character.md."""
    content = Path(character_md).read_text()
    anchor = {}
    fields = {
        "age": r"Age range:\s*(.+)",
        "build": r"Build:\s*(.+)",
    }
    for key, pattern in fields.items():
        m = re.search(pattern, content)
        if m:
            anchor[key] = m.group(1).strip()
    ratio = re.search(r"head.*?(\d:\d)", content)
    if ratio:
        anchor["ratio"] = ratio.group(1)
    return anchor


def get_char_name(character_md):
    content = Path(character_md).read_text()
    m = re.search(r"# Character:\s*(.+)", content)
    return m.group(1).strip() if m else ""


def get_story_title(story_dir):
    scenes_dir = Path(story_dir) / "scenes"
    if not scenes_dir.exists():
        return ""
    for sdir in sorted(scenes_dir.iterdir()):
        if sdir.is_dir():
            scene_md = sdir / "scene.md"
            if scene_md.exists():
                content = scene_md.read_text()
                m = re.search(r"# Scene \d+:\s*(.+)", content)
                if m:
                    return m.group(1).strip()


def upload_file(path):
    script = Path(__file__).parent / "fal_upload.py"
    r = subprocess.run(["python3", str(script), str(path)],
                       capture_output=True, text=True)
    url = r.stdout.strip()
    return url if url.startswith("http") else ""


def read_scene_narratives(story_dir, n=3):
    """Read first N scene narrations + characters to infer cover composition."""
    scenes_dir = Path(story_dir) / "scenes"
    texts = []
    for sdir in sorted(scenes_dir.iterdir())[:n]:
        if sdir.is_dir():
            scene_md = sdir / "scene.md"
            if scene_md.exists():
                content = scene_md.read_text()
                # Extract Narration or Narrative section
                m = re.search(r"## Narrat(?:ion|ive)\n(.+?)(?:\n## |$)", content, re.DOTALL)
                if m:
                    texts.append(m.group(1).strip())
    return texts


def infer_cover_characters(story_dir):
    """Infer which characters should appear on the cover based on story structure."""
    cast_json = Path(story_dir) / "cast.json"
    cast = []
    if cast_json.exists():
        cast = json.loads(cast_json.read_text()).get("cast", [])

    if not cast:
        char_dir = Path(story_dir) / "character"
        return [{"id": "main", "dir": str(char_dir), "role": "protagonist"}]

    protagonist = next((c for c in cast if c.get("role") == "protagonist"), None)
    mentors = [c for c in cast if c.get("role") in ("teacher", "mentor", "parent")]
    friends = [c for c in cast if c.get("role") == "friend"]

    # Read first 2-3 scenes to detect patterns
    scenes_dir = Path(story_dir) / "scenes"
    scene_texts = []
    for sdir in sorted(scenes_dir.iterdir())[:3]:
        if sdir.is_dir():
            scene_md = sdir / "scene.md"
            if scene_md.exists():
                content = scene_md.read_text()
                # Get Narration + Characters sections for pattern detection
                m = re.search(r"## (?:Narrat(?:ion|ive)|Characters)\n(.+?)(?:\n## |$)", content, re.DOTALL)
                if m:
                    scene_texts.append(m.group(1).strip())
    all_text = " ".join(scene_texts).lower()

    # Count which characters appear in which scenes
    char_mentions = {}
    for c in cast:
        char_mentions[c["id"]] = all_text.count(c["id"])

    # Pattern: protagonist + teacher/mentor bond
    if mentors and protagonist:
        mentor_ids = {m["id"] for m in mentors}
        # Check if scene 2 mentions the mentor
        scene2_text = scene_texts[1] if len(scene_texts) > 1 else ""
        scene2_names = {c["id"] for c in cast if c["id"] in scene2_text.lower()}
        if mentor_ids & scene2_names or any(cid in all_text for cid in mentor_ids):
            return [
                {"id": protagonist["id"], "dir": str(Path(story_dir) / protagonist["char_dir"]), "role": "protagonist"},
                {"id": mentors[0]["id"], "dir": str(Path(story_dir) / mentors[0]["char_dir"]), "role": "mentor"},
            ]

    # Pattern: group of friends (3+ characters mentioned across scenes)
    group_chars = [c for c in cast if char_mentions.get(c["id"], 0) > 0]
    if len(group_chars) >= 3:
        return [{"id": c["id"], "dir": str(Path(story_dir) / c["char_dir"]), "role": c.get("role", "")} for c in group_chars[:4]]

    # Pattern: protagonist + first 1-2 characters that appear together
    appearing = [c for c in cast if char_mentions.get(c["id"], 0) > 0]
    if len(appearing) > 1:
        return [{"id": c["id"], "dir": str(Path(story_dir) / c["char_dir"]), "role": c.get("role", "")} for c in appearing]

    # Default: protagonist only
    if protagonist:
        return [{"id": protagonist["id"], "dir": str(Path(story_dir) / protagonist["char_dir"]), "role": "protagonist"}]
    return cast[:1]


def get_best_background(story_dir):
    """Find the most relevant background for the cover."""
    bg_dir = Path(story_dir) / "backgrounds"
    if not bg_dir.exists():
        return None
    for bg in sorted(bg_dir.iterdir()):
        if bg.is_dir():
            url_file = bg / "background_url.txt"
            if url_file.exists():
                return {"name": bg.name, "url": url_file.read_text().strip(), "path": str(bg / "background.png")}
    return None


def build_cover_prompt(cover_chars, background, narratives):
    """Build the cover prompt based on inferred composition."""
    ratios = {}
    for c in cover_chars:
        md_file = Path(c["dir"]) / "character.md"
        if md_file.exists():
            anchor = get_char_anchor(md_file)
            ratios[c["id"]] = anchor.get("ratio", "1:4")
            c["age"] = anchor.get("age", "toddler")
            c["name"] = get_char_name(md_file)

    lines = []

    # Background reference
    if background:
        n = len(cover_chars) + 1
        lines.append(f"Image {n} is the {background['name']} environment — place the characters inside this exact {background['name']}.")
    else:
        # Describe setting contextually
        lines.append("Warm magical storybook atmosphere with soft glowing golden background, gentle sparkles, Pixar-style storybook feel.")

    # Characters
    n_chars = len(cover_chars)
    if n_chars == 1:
        lines.append(f"One Pixar character centered:")
    else:
        lines.append(f"{n_chars} distinct Pixar characters:")
    lines.append("")

    for i, c in enumerate(cover_chars):
        cid = c["id"]
        age = c.get("age", "toddler")
        ratio = ratios.get(cid, "1:4")
        name = c.get("name", cid)

        if n_chars == 1:
            lines.append(f"Image 1 ({name}, {age}, head {ratio}): facing the viewer with a warm gentle smile, wonder in their eyes.")
        elif n_chars == 2:
            if c["role"] == "protagonist":
                lines.append(f"Image {i+1} ({name}, {age}, head {ratio}): wrapped in a warm embrace, eyes bright with pure joy.")
            else:
                lines.append(f"Image {i+1} ({name}, adult, head {ratio}): arms wrapped around {cover_chars[0]['id']} in a huge warm hug, radiant smile, tender protective expression.")
        elif n_chars >= 3:
            actions = ["center looking at viewer with joyful smile",
                       "right side, laughing together",
                       "left side, playful expression"]
            lines.append(f"Image {i+1} ({name}, {age}, head {ratio}): {actions[min(i, len(actions)-1)]}.")

    lines.append("")
    lines.append("Warm cinematic lighting, soft golden glow, magical storybook atmosphere.")
    lines.append(f"{n_chars} distinct characters — never clone or merge. All characters must keep their exact outfits and appearance from their reference images — do not change any clothing or hair.")
    lines.append("No text, no titles, no words, no watermark.")
    lines.append("16:9 landscape. Disney-Pixar aesthetic, rounded plastic-like forms, subsurface scattering on skin, bright saturated color palette, cinematic lighting, shallow depth of field.")

    return "\n".join(lines)


def generate_cover(story_dir, output_path):
    """Generate cover using image-to-image with character references."""
    story_dir = Path(story_dir)

    # Infer composition
    cover_chars = infer_cover_characters(str(story_dir))
    background = get_best_background(str(story_dir))
    narratives = read_scene_narratives(str(story_dir))

    # Build prompt
    prompt = build_cover_prompt(cover_chars, background, narratives)

    # Upload all character images
    image_urls = []
    for c in cover_chars:
        img = Path(c["dir"]) / "character.png"
        if img.exists():
            url = upload_file(str(img))
            if url:
                image_urls.append(url)
            else:
                print(f"ERROR uploading {c['id']} image")
                return False

    # Add background URL last
    if background:
        image_urls.append(background["url"])

    print(f"\n  Cover composition: {[c['id'] for c in cover_chars]}")
    print(f"  Background: {background['name'] if background else 'none'}")
    print(f"  References: {len(image_urls)} images")

    payload = {
        "prompt": prompt,
        "image_urls": image_urls,
        "aspect_ratio": "16:9",
        "output_format": "png",
        "num_images": 1,
        "safety_tolerance": "6",
        "resolution": "1K",
        "limit_generations": True,
    }

    resp = subprocess.run(
        ["curl", "-s", "--max-time", "180", NB2_EDIT_ENDPOINT,
         "-H", f"Authorization: Key {FAL_KEY}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )

    try:
        data = json.loads(resp.stdout)
        url = data.get("images", [{}])[0].get("url", "")
        if url:
            subprocess.run(["curl", "-sLo", str(output_path), url], check=True)
            size = os.path.getsize(output_path)
            print(f"  Cover: {output_path} ({size / 1024:.0f} KB)")
            return True
        else:
            print(f"  ERROR: {data.get('detail', resp.stdout[:200])}")
            return False
    except json.JSONDecodeError:
        print(f"  ERROR: {resp.stdout[:200]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate Pixar storybook cover using character references")
    parser.add_argument("story_dir", help="Path to story directory")
    args = parser.parse_args()

    story_dir = Path(args.story_dir)
    if not story_dir.exists():
        print(f"ERROR: directory not found: {story_dir}")
        return 1

    output = story_dir / "cover.png"
    ok = generate_cover(str(story_dir), str(output))
    return 0 if ok else 1


if __name__ == "__main__":
    exit(main())
