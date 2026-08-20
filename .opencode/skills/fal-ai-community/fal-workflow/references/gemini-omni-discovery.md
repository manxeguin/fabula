# Gemini Omni Flash — discovery notes

> Captured during Phase 0 of the tailes Gemini Omni integration. All endpoint
> behavior, pricing, and quirks below were verified via `genmedia` on 2026-07-11
> against fal.ai.

## Endpoint inventory

| Endpoint ID | Category | Use case |
|-------------|----------|----------|
| `google/gemini-omni-flash` | text-to-video | Text → video with audio |
| `google/gemini-omni-flash/image-to-video` | image-to-video | Still image → video with audio |
| `google/gemini-omni-flash/reference-to-video` | image-to-video | Multiple reference images + text prompt → video |
| `google/gemini-omni-flash/edit` | video-to-video | Iterative natural-language edits to a video |

**Product name on fal.ai:** "Gemini Omni Flash" (Flash tier of Gemini Omni).
**DeepMind product name:** "Gemini Omni" (see `https://deepmind.google/models/gemini-omni/prompt-guide/`).

## Pricing

Token-based billing. For 720p output: **~$0.13 per second of video**.

- Input tokens (text/audio/video): $1.875 per 1M tokens
- Output tokens: $21.875 per 1M tokens

`genmedia pricing <endpoint_id>` returns `unit_price: 1, unit: "units"` which
is a token-unit representation, not a flat $1/call. The actual US dollar cost
is per-second, sourced from the model page footer (not from the genmedia
pricing CLI).

For comparison, current pipeline video models:

| Model | Per-second | Notes |
|-------|-----------|-------|
| Grok Imagine | $0.05 | No audio, no first frame |
| Kling 2.5 Turbo | $0.07 | 5s fixed, sync, no audio |
| Kling O1 Std | $0.084 | 5/10s, `start_image_url` style ref |
| Vidu | $0.05 | First/last frame |
| **Gemini Omni Flash** | **~$0.13** | **Audio included** |
| Kling O1 Pro | $0.112 | Higher quality |
| Veo 3.1 (standard) | ~$0.10-0.20 | Audio included |
| Seedance 2.0 | $0.30 | Audio included, queue-based |
| Wan FLF2V | $0.40 flat | Fixed 5s |

**Cost implication for tailes:** A 5-scene story at 5s/scene = 25s ≈ $3.25 in
Omni video cost, comparable to the `quality` preset (~$4.50 with Seedance).
Audio is included, which means the xAI TTS step could be replaced when using
Omni — a net cost reduction if dialogue matches the desired narration.

## Schema (all four endpoints)

All four endpoints share a minimal schema: prompt + duration + aspect_ratio
(+ image_url / image_urls / video_url as appropriate). No `negative_prompt`,
no `safety_tolerance`, no `resolution`, no `seed`, no `generate_audio` (audio
is always on).

### text-to-video `google/gemini-omni-flash`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `prompt` | string | yes | — | Natural language description |
| `duration` | integer | no | 8 | Accepts a range (no enum shown) |
| `aspect_ratio` | string | no | "16:9" | Enum: "16:9", "9:16" |

Output: `video` (file).

### image-to-video `google/gemini-omni-flash/image-to-video`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `prompt` | string | yes | — | Describes motion only (still frame from image) |
| `image_url` | string | yes | — | Single starting frame |
| `duration` | integer | no | 8 | |
| `aspect_ratio` | string | no | "16:9" | |

Output: `video`.

**Field naming:** `image_url` (NOT `start_image_url` — that's the Kling O1
pattern). Same as Kling 2.5 Turbo and Grok Imagine.

### reference-to-video `google/gemini-omni-flash/reference-to-video`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `prompt` | string | yes | — | Use `<IMAGE_REF_0>`, `<IMAGE_REF_1>`, etc. to bind refs to roles |
| `image_urls` | array\<string\> | yes | — | Multiple reference images |
| `duration` | integer | no | 8 | |
| `aspect_ratio` | string | no | "16:9" | |

Output: `video`.

**Prompt syntax (NEW pattern):** `<IMAGE_REF_0>`, `<IMAGE_REF_1>`, ...
Different from the @image1 / Image 1 (name) patterns used by FLUX.2 Pro Edit
and Nano Banana 2 Edit respectively. The schema description explicitly says
"bind reference images to roles inline using tags like `<IMAGE_REF_0>`".

**Caveat:** The endpoint description says it accepts "text, images, audio, and
video together as input" but the schema only exposes `image_urls`. Audio and
video inputs are not yet in the schema (or are accepted via undocumented
fields). Treat as image+text only until verified.

### edit `google/gemini-omni-flash/edit`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `prompt` | string | yes | — | Simple instruction; "Keep everything else the same." recommended |
| `video_url` | string | yes | — | Video to edit |

Output: `video` (edited).

**Notes:**
- "Simple prompts work best" — schema description.
- Append "Keep everything else the same." to preserve the rest.
- Voice editing is not supported.
- **Geo-restricted:** "editing uploaded videos is not available for users in
  the European Economic Area (EEA), Switzerland, and the United Kingdom."

## Behavior assumptions (to be tested in Phase 3)

- **Sync vs queue:** Not yet confirmed. Most Google video models on fal.ai
  (Veo 3.1, etc.) are queue-based (async, requires polling). Conservative
  default: assume queue. Validate with a smoke test before relying on
  `video_poll_sync: true` in the preset.
- **Duration range:** Schema does not expose an enum. Default 8s. Veo 3.1
  uses 4s/6s/8s; Omni Flash likely accepts a wider range (1-15s?). Validate
  via a test call before declaring `duration_limits.omni`.
- **Aspect ratio input requirement:** Image-to-video probably requires the
  input image to match `aspect_ratio` (16:9 or 9:16). Other models on fal crop
  to fit; behavior here is unconfirmed.
- **Audio behavior:** "Audio included" is in the model description. Cannot
  be disabled. If used in the pipeline, the existing `pixar-audio` step may
  conflict — or can be skipped for scenes where Omni-generated audio is
  preferred (e.g., ambient scenes without narration).

## Cross-references for the integration

- The existing `fal-prompting/references/kling.md` follows the right
  structure for `fal-prompting/references/gemini-omni.md`.
- The existing `model-routing/SKILL.md` "Video generation" sections show
  where to add a new "Reasoning-based video" or "Iterative video editing"
  section.
- The existing `pipeline_config.json` presets are the template for the new
  `omni` preset.
- The `pixar-pipeline/SKILL.md` 7-element video prompt template is built for
  Kling/Seedance (verbose positional) — Omni is the inverse (terse
  natural-language). This is the single most error-prone integration point.
