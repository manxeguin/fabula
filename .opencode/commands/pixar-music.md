---
description: Generate instrumental music and mix with video + narration
agent: pixar-orchestrator
subtask: true
---
Generate instrumental background music matched to the exact video duration, then mix it with the video and optional narration track.

## User Input
$ARGUMENTS

## Parse arguments
- `--story <slug>` → which story (REQUIRED)
- `--voice <name>` → mix with this narration variant (optional: ara, eve, sal)
- `--prompt <text>` → custom music style prompt (optional, auto-generated from story context if omitted)
- `--youtube <url>` → download audio from YouTube instead of generating (mutually exclusive with `--prompt`)
- `--start <seconds>` → start offset for YouTube audio (default: 0)
- `--volume <0-1>` → music volume (default: 0.25 with narration, 0.30 without)

## Auto-prompt generation (if no --prompt and no --youtube provided)

Read the story context to generate a music prompt. For a Feria de Sevilla story:
```
"instrumental flamenco guitar, festive Spanish fair atmosphere, warm and playful, children's wonder, cinematic Pixar soundtrack style, acoustic, no vocals"
```

For other stories, adapt accordingly: read `character/character.md` and scene narratives to understand the mood.

## Workflow

### 1. Resolve story
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
```

### 2. Get video duration
```bash
VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$STORY_DIR/final.mp4")
DUR_INT=$(python3 -c "import math; print(math.ceil($VIDEO_DUR))")
```

### 3. Get music source
**If `--youtube` is set:**
```bash
bash scripts/yt_audio.sh "$YOUTUBE_URL" "$STORY_DIR/music.mp3" --start "${START:-0}"
# The add_music.sh script will handle looping/trimming to exact video duration
```

**Otherwise (Sonilo generation):**
```bash
bash scripts/fal_music.sh "$MUSIC_PROMPT" "$STORY_DIR/music.mp3" "$DUR_INT"
```

### 4. Mix with video (+ optional narration)
```bash
if [ -n "$voice" ]; then
  bash scripts/add_music.sh "$STORY_DIR/final.mp4" "$STORY_DIR/music.mp3" \
    "$STORY_DIR/narration_${voice}.mp3" "$STORY_DIR/final_with_music_${voice}.mp4"
else
  bash scripts/add_music.sh "$STORY_DIR/final.mp4" "$STORY_DIR/music.mp3" \
    "$STORY_DIR/final_with_music.mp4"
fi
```

### 5. Report
- Music prompt used
- Duration match accuracy
- Output file paths and sizes
- Suggest comparing with/without narration
- **ALWAYS show cost summary:**
  ```bash
  export PATH="$HOME/.genmedia/bin:$PATH"
  bash scripts/fal_cost_summary.sh "$STORY_DIR"
  ```
