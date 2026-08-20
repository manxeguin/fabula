# Prompting Gemini Omni Flash

Gemini Omni is Google's reasoning-based video model. On fal.ai it ships as **Gemini Omni Flash** with four endpoints. The single most important thing to know: **Omni is the inverse of every other video model in this skill on prompt style**. With Kling, Seedance, Veo 3.1 — longer, more prescriptive prompts win. With Omni, **shorter natural-language briefs that lean on world knowledge win**.

> The pattern that the fal.ai schema description and the official Google DeepMind prompt guide both emphasize: "Simple prompts work best." Treat Omni like a smart collaborator, not a slot machine.

## Endpoints

| Endpoint | Use when |
|----------|----------|
| `google/gemini-omni-flash` | Text → video with audio. No reference frames. |
| `google/gemini-omni-flash/image-to-video` | One reference image + text → video with audio. Default for tailes scene generation. |
| `google/gemini-omni-flash/reference-to-video` | Multiple reference images + text → video with audio. Bind refs to roles via `<IMAGE_REF_N>` tags. |
| `google/gemini-omni-flash/edit` | Iterative conversational edits to an existing video. **Omni's signature capability** — no other model in the catalog does this. |

## Standard vs other tiers

Gemini Omni Flash is the Flash tier. The fal.ai catalog currently exposes Flash only; Pro/Standard tiers may be added later. Treat Flash as the default for cost-sensitive production.

## Pricing (verify with `genmedia pricing <endpoint_id>` and the model page)

~$0.13 per second of 720p video. Audio is included. Token-based billing
(input: $1.875 / 1M tokens, output: $21.875 / 1M tokens) — see
`references/../fal-workflow/references/gemini-omni-discovery.md` for the
discovery note.

## Prompt structure (the inverse rule)

Where other video models want a 40-80 word structured positional description,
Omni wants a 20-40 word natural-language brief that *describes what the
video is, not how to render it*.

```text
[subject] [doing what] in [setting]. [One natural sentence about mood or
intent]. [Optional camera note in plain English].
```

Example (image-to-video, animating a still of a girl at a fair):

```text
The girl waves at the carousel horses as the ride starts to turn, looking
up with wonder. Golden evening light, soft breeze in her hair.
```

Bad (Kling-style positional prompt that underperforms here):

```text
Slow push-in from medium shot. Golden hour key light from camera right.
Rim light on hair. Subject waves with right arm. Horses rotate clockwise
in background. Dust particles in light beam. 50mm lens feel. Shallow
depth of field. Playful anticipation. Cinematic Pixar 3D aesthetic.
```

That verbose positional format is what Omni's reasoning architecture is
designed to *not need*. The world knowledge and physical-understanding
training fills in the rendering details automatically. Piling on
cinematography terms gives the model less signal, not more.

## When to use which prompt length

| Use case | Length | Why |
|----------|--------|-----|
| Image-to-video (animate a still) | 1-2 sentences, 20-40 words | Image carries identity, setting, lighting. Prompt = motion + intent. |
| Text-to-video (no reference) | 3-5 sentences, 40-80 words | No image to anchor identity; world knowledge needs more context. |
| Reference-to-video (multiple refs) | 2-4 sentences, 30-60 words | Roles are bound via tags. Prompt describes the *scene*, refs provide *who/what*. |
| Edit (iterative amend) | One short imperative sentence | "Replace the pomegranates with apples." "Keep everything else the same." Append "Keep everything else the same." to preserve the rest. |

## Multi-input / multi-shot patterns

### Reference-to-video with `<IMAGE_REF_N>` tags

The reference-to-video endpoint uses an inline tag syntax — different from
the @image1 / "Image 1 (name)" patterns used by FLUX.2 Pro Edit and
Nano Banana 2 Edit.

```text
The astronaut from <IMAGE_REF_0> walks across the surface of Mars in
<IMAGE_REF_1>, leaving boot prints in the red dust. The sky shifts from
dusk to deep blue. 8 seconds, one continuous shot.
```

Refs are passed via the `image_urls` array. The numeric index in the tag
matches the array position.

> **Schema caveat:** The endpoint description claims it accepts "text,
> images, audio, and video together as input" but the schema only exposes
> `image_urls`. Treat audio/video references as experimental until verified.

### Iterative video editing (signature pattern)

The edit endpoint preserves the video across multiple conversational
amends — the same video can be passed to `google/gemini-omni-flash/edit`
repeatedly with different `prompt` instructions. Each call rewrites the
video according to the new instruction while preserving the parts that
weren't changed.

```text
# Turn 1
"Replace the pomegranates with apples."

# Turn 2 (on the result of Turn 1)
"Change the tablecloth to blue linen. Keep everything else the same."

# Turn 3 (on the result of Turn 2)
"Add a small vase of sunflowers in the center of the table."
```

The schema description says: *"Simple prompts work best; add 'Keep
everything else the same.' to preserve the rest of the scene."* Always
append that phrase unless the instruction is intended to redo the whole
video.

**Geo-restriction:** Editing uploaded videos is not available in the
European Economic Area (EEA), Switzerland, and the United Kingdom.
T2V / I2V generation is unrestricted.

**Voice editing is not supported.** Schema explicitly says so.

## Camera vocabulary that works

Omni's prompt guide introduced specific camera terms that the model
recognizes as named directions (not just descriptive language):

