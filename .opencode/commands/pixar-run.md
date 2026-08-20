---
description: Run the full Pixar pipeline from story to final video automatically
agent: pixar-orchestrator
subtask: true
---
You need to run the complete Pixar pipeline automatically for a story. This chains all phases without manual intervention.

## User Input
$ARGUMENTS

## How to interpret the arguments

- `--story <slug>` — story to run (REQUIRED)
- `--auto` — fully automated, no review pauses
- `--review` — pause at each review checkpoint (character, background, scenes)
- Everything else → story premise (only if story needs to be written)

## Prerequisites
The story must have:
- Characters in the cast (`cast.json` with at least 1 character)
- Backgrounds generated (optional — scenes will use textual descriptions if none)
- A `scenes/` directory with `scene.md` files (or the premise will be used to write them)

## Pipeline Phases (in order)

### Phase 1: Story (skip if scenes exist)
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
if [ ! -d "$STORY_DIR/scenes" ] || [ -z "$(ls -A "$STORY_DIR/scenes" 2>/dev/null)" ]; then
  # Invoke pixar-story-writer subagent to write scenes
  # Auto-detects cast.json and backgrounds/ directory
fi
```

### Phase 2: Scene Images (with optional review)
```bash
# Detect if multi-character
CHAR_COUNT=$(python3 -c "import json; c=json.load(open('$STORY_DIR/cast.json')); print(len(c['cast']))" 2>/dev/null || echo "1")

# Generate images
if [ "$REVIEW_MODE" = "true" ]; then
  /pixar-generate --review --story <slug>
  # Wait for user to run /pixar-review, then continue
else
  /pixar-generate --skip-review --story <slug>
fi
```

### Phase 3: Videos
```bash
/pixar-generate --videos-only --story <slug>
```

### Phase 4: Audio Narration
```bash
/pixar-audio --story <slug>
```

### Phase 5: Music + Final Mix
```bash
/pixar-music --story <slug>
```

### Phase 6: Cost Summary
```bash
bash scripts/fal_cost_summary.sh "$STORY_DIR"
```

## Review Mode (`--review`)
If `--review` is set, pause after scene images generation:
1. Run `/pixar-generate --review --story <slug>` (generates images only)
2. Tell user: "Review with `/pixar-review <slug>`. After approval, run `/pixar-run --resume <slug>`"

## Resume Mode (`--resume`)
Continue from the last completed phase. Check `story_state.json` → `phase` to determine where to resume.

## Automatic Mode (`--auto`)
Run all phases sequentially without pausing. Report progress at each phase. Show final video path and cost summary.

## Post-Action
Report: total phases completed, final video path, storybook PDF path, total cost.
