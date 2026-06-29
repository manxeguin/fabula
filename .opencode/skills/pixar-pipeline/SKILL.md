---
name: pixar-pipeline
description: Config-driven Pixar story video pipeline — switch models by changing PIPELINE_PRESET env var
---
## What I Do
I document the Pixar story video generation pipeline. Models are selected via presets in `pipeline_config.json`. Switch between debug/testing/budget/quality by setting the `PIPELINE_PRESET` environment variable. Uses prompt craft rules from the [fal-ai-community skills](https://github.com/fal-ai-community/skills) (vendored in `.opencode/skills/fal-ai-community/`).

## Architecture

```
Prompt → Character → Story → Scenes → Videos → Narration → Merge → Music → Final
         (config)    (LLM)   (config)  (config)  (xAI TTS)  (FFmpeg) (Sonilo) (FFmpeg)
```

## Presets

| Preset | Character (text) | Character (photo ref) | Scene Images | Videos | 5-Scene Cost |
|---|---|---|---|---|---|---|
| `debug` (default) | FLUX.2 Klein 9B (~$0.005) | FLUX.2 Klein 9B Edit (~$0.005) | FLUX.2 Klein 9B (~$0.005) | Grok Imagine Video (~$0.05) | ~$0.30 |
| `testing` | Nano Banana 2 ($0.08) | Nano Banana 2 Edit ($0.08) | Nano Banana 2 Edit ($0.08) | Kling 2.5 Turbo ($0.35) | ~$2.23 |
| `budget` | Seedream V4 ($0.03) | Nano Banana 2 Edit ($0.08) | Nano Banana 2 Edit ($0.08) | Kling 2.5 Turbo ($0.35) | ~$2.18 |
| `quality` | GPT Image 2 (~$0.10) | GPT Image 2 Edit (~$0.10) | GPT Image 2 Edit (~$0.10) | Seedance 2.0 (~$0.70) | ~$4.50 |

**Note**: GPT Image 2 Edit is unreliable with photo references (frequent timeouts). For photo-based character generation, Nano Banana 2 Edit is recommended regardless of preset. **Quality preset** prefers Seedance 2.0 for video (best image-to-video quality per fal-ai-community model-routing), with Kling v3 Pro as fallback for multi-prompt/element control.

## Prompt Crafting Rules

These rules come from the fal-ai-community `fal-prompting` skill and apply to ALL presets:

1. **Visual facts beat prestige adjectives.** Replace "stunning, cinematic masterpiece, beautiful, gorgeous, Pixar animation style, 3D render quality, soft lighting" with concrete descriptors: "overcast daylight, 50mm lens feel, dappled shadows, warm tungsten accent."

2. **Video prompts must be comprehensive, not minimal.** Kling O1 uses `start_image_url` as a character/style reference — the image carries identity, but the prompt guides motion, atmosphere, lighting, and mood. Every video prompt needs 7 elements in order: camera movement, setting, time of day, lighting, atmospheric details, character motion, mood cue, and Pixar style vocabulary. Target 40-80 words, 5-7 sentences.

   ❌ **Bad:** "slow push-in toward the subject, subtle breeze in hair, ambient crowd movement in background."
   → 3 fragments, no setting, no lighting, no mood. Generic motion, no visual anchoring.

   ✅ **Good:** "Slow push-in from the doorway toward the garden path. Golden morning sunlight streams through leaves, casting dappled shadows on the stone path. Dust particles float lazily in the warm light beams. The character's pigtails bounce with each small step forward, arms slightly out for toddler balance. A yellow bucket swings gently from one hand. Playful eager anticipation. Disney-Pixar aesthetic, rounded plastic-like forms, subsurface scattering on skin, bright saturated color palette, cinematic lighting."
   → 7 sentences, 80 words. All 7 elements present.

3. **SCLCAM structure for visual prompts.** Build in this order: **S**ubject → **C**ontext → **L**ens/Framing → **C**amera Motion → **A**tmosphere → **M**ood/Color.

4. **GPT Image 2 (quality preset).** Use the five-section template: Scene / Subject / Important details / Use case / Constraints. In edit mode: separate "Change:" from "Preserve:" clearly.

5. **Never use** weighted parentheses, booru tags, JSON-in-prompts, or style markup. Plain English only.

Camera vocabulary is defined in `pipeline_config.json` → `camera_vocabulary`.

## Switching Presets

```bash
# Testing (cheapest, fast iteration)
export PIPELINE_PRESET=testing
/pixar-story "a brave turtle"
```

This works because the orchestrator reads `pipeline_config.json` and builds cURL commands dynamically from the preset's model IDs, endpoints, and parameter mappings.

## Config Structure
The config handles model-specific differences:
- `scene_image_param`: `image_urls` (most models) 
- `video_image_param`: `image_url` (Kling 2.5, Ovi) or `start_image_url` (Kling v3)
- `video_has_elements`: true only for Kling v3 (character consistency via `elements`)
- `video_poll_sync`: whether to poll for completion or expect sync response

## File Upload Pattern
```bash
URL=$(python3 scripts/fal_upload.py path/to/file.png)
```
Upload character.png ONCE, store URL, reuse everywhere.

## Directory Structure
```
stories/<preset>_<slug>/
├── character/
│   ├── character.md
│   ├── character.png
│   └── character_url.txt
├── scenes/
│   ├── manifest.txt
│   ├── 01-title/
│   │   ├── scene.md, scene.png, scene_url.txt, scene.mp4
│   │   ├── .status, .video_status, generate.log, video_generate.log
│   │   ├── scene_narration_{voice}.mp3   ← per-scene padded narration
│   │   └── ...
│   └── ...
├── narration_{voice}.mp3                ← full story concat
├── final_narrated_{voice}.mp4           ← video + narration
└── final.mp4
```

### Audio File Naming (consistent convention)
| File | Scope | Pattern | Keeper |
|---|---|---|---|
| `speech_{voice}.mp3` | Per scene | Raw TTS output | ❌ deleted after padding |
| `scene_narration_{voice}.mp3` | Per scene | Padded to video duration | ✅ |
| `narration_{voice}.mp3` | Story | All scenes concatenated | ✅ |
| `music.mp3` | Story | Instrumental background track | ✅ |
| `final_with_music_{voice}.mp4` | Story | Video + narration + music mixed | ✅ |
| `final_narrated_{voice}.mp4` | Story | Video + narration mixed | ✅ |

Voices: `ara` (warm), `eve` (energetic), `sal` (smooth) — all female, all Spanish.

## Resolution Consistency

All scenes MUST use the same resolution. The pipeline enforces **16:9 landscape**:
- Nano Banana 2 edit: `aspect_ratio: "16:9"`
- GPT Image 2 edit: `image_size: "landscape_16_9"`
- Kling video models: inherit input image resolution

This is configured in `pipeline_config.json` → `presets.<name>.scene_params`.
`merge_videos.sh` auto-detects mismatches and normalizes if needed.

### Why 16:9
- Supported by ALL models (Nano Banana 2, GPT Image 2, Kling, Seedream)
- Standard cinematic/video format
- Consistent across text-to-image, image-to-image, and image-to-video
- Character images use 1:1 (square) for reference sheets

## Character Anchor System

From the fal-ai-community `character-design` skill. The CHARACTER ANCHOR is the identity contract:

```markdown
## CHARACTER ANCHOR
- Codename: [name]
- Age range: [5 years old]
- Face: [round face, soft jawline]
- Eyes: [large wide-set hazel eyes, thick eyelashes]
- Nose and mouth: [small button nose, wide expressive smile]
- Skin: [warm olive skin, scattered freckles]
- Hair: [chestnut brown shoulder-length wavy hair, side part]
- Build: [short sturdy build, Pixar-proportioned, bouncy posture]
- Signature: [bright pink smocked dress, yellow ribbon in hair]
```

**Rules:**
- Create the anchor once in `character/character.md`.
- Copy-paste it VERBATIM into every scene visual prompt. Never rephrase.
- The anchor defines what stays the same. Only the SCENE VARIABLE (expression, pose, setting, camera, lighting) changes per shot.
- If a result changes identity, strengthen the anchor — don't add more style words.

### Consistency Rules (Anti-Drift)

Three mechanisms prevent character age and style drift across scenes:

| Rule | How | Why |
|---|---|---|
| **Visual reference** | Debug preset uses `image_urls` (FLUX.2 Klein Edit) — upload character.png once, pass as reference for every scene | Model starts from the same visual anchor, not from scratch |
| **Proportion lock** | Every visual prompt repeats explicit body ratio: "toddler proportions, head 1:4 of total body height, chubby limbs" | Without numeric ratios, models guess age randomly |
| **Style lock** | Every visual prompt ends with: "Disney-Pixar aesthetic, rounded plastic-like forms, subsurface scattering on skin, bright saturated color palette" | Prevents style drift (flat illustration vs 3D render vs anime) |

Text descriptors that caused drift (DO NOT USE):
- "Pixar animation style" → too vague, model guesses
- "3D render quality" → can become generic CGI
- "cinematic" → 0 signal, every model thinks everything is cinematic

### Pixar Style Vocabulary (USE THIS)
```
Disney-Pixar aesthetic, rounded plastic-like forms, subsurface scattering on skin,
bright saturated color palette, cinematic lighting, shallow depth of field, 50mm lens feel
```
Include this exact phrase at the end of every visual prompt.

## Video Prompt Crafting

Video prompts must be comprehensive — minimal 2-line prompts produce underwhelming results. Every video prompt MUST include these 7 elements, in order:

| # | Element | Source in scene.md | Example |
|---|---|---|---|
| 1 | Camera movement + framing | `## Visual Direction` → Camera | "Slow push-in from doorway toward garden path" |
| 2 | Setting + time of day | `## Visual Prompt` context | "Golden morning sunlight streaming through leaves" |
| 3 | Lighting conditions | `## Visual Direction` → Lighting | "Dappled shadows on stone path, warm backlight" |
| 4 | Atmospheric details | `## Visual Prompt` | "Dust particles floating lazily in light beams" |
| 5 | Character motion | `## Narrative` context | "Pigtails bounce with each small step, arms out for toddler balance" |
| 6 | Mood cue | `## Visual Direction` → Mood | "Playful eager anticipation" |
| 7 | Style vocabulary | (standard phrase) | "Disney-Pixar aesthetic, rounded plastic-like forms..." |

**Format**: 5-7 sentences, 40-80 words. Single flowing paragraph. Never re-describe the character's static traits (clothing, hair color) — the reference image carries that.

**Wrong (old minimal style)**:
```
slow push-in toward the poster, dust particles floating, hair swaying
```

**Correct (new comprehensive style)**:
```
Slow push-in from the doorway toward the garden path. Golden morning sunlight
streams through leaves, casting dappled shadows on the stone path. Dust
particles float lazily in the warm light beams. The character's pigtails bounce
with each small step forward, arms slightly out for toddler balance. A yellow
bucket swings gently from one hand. Playful eager anticipation. Disney-Pixar
aesthetic, rounded plastic-like forms, subsurface scattering on skin, bright
saturated color palette, cinematic lighting.
```

## Photo-to-Character (Vision Model)

When a user provides a reference photo (`--photo path.jpg`) but doesn't describe who's in it, the pipeline auto-describes the photo using FAL's vision model:

| Model | Endpoint | Price |
|---|---|---|
| Nemotron Nano Omni Vision | `nvidia/nemotron-3-nano-omni/vision` | $0.006/1K tokens |

```bash
# Auto-describe photo
bash scripts/fal_describe_image.sh path/to/photo.jpg
# Output: detailed description of subject, appearance, clothing, setting
```

The description feeds into the CHARACTER ANCHOR and Pixar generation prompt. Skip if the user already described the subject.

## Character Reference Rules

### FORBIDDEN: Multi-pose sheets
- Character reference images must show exactly ONE character, ONE pose, plain background
- Never use "character reference sheet", "turnaround", "multiple views", "variations" in prompts
- Multi-pose images cause scene models to duplicate the character (4 Claudias in one scene)

## Scene Prompt Quality Rules

### Spatial coherence
- Characters and objects must obey physical reality in prompts
- Describe WHERE people are: "kneels beside the stool inside the room", not "hands appear from frame edge"
- Never describe body parts crossing through windows, walls, or solid objects
- Always specify "a single [character]" or "only one child" to prevent duplicates
- When including secondary characters (parent), describe them as distinct people, not just body parts

### Landscape framing
- Every scene visual prompt must frame for 16:9
- Distribute elements horizontally (left/center/right)
- Never center a single tall figure — that produces portrait padding

## Safety Filters

All presets configure the minimum safety level for each model:

| Model | Setting | Value | Notes |
|---|---|---|---|
| Nano Banana 2 | `safety_tolerance` | `"6"` | 6 = most permissive. Internal Gemini filters still apply. |
| Seedream V4 | `enable_safety_checker` | `false` | Disables external checker. |
| GPT Image 2 | none | — | OpenAI content policy is built-in, not configurable. |

### Known Triggers (even at max permissive)
Concepts that can still get blocked by internal model guardrails:
- Minors in distress / crying / fear / panic
- "Lost child", "abandoned", "alone and scared"
- Any prompt suggesting harm to children

### Workaround
If a prompt is blocked, **rewrite it with positive framing**:
- "Lost and crying in a crowd" → "Looking around with curious wonder among colorful festival-goers"
- "Scared and alone" → "Taking a quiet moment to gather courage"
- "Tears streaming down her face" → "Her eyes glisten with emotion as she takes a deep breath"

This preserves the emotional beat while avoiding flagged concepts.

## Music Pipeline

Model: **Sonilo v1.1 text-to-music** ($0.0025/sec, ~$0.06 per 25s story). Exact duration match via `duration` param. Instrumental by prompt ("no vocals"). cURL sync API.

### Command
```
/pixar-music --story sevillana-feria                       → auto-prompt, music only
/pixar-music --story sevillana-feria --voice ara           → music + narration mix
/pixar-music --story sevillana-feria --prompt "joyful flamenco"
/pixar-music --story sevillana-feria --youtube "https://youtube.com/..." --voice ara
/pixar-music --story sevillana-feria --youtube "https://youtube.com/..." --start 45
```

### YouTube Audio
When `--youtube <url>` is set, downloads audio from YouTube via `yt-dlp` instead of generating via Sonilo. Mutually exclusive with `--prompt`. Audio is looped/trimmed to match video duration automatically.

- `--start <seconds>`: start offset for the YouTube track (default: 0)
- Download + convert to MP3 via `scripts/yt_audio.sh`
- Mixing (loudnorm, volume, amix) works identically regardless of audio source

### Auto-prompt
Reads story context and generates style-matched prompt:
```
"instrumental flamenco guitar, festive Spanish fair atmosphere, warm and playful,
 children's wonder, cinematic Pixar soundtrack style, acoustic, no vocals"
```

### Mix Levels
| Track | Processing | Effective Level |
|---|---|---|
| Narration | `loudnorm=I=-16:TP=-1.5:LRA=11` | -16 LUFS (broadcast speech) |
| Music | `loudnorm=I=-24:TP=-2:LRA=7,volume=0.50` | ~-30 LUFS (background) |

`amix` with `normalize=0` — prevents auto-attenuation of narration.
Music is looped if shorter than video, trimmed if longer.

### Why Sonilo
| Model | Price (25s) | Duration Control | Instrumental | API |
|---|---|---|---|---|
| Sonilo v1.1 | **$0.06** | `duration` param | Prompt-based | sync cURL |
| ElevenLabs Music | $0.33 | `music_length_ms` | `force_instrumental` | sync cURL |
| MiniMax v2 | $0.03 | none | requires lyrics | sync cURL |

## Narration Rules

Narration is a single flowing children's story, not per-scene descriptions. The listener should not perceive scene boundaries.

### Narrative Style (NOT Scene Description)

| Mechanic | ❌ Wrong | ✅ Right | Why |
|---|---|---|---|
| Perspective | "Carmen elige un libro." | "Cada tarde, Carmen elegía un libro..." | Storytelling voice, not report |
| Transitions | "Carmen entra en Wonderland." | "De repente, las páginas brillaron y..." | Connect to previous event |
| Emotion | "Carmen está feliz." | "Una sonrisa iluminó su carita." | Show through action, don't state |
| Hooks | "Carmen vuelve a casa." | "Cuando el sol se puso, Carmen supo que..." | Create anticipation |
| Naming | "Carmen hace X. Carmen va a Y." | "Se acurrucó en su rincón... Cerró los ojos y..." | Avoid repeating name every sentence |

### Speaking Rate & Length
Spanish TTS speaks ~12 chars/s at natural pace. Audio acceleration is forbidden.

| Scene duration | Narration length | Rationale |
|---|---|---|
| 5s | 40-55 chars | Tight scene, tight narration |
| 8s | 70-90 chars | Room for narrative richness |
| 10s | 90-110 chars | Full storybook sentence |

Formula: `chars ≈ (duration − 1.5s) × 12`. The 1.5s natural silence at scene end is the pause — no synthetic gaps needed.

### Padding Strategy
| Transition type | Gap before | Gap after |
|---|---|---|
| `last_frame_continuity` | 0s (`--gap none`) | 0s |
| `cut` (same context) | 0.05s (`--gap minimal`) | 0s |
| `cut` (context change) | 0.15s (`--gap normal`) | 0.15s |

`pad_audio.sh --gap none|minimal|normal` controls gap strategy. Default: `--gap minimal` (subtle breath).

## Review Workflow

Optionally stop after scene images to inspect and approve before costly video generation.

```
Character → Story → Scene Images ──┬── AUTO (--skip-review) ──→ Videos → Merge → Narration → Music
                                    │
                                    └── REVIEW (--review) ──→ /pixar-review ──→ Videos
```

### Commands
```bash
# Stop after images, show for review
/pixar-generate --review <story-slug>

# Review and approve each scene
/pixar-review <story-slug>
# Shows scene.png + visual prompt + motion prompt + narration
# Actions: ok / reject / edit "feedback" / all good

# After approval, generate only videos
/pixar-generate --videos-only <story-slug>

# Skip review entirely (current default behavior)
/pixar-generate --skip-review <story-slug>
```

State keys: `review_done` (story level), per-scene review status via `.reviewed` marker file.

## Model Quirks & Gotchas

Lessons from production errors. See `pipeline_config.json` → `model_quirks` for full details.

| Issue | Models affected | Fix |
|---|---|---|
| Requires `prompt` field (not just image) | Kling 2.5T, Kling O1, Grok Imagine, Seedance, Wan | Always pass `prompt` in video calls |
| Field name is `start_image_url` not `image_url` | Kling O1, Wan FLF2V | Check `video_image_param` in config |
| `start_image_url` is style reference, NOT first frame | Kling O1 | Kling O1 uses start_image_url for identity cues only — video does NOT start from the exact input frame. For strict frame-to-frame continuity, use Wan FLF2V |
| Duration restricted with start_image | Kling O1: 5s or 10s only | Validate scene duration against `duration_limits` |
| TTS field is `text` not `input` | xAI TTS | Always use `text` field |
| `safety_tolerance` must be string | Nano Banana 2 | Use `"6"` (string), not `6` (int) |
| MP3 concat with `-c copy` corrupts | FFmpeg | Use `filter_complex` re-encode, not concat demuxer |
| Sync vs async response | Kling/Grok=sync, Seedance/Wan=queue | Check `video_poll_sync` in config |

## Retry Rules
- Every FAL API call: retry once after 30s
- If blocked by safety filter: retry once with softened/positive prompt
- On second failure: report error and ask user
- Validate: images >10KB, videos >100KB

## Variable Scene Durations

Scenes are no longer fixed at 5 seconds. Each scene has a `## Duration` field in its `scene.md`.

### Default durations by story beat:
| Beat | Scene | Duration | Why |
|---|---|---|---|
| Hook | 1 | 4s | Quick establishing, grab attention |
| Development 1 | 2 | 7s | Room for action and movement |
| Development 2 | 3 | 6s | Medium paced beat |
| Turn / Climax | 4 | 8s | Needs time for emotional weight |
| Close | 5 | 5s | Strong final frame |

### Duration limits by preset:
| Preset | Min | Max | Model |
|---|---|---|---|
| debug | 3s | 10s | Grok Imagine |
| testing | 5s | 5s | Kling 2.5 Turbo (fixed) |
| budget | 5s | 10s | Kling O1 Standard |
| quality | 5s | 15s | Seedance 2.0 |
| cinematic | 5s | 15s | Seedance 2.0 Fast |

### Natural language control:
```
make scene 2 8 seconds
make the opening longer, 7s
```

## Frame Continuity

Scenes can visually connect using the previous scene's last frame as the starting image.

### Transition modes:
| Mode | Behavior | Speed |
|---|---|---|
| `cut` (default) | Independent scene, no visual connection. Parallel generation. | Fast |
| `last_frame_continuity` | Uses previous video's last frame as `start_image_url`. Sequential. | Slow |

### How it works:
```
Scene 2 video → extract_last_frame.sh → scene2/scene_last_frame.png
  → upload to CDN → used as start_image_url for Scene 3 video
```

After every video generates, its last frame is automatically saved as `scene_last_frame.png` for future editing/iteration.

### Natural language control:
```
connect scene 3 to scene 4
all cuts, no continuity
scene 2 should flow naturally into scene 3
```

### Models supporting frame continuity:
| Model | Field | Duration |
|---|---|---|
| Kling O1 Standard | `start_image_url` | 5s or 10s |
| Kling O1 Pro | `start_image_url` | 5s or 10s |
| Seedance 2.0 | `image_url` + `end_image_url` | 4-15s |
| Wan FLF2V | `start_image_url` + `end_image_url` | flat rate |

## Retry Rules (continued)
