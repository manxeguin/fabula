---
description: Mix narration audio with scene videos or final video
agent: pixar-orchestrator
subtask: true
---
Mix narration audio tracks with the video — either scene by scene or the full video.

## User Input
$ARGUMENTS

## Parse arguments
- `--story <slug>` → which story (REQUIRED)
- `--voice <name>` → which voice variant to use (default: ara)
- `--mode <mode>` → "scenes" (mix per scene) or "final" (mix with final.mp4) (default: scenes)
- `--volume <0.0-2.0>` → narration volume multiplier (default: 1.0)

## Workflow

### 1. Resolve
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
VOICE="${voice:-ara}"
```

### 2. Mode: scenes (mix narration into each scene video)
```bash
for scene_dir in $(ls -d "$STORY_DIR/scenes"/*/ | sort); do
  scene_name=$(basename "$scene_dir")
  INPUT_VIDEO="$scene_dir/scene.mp4"
  INPUT_AUDIO="$scene_dir/scene_narration_${VOICE}.mp3"
  OUTPUT="$scene_dir/scene_narrated.mp4"
  
  if [ ! -f "$INPUT_AUDIO" ]; then
    echo "  WARNING: $scene_name — no narration for voice $VOICE, skipping"
    continue
  fi
  
  # Check if video has an audio track
  HAS_AUDIO=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 "$INPUT_VIDEO" 2>/dev/null)
  
  if [ -n "$HAS_AUDIO" ]; then
    # Mix: keep original audio + add narration
    ffmpeg -y -i "$INPUT_VIDEO" -i "$INPUT_AUDIO" \
      -filter_complex "[1:a]volume=${volume:-1.0}[nar];[0:a][nar]amix=inputs=2:duration=first" \
      -c:v copy "$OUTPUT" -loglevel error
  else
    # Video has no audio — just add narration as the audio track
    ffmpeg -y -i "$INPUT_VIDEO" -i "$INPUT_AUDIO" \
      -filter_complex "[1:a]volume=${volume:-1.0}[a]" \
      -c:v copy -map 0:v -map "[a]" "$OUTPUT" -loglevel error
  fi
  
  echo "  $scene_name → scene_narrated.mp4"
done
```

### 3. Mode: final (mix narration_full with final.mp4)
```bash
INPUT_VIDEO="$STORY_DIR/final.mp4"
INPUT_AUDIO="$STORY_DIR/narration_${VOICE}.mp3"
OUTPUT="$STORY_DIR/final_narrated_${VOICE}.mp4"

HAS_AUDIO=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 "$INPUT_VIDEO" 2>/dev/null)

if [ -n "$HAS_AUDIO" ]; then
  ffmpeg -y -i "$INPUT_VIDEO" -i "$INPUT_AUDIO" \
    -filter_complex "[1:a]volume=${volume:-1.0}[nar];[0:a][nar]amix=inputs=2:duration=first" \
    -c:v copy "$OUTPUT" -loglevel error
else
  ffmpeg -y -i "$INPUT_VIDEO" -i "$INPUT_AUDIO" \
    -filter_complex "[1:a]volume=${volume:-1.0}[a]" \
    -c:v copy -map 0:v -map "[a]" "$OUTPUT" -loglevel error
fi

echo "Done: final_narrated_${VOICE}.mp4 ($(ls -lh "$OUTPUT" | awk '{print $5}'))"
```

### 4. If audio doesn't exist yet
Tell the user to run `/pixar-audio --story <slug> --voice <voice>` first.

### 5. Report
- Which mode used
- How many scenes mixed
- Output file paths and sizes
- Compare the 3 voice variants if all were generated
