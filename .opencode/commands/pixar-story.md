---
description: Write or rewrite the Pixar story scenes
agent: pixar-orchestrator
subtask: true
---
You need to write or rewrite the scene-by-scene story for a Pixar tale.

## User Input
$ARGUMENTS

## Parse arguments
Look for:
- `--story <slug>` → which story to work on (REQUIRED)
- `--scenes <N>` → force specific scene count (optional, default: 4-6 auto-determined)
- Everything else → the story premise or feedback

## Workflow

1. **Resolve story directory**:
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <slug>)
```

2. **Read character context**:
```bash
cat "$STORY_DIR/character/character.md"
```

3. **Create or update scenes**:
   - If scenes/ is empty or --rewrite flag: invoke pixar-story-writer subagent to write all scenes
   - If scenes exist but user wants changes: rewrite only the scenes mentioned

4. **Write manifest**:
```bash
ls -d "$STORY_DIR/scenes"/*/ | xargs -n1 basename | sort > "$STORY_DIR/scenes/manifest.txt"
```

5. **Update state**:
```bash
bash scripts/story_state.sh set "$STORY_DIR" story_done true
bash scripts/story_state.sh set "$STORY_DIR" phase story
```

6. **Report**: scene count, titles, what's next (run /pixar-generate)
