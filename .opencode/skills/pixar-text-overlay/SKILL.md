---
name: pixar-text-overlay
description: Overlay short text labels onto scene images for the PDF storybook. Pure Python (Pillow). 4 typography styles. Heuristic + luminance layout. Never modifies scene.png.
---

# Pixar Text Overlay

Renders short 2-4 word labels (like "Mañana gruñona", "El patio") onto a copy of each scene image using one of 4 bundled typography styles. The original `scene.png` is never modified — the overlay is written to `scenes/<n>/pages/01.png` and consumed by `generate_pdf.py` to produce a text-augmented storybook PDF.

The video pipeline is **untouched**: it still reads clean `scene.png`.

## When to use

- Before regenerating a storybook PDF that should have labels
- When the user wants a print-ready storybook (vs the video-only output)
- After a new story is generated and the user wants to "publish" it as a PDF

## When NOT to use

- For video generation (the video pipeline never reads `pages/01.png`)
- For subtitles on video (out of scope — see "Non-goals")
- For interactive content (this is a print/export format)

## Components

```
scripts/
  text_fonts.py         Font loader (system Georgia/Marker/Avenir as fallback)
  text_layout.py        Heuristic + luminance-based layout engine
  text_render.py        Pillow compositor with style-aware multi-layer compositing
  text_styles.py        Style loader (reads assets/text_styles.json)
  text_decorations.py   Star / sparkle / dot / heart drawer
  text_moondream.py     Moondream 2 object-detection fallback (opt-in)
  overlay_text.py       Orchestrator + logging (entry point)

assets/
  text_styles.json      4 style definitions (storybook, handwritten, movie, whimsical)
  fonts/                4 bundled Google Fonts (OFL, free)
    Fredoka-Variable.ttf          — storybook style
    CaveatBrush-Regular.ttf       — handwritten style
    Bungee-Regular.ttf            — movie style
    Quicksand-Variable.ttf        — whimsical style
    (10 additional dev-only fonts also live here; they are auditioned by
     scripts/variant_generator.py and are not part of any shipped style.)
```

## Typography styles (4 bundled)

| Style | Font | Look | Best for |
|---|---|---|---|
| **storybook** (default) | Fredoka (SemiBold) | White text + 3px black outline + soft drop shadow | Pixar movie title (Toy Story / Up) — works on any scene |
| **handwritten** | Caveat Brush | Dark brown text + 1px brown outline + cream parchment panel + slight tilt | Warm, personal (Coco / Soul vibe) |
| **movie** | Bungee | White text + 4px black outline + 3D multi-layer shadow + yellow gradient panel | Bold cinematic (Incredibles / Elemental) |
| **whimsical** | Quicksand Bold | Cream text + pink outline + soft white glow + ★ sparkle decorations | Most kid-magical (picture-book feel) |

All 4 styles use the same layout positions — only the visual treatment differs. Select once per story via `--style`.

## Usage

```bash
# Default (storybook)
python3 scripts/overlay_text.py <story_dir>

# Other styles
python3 scripts/overlay_text.py <story_dir> --style handwritten
python3 scripts/overlay_text.py <story_dir> --style movie
python3 scripts/overlay_text.py <story_dir> --style whimsical

# Force re-overlay
python3 scripts/overlay_text.py <story_dir> --style storybook --force

# Regenerate PDF (auto-picks up overlaid images)
python3 scripts/generate_pdf.py <story_dir>
```

## Label field

Every `scene.md` MUST have a `## Label` section:

```markdown
## Label
Mañana gruñona
```

**Rules:**
- 2-4 words, sentence case (first word capitalized, rest lowercase)
- Same language as the narration
- Derive from scene title or first prominent noun in `## Visual Prompt`
- Never the full narration

If `## Label` is missing, the orchestrator auto-derives it from `# Scene N: <Title>` and logs a warning.

## Layout strategy (hybrid)

Tier 1 — **Heuristic** (no API calls, $0):
- Parse `## Visual Prompt` for framing keywords
- `wide establishing shot` / `wide shot` → wide band (full width, bottom 15%)
- `close-up` / `extreme close-up` → narrow bottom band (centered, 50% width)
- `over-the-shoulder` / `POV` → top band (full width, top 15%)
- Default (medium/full shot) → bottom-left quadrant (55% width, 20% height)

