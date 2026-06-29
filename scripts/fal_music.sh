#!/usr/bin/env bash
# Generate instrumental music via Sonilo v1.1 text-to-music on FAL.
#
# Usage:
#   bash scripts/fal_music.sh "<prompt>" <output.mp3> <duration_seconds>
#
# Example:
#   bash scripts/fal_music.sh "instrumental flamenco guitar, festive Spanish atmosphere" music.mp3 26

set -euo pipefail

PROMPT="${1:-}"
OUTPUT="${2:-}"
DURATION="${3:-30}"

if [ -z "$PROMPT" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: bash fal_music.sh \"<prompt>\" <output.mp3> [duration_seconds]" >&2
  exit 1
fi

FAL_API_KEY="${FAL_API_KEY:-$(grep -o 'FAL_API_KEY=[^[:space:]]*' ~/.zshrc 2>/dev/null | head -1 | cut -d= -f2)}"
if [ -z "$FAL_API_KEY" ]; then
  echo "ERROR: FAL_API_KEY not set" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

# Round up duration to integer (Sonilo requires integer seconds)
DUR_INT=$(python3 -c "import math; print(math.ceil($DURATION))")

echo "Generating music: ${DUR_INT}s, prompt: ${PROMPT:0:80}..."

RESPONSE=$(curl -s --max-time 120 \
  "https://fal.run/sonilo/v1.1/text-to-music" \
  -H "Authorization: Key $FAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg prompt "$PROMPT" --argjson dur "$DUR_INT" '{
    prompt: $prompt,
    duration: $dur,
    num_samples: 1
  }')")

AUDIO_URL=$(echo "$RESPONSE" | jq -r '.audio.url // empty')
if [ -z "$AUDIO_URL" ]; then
  echo "ERROR: no audio URL in response" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

curl -sLo "$OUTPUT" "$AUDIO_URL"
SZ=$(stat -f%z "$OUTPUT" 2>/dev/null || stat -c%s "$OUTPUT" 2>/dev/null || echo 0)
DUR_ACTUAL=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT" 2>/dev/null || echo "?")

echo "Saved: $OUTPUT (${SZ} bytes, ${DUR_ACTUAL}s)"
