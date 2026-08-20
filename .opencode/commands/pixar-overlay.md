---
description: Overlay short text labels onto scene images for the PDF storybook
agent: pixar-orchestrator
subtask: true
---

# /pixar-overlay

Generate text-overlay versions of all scene images for the PDF storybook.

**Usage:** `/pixar-overlay <story_dir> [--force] [--strategy hybrid|heuristic|vision] [--style storybook|handwritten|movie|whimsical]`

**Typography styles (`--style`):**

| Style | Look | Best for |
|---|---|---|
| `storybook` (default) | White text + dark outline + soft drop shadow, Fredoka font | Pixar movie title (Toy Story / Up) — works on any scene |
| `handwritten` | Dark brown text on cream parchment panel, Caveat Brush font, slight tilt | Warm personal scenes (Coco / Soul vibe) |
| `movie` | White text on yellow gradient panel with 3D shadow, Bungee font | Bold cinematic (Incredibles / Elemental) |
| `whimsical` | Cream text with pink outline + sparkles + soft glow, Quicksand font | Picture-book magical scenes |

**Other options:**
- `--force` — Re-overlay even if `pages/01.png` already exists
- `--strategy=hybrid` — (default) Heuristic + luminance-based quadrant selection (no API)
- `--strategy=heuristic` — Pure heuristic, no API calls (free)
- `--strategy=vision` — Always call Moondream 2 (best for complex multi-character scenes, $0.06/scene)

**Reads:**
- `scenes/<n>/scene.md` (`## Label`, `## Visual Prompt`)
- `scenes/<n>/scene.png`

**Writes:**
- `scenes/<n>/pages/01.png` (overlaid, **never modifies `scene.png`**)
- `generation_log.jsonl` (logs each overlay operation with layout, style, and cost)

**Does NOT affect:**
- Video pipeline (uses `scene.png` directly)
- Existing animation
- Existing PDFs (until `generate_pdf.py` is re-run)

**Subsequent step:** Run `python3 scripts/generate_pdf.py <story_dir>` to rebuild the PDF with the new overlaid images.

**Examples:**
```
/pixar-overlay stories/testing_aula-de-patri                              # default storybook style
/pixar-overlay stories/testing_aula-de-patri --style handwritten          # warm/personal
/pixar-overlay stories/testing_aula-de-patri --style whimsical --force   # re-overlay with sparkles
python3 scripts/generate_pdf.py stories/testing_aula-de-patri
```

**Backfill behavior:** If a scene.md is missing the `## Label` field, the script auto-derives a label from `# Scene N: <Title>` (sentence case) and logs a warning.

**To revert to clean (no-text) PDF:**
```
rm -rf stories/<story>/scenes/*/pages
python3 scripts/generate_pdf.py stories/<story>
```