- **Continuous shot / oner**: "one continuous shot", "oner", "single take"
- **Push / pull**: "push in", "punch in", "pull back", "pull out"
- **Dolly effects**: "dolly zoom" (vertigo effect), "dolly in", "dolly out"
- **Static / locked**: "static", "locked off", "fixed camera"
- **Movement style**: "natural smartphone zoom", "film camera", "webcam style"
- **Standard cinematography**: "slow pan", "crane up", "low angle", etc.

When using these terms, keep them isolated. Don't combine with prestige
adjectives ("cinematic slow push-in with golden hour") — that conflates
two different signals. Pick the camera direction; let Omni choose the
look.

## World knowledge and "less is more"

The official prompt guide is explicit: *"With Veo, you need to share
precise instructions to get the best results. But with Gemini Omni, you
don't have to be as prescriptive with your prompt."*

This means:

- For historical / scientific / cultural content, **name the thing**
  instead of describing it. "A 1960s diner" beats "a retro restaurant
  with chrome stools and a milkshake machine." Omni knows what a 1960s
  diner looks like.
- For complex actions, **name the action** once. Omni applies it across
  the video frames. "She does a skateboard kickflip" beats describing
  each joint angle per frame.
- For style transfer, **name the style** plainly. "In the style of
  watercolor" beats "soft translucent washes with visible paper texture."

## Text rendering in sync with visuals

Omni can render text inside the video in sync with the motion. Examples
from the prompt guide:

- "word by word, one word on the screen at a time: did, you, know, that,
  this, model, can, do, pretty, good, text!? each word appears with a
  different animated style, perfect pacing to a rhythm, sizzle reel."
- "The screen reads 'SALE' in large red letters that pulse on every beat."

This is a sharp differentiator from Veo 3.1 and other video models where
on-screen text often renders misspelled or out-of-sync.

## Storyboard input

Omni accepts a storyboard as a sequence of reference images + a text
brief that names the beats:

```text
Show me in this story. Follow the story exactly in order starting top
left. Entire story in 10 seconds. Cinematic.
```

This collapses a multi-shot sequence into a single call — useful for
social stories and short ads. For longer narrative films (the tailes
default), per-scene generation is still the right pattern.

## Style transfer (multi-part progression)

Omni can transition through multiple styles in one video. Example from
the prompt guide:

```text
Create a four-part stylistic progression of the video reference that
begins with a vibrant colored crayon aesthetic, featuring rich, waxy,
textured strokes and playful, hand-drawn character designs against a
backdrop of heavily granulated paper. Transition seamlessly into a
graphite pencil sketch on textured paper, utilizing cross-hatching,
varying line weights, and a 12fps "line boiling" effect to emphasize a
hand-drawn feel. Next, morph into a hyper-realistic 3D translucent
glass style, characterized by complex light refractions, caustic
patterns, and soft internal glows within a minimalist studio setting.
Conclude the sequence with a tactile risograph print look, applying a
limited three-color palette, grainy halftone textures, and intentional
registration overlays for a retro, mechanical finish.
```

## Don't

- **Don't pad with prestige adjectives.** "stunning", "cinematic",
  "masterpiece", "beautiful", "gorgeous" — drop them. Omni's reasoning
  interprets these as noise.
- **Don't over-position the subject.** "She stands three feet to the
  left of the table" is anti-signal. Say "she stands by the table."
- **Don't restate what the reference image already shows.** Pass the
  image; don't describe its contents in the prompt unless you want
  them changed.
- **Don't use weighted parentheses, booru tags, or JSON-in-prompts.**
  Omni ignores them.
- **Don't request extreme slow-motion, 1000fps+ time-warps, or other
  implausible physics.** Omni has improved physical understanding but
  these still fail.
- **Don't try to disable audio.** Audio is always on for text-to-video
  and image-to-video. For pure silent video, generate without a
  separate silence step and accept the model's ambient audio.
- **Don't combine camera vocabulary with lighting/grade adjectives.**
  Pick one signal. "Slow push-in" or "golden hour", not both at once.

## Common parameters

Run `genmedia schema <endpoint_id> --json` for the authoritative list. The
exposed parameter set is intentionally minimal:

- `prompt` (required) — natural-language description
- `duration` (integer, default 8) — length in seconds
- `aspect_ratio` (string, default "16:9", enum "16:9" / "9:16")
- `image_url` (image-to-video) — single starting frame
- `image_urls` (reference-to-video) — array of reference images
- `video_url` (edit) — video to amend

**Not exposed:** `negative_prompt`, `safety_tolerance`, `resolution`,
`seed`, `generate_audio`, `cfg_scale`. Internal Gemini guardrails apply
for safety. The other omissions are deliberate — Omni's reasoning
architecture is the control.

## Tailes-specific notes

- **Default for new `omni` preset:** `google/gemini-omni-flash/image-to-video`
  with `image_url` (the field name matches Kling 2.5 Turbo / Grok Imagine
  patterns, not Kling O1's `start_image_url`).
- **Audio replaces narration:** Omni generates audio, which means the
  xAI TTS narration step in the tailes pipeline can be skipped for
  scenes that don't need voice (e.g., ambient establishing shots). For
  scenes that need Spanish narration matching scene beats, keep the
  existing `pixar-audio` step and use Omni's audio as the bed.
- **Cost fit:** $0.13/s with audio included. A 5-scene story at 5s =
  25s = $3.25. Comparable to `quality` (~$4.50) with audio *added* on
  top, so the `omni` preset is the cheaper path when audio is desired.
