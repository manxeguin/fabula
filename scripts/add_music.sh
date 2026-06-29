#!/usr/bin/env bash
# Mix music, narration, and video into a single output.
#
# Usage:
#   bash add_music.sh <video.mp4> <music.mp3> [narration.mp3] <output.mp4>
#
# If narration is provided: mixes music(25%) + narration(100%) + video
# If no narration:         mixes music(30%) + video only
#
# Music is looped if shorter than video, trimmed if longer.

set -euo pipefail

VIDEO="${1:-}"
MUSIC="${2:-}"
NARRATION="${3:-}"
OUTPUT="${4:-}"

# If 3rd arg is output (no narration), shift
if [ $# -eq 3 ]; then
  OUTPUT="$3"
  NARRATION=""
fi

if [ -z "$VIDEO" ] || [ -z "$MUSIC" ] || [ -z "$OUTPUT" ]; then
  echo "Usage: bash add_music.sh <video.mp4> <music.mp3> [narration.mp3] <output.mp4>" >&2
  exit 1
fi

if ! command -v ffmpeg &>/dev/null; then echo "ERROR: ffmpeg not installed" >&2; exit 1; fi
if ! command -v ffprobe &>/dev/null; then echo "ERROR: ffprobe not installed" >&2; exit 1; fi

mkdir -p "$(dirname "$OUTPUT")"

VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$VIDEO" 2>/dev/null || echo "0")
echo "Video: ${VIDEO_DUR}s"

# Process music: loop if shorter, trim if longer
TMP_MUSIC="/tmp/music_looped_$$.mp3"
ffmpeg -y -stream_loop -1 -i "$MUSIC" -t "$VIDEO_DUR" -ac 1 -ar 24000 -codec:a libmp3lame -q:a 5 "$TMP_MUSIC" -loglevel error 2>/dev/null
echo "Music: looped/trimmed to ${VIDEO_DUR}s"

if [ -n "$NARRATION" ] && [ -f "$NARRATION" ]; then
  # Loudnorm narration to -16 LUFS (broadcast speech), normalize music to -24 LUFS (background),
  # mix narration 100% + music 65% with NO amix auto-normalization
  echo "Mixing: music(background) + narration(loudnorm -16 LUFS) + video"
  ffmpeg -y -i "$VIDEO" -i "$TMP_MUSIC" -i "$NARRATION" \
    -filter_complex "[1:a]loudnorm=I=-24:TP=-2:LRA=7,volume=0.50[m];[2:a]loudnorm=I=-16:TP=-1.5:LRA=11[n];[m][n]amix=inputs=2:duration=first:normalize=0[a]" \
    -c:v copy -map 0:v -map "[a]" \
    "$OUTPUT" -loglevel error 2>/dev/null
else
  # Music 30%, no narration
  echo "Mixing: music(30%) + video (no narration)"
  ffmpeg -y -i "$VIDEO" -i "$TMP_MUSIC" \
    -filter_complex "[1:a]volume=0.3[a]" \
    -c:v copy -map 0:v -map "[a]" \
    "$OUTPUT" -loglevel error 2>/dev/null
fi

rm -f "$TMP_MUSIC"

SZ=$(ls -lh "$OUTPUT" 2>/dev/null | awk '{print $5}' || echo "?")
DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT" 2>/dev/null || echo "?")
echo "Done: $OUTPUT (${DUR}s, $SZ)"