Tier 2 — **Luminance-based quadrant selection** (no API calls, $0):
- For default (medium-shot) scenes, sample both bottom quadrants and pick the one with lower standard deviation (more uniform = less busy = better for text)
- Triggered when no framing keyword is detected
- Replaces the bottom-left default with bottom-right if the right side is less busy

Tier 3 — **Moondream 2 object detection** (~$0.02/call, opt-in only):
- Disabled by default because the Moondream 2 endpoint takes a single object per call, requiring 3 calls (face, hand, person) per scene to detect all the things we want to avoid
- Total cost: $0.06/scene, 12-18s latency — too expensive for the benefit
- Available via `--strategy=vision` for users who want to opt in

## Renderer (style-aware, 5-7 layer composite)

Each style composites a different set of layers. The storybook style is:

1. **Shadow layer**: text drawn at +2,+3 offset, Gaussian blur 5, 50% black
2. **Outline layer**: 3px outline drawn around each character in solid black
3. **Text layer**: white text on top

The movie style adds a 3-layer 3D shadow stack and a gradient background panel:

1. **Background panel**: yellow rounded rectangle
2. **Shadow stack 1** (yellow): +1,+1 offset
3. **Shadow stack 2** (orange): +3,+3 offset
4. **Shadow stack 3** (black): +6,+6 offset, blur 2
5. **Outline layer**: 4px black outline
6. **Text layer**: white text

The whimsical style adds glow + decorations:

1. **Decorations** (★ left, ✦ right): drawn behind text
2. **Glow layer**: white halo, blur 12, 30% alpha
3. **Shadow layer**: 1,+2 offset, blur 4
4. **Outline layer**: 2px pink outline
5. **Text layer**: cream text

The handwritten style uses a parchment background panel + warm brown text + slight tilt (-1.5°).

Color/panel decision is **per style** — not auto-detected. The style is the source of truth.

## Adding a new style

1. Add a new font to `assets/fonts/` (OFL/Apache license)
2. Add a new entry in `assets/text_styles.json` with all required fields:
   ```json
   "newstyle": {
     "description": "...",
     "font": "FontFile.ttf",
     "font_weight": 700,
     "font_size_multiplier": 1.0,
     "text_color": [R, G, B, A],
     "outline_color": [R, G, B, A],
     "outline_width": 3,
     "shadow": { "color": [...], "offset": [x, y], "blur": 5 },
     "glow": null,
     "background": null,
     "rotation_deg": 0,
     "letter_spacing_pct": 0,
     "decorations": null
   }
   ```
3. The style auto-appears in `--help` via `text_styles.list_styles()`

## Caching and PDF integration

`generate_pdf.py` automatically reads `pages/01.png` if it exists, else falls back to `scene.png`. To re-generate the PDF with text:

```bash
python3 scripts/overlay_text.py <story_dir> --style <name>  # writes pages/01.png
python3 scripts/generate_pdf.py <story_dir>                  # reads pages/01.png
```

To revert to clean (no-text) PDF, delete `pages/` directories:

```bash
rm -rf stories/<story>/scenes/*/pages
```

## Cost & latency

| Layer | Cost | Latency |
|---|---|---|
| Heuristic layout | $0 | <100ms |
| Luminance-based quadrant selection | $0 | <200ms |
| Pillow render (per scene) | $0 | <500ms |
| **Per scene** | **$0** | **<1s** |
| **Per 6-scene story** | **$0** | **<6s** |
| Moondream 2 (opt-in, --strategy=vision) | $0.06/scene | 12-18s |

## Failure modes

| Failure | Behavior |
|---|---|
| `scene.png` missing | Scene skipped with warning, others continue |
| `## Label` missing | Auto-derive from scene title, log warning |
| Font file missing | Fall back to system fonts (Georgia, Marker Felt, Avenir), log warning |
| Moondream API down | Fall back to heuristic, log warning |
| Output write fails | Scene skipped, others continue, exit code != 0 |
| Original `scene.png` modified by mistake | **Should never happen** — verified by md5 before/after |

## Non-goals

- Speech bubbles, dialogue, thoughts, quotes (only `## Label` text)
- Subtitle rendering on video
- Manual positioning
- Per-scene style override (story-level only for v1)
- Multi-language typography (one font set for Latin-extended)
- Cover overlay
- Animated typography
