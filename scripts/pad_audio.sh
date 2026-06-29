#!/usr/bin/env bash
# Normalize audio to exact target duration with silence breathing room.
#
# Generates a silent track of target duration, then overlays the speech
# at the pad_start offset. This guarantees sample-accurate duration matching.
#
# Usage:
#   bash pad_audio.sh <input> <output> <target_s> [--gap none|minimal|normal]
#
# Gap presets override pad_start/pad_end:
#   --gap none      → 0s start, 0s end   (continuity scenes, last_frame_continuity)
#   --gap minimal   → 0.05s start, 0s end (continuous cuts, same context)
#   --gap normal    → 0.15s start, 0.15s end (context change cuts)
#
# Without --gap, defaults: pad_start=0.1s, pad_end=0s

set -euo pipefail

INPUT="${1:-}"
OUTPUT="${2:-}"
TARGET="${3:-}"
PAD_START="0.1"
PAD_END="0"

# Parse --gap flag
shift 3 2>/dev/null || true
while [ $# -gt 0 ]; do
  case "$1" in
    --gap)
      case "$2" in
        none) PAD_START="0"; PAD_END="0" ;;
        minimal) PAD_START="0.05"; PAD_END="0" ;;
        normal) PAD_START="0.15"; PAD_END="0.15" ;;
        *) echo "Unknown gap: $2. Use none|minimal|normal" >&2; exit 1 ;;
      esac
      shift 2 ;;
    *) shift ;;
  esac
done

MAX_SPEED="1.0"

if [ -z "$INPUT" ] || [ -z "$OUTPUT" ] || [ -z "$TARGET" ]; then
  echo "Usage: bash pad_audio.sh <input> <output> <target_s> [--gap none|minimal|normal]" >&2
  exit 1
fi

if ! command -v ffmpeg &>/dev/null; then echo "ERROR: ffmpeg not installed" >&2; exit 1; fi
if ! command -v ffprobe &>/dev/null; then echo "ERROR: ffprobe not installed" >&2; exit 1; fi

mkdir -p "$(dirname "$OUTPUT")"

INPUT_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT" 2>/dev/null || echo "0")
SPEECH_SLOT=$(python3 -c "print(max(0.5, $TARGET - $PAD_START - $PAD_END))")

# Calculate speed
SPEED=1.0
if python3 -c "exit(0 if $INPUT_DUR > $SPEECH_SLOT else 1)" 2>/dev/null; then
  SPEED=$(python3 -c "s=$INPUT_DUR/$SPEECH_SLOT; print(min($MAX_SPEED, s))")
fi

ATEMPO_FILTER=""
if python3 -c "exit(0 if abs($SPEED - 1.0) < 0.01 else 1)" 2>/dev/null; then
  ATEMPO_FILTER="anull"
else
  ATEMPO_FILTER="atempo=$SPEED"
fi

TRIM_FILTER=""
if python3 -c "exit(0 if $INPUT_DUR / $SPEED <= $SPEECH_SLOT else 1)" 2>/dev/null; then
  TRIM_FILTER=",atrim=0:$SPEECH_SLOT"
fi

DELAY_S=$(python3 -c "print($PAD_START)")

ffmpeg -y \
  -f lavfi -i "anullsrc=r=24000:cl=mono:d=$TARGET" \
  -i "$INPUT" \
  -filter_complex "[1:a]$ATEMPO_FILTER$TRIM_FILTER,adelay=${DELAY_S}s:all=1[s];[0:a][s]amix=inputs=2:duration=first" \
  -ac 1 -ar 24000 -codec:a libmp3lame -q:a 5 \
  "$OUTPUT" -loglevel error 2>/dev/null

OUT_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT" 2>/dev/null || echo "0")
DIFF=$(python3 -c "print(abs($OUT_DUR - $TARGET))")
GAP_LABEL="start=${PAD_START}s end=${PAD_END}s"

echo "Padded: ${GAP_LABEL} + speech(@${SPEED}x) = ${OUT_DUR}s (diff: ${DIFF}s)"
