# Gemini Omni iterative video edit

> Recipe for the "Nano Banana for video" pattern. Take an existing video,
> amend it through natural-language instructions across multiple turns,
> preserve the parts that work. No other model in the fal.ai catalog does
> this — `google/gemini-omni-flash/edit` is Omni's signature capability.

## When to use

- The user wants to tweak a single element of an existing video without
  re-rendering the whole thing. "Change her shirt to red. Keep everything
  else the same."
- The user is iterating on a generated video and wants quick
  conversational amends between turns.
- The user wants to refine a video's camera direction, lighting, or
  action without going back to the prompt-engineering stage.

Do not use this recipe for:

- First-time video generation (use the standard text-to-video or
  image-to-video route).
- Style transfer across the whole video (use
  `fal-ai/kling-video/o3/pro/video-to-video/reference` or similar).
- Bulk automated re-edits at scale (this is conversational, designed
  for human-in-the-loop iteration).

## Endpoints and schema

| Endpoint | Use for |
|----------|---------|
| `google/gemini-omni-flash/edit` | Conversational amend. `prompt` (simple instruction) + `video_url` (the video to amend). |

The schema is intentionally minimal — there is no `negative_prompt`,
no `duration` override, no `aspect_ratio` change. The output preserves
the input video's duration and aspect ratio. This is deliberate: the
edit endpoint is for *changing*, not *re-rendering*.

**Geo-restriction:** Editing uploaded videos is not available in the
European Economic Area (EEA), Switzerland, and the United Kingdom.
T2V / I2V generation is unrestricted.

**Voice editing is not supported.** You can ask the model to change
visual elements (objects, lighting, camera, color, characters'
appearance) but not to alter the audio track.

## Prompt rules (the inverse rule)

Where the rest of the fal-ai ecosystem rewards verbose positional
prompts, the edit endpoint rewards *short imperative instructions*.
The official prompt guide is explicit: "Simple prompts work best."

| Style | Example |
|-------|---------|
| ✅ Good | "Replace the pomegranates with apples." |
| ✅ Good | "Change the camera angle to a close-up on his hands. Keep everything else the same." |
| ❌ Bad | "Slowly, in the foreground, on the wooden table, replace the three round red pomegranates with five round green apples, preserving the lighting and composition" |
| ❌ Bad | "Make it more cinematic, with golden hour lighting and a 50mm lens feel" |

**Always append "Keep everything else the same."** unless the
instruction is intended to redo the whole video. Without that
phrase, Omni may rewrite aspects of the scene that the user wanted
to keep.

## Workflow

### 1. Start with a generated video

Generate the base video using any T2V / I2V / R2V endpoint
(Seedance, Kling v3, Omni T2V/I2V, etc.). Save the result URL.

### 2. Iterate one amend at a time

For each turn, run `google/gemini-omni-flash/edit` with the previous
turn's output URL plus a new amend instruction.

```bash
# Turn 1: change shirt color
genmedia run google/gemini-omni-flash/edit \
  --prompt "Change her shirt to red. Keep everything else the same." \
  --video_url "$BASE_VIDEO_URL" \
  --json

# Capture the new video URL from the response
TURN1_VIDEO_URL=$(... | jq -r '.video.url')

# Turn 2: refine the camera on the result of Turn 1
genmedia run google/gemini-omni-flash/edit \
  --prompt "Reframe as a close-up on her face. Keep everything else the same." \
  --video_url "$TURN1_VIDEO_URL" \
  --json
```

### 3. Track conversation history

Each turn's output is the input to the next. The recipe assumes a
human is in the loop and writes the next instruction. For automated
pipelines, store the conversation in a JSON file:

```json
{
  "turns": [
    { "instruction": "Change her shirt to red.", "video_url": "https://..." },
    { "instruction": "Reframe as a close-up.", "video_url": "https://..." }
  ]
}
```

### 4. Cost

Pricing is per-second, ~$0.13/s. Each turn re-renders the full video
(no incremental cost vs full generation). Budget the full
target-duration cost per turn.

## Iteration patterns

### Object swap

```text
Replace the [old object] with [new object]. Keep everything else the same.
```

Examples:
- "Replace the pomegranates with apples."
- "Replace the wooden chair with a red velvet armchair."
- "Replace the yellow umbrella with a clear one."

### Color and material

```text
Change the [element]'s [color/material] to [new value]. Keep everything else the same.
```

Examples:
- "Change her dress to deep blue velvet."
- "Change the walls to a warm terracotta."
- "Change the tablecloth to white linen."

### Camera

```text
Change the camera to [movement]. Keep everything else the same.
```

Examples:
- "Reframe as a close-up on his hands."
- "Pull the camera back to a wide shot."
- "Change to a low angle, looking up."
- "Dolly in slowly toward the subject."

### Action

```text
Change the [subject] to [new action]. Keep everything else the same.
```

Examples:
- "Make her smile wider."
- "Have him turn his head to look over his shoulder."
- "Change her pose to a dance move."

### Environment

```text
Change the [environment element] to [new state]. Keep everything else the same.
```

Examples:
- "Make it rain."
- "Change the time of day to sunset."
- "Add snow on the ground."

## Don't

- **Don't combine multiple changes in one instruction.** Split them across
  turns. "Replace the pomegranates with apples, change the shirt to blue,
  and reframe as a close-up" is three separate turns.
- **Don't ask for changes the endpoint cannot do.** Voice editing is
  explicitly not supported. Asking "change the music to jazz" will be
  ignored or produce a non-deterministic result.
- **Don't skip "Keep everything else the same."** Without it, Omni
  rewrites parts of the scene that you wanted to keep.
- **Don't iterate more than ~5-10 turns.** Each turn re-renders; identity
  drift accumulates. If you need a major rework, regenerate from scratch.
- **Don't expect seed-stable results.** There is no `seed` parameter.
  The same instruction on the same input will produce a different video
  each call.

## Cross-references

- Endpoint family details: [fal-prompting/references/gemini-omni.md](../../fal-prompting/references/gemini-omni.md)
- Catalog entry: [fal-models-catalog/references/video-to-video.md](../../fal-models-catalog/references/video-to-video.md)
- Model routing: [model-routing/SKILL.md](../../model-routing/SKILL.md) (search for "Conversational iterative edit")
- Workflow JSON examples: [fal-workflow/references/MODELS.md](../../fal-workflow/references/MODELS.md) (search for "Gemini Omni Flash (Edit)")
