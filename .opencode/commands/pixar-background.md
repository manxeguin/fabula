---
description: Generate a Pixar-style background/environment from a source photo
agent: pixar-orchestrator
subtask: true
---
You need to generate a Pixar-style background environment from a reference photo. Use the `pixar-background` subagent for the generation logic.

## User Input
$ARGUMENTS

## How to interpret the arguments

- `--photo <path>` — reference photo of the location (REQUIRED)
- `--story <slug>` — story to add the background to (REQUIRED)
- `--name <bg_name>` — name for this background, e.g. `classroom`, `playground`, `patio` (REQUIRED)
- Everything else → description of the desired environment (optional, the model will auto-describe from photo if omitted)

## Steps

### 1. Resolve story directory
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
```

### 2. Generate background
Invoke the `pixar-background` subagent with the photo path, story directory, and background name. The subagent will:
- Upload the source photo to FAL CDN
- Auto-describe it if no description was provided
- Use Nano Banana 2 Edit to transform it into a Pixar 3D animated environment
- Keep the layout and structure of the original photo
- Download to `backgrounds/<name>/background.png`
- Upload for CDN reuse

Or use the direct bash script:
```bash
bash scripts/fal_background.sh <photo_path> "$STORY_DIR" <bg_name>
```

### 3. Report
Show the generated background image path and size. Let the user review.

## Post-Action
Tell the user the background was generated. List all backgrounds now available for this story:
```bash
ls -la "$STORY_DIR/backgrounds/" 2>/dev/null || echo "No backgrounds yet"
```
