---
description: Generate or iterate on a Pixar character
agent: pixar-orchestrator
subtask: true
---
You need to generate or iterate on a Pixar-style character for a story.

## User Input
$ARGUMENTS

## How to interpret the arguments

Look for these patterns in $ARGUMENTS:
- `--photo <path>` → user provided a reference photo
- `--story <slug>` → work on an existing story (regenerate character)
- `--preset <name>` → override default preset (testing/budget/quality)
- Everything else → the character description/prompt

## If --story is provided (iteration mode)
1. Resolve the story directory: `STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)`
2. Read the existing character.md for context
3. Regenerate only character.png using the feedback in the prompt
4. Update story_state.json

## If --story is NOT provided (new character mode)
1. Generate a story slug from the prompt: `SLUG=$(bash scripts/resolve_scene.sh --slug "<prompt>")`
2. If --preset was given, use it; otherwise read default from pipeline_config.json
3. Get preset from config: `PRESET="${PIPELINE_PRESET:-$(python3 -c "import json; print(json.load(open('pipeline_config.json'))['default'])")}"`
4. Create directory: `STORY_DIR="stories/${PRESET}_${SLUG}"` and `mkdir -p "$STORY_DIR/character" "$STORY_DIR/scenes"`
5. Initialize state: `bash scripts/story_state.sh init "$STORY_DIR" "$PRESET"`

## Character generation

### If a photo was provided
1. Upload the photo: `PHOTO_URL=$(python3 scripts/fal_upload.py "<photo_path>")`
2. Use the character_edit_model from config (Nano Banana 2 Edit)
3. Build a prompt that describes the desired Pixar character based on $ARGUMENTS + the photo
4. Call the edit endpoint via cURL, download to character/character.png

### If no photo
1. Build a prompt describing the Pixar character based on $ARGUMENTS
2. Call the text-to-image endpoint from config
3. Download to character/character.png

### After generation
1. Write character.md with detailed description if it doesn't exist
2. Update state: `bash scripts/story_state.sh set "$STORY_DIR" character_done true`
3. Report: character name, image path, size
