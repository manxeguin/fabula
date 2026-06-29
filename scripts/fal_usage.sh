#!/usr/bin/env bash
# Query FAL usage costs for specific models.
#
# Usage:
#   bash scripts/fal_usage.sh [--admin-key KEY] [--hours N] [model_id ...]
#
# If --admin-key is provided, queries the FAL Platform API for real costs.
# Otherwise, estimates costs from pipeline_config.json pricing data.
#
# Examples:
#   bash scripts/fal_usage.sh --hours 24 fal-ai/kling-video/v3/pro/image-to-video
#   bash scripts/fal_usage.sh --admin-key "$FAL_ADMIN_KEY" fal-ai/nano-banana-2/edit

set -euo pipefail

ADMIN_KEY=""
HOURS=24
MODELS=()
OUTPUT_MODE="summary"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --admin-key) ADMIN_KEY="$2"; shift 2 ;;
    --hours) HOURS="$2"; shift 2 ;;
    --json) OUTPUT_MODE="json"; shift ;;
    *) MODELS+=("$1"); shift ;;
  esac
done

START_DATE=$(date -u -v-"${HOURS}H" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "${HOURS} hours ago" +%Y-%m-%dT%H:%M:%SZ)
END_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# --- LIVE API QUERY ---
if [ -n "$ADMIN_KEY" ]; then
  ENDPOINT_PARAMS=""
  for m in "${MODELS[@]}"; do
    ENDPOINT_PARAMS="$ENDPOINT_PARAMS&endpoint_id=$m"
  done

  RESPONSE=$(curl -s --max-time 30 \
    "https://api.fal.ai/v1/models/usage?expand=summary&start=$START_DATE&end=$END_DATE$ENDPOINT_PARAMS" \
    -H "Authorization: Key $ADMIN_KEY")

  if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo "ERROR: $(echo "$RESPONSE" | jq -r '.error.message')" >&2
    echo "Falling back to estimates..." >&2
  else
    if [ "$OUTPUT_MODE" = "json" ]; then
      echo "$RESPONSE" | jq '.summary'
    else
      echo "FAL Usage (last ${HOURS}h) — live API data"
      echo "============================================="
      echo ""
      TOTAL=0
      echo "$RESPONSE" | jq -r '.summary[]? | "\(.endpoint_id)\t\(.unit)\t\(.quantity)\t$\(.unit_price)/\(.unit)\t$\(.cost)"' | while IFS=$'\t' read -r ep unit qty uprice cost; do
        printf "  %-55s  %5s x %-8s @ %-12s = \$%s\n" "$ep" "$qty" "$unit" "\$$uprice/$unit" "$cost"
      done
      TOTAL=$(echo "$RESPONSE" | jq '[.summary[]?.cost // 0] | add')
      echo ""
      echo "  TOTAL: \$$TOTAL"
    fi
    exit 0
  fi
fi

# --- CONFIG-BASED ESTIMATION ---
if [ ! -f "pipeline_config.json" ]; then
  echo "ERROR: pipeline_config.json not found. Cannot estimate costs." >&2
  exit 1
fi

echo "FAL Usage (last ${HOURS}h) — estimated from config pricing"
echo "============================================================"
echo "  (set FAL_ADMIN_KEY for live data)"
echo ""

# Pricing lookup — simple function, works on bash 3.2+
get_price() {
  case "$1" in
    fal-ai/nano-banana-2)                          echo "0.08" ;;
    fal-ai/nano-banana-2/edit)                     echo "0.08" ;;
    fal-ai/bytedance/seedream/v4/text-to-image)    echo "0.03" ;;
    openai/gpt-image-2)                            echo "0.10" ;;
    openai/gpt-image-2/edit)                       echo "0.10" ;;
    fal-ai/kling-video/v2.5-turbo/pro/image-to-video) echo "0.35" ;;
    fal-ai/kling-video/v3/pro/image-to-video)      echo "0.75" ;;
    fal-ai/ovi/image-to-video)                     echo "0.20" ;;
    *) echo "unknown" ;;
  esac
}

get_unit() {
  case "$1" in
    fal-ai/*/image-to-video|fal-ai/ovi/*) echo "video" ;;
    *) echo "image" ;;
  esac
}

if [ ${#MODELS[@]} -eq 0 ]; then
  MODELS=(
    fal-ai/nano-banana-2
    fal-ai/nano-banana-2/edit
    fal-ai/bytedance/seedream/v4/text-to-image
    openai/gpt-image-2
    openai/gpt-image-2/edit
    fal-ai/kling-video/v2.5-turbo/pro/image-to-video
    fal-ai/kling-video/v3/pro/image-to-video
    fal-ai/ovi/image-to-video
  )
fi

TOTAL=0
for m in "${MODELS[@]}"; do
  price=$(get_price "$m")
  unit=$(get_unit "$m")
  printf "  %-55s  \$%s/%s\n" "$m" "$price" "$unit"
done

echo ""
echo "  For exact per-request costs, use: --admin-key \$FAL_ADMIN_KEY"
