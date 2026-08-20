#!/usr/bin/env python3
"""DEV-ONLY tool: generate typography variants for one scene to compare styles.

Not part of the production pipeline — used to audition font/style combinations
before baking a style into assets/text_styles.json.

Renders 24 distinct variants (6 groups of 4) on the same scene image and
composes them into a labeled comparison grid.

Output: tmp_variants/grid.png — one big image with all variants side-by-side
        tmp_variants/variant_XX.png — individual variant files

Usage:
    python3 scripts/variant_generator.py
"""

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from text_layout import Layout
from text_render import render_label
from text_styles import list_styles, load_style, FONTS_DIR
from text_styles import _load_styles_file


# ---------------------------------------------------------------------------
# Test scene and label
# ---------------------------------------------------------------------------

TEST_SCENE = "/Users/manxeguin/projects/tailes/stories/testing_aula-de-patri/scenes/01-manana-grunon/scene.png"
TEST_LABEL = "Mañana gruñona"
OUT_DIR = Path("/Users/manxeguin/projects/tailes/tmp_variants")

# Use the layout that heuristic + luminance picked for this scene
TEST_LAYOUT = Layout(
    x=55, y=552, width=756, height=153,
    font_size=76, alignment="left", needs_panel=False, style="narration"
)


# ---------------------------------------------------------------------------
# Base style (storybook) — cloned with overrides per variant
# ---------------------------------------------------------------------------

def _base_storybook():
    """Return a deep copy of the storybook style as the base for variants."""
    return json.loads(json.dumps(load_style("storybook")))


def _set_bg(style_dict, color, radius_pct=14):
    """Set a background panel on the style."""
    style_dict["background"] = {"color": color, "corner_radius_pct": radius_pct}


def _clear_bg(style_dict):
    style_dict["background"] = None


def _set_outline(style_dict, color, width=3):
    style_dict["outline_color"] = color
    style_dict["outline_width"] = width


def _set_shadow(style_dict, color, offset, blur):
    style_dict["shadow"] = {"color": color, "offset": offset, "blur": blur}


# ---------------------------------------------------------------------------
# Variant definitions
# ---------------------------------------------------------------------------

