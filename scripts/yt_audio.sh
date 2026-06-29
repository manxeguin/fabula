#!/usr/bin/env bash
# Download audio from YouTube URL and convert to MP3.
#
# Usage:
#   bash yt_audio.sh <url> <output.mp3> [--start 0] [--duration 30]
#
# Example:
#   bash yt_audio.sh "https://youtube.com/watch?v=..." music.mp3
#   bash yt_audio.sh "https://youtube.com/watch?v=..." music.mp3 --start 45 --duration 26

set -euo pipefail

URL="${1:-}"
OUTPUT="${2:-}"
shift 2 2>/dev/null || true

START="0"
DURATION=""

while [ $# -gt 0 ]; do
  case "$1" in
    --start) START="$2"; shift 2 ;;
    --duration) DURATION="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$URL" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: bash yt_audio.sh <url> <output.mp3> [--start 0] [--duration 30]" >&2
  exit 1
fi

if ! command -v yt-dlp &>/dev/null; then echo "ERROR: yt-dlp not installed (brew install yt-dlp)" >&2; exit 1; fi
if ! command -v ffmpeg &>/dev/null; then echo "ERROR: ffmpeg not installed (brew install ffmpeg)" >&2; exit 1; fi

mkdir -p "$(dirname "$OUTPUT")"

TITLE=$(yt-dlp --print title --skip-download "$URL" 2>/dev/null)
echo "Downloading: $TITLE"

TMP="/tmp/yt_audio_$$.m4a"

# Download best audio
yt-dlp -q --no-warnings -f bestaudio -o "$TMP" "$URL" 2>/dev/null

# Slice and convert to MP3
if [ -n "$DURATION" ]; then
  ffmpeg -y -i "$TMP" -ss "$START" -t "$DURATION" -ac 1 -ar 24000 -codec:a libmp3lame -q:a 5 "$OUTPUT" -loglevel error 2>/dev/null
else
  ffmpeg -y -i "$TMP" -ss "$START" -ac 1 -ar 24000 -codec:a libmp3lame -q:a 5 "$OUTPUT" -loglevel error 2>/dev/null
fi

rm -f "$TMP"

SZ=$(stat -f%z "$OUTPUT" 2>/dev/null || stat -c%s "$OUTPUT" 2>/dev/null || echo 0)
DUR_ACTUAL=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT" 2>/dev/null || echo "?")

echo "Saved: $OUTPUT (${SZ} bytes, ${DUR_ACTUAL}s)"
