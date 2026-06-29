---
description: List all Pixar stories and their scene status
agent: pixar-orchestrator
---
List all Pixar stories and show their scene generation status.

## Instructions

1. Run this to list every story directory and its scenes:
```bash
for story_dir in stories/*/; do
  slug=$(basename "$story_dir")
  preset=$(cat "$story_dir/story_state.json" 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('preset','?'))" 2>/dev/null || echo "?")
  
  final_sz=""
  [ -f "$story_dir/final.mp4" ] && final_sz="$(ls -lh "$story_dir/final.mp4" | awk '{print $5}')"
  
  echo "  $slug ($preset)"
  [ -n "$final_sz" ] && echo "    final: $final_sz ✅" || echo "    final: ❌"
  
  for scene_dir in $(ls -d "$story_dir/scenes"/*/ 2>/dev/null | sort); do
    name=$(basename "$scene_dir")
    img="❌"; vid="❌"
    [ -f "$scene_dir/scene.png" ] && img="✅"
    [ -f "$scene_dir/scene.mp4" ] && vid="✅"
    isz=$(ls -lh "$scene_dir/scene.png" 2>/dev/null | awk '{print $5}' || echo "-")
    vsz=$(ls -lh "$scene_dir/scene.mp4" 2>/dev/null | awk '{print $5}' || echo "-")
    printf "    %-30s img:%-3s vid:%-3s  %6s  %6s\n" "$name" "$img" "$vid" "$isz" "$vsz"
  done
  echo ""
done
```
