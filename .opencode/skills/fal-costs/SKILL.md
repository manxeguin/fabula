---
name: fal-costs
description: Track and report FAL API costs per model after a pipeline run
---
## What I Do
I track how much each FAL model call costs. I support two modes:
1. **Live API query** — calls `https://api.fal.ai/v1/models/usage` (requires admin API key)
2. **Config-based estimation** — uses known prices from `pipeline_config.json` (always works)

## Usage

### After a pipeline run, the orchestrator calls:
```bash
# Estimate costs
bash scripts/fal_usage.sh --hours 1 \
  fal-ai/nano-banana-2 \
  fal-ai/nano-banana-2/edit \
  fal-ai/kling-video/v2.5-turbo/pro/image-to-video

# Or with live data (if you have an admin key)
bash scripts/fal_usage.sh --admin-key "$FAL_ADMIN_KEY" --hours 1 \
  fal-ai/kling-video/v3/pro/image-to-video
```

### The orchestrator can also query costs from a story directory's generation logs:
```bash
# Scan .status files to count successful generations per model
for d in stories/*/scenes/*/; do
  cat "$d/.status" 2>/dev/null | grep -q "DONE" && echo "scene image: $d"
  cat "$d/.video_status" 2>/dev/null | grep -q "DONE" && echo "scene video: $d"
done
```

## FAL Platform API (live costs)

**Endpoint**: `GET https://api.fal.ai/v1/models/usage`

**Auth**: Requires an **admin** API key (not the inference key). Prefixed with `Key `.

**Parameters**:
| Param | Description | Example |
|---|---|---|
| `endpoint_id` | Filter by model | `fal-ai/kling-video/v3/pro/image-to-video` |
| `start` | Start date ISO8601 | `2025-06-22T00:00:00Z` |
| `end` | End date ISO8601 | `2025-06-22T23:59:59Z` |
| `expand` | `summary` or `time_series` | `summary` |

**Response** (summary):
```json
{
  "summary": [
    {
      "endpoint_id": "fal-ai/kling-video/v3/pro/image-to-video",
      "unit": "second",
      "quantity": 25,
      "unit_price": 0.15,
      "cost": 3.75,
      "currency": "USD"
    }
  ]
}
```

## Known Model Prices (for estimation)

| Model | Unit | Price |
|---|---|---|
| `fal-ai/nano-banana-2` | image | $0.08 |
| `fal-ai/nano-banana-2/edit` | image | $0.08 |
| `fal-ai/bytedance/seedream/v4/text-to-image` | image | $0.03 |
| `openai/gpt-image-2` | image | ~$0.10 |
| `openai/gpt-image-2/edit` | image | ~$0.10 |
| `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | video | $0.35 |
| `fal-ai/kling-video/v3/pro/image-to-video` | video | ~$0.75 |
| `fal-ai/ovi/image-to-video` | video | $0.20 |
| `google/gemini-omni-flash` | second | ~$0.13 (720p, audio included) |
| `google/gemini-omni-flash/image-to-video` | second | ~$0.13 (720p, audio included) |
| `google/gemini-omni-flash/reference-to-video` | second | ~$0.13 (720p, audio included) |
| `google/gemini-omni-flash/edit` | second | ~$0.13 (720p, re-renders full video) |

**Gemini Omni pricing note:** `genmedia pricing` returns a token-based
representation (input: $1.875 / 1M tokens, output: $21.875 / 1M tokens)
which is harder to estimate for a fixed-duration call. The model page
footer documents the practical per-second rate: **~$0.13/s for 720p
output, with audio included**. For 8s default duration, that's ~$1.04
per video. A 5-scene story at 5s/scene = 25s = ~$3.25, with audio
included (replaces the xAI TTS narration step).

## Integration with Pipeline

The orchestrator should call `fal_usage.sh` at the end of each pipeline run to report costs. The skill can be loaded by the orchestrator when it needs cost information.

```bash
# In orchestrator prompt, add after merge:
echo "=== Cost Report ==="
bash scripts/fal_usage.sh --hours 1 \
  "$CHAR_MODEL" \
  "$SCENE_MODEL" \
  "$VIDEO_MODEL"
```
