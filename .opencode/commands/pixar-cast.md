---
description: Manage the character cast for a multi-character Pixar story
agent: pixar-orchestrator
subtask: true
---
You need to manage the character cast registry for a Pixar story. The cast system uses symlinks — characters are stored in their original story directories and linked into the target story's `characters/` folder. This keeps images reusable across stories.

## User Input
$ARGUMENTS

## Subcommands

### `init <story_slug>`
Initialize a new cast for a story:
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <story_slug>)
bash scripts/cast.sh init "$STORY_DIR"
```
This creates `cast.json` and `characters/` directory. If the story already has a `character/` directory, it migrates those files into the cast system.

### `add <char_id> --from <source_story> --story <story_slug> [--role <role>]`
Add a character from an existing story to the cast via symlink:
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <story_slug>)
SOURCE_DIR=$(bash scripts/resolve_scene.sh <source_story>)
bash scripts/cast.sh add "$STORY_DIR" <char_id> "$SOURCE_DIR"
```
The character's `.png` and `.md` files are symlinked (reusable). If `--role` is specified, update it in cast.json:
```bash
python3 -c "
import json
with open('$STORY_DIR/cast.json') as f: cast = json.load(f)
for c in cast['cast']:
    if c['id'] == '<char_id>': c['role'] = '<role>'
with open('$STORY_DIR/cast.json', 'w') as f: json.dump(cast, f, indent=2)
"
```

### `remove <char_id> --story <story_slug>`
Remove a character from the cast (removes symlinks, updates cast.json):
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <story_slug>)
bash scripts/cast.sh remove "$STORY_DIR" <char_id>
```

### `list <story_slug>`
Show the current cast for a story:
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <story_slug>)
bash scripts/cast.sh list "$STORY_DIR"
```

### `urls <story_slug>`
Get CDN URLs for all cast members (uploads if needed, caches results):
```bash
STORY_DIR=$(bash scripts/resolve_scene.sh <story_slug>)
bash scripts/cast.sh urls "$STORY_DIR" --json
```

## Post-Action
Report the current state of the cast (who's in it, roles, source stories).
