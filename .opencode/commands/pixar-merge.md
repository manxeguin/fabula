---
description: Merge all scene videos into the final video
agent: pixar-orchestrator
subtask: true
---
Merge all generated scene videos into a single final video.

## User Input
$ARGUMENTS

## Parse arguments
- `--story <slug>` → which story to merge (REQUIRED)
- `--output <path>` → custom output path (optional, default: stories/<slug>/final.mp4)

## Workflow

### 1. Resolve story directory
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
OUTPUT="${output:-$STORY_DIR/final.mp4}"
```

### 2. Merge
```bash
bash scripts/merge_videos.sh "$STORY_DIR" "$OUTPUT"
```

### 3. Update state
```bash
bash scripts/story_state.sh set "$STORY_DIR" phase merged
```

### 4. Report
Output path, file size, duration estimate (scene count × 5s).
Suggest viewing the video.
