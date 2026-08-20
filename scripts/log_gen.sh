#!/usr/bin/env bash
# Append a generation entry to the story's generation_log.jsonl.
#
# Usage:
#   bash scripts/log_gen.sh <story_dir> <asset_type> <asset_path> \
#     <model_id> <params_json> <prompt> <ref_count> <output_json> <cost_json> \
#     <duration_ms> [retries]
#
# asset_type: character_image | scene_image | scene_video | background_image | narration_audio | music_audio
#
# params_json examples:
#   '{"aspect_ratio":"16:9","resolution":"1K","safety_tolerance":"6"}'
#   '{"duration":"5","cfg_scale":0.5,"negative_prompt":"blur"}'
#
# output_json: '{"url":"...","size":1533311,"width":1928,"height":1072}'  (duration for video/audio)
# cost_json: '{"unit":"image","price":0.08}'
#
# Pipeline JSONL schema — one JSON object per line, durable across stories for analysis.

set -euo pipefail

STORY_DIR="${1:-}"; ASSET_TYPE="${2:-}"; ASSET_PATH="${3:-}"
MODEL_ID="${4:-}"; PARAMS_JSON="${5:-}"; PROMPT="${6:-}"
REF_COUNT="${7:-0}"; OUTPUT_JSON="${8:-}"; COST_JSON="${9:-}"
DURATION_MS="${10:-0}"; RETRIES="${11:-0}"

if [ -z "$STORY_DIR" ] || [ -z "$ASSET_TYPE" ] || [ -z "$MODEL_ID" ]; then
  echo "Usage: log_gen.sh <story_dir> <asset_type> <asset_path> <model_id> <params_json> <prompt> <ref_count> <output_json> <cost_json> <duration_ms> [retries]" >&2
  exit 1
fi

LOG_FILE="$STORY_DIR/generation_log.jsonl"
PRESET=$(python3 -c "import json; print(json.load(open('$STORY_DIR/story_state.json')).get('preset','unknown'))" 2>/dev/null || echo "unknown")
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Escape prompt for JSON (Python handles unicode correctly)
PROMPT_ESCAPED=$(python3 -c "import json; print(json.dumps('''$PROMPT'''))")

# Build entry
python3 -c "
import json, sys, datetime

entry = {
  'ts': '$TS',
  'asset': '$ASSET_TYPE',
  'path': '$ASSET_PATH',
  'model': '$MODEL_ID',
  'params': json.loads('''$PARAMS_JSON'''),
  'input': {
    'prompt': json.loads('''$PROMPT_ESCAPED'''),
    'refs': $REF_COUNT
  },
  'output': json.loads('''$OUTPUT_JSON'''),
  'cost': json.loads('''$COST_JSON'''),
  'duration_ms': $DURATION_MS,
  'retries': $RETRIES,
  'preset': '$PRESET'
}

with open('$LOG_FILE', 'a') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')

print(json.dumps(entry, indent=2, ensure_ascii=False))
"
