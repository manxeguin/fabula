---
description: Regenerate a single scene's image and video
agent: pixar-orchestrator
subtask: true
---
Regenerate a specific scene's media based on user feedback.

## User Input
$ARGUMENTS

## Parse arguments
First argument should be the scene reference (story-slug/scene-ref):
- `sevillana-feria/3` — scene 3
- `sevillana-feria/lost` — partial name match
- `sevillana-feria` — regenerate ALL scenes in the story (implies --all)

Remaining arguments are the feedback text describing what to change.

## Workflow

### 1. Resolve the scene directory
```bash
SCENE_DIR=$(bash scripts/resolve_scene.sh <story-slug>/<scene-ref>)
STORY_DIR=$(dirname $(dirname "$SCENE_DIR"))
```

### 2. If feedback is provided about the story/narrative
Rewrite the scene.md for that scene based on feedback, keeping the format (Narrative, Visual Direction, Visual Prompt, Motion Prompt).

### 3. If feedback is about visuals (lighting, camera, colors, mood)
Update only the Visual Direction and Visual Prompt sections. Keep the Narrative and Motion Prompt unless feedback mentions motion.

### 4. Regenerate scene image
```bash
CHAR_URL=$(cat "$STORY_DIR/character/character_url.txt")
VISUAL=$(python3 -c "import re; text=open('$SCENE_DIR/scene.md').read(); m=re.search(r'## Visual Prompt\n(.*?)(?=\n## )', text, re.DOTALL); print(m.group(1).strip()) if m else exit(1)")

# Use scene endpoint from config
curl -s --max-time 180 "$SCENE_ENDPOINT" \
  -H "Authorization: Key $FAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg prompt "$VISUAL" --arg ref "$CHAR_URL" '{
    prompt: $prompt, image_urls: [$ref],
    num_images: 1, output_format: "png",
    safety_tolerance: "6", limit_generations: true
  }')" | jq -r '.images[0].url' | xargs curl -sLo "$SCENE_DIR/scene.png"
```

### 5. Regenerate scene video
Upload scene.png, call video endpoint from config, download.

### 6. Clean up old status and update
```bash
rm -f "$SCENE_DIR/.status" "$SCENE_DIR/.video_status"
bash scripts/story_state.sh scene "$STORY_DIR" "$(basename $SCENE_DIR)" img true
bash scripts/story_state.sh scene "$STORY_DIR" "$(basename $SCENE_DIR)" vid true
```

### 7. Report
What was changed, new file sizes, suggest running /pixar-merge if all scenes are ready.
