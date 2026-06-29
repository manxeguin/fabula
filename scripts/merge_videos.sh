#!/usr/bin/env bash
# Merge scene videos into a final video using FFmpeg concat demuxer.
#
# Usage: bash merge_videos.sh <story_dir> [output.mp4]
#
# Reads scenes from a manifest file (<story_dir>/scenes/manifest.txt) that
# lists scene directories one per line in order. Falls back to alphabetical
# find if no manifest exists.
#
# Requires: ffmpeg

set -euo pipefail

STORY_DIR="${1:-}"
OUTPUT="${2:-}"

if [ -z "$STORY_DIR" ]; then
    echo "Usage: bash merge_videos.sh <story_dir> [output.mp4]" >&2
    exit 1
fi

SCENES_DIR="$STORY_DIR/scenes"
OUTPUT="${OUTPUT:-$STORY_DIR/final.mp4}"

if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg is not installed. Install with: brew install ffmpeg" >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

# Collect scene videos in order
SCENE_FILES=()

MANIFEST="$SCENES_DIR/manifest.txt"
if [ -f "$MANIFEST" ]; then
    echo "Reading scene order from manifest: $MANIFEST"
    while IFS= read -r scene_name; do
        [ -z "$scene_name" ] && continue
        video="$SCENES_DIR/$scene_name/scene.mp4"
        if [ -f "$video" ]; then
            SCENE_FILES+=("$video")
            echo "  $scene_name  (from manifest)"
        else
            echo "  WARNING: $scene_name/scene.mp4 not found, skipping" >&2
        fi
    done < "$MANIFEST"
else
    echo "No manifest found, using alphabetical order"
    while IFS= read -r -d '' file; do
        SCENE_FILES+=("$file")
    done < <(find "$SCENES_DIR" -name "scene.mp4" -print0 | sort -z)
fi

if [ ${#SCENE_FILES[@]} -eq 0 ]; then
    echo "ERROR: No scene.mp4 files found under $SCENES_DIR" >&2
    exit 1
fi

echo "Merging ${#SCENE_FILES[@]} scenes..."
for f in "${SCENE_FILES[@]}"; do
    echo "  $f"
done

# Check for resolution mismatches
FIRST_RES=$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "${SCENE_FILES[0]}" 2>/dev/null)
HAS_MISMATCH=false
for f in "${SCENE_FILES[@]}"; do
    RES=$(ffprobe -v error -select_streams v -show_entries stream=width,height -of csv=p=0 "$f" 2>/dev/null)
    if [ "$RES" != "$FIRST_RES" ]; then
        echo "  WARNING: resolution mismatch: $f ($RES) vs expected ($FIRST_RES)"
        HAS_MISMATCH=true
    fi
done

# If mismatched, re-encode all to first resolution
if [ "$HAS_MISMATCH" = true ]; then
    echo "  Normalizing all scenes to $FIRST_RES..."
    NORMALIZED=()
    W=$(echo "$FIRST_RES" | cut -d, -f1)
    H=$(echo "$FIRST_RES" | cut -d, -f2)
    for f in "${SCENE_FILES[@]}"; do
        nf="$(dirname "$f")/scene_normalized.mp4"
        ffmpeg -y -i "$f" \
            -vf "scale=${W}:${H}:force_original_aspect_ratio=decrease,pad=${W}:${H}:(ow-iw)/2:(oh-ih)/2" \
            -c:v libx264 -preset fast -crf 18 -an \
            "$nf" -loglevel error 2>/dev/null
        NORMALIZED+=("$nf")
    done
    SCENE_FILES=("${NORMALIZED[@]}")
fi

# Create concat file for FFmpeg
CONCAT_FILE="$(mktemp /tmp/concat_list.XXXXXX.txt)"
trap "rm -f '$CONCAT_FILE'" EXIT

for f in "${SCENE_FILES[@]}"; do
    echo "file '$(realpath "$f")'" >> "$CONCAT_FILE"
done

ffmpeg -f concat -safe 0 -i "$CONCAT_FILE" -c copy "$OUTPUT" -y -loglevel error

if [ -f "$OUTPUT" ]; then
    SIZE=$(stat -f%z "$OUTPUT" 2>/dev/null || stat -c%s "$OUTPUT" 2>/dev/null || echo "unknown")
    echo "Done: $OUTPUT ($SIZE bytes)"
else
    echo "ERROR: Failed to create $OUTPUT" >&2
    exit 1
fi
