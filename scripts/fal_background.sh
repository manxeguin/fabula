#!/usr/bin/env bash
# Generate a Pixar-style background/environment from a source photo.
#
# Usage:
#   fal_background.sh <source_photo> <story_dir> <bg_name>
#
# Output:
#   backgrounds/<bg_name>/background.png
#   backgrounds/<bg_name>/background_url.txt
#   backgrounds/<bg_name>/source.jpg

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_PHOTO="${1:-}"
STORY_DIR="${2:-}"
BG_NAME="${3:-}"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -n "$SOURCE_PHOTO" ] || die "Usage: fal_background.sh <source_photo> <story_dir> <bg_name>"
[ -n "$STORY_DIR" ] || die "Usage: fal_background.sh <source_photo> <story_dir> <bg_name>"
[ -n "$BG_NAME" ] || die "Usage: fal_background.sh <source_photo> <story_dir> <bg_name>"
[ -f "$SOURCE_PHOTO" ] || die "Source photo not found: $SOURCE_PHOTO"

FAL_KEY="${FAL_KEY:-${FAL_API_KEY:-$(grep -o 'FAL_API_KEY=[^[:space:]]*' ~/.zshrc 2>/dev/null | head -1 | cut -d= -f2)}}"
[ -n "$FAL_KEY" ] || die "FAL_API_KEY not set"

BG_DIR="$STORY_DIR/backgrounds/$BG_NAME"
mkdir -p "$BG_DIR"

# Copy source photo
cp "$SOURCE_PHOTO" "$BG_DIR/source.jpg" 2>/dev/null || cp "$SOURCE_PHOTO" "$BG_DIR/source.png"

# Upload source photo
PHOTO_URL=$(python3 "$SCRIPT_DIR/fal_upload.py" "$SOURCE_PHOTO" 2>/dev/null)
[ -n "$PHOTO_URL" ] || die "Failed to upload photo"

# Generate Pixar-style background
PROMPT="Transform this photo into a Pixar 3D animated film environment. Keep the exact layout, structure, and spatial arrangement of the room/location. Pixar-style: rounded forms, bright saturated colors, cinematic lighting, warm atmosphere. Disney-Pixar aesthetic, subsurface scattering, shallow depth of field. No characters, no people — just the empty environment. 16:9 landscape."

RESPONSE=$(curl -s --max-time 180 \
  "https://fal.run/fal-ai/nano-banana-2/edit" \
  -H "Authorization: Key $FAL_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg prompt "$PROMPT" --arg ref "$PHOTO_URL" '{
    prompt: $prompt, image_urls: [$ref],
    aspect_ratio: "16:9", output_format: "png",
    num_images: 1, safety_tolerance: "6",
    resolution: "1K", limit_generations: true
  }')")

BG_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['images'][0]['url'])" 2>/dev/null)
[ -n "$BG_URL" ] || die "Failed to generate background. Response: $(echo "$RESPONSE" | head -c 300)"

# Download background
curl -sLo "$BG_DIR/background.png" "$BG_URL"
SIZE=$(stat -f%z "$BG_DIR/background.png" 2>/dev/null || stat -c%s "$BG_DIR/background.png" 2>/dev/null)
[ "$SIZE" -gt 10000 ] || die "Background image too small: $SIZE bytes"

# Upload for CDN reuse
BG_CDN_URL=$(python3 "$SCRIPT_DIR/fal_upload.py" "$BG_DIR/background.png" 2>/dev/null)
echo "$BG_CDN_URL" > "$BG_DIR/background_url.txt"

echo "Background generated: $BG_DIR/background.png ($SIZE bytes)"
echo "CDN URL: $BG_CDN_URL"
