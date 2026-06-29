---
description: Review scene images and prompts before video generation
agent: pixar-orchestrator
subtask: true
---
Review all scene images and their visual/motion prompts before proceeding to video generation. User can approve, reject, or request edits per scene.

## User Input
$ARGUMENTS

## Parse arguments
- `<story-slug>` → which story to review (REQUIRED)

## Workflow

### 1. Resolve story
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <story-slug>)
```

### 2. Count scenes
```bash
SCENE_COUNT=$(ls -d "$STORY_DIR/scenes"/*/scene.md 2>/dev/null | wc -l)
```

### 3. For each scene, present:
```
  Scene N/5: <Title>

  Image: scenes/<dir>/scene.png  (show the image)
  Visual Prompt: <full prompt text>
  Motion Prompt: <full motion prompt text>
  Narration: <Spanish narration text>

  Status: [pending review]
```

### 4. Per-scene actions
- `ok` or `approve` → mark scene as reviewed, move to next
- `reject <scene-ref>` → mark scene for regeneration
- `edit <scene-ref> "<feedback>"` → rewrite scene.md sections based on feedback, then regenerate scene.png
- `all good` or `proceed` → approve all remaining, mark story ready for videos
- Duration/transition via natural language:
  - `make scene 2 8 seconds` → updates `## Duration` to `8s`, validates against preset limits
  - `make the opening longer, 7s` → updates scene 1 duration
  - `connect scene 3 to scene 4` → sets scene 4 Transition to `last_frame_continuity`
  - `all cuts, no continuity` → resets all transitions to `cut`
  - `scene 4 should flow from scene 3` → same as connect

### 5. On edit:
```bash
# Read existing scene.md
# Apply feedback to relevant sections (Visual Direction, Visual Prompt, Motion Prompt, Narration)
# Rewrite scene.md
# Regenerate scene.png (same model as preset)
# Show new image
```

### 6. On approve all:
```bash
bash scripts/story_state.sh set "$STORY_DIR" review_done true
```

### 7. Report
```
All 5 scenes reviewed. Ready for videos.
Run: /pixar-generate --videos-only <story-slug>
```
