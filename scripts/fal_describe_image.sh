#!/usr/bin/env bash
# Describe an image using FAL's vision model (Nemotron Nano Omni Vision).
#
# Usage:
#   bash fal_describe_image.sh <image_path>
#
# Output: image description (plain text)

set -euo pipefail

IMAGE="${1:-}"

if [ -z "$IMAGE" ] || [ ! -f "$IMAGE" ]; then
  echo "Usage: bash fal_describe_image.sh <image_path>" >&2
  exit 1
fi

FAL_KEY="${FAL_KEY:-$(grep -o 'FAL_API_KEY=[^[:space:]]*' ~/.zshrc 2>/dev/null | head -1 | cut -d= -f2)}"
if [ -z "$FAL_KEY" ]; then
  echo "ERROR: FAL_KEY or FAL_API_KEY not set" >&2
  exit 1
fi
export FAL_KEY

# Upload image
IMG_URL=$(python3 "$(dirname "$0")/fal_upload.py" "$IMAGE" 2>/dev/null)
if [ -z "$IMG_URL" ] || [ "$IMG_URL" = "null" ]; then
  echo "ERROR: failed to upload image" >&2
  exit 1
fi

# Describe via vision model
RESULT=$(curl -s --max-time 30 \
  "https://fal.run/nvidia/nemotron-3-nano-omni/vision" \
  -H "Authorization: Key $FAL_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg img "$IMG_URL" '{
    image_url: $img,
    prompt: "Describe this photo in detail. Include: subject (age, gender), facial features, hair, expression, clothing, setting, lighting, and mood. Be specific and concrete — no fluff adjectives."
  }')")

DESC=$(echo "$RESULT" | jq -r '.output // empty')
if [ -z "$DESC" ] || [ "$DESC" = "null" ]; then
  echo "ERROR: no description in response: $(echo "$RESULT" | head -c 200)" >&2
  exit 1
fi

echo "$DESC"
