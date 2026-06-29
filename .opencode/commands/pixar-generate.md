---
description: Generate all scene images and videos for a story
agent: pixar-orchestrator
subtask: true
---
Generate scene images and videos for all pending scenes in a story.

## User Input
$ARGUMENTS

## Parse arguments
- `--story <slug>` → which story (REQUIRED)
- `--scene <ref>` → generate only this scene (optional)
- `--force` → regenerate even if already done
- `--images-only` → skip video generation
- `--videos-only` → skip image generation

## Workflow

### 1. Resolve and load config
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
PRESET=$(bash scripts/story_state.sh get "$STORY_DIR" preset)
PRESET="${PRESET:-testing}"

# Load config values for this preset
CONFIG=$(cat pipeline_config.json)
SCENE_ENDPOINT=$(echo "$CONFIG" | jq -r ".presets[\"$PRESET\"].scene_endpoint")
VIDEO_ENDPOINT=$(echo "$CONFIG" | jq -r ".presets[\"$PRESET\"].video_endpoint")
VIDEO_IMG_PARAM=$(echo "$CONFIG" | jq -r ".presets[\"$PRESET\"].video_image_param")
```

### 2. Upload character reference (if not already uploaded)
```bash
if [ ! -f "$STORY_DIR/character/character_url.txt" ]; then
  python3 scripts/fal_upload.py "$STORY_DIR/character/character.png" > "$STORY_DIR/character/character_url.txt"
fi
CHAR_URL=$(cat "$STORY_DIR/character/character_url.txt")
```

### 3. Determine which scenes to process
If --scene is provided: process only that scene.
Otherwise: process all scenes that don't have DONE status (or all if --force).

### 4. Scene image generation
For each pending scene, extract Visual Prompt, call scene endpoint, download to scene.png.
Run in parallel for all scenes.

### 5. Scene video generation
For each scene with a scene.png, upload it, call video endpoint, download to scene.mp4.
Run in parallel for all scenes.

### 6. Update state after each generation
```bash
bash scripts/story_state.sh scene "$STORY_DIR" "<scene_name>" img true
bash scripts/story_state.sh scene "$STORY_DIR" "<scene_name>" img_size "$SIZE"
```

### 7. Report
Status of all scenes, suggest running /pixar-merge.
