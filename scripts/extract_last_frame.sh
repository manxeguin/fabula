#!/usr/bin/env bash
# Extract the last frame from a video as PNG.
#
# Usage: bash extract_last_frame.sh <video.mp4> <output.png>
#
# Uses ffmpeg to seek to the last second and capture a single frame.

set -euo pipefail

VIDEO="${1:-}"
OUTPUT="${2:-}"

if [ -z "$VIDEO" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: bash extract_last_frame.sh <video.mp4> <output.png>" >&2
  exit 1
fi

if ! command -v ffmpeg &>/dev/null; then echo "ERROR: ffmpeg not installed" >&2; exit 1; fi

mkdir -p "$(dirname "$OUTPUT")"

# Get video duration, seek to last 0.5s, capture one frame
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO" 2>/dev/null || echo "5")
SEEK=$(python3 -c "print(max(0, float($DUR) - 0.5))")

ffmpeg -y -nostdin -ss "$SEEK" -i "$VIDEO" -vframes 1 -q:v 2 "$OUTPUT" -loglevel error 2>/dev/null

SZ=$(stat -f%z "$OUTPUT" 2>/dev/null || stat -c%s "$OUTPUT" 2>/dev/null || echo 0)
echo "Last frame: $OUTPUT (${SZ} bytes, from ${SEEK}s of ${DUR}s video)"