def build_variants():
    """Return list of (group_label, variant_label, style_dict) tuples."""

    variants = []

    # --- Group A: Baseline styles ---
    for name in ["storybook", "handwritten", "movie", "whimsical"]:
        variants.append((
            "A · BASELINE",
            name.upper(),
            load_style(name),
        ))

    # --- Group B: Color variations on storybook base ---
    color_combos = [
        ("Cream + Teal",      [255, 248, 230, 255], [22, 78, 99, 255]),     # warm sunset
        ("Pink + Plum",       [255, 200, 220, 255], [80, 30, 70, 255]),     # playful
        ("Mint + Forest",     [220, 245, 230, 255], [30, 70, 50, 255]),     # nature
        ("Sunshine + Navy",   [255, 240, 100, 255], [20, 30, 80, 255]),     # cartoon
    ]
    for label, txt_col, out_col in color_combos:
        s = _base_storybook()
        s["text_color"] = txt_col
        s["outline_color"] = out_col
        variants.append((
            "B · COLOR",
            label,
            s,
        ))

    # --- Group C: Decorative additions (storybook base) ---
    s_panel = _base_storybook()
    _set_bg(s_panel, [40, 40, 60, 180], radius_pct=18)
    variants.append(("C · DECOR", "Panel", s_panel))

    s_underline = _base_storybook()
    s_underline["decorations"] = {
        "left": None, "right": None,
        "underline": True,
        "underline_color": [255, 200, 100, 255],
        "spacing_px": 0,
    }
    variants.append(("C · DECOR", "Underline", s_underline))

    s_bubble = _base_storybook()
    _set_bg(s_bubble, [255, 255, 255, 230], radius_pct=40)
    s_bubble["text_color"] = [40, 40, 60, 255]
    s_bubble["outline_color"] = [40, 40, 60, 200]
    s_bubble["shadow"] = {"color": [0, 0, 0, 100], "offset": [2, 3], "blur": 6}
    variants.append(("C · DECOR", "Speech Bubble", s_bubble))

    s_circle = _base_storybook()
    s_circle["decorations"] = {
        "left": None, "right": None,
        "circle_background": True,
        "circle_color": [255, 220, 130, 230],
        "spacing_px": 0,
    }
    variants.append(("C · DECOR", "Circle BG", s_circle))

    # --- Group D: Outline / shadow variations (storybook base) ---
    s_thin = _base_storybook()
    _set_outline(s_thin, [26, 26, 26, 255], width=1)
    variants.append(("D · OUTLINE", "Thin (1px)", s_thin))

    s_thick = _base_storybook()
    _set_outline(s_thick, [26, 26, 26, 255], width=6)
    variants.append(("D · OUTLINE", "Thick (6px)", s_thick))

    s_3d = _base_storybook()
    s_3d["shadow"] = {
        "color": [0, 0, 0, 200],
        "offset": [4, 4],
        "blur": 0,
        "stack": [
            {"offset": [2, 2], "blur": 0, "color": [255, 200, 50, 255]},
            {"offset": [5, 5], "blur": 0, "color": [200, 100, 30, 255]},
            {"offset": [9, 9], "blur": 2, "color": [0, 0, 0, 200]},
        ],
    }
    s_3d["outline_width"] = 4
    variants.append(("D · OUTLINE", "3D Stack", s_3d))

    s_glow = _base_storybook()
    s_glow["shadow"] = None
    s_glow["glow"] = {"color": [255, 255, 255, 200], "blur": 24}
    variants.append(("D · OUTLINE", "Soft Glow", s_glow))

    # --- Group E: Different fonts on storybook base ---
    font_variants = [
        ("Avenir Black",    "/System/Library/Fonts/Avenir.ttc", False, 800),
        ("Marker Felt",     "/System/Library/Fonts/MarkerFelt.ttc", False, 400),
        ("Optima",          "/System/Library/Fonts/Optima.ttc", False, 700),
        ("Big Caslon",      "/System/Library/Fonts/Supplemental/BigCaslon.ttf", False, 700),
    ]
    for name, font_path, _var, weight in font_variants:
        s = _base_storybook()
        s["font"] = font_path  # use absolute path
        s["font_weight"] = weight
        s["font_size_multiplier"] = 1.0
        variants.append((
            "E · FONT",
            name,
            s,
        ))

    # --- Group F: Position + tilt variations ---
    s_tilted = _base_storybook()
    s_tilted["rotation_deg"] = -3.0
    variants.append(("F · POS/TILT", "Tilted -3°", s_tilted))

    s_topband = _base_storybook()
    # Override layout to top band via direct font_size change
    top_layout = Layout(
        x=68, y=46, width=1240, height=115,
        font_size=65, alignment="center", needs_panel=False, style="narration"
    )
    variants.append(("F · POS/TILT", "Top Band", s_topband, top_layout))

    s_centered = _base_storybook()
    centered_layout = Layout(
        x=275, y=568, width=826, height=138,
        font_size=72, alignment="center", needs_panel=False, style="narration"
    )
    variants.append(("F · POS/TILT", "Bottom Center", s_centered, centered_layout))

    s_tilt_pos = _base_storybook()
    s_tilt_pos["rotation_deg"] = 2.0
    variants.append(("F · POS/TILT", "Tilted +2°", s_tilt_pos))

    # --- Group G: Special looks (bonus) ---
    s_soft = _base_storybook()
    s_soft["text_color"] = [60, 40, 30, 255]      # dark warm brown
    s_soft["outline_color"] = [255, 240, 220, 80] # very thin cream outline
    s_soft["outline_width"] = 1
    s_soft["shadow"] = {"color": [60, 40, 30, 100], "offset": [1, 2], "blur": 6}
    s_soft["letter_spacing_pct"] = 3
    variants.append(("G · SPECIAL", "Soft Pastel", s_soft))

    s_neon = _base_storybook()
    s_neon["text_color"] = [255, 255, 255, 255]
    s_neon["outline_color"] = [255, 100, 200, 255]  # hot pink
    s_neon["outline_width"] = 4
    s_neon["shadow"] = None
    s_neon["glow"] = {"color": [255, 100, 200, 200], "blur": 16}
    variants.append(("G · SPECIAL", "Neon", s_neon))

    s_vintage = _base_storybook()
    s_vintage["font"] = "/System/Library/Fonts/Supplemental/BigCaslon.ttf"
    s_vintage["font_weight"] = 700
    s_vintage["text_color"] = [70, 30, 20, 255]    # dark sepia
    s_vintage["outline_color"] = [70, 30, 20, 255]
    s_vintage["outline_width"] = 2
    s_vintage["shadow"] = None
    _set_bg(s_vintage, [255, 245, 220, 200], radius_pct=8)
    s_vintage["letter_spacing_pct"] = 4
    variants.append(("G · SPECIAL", "Vintage Book", s_vintage))

    s_clean = _base_storybook()
    s_clean["outline_width"] = 0
    s_clean["shadow"] = {"color": [0, 0, 0, 150], "offset": [2, 4], "blur": 8}
    variants.append(("G · SPECIAL", "Clean Shadow Only", s_clean))

    # --- Group H: Fun fonts (the new ones) ---
    fun_fonts = [
        ("Bangers",            "Bangers-Regular.ttf",            700),
        ("Rubik Doodle Shadow","RubikDoodleShadow-Regular.ttf",  400),
        ("Permanent Marker",   "PermanentMarker-Regular.ttf",    400),
        ("Henny Penny",        "HennyPenny-Regular.ttf",         400),
        ("Fontdiner Swanky",   "FontdinerSwanky-Regular.ttf",    400),
        ("Luckiest Guy",       "LuckiestGuy-Regular.ttf",        400),
        ("Love Ya Like Sister","LoveYaLikeASister.ttf",          400),
        ("Ranchers",           "Ranchers-Regular.ttf",           400),
        ("Finger Paint",       "FingerPaint-Regular.ttf",        400),
        ("Slackey",            "Slackey-Regular.ttf",            400),
    ]
    for fname, ffile, weight in fun_fonts:
        s = _base_storybook()
        s["font"] = ffile  # just filename — resolve_font_path adds assets/fonts/
        s["font_weight"] = weight
        # Each font has its own personality — tweak defaults
        if fname == "Bangers":
            # Comic book style — keep the 3D-ish shadow, dark outline
            s["text_color"] = [255, 255, 255, 255]
            s["outline_color"] = [20, 20, 20, 255]
            s["outline_width"] = 4
        elif fname == "Rubik Doodle Shadow":
            # Doodle font has its own shadow — light outline
            s["outline_width"] = 0
            s["shadow"] = {"color": [0, 0, 0, 80], "offset": [1, 2], "blur": 2}
        elif fname == "Henny Penny":
            # Quirky — needs no outline, subtle shadow
            s["outline_width"] = 0
            s["text_color"] = [60, 30, 80, 255]
            s["shadow"] = {"color": [0, 0, 0, 120], "offset": [2, 3], "blur": 4}
        elif fname == "Fontdiner Swanky":
            # Retro 50s — dark text on light background works best
            s["text_color"] = [180, 50, 90, 255]  # pink/rose
            s["outline_color"] = [60, 20, 40, 255]
            s["outline_width"] = 2
            s["shadow"] = {"color": [0, 0, 0, 100], "offset": [2, 3], "blur": 3}
        elif fname == "Luckiest Guy":
            # Bold display — work well with strong outline
            s["outline_width"] = 5
            s["outline_color"] = [15, 15, 15, 255]
        elif fname == "Love Ya Like Sister":
            # Handwritten casual — soft, no outline needed
            s["outline_width"] = 0
            s["text_color"] = [100, 50, 130, 255]
            s["shadow"] = {"color": [0, 0, 0, 100], "offset": [1, 2], "blur": 3}
        elif fname == "Ranchers":
            # Western — strong outline
            s["outline_width"] = 4
        elif fname == "Finger Paint":
            # Messy/playful — no outline, just shadow
            s["outline_width"] = 0
            s["text_color"] = [70, 100, 180, 255]
            s["shadow"] = {"color": [0, 0, 0, 120], "offset": [2, 3], "blur": 4}
        elif fname == "Slackey":
            # Chunky — needs a little outline to define
            s["outline_width"] = 2
            s["text_color"] = [255, 255, 255, 255]
            s["outline_color"] = [20, 20, 20, 255]
        # Permanent Marker: keep storybook default settings
        variants.append(("H · FUN FONTS", fname, s))

    # --- Group I: Color and border variations on the fun fonts ---
    # Pick the 4 most "Pixar-toddler-book" friendly fonts and show them in different colors
    fun_color_combos = [
        ("Bangers + Magenta",     "Bangers-Regular.ttf", [255, 60, 130, 255], [60, 20, 60, 255], 4),
        ("Bangers + Cyan",        "Bangers-Regular.ttf", [80, 230, 255, 255], [10, 30, 80, 255], 4),
        ("Luckiest + Sunshine",   "LuckiestGuy-Regular.ttf", [255, 230, 60, 255], [80, 40, 0, 255], 4),
        ("Luckiest + Mint",       "LuckiestGuy-Regular.ttf", [120, 240, 180, 255], [10, 60, 30, 255], 4),
        ("Permanent + Coral",     "PermanentMarker-Regular.ttf", [255, 130, 110, 255], [80, 20, 20, 255], 0),
        ("Permanent + Purple",    "PermanentMarker-Regular.ttf", [200, 130, 240, 255], [40, 20, 80, 255], 0),
        ("Henny + Forest",        "HennyPenny-Regular.ttf", [180, 220, 120, 255], [30, 50, 20, 255], 0),
        ("Henny + Plum",          "HennyPenny-Regular.ttf", [240, 130, 200, 255], [60, 20, 60, 255], 0),
        ("Finger + Sky",          "FingerPaint-Regular.ttf", [120, 200, 250, 255], [20, 40, 80, 255], 0),
        ("Slackey + Lime",        "Slackey-Regular.ttf", [180, 250, 100, 255], [30, 60, 10, 255], 2),
    ]
    for label, ffile, txt_col, out_col, out_w in fun_color_combos:
        s = _base_storybook()
        s["font"] = ffile
        s["font_weight"] = 400
        s["text_color"] = txt_col
        s["outline_color"] = out_col
        s["outline_width"] = out_w
        s["shadow"] = {"color": [0, 0, 0, 130], "offset": [2, 3], "blur": 5}
        variants.append(("I · FUN COLORS", label, s))

    # --- Group J: Border/frame variations on fun fonts ---
    # Show how the fun fonts look with strong borders (Pixar title card style)
    border_combos = [
        ("Bangers Black Border",     "Bangers-Regular.ttf", [255, 255, 255, 255], [0, 0, 0, 255], 6),
        ("Luckiest Black Border",    "LuckiestGuy-Regular.ttf", [255, 240, 200, 255], [20, 10, 0, 255], 5),
        ("Ranchers Color Border",    "Ranchers-Regular.ttf", [255, 220, 100, 255], [120, 30, 20, 255], 5),
        ("Slackey Color Border",     "Slackey-Regular.ttf", [255, 200, 220, 255], [80, 20, 60, 255], 3),
    ]
    for label, ffile, txt_col, out_col, out_w in border_combos:
        s = _base_storybook()
        s["font"] = ffile
        s["font_weight"] = 400
        s["text_color"] = txt_col
        s["outline_color"] = out_col
        s["outline_width"] = out_w
        s["shadow"] = {"color": [0, 0, 0, 180], "offset": [3, 4], "blur": 4}
        variants.append(("J · BORDERS", label, s))

    # --- Group K: Bordered variants for every fun font (40 total) ---
    # User feedback: bordered fonts are easier to read. Apply 4 border
    # strategies to each of the 10 fun fonts.
    #
    # B-Thin   = 2px black outline + soft shadow          (subtle definition)
    # B-Heavy  = 5-6px black outline                     (strong comic book)
    # B-White  = 3px white outline on dark text          (works on warm scenes)
    # B-Shadow = 3px black outline + strong drop shadow  (most readable)
    fun_fonts_for_borders = [
        # (display name, file, weight)
        ("Bangers",            "Bangers-Regular.ttf",            700),
        ("Rubik Doodle",       "RubikDoodleShadow-Regular.ttf",  400),
        ("Permanent Marker",   "PermanentMarker-Regular.ttf",    400),
        ("Henny Penny",        "HennyPenny-Regular.ttf",         400),
        ("Fontdiner Swanky",   "FontdinerSwanky-Regular.ttf",    400),
        ("Luckiest Guy",       "LuckiestGuy-Regular.ttf",        400),
        ("Love Ya Like Sister","LoveYaLikeASister.ttf",          400),
        ("Ranchers",           "Ranchers-Regular.ttf",           400),
        ("Finger Paint",       "FingerPaint-Regular.ttf",        400),
        ("Slackey",            "Slackey-Regular.ttf",            400),
    ]

    # Default text color and shadow per font (tuned to font character)
    font_defaults = {
        "Bangers":             ([255, 255, 255, 255], [20, 20, 20, 255]),
        "Rubik Doodle":        ([60, 40, 80, 255],    [255, 240, 220, 255]),
        "Permanent Marker":    ([50, 50, 60, 255],    [20, 20, 30, 255]),
        "Henny Penny":         ([60, 30, 80, 255],    [255, 240, 200, 255]),
        "Fontdiner Swanky":    ([180, 50, 90, 255],   [40, 15, 30, 255]),
        "Luckiest Guy":        ([255, 240, 200, 255], [20, 10, 0, 255]),
        "Love Ya Like Sister": ([100, 50, 130, 255],  [255, 240, 230, 255]),
        "Ranchers":            ([255, 230, 100, 255], [60, 20, 0, 255]),
        "Finger Paint":        ([70, 100, 180, 255],  [20, 30, 80, 255]),
        "Slackey":             ([255, 255, 255, 255], [20, 20, 20, 255]),
    }

    border_strategies = [
        # (suffix, outline_width, outline_color_override, shadow_override)
        ("B-Thin",   2,  None, None),                                         # subtle
        ("B-Heavy",  5,  None, None),                                         # strong
        ("B-White",  3,  [255, 255, 255, 255], None),                         # white outline
        ("B-Shadow", 3,  None, {"color": [0, 0, 0, 200], "offset": [3, 4], "blur": 6}),  # max readable
    ]

    for fname, ffile, weight in fun_fonts_for_borders:
        default_text, default_outline = font_defaults[fname]
        for suffix, out_w, out_col, shadow in border_strategies:
            s = _base_storybook()
            s["font"] = ffile
            s["font_weight"] = weight
            s["text_color"] = default_text
            s["outline_color"] = out_col if out_col else default_outline
            s["outline_width"] = out_w
            if shadow:
                s["shadow"] = shadow
            else:
                s["shadow"] = {"color": [0, 0, 0, 130], "offset": [2, 3], "blur": 4}
            variants.append((f"K · {suffix}", f"{fname}", s))

    return variants


