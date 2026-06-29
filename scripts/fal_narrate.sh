#!/usr/bin/env bash
# Generate narration audio from text using xAI TTS via FAL API.
#
# Usage:
#   bash scripts/fal_narrate.sh "<text>" <output.mp3> [--voice ara] [--lang es-ES]
#
# Voices: eve (energetic), ara (warm/friendly), sal (smooth/balanced)
# Languages: es-ES (Spain), es-MX (Mexico), en, fr, de, it, pt-BR, etc.

set -euo pipefail

TEXT="${1:-}"
OUTPUT="${2:-}"
VOICE="${3:-ara}"
LANG="${4:-es-ES}"

if [ -z "$TEXT" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: bash fal_narrate.sh \"<text>\" <output.mp3> [voice] [lang]" >&2
  exit 1
fi

# Parse --voice and --lang flags
for arg in "$@"; do
  case "$arg" in
    --voice) VOICE="$2"; shift 2 ;;
    --lang)  LANG="$2"; shift 2 ;;
  esac
done

# Override positional if flags used
if [ "${3:-}" != "" ] && [ "${3:0:2}" != "--" ]; then VOICE="$3"; fi
if [ "${4:-}" != "" ] && [ "${4:0:2}" != "--" ]; then LANG="$4"; fi

FAL_API_KEY="${FAL_API_KEY:-$(grep -o 'FAL_API_KEY=[^[:space:]]*' ~/.zshrc 2>/dev/null | head -1 | cut -d= -f2)}"
if [ -z "$FAL_API_KEY" ]; then
  echo "ERROR: FAL_API_KEY not set" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

RESPONSE=$(curl -s --max-time 60 \
  "https://fal.run/xai/tts/v1" \
  -H "Authorization: Key $FAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg text "$TEXT" --arg voice "$VOICE" --arg lang "$LANG" '{
    text: $text,
    voice: $voice,
    language: $lang
  }')")

AUDIO_URL=$(echo "$RESPONSE" | jq -r '.audio.url // empty')
if [ -z "$AUDIO_URL" ]; then
  echo "ERROR: no audio URL in response" >&2
  echo "$RESPONSE" >&2
  exit 1
fi

curl -sLo "$OUTPUT" "$AUDIO_URL"
SZ=$(stat -f%z "$OUTPUT" 2>/dev/null || stat -c%s "$OUTPUT" 2>/dev/null || echo 0)
echo "Saved: $OUTPUT ($SZ bytes)"
