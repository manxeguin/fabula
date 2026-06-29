---
description: Generate Spanish narration audio matching scene durations — 3 female voice variants
agent: pixar-orchestrator
subtask: true
---
Generate a Spanish narration audio track for a Pixar story, with duration matched per-scene to the video.

## User Input
$ARGUMENTS

## Parse arguments
- `--story <slug>` → which story (REQUIRED)
- `--voice <name>` → voice variant: ara, eve, sal, or "all" (default: all = generates 3 variants)
- `--lang <code>` → language code (default: es-ES)

## Available Voices (all female/feminine)
| Voice | Character | Best for |
|---|---|---|
| `ara` | Warm, friendly | Emotional stories, gentle narration |
| `eve` | Energetic, upbeat | Exciting adventures, playful tales |
| `sal` | Smooth, balanced | Neutral narration, calm stories |

## Workflow

### 1. Resolve story
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
```

### 2. Source API key
```bash
export FAL_API_KEY=$(grep -o 'FAL_API_KEY=[^[:space:]]*' ~/.zshrc | head -1 | cut -d= -f2)
```

### 3. Determine voices to generate
If `--voice all` or no `--voice` specified: generate ara, eve, sal (3 variants).
If `--voice ara`: generate only ara.

### 4. For each scene, for each voice:
```bash
# Get video duration
VIDEO_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$scene_dir/scene.mp4")

# Write a SHORT Spanish narration (60-80 chars target, ~3-4s speech).
# Use [pause] and [sigh] tags for emotional pacing.
# Keep it brief — pad_audio.sh will add 0.3s silence before and 0.5s after.
SPANISH_TEXT="Carmencita se mira al espejo con su vestido rojo de lunares. Su madre le coloca una flor. Hoy va a la Feria."

# Generate audio via xAI TTS
bash scripts/fal_narrate.sh "$SPANISH_TEXT" "$scene_dir/speech_$voice.mp3" --voice $voice --lang es-ES

# Pad with breathing room: 0.3s silence before, 0.5s silence after
bash scripts/pad_audio.sh "$scene_dir/speech_$voice.mp3" "$scene_dir/scene_narration_$voice.mp3" "$VIDEO_DUR" 0.3 0.5

# Clean up intermediate speech file (intermediate, not needed after padding)
rm -f "$scene_dir/speech_$voice.mp3"
```

**Narration length rule**: target 40-60 characters per scene. Spanish TTS speaks ~15 chars/second, so 50 chars ≈ 3.3s speech. With 0.3s + 0.5s padding = 4.1s total, fitting easily in 5s. Keep narrations extremely concise — one sentence per emotional beat.

```
|0.3s silence|── speech (~3-4s at 1.0x) ──|0.5s silence| = 5.0s
```

### 5. Concatenate all matched scene narrations into full track
```bash
# Re-encode concat for precise duration (NOT -c copy — MP3 copy causes timestamp drift)
for voice in ara eve sal; do
  INPUTS=""
  FILTER=""
  i=0
  for scene_dir in $(ls -d "$STORY_DIR/scenes"/*/ | sort); do
    INPUTS="$INPUTS -i $scene_dir/scene_narration_$voice.mp3"
    FILTER="${FILTER}[${i}:a]"
    i=$((i+1))
  done
  FILTER="${FILTER}concat=n=$i:v=0:a=1"
  
  ffmpeg -y $INPUTS -filter_complex "$FILTER" -ac 1 -ar 24000 "$STORY_DIR/narration_$voice.mp3" -loglevel error
  DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$STORY_DIR/narration_$voice.mp3")
  echo "  narration_$voice.mp3: ${DUR}s"
done
```

**Important**: Use `-filter_complex concat` with re-encoding, NOT `-c copy`. MP3 stream copy corrupts timestamps from padded files, causing duration drift and the last scene to detach.

### 6. Report
- How many scenes narrated
- Duration of each full track (should match final.mp4)
- File sizes
- Suggest running `/pixar-mix --story <slug> --voice ara` to mix with video

## Tone Matching Guidelines
Write SHORT narrations (40-60 chars). One sentence, clear emotion. 15 chars/sec in Spanish.

| Mood | TTS Tags | Example (Spanish, ~45 chars) |
|---|---|---|
| Wonder, excitement | Flowing | "Carmencita se mira al espejo con su vestido de lunares. Hoy va a la Feria." |
| Awe, overwhelm | `[pause]` | "La Feria es enorme. [pause] Carmencita se agarra a su madre." |
| Fear → courage | `[sigh]`, firm ending | "Se ha soltado. [sigh] Pero escucha sus pulseras. Respira." |
| Joy, connection | Upbeat | "Su madre le enseña el ritmo. ¡Carmencita levanta los brazos!" |
| Triumph, belonging | `[laugh]` | "Carmencita gira bajo los farolillos. [laugh] Esta es su Feria." |

## Breathing Room Layout
```
Target (5.0s)
|← 0.3s silence →|← speech 3-4s →|← 0.5s silence →|
                 ↑ narration      scene transition →
```