# ---------------------------------------------------------------------------
# Render and compose grid
# ---------------------------------------------------------------------------

def render_variants():
    """Render each variant, save individually, then compose grid."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    variants = build_variants()
    rendered = []
    manifest_entries = []
    print(f"Rendering {len(variants)} variants on {Path(TEST_SCENE).name}...")
    print(f"  Label: {TEST_LABEL!r}")
    print()

    for i, variant in enumerate(variants):
        if len(variant) == 4:
            group, label, style, layout = variant
        else:
            group, label, style = variant
            layout = TEST_LAYOUT

        out_path = OUT_DIR / f"variant_{i+1:02d}.png"
        font_label = f"V{i+1:02d} · {group.strip()} · {label}"
        try:
            _render_with_custom_style(out_path, TEST_SCENE, TEST_LABEL, layout, style, font_label=font_label)
        except Exception as e:
            print(f"  ERR variant {i+1:02d} ({label}): {e}")
            continue

        rendered.append((i+1, group, label, out_path))
        manifest_entries.append({
            "id": i + 1,
            "file": out_path.name,
            "group": group.strip(),
            "name": label,
            "font": style.get("font", ""),
            "text_color": style.get("text_color"),
            "outline_color": style.get("outline_color"),
            "outline_width": style.get("outline_width"),
            "rotation": style.get("rotation_deg", 0),
            "discard": False,
        })
        print(f"  [{i+1:02d}] {group:14} {label:22} -> {out_path.name}")

    # Write manifest
    manifest_path = OUT_DIR / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_entries, f, indent=2, ensure_ascii=False)
    print(f"\nManifest: {manifest_path} ({len(manifest_entries)} entries)")
    print(f"  Edit `discard: true` on entries you want to remove, then run:")
    print(f"    python3 scripts/variant_generator.py --discard")

    return rendered


def _render_with_custom_style(out_path, image_path, text, layout, custom_style, font_label=None):
    """Render a label using a custom style dict (not a named style).

    Args:
        out_path: where to save
        image_path: source image
        text: label text
        layout: Layout object
        custom_style: style dict
        font_label: if provided, a small label strip with the font name is burned
                    into the bottom of the image
    """
    from text_styles import _load_styles_file

    styles = _load_styles_file()
    custom_name = "__custom__"

    original = styles.get(custom_name)
    styles[custom_name] = custom_style

    try:
        render_label(image_path, out_path, text, layout, style_name=custom_name)
    finally:
        if original is None:
            styles.pop(custom_name, None)
        else:
            styles[custom_name] = original

    # Burn font name label strip into the image (so each file is self-identifying)
    if font_label:
        _add_font_label_strip(out_path, font_label)


def _add_font_label_strip(image_path, font_label):
    """Add a small label strip at the bottom of the image with the font name.

    This makes each variant file self-identifying when viewed in a file
    browser or image viewer.
    """
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    strip_h = 38
    new_img = Image.new("RGB", (w, h + strip_h), (30, 30, 35))
    new_img.paste(img, (0, 0))
    d = ImageDraw.Draw(new_img)
    # Try to find a good font
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    # Draw the label
    d.text((16, h + 8), font_label, font=font, fill=(240, 240, 250))
    new_img.save(image_path, "PNG", optimize=True)


def compose_grid(rendered, output_path):
    """Compose all rendered variants into a labeled grid."""
    if not rendered:
        print("No variants to compose.")
        return

    # Cell dimensions
    cell_w = 520
    cell_h = 300
    label_h = 32
    group_h = 28
    padding = 16
    cols = 4

    n = len(rendered)
    rows = (n + cols - 1) // cols

    # Adjust cell size based on number of variants
    if n > 80:
        cell_w = 360
        cell_h = 200
    elif n > 60:
        cell_w = 400
        cell_h = 220
    elif n > 36:
        cell_w = 410
        cell_h = 232
    elif n > 24:
        cell_w = 460
        cell_h = 260

    title_h = 70
    grid_w = cols * cell_w + (cols + 1) * padding
    grid_h = title_h + rows * (cell_h + label_h + group_h) + (rows + 1) * padding

    grid = Image.new("RGB", (grid_w, grid_h), (245, 245, 248))
    gd = ImageDraw.Draw(grid)

    # Title
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 28)
        meta_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
        cell_label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
        group_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 13)
    except Exception:
        title_font = meta_font = cell_label_font = group_font = ImageFont.load_default()

    gd.text(
        (padding, 18),
        "Typography Variants — Mañana gruñona (scene 01)",
        font=title_font,
        fill=(20, 20, 30),
    )
    gd.text(
        (padding, 50),
        f"{n} variants · 14 groups · 1376×768 source · pick a favorite",
        font=meta_font,
        fill=(80, 80, 100),
    )

    # Cells
    for idx, (num, group, label, path) in enumerate(rendered):
        col = idx % cols
        row = idx // cols
        x = padding + col * (cell_w + padding)
        y = title_h + padding + row * (cell_h + label_h + group_h + padding)

        # Image
        img = Image.open(path).convert("RGB")
        img.thumbnail((cell_w, cell_h), Image.LANCZOS)
        # Center in cell
        ix = x + (cell_w - img.size[0]) // 2
        iy = y + (cell_h - img.size[1]) // 2
        # Border
        gd.rectangle([x-1, y-1, x+cell_w, y+cell_h], outline=(200, 200, 210), width=1)
        grid.paste(img, (ix, iy))

        # Group label (top)
        gd.text(
            (x + 4, y + cell_h + 4),
            group,
            font=group_font,
            fill=(150, 150, 170),
        )

        # Cell label (bottom)
        gd.text(
            (x + 4, y + cell_h + 4 + group_h - 14),
            label,
            font=cell_label_font,
            fill=(20, 20, 30),
        )

    grid.save(output_path, "PNG", optimize=True)
    print(f"\nGrid saved: {output_path} ({grid.size[0]}×{grid.size[1]}, {n} variants)")


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Generate or curate typography variants")
    parser.add_argument("--discard", action="store_true",
                        help="Read manifest.json and delete variants marked discard=true")
    parser.add_argument("--list", action="store_true",
                        help="List all variants in the manifest and exit")
    args = parser.parse_args()

    if args.list:
        manifest_path = OUT_DIR / "manifest.json"
        if not manifest_path.exists():
            print("manifest.json not found. Run without --list first.")
            sys.exit(1)
        with open(manifest_path) as f:
            entries = json.load(f)
        for e in entries:
            mark = "  X" if e.get("discard") else "   "
            print(f"{mark} V{e['id']:02d}  {e['group']:14}  {e['name']:30}  font={e['font']}")
        sys.exit(0)

    if args.discard:
        manifest_path = OUT_DIR / "manifest.json"
        if not manifest_path.exists():
            print("manifest.json not found. Run without --discard first.")
            sys.exit(1)
        with open(manifest_path) as f:
            entries = json.load(f)
        removed = 0
        kept = 0
        for e in entries:
            fpath = OUT_DIR / e["file"]
            if e.get("discard"):
                if fpath.exists():
                    fpath.unlink()
                    removed += 1
                else:
                    print(f"  V{e['id']:02d} {e['name']}: marked discard but file missing")
            else:
                kept += 1
        print(f"Removed {removed} variants, kept {kept}")

        # Rebuild grid from kept variants
        kept_paths = [(i+1, e["group"], e["name"], OUT_DIR / e["file"])
                      for i, e in enumerate(entries) if not e.get("discard") and (OUT_DIR / e["file"]).exists()]
        compose_grid(kept_paths, OUT_DIR / "grid.png")
        sys.exit(0)

    rendered = render_variants()
    grid_path = OUT_DIR / "grid.png"
    compose_grid(rendered, grid_path)
