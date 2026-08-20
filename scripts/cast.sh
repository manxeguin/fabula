#!/usr/bin/env bash
# Character cast registry for multi-character stories.
#
# Usage:
#   cast.sh init <story_dir> [--preset <name>]
#   cast.sh add <story_dir> <char_id> <source_story_dir>
#   cast.sh list <story_dir> [--json]
#   cast.sh urls <story_dir> [--json]
#   cast.sh update-urls <story_dir>
#
# cast.json format:
# {
#   "preset": "testing",
#   "cast": [
#     { "id": "claudia", "role": "protagonist", "source": "testing_claudia-kikis",
#       "char_dir": "characters/claudia", "age": "toddler 2-3yr", "height_ratio": "1:4" }
#   ]
# }

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMAND="${1:-}"
STORY_DIR="${2:-}"

die() { echo "ERROR: $*" >&2; exit 1; }

ensure_dirs() {
  mkdir -p "$STORY_DIR/characters"
}

init_cast() {
  ensure_dirs
  local preset="${3:-testing}"

  # Check if cast.json already exists
  if [ -f "$STORY_DIR/cast.json" ]; then
    echo "cast.json already exists at $STORY_DIR/cast.json"
    return 0
  fi

  # Check for existing character/
  if [ -f "$STORY_DIR/character/character.md" ]; then
    local name=$(grep -m1 '^# Character:' "$STORY_DIR/character/character.md" | sed 's/^# Character: //' || echo "main")
    mkdir -p "$STORY_DIR/characters/$name"
    # Move (not symlink) since it's in the same story
    mv "$STORY_DIR/character/character.md" "$STORY_DIR/characters/$name/" 2>/dev/null || true
    mv "$STORY_DIR/character/character.png" "$STORY_DIR/characters/$name/" 2>/dev/null || true
    mv "$STORY_DIR/character/character_url.txt" "$STORY_DIR/characters/$name/" 2>/dev/null || true
    rmdir "$STORY_DIR/character" 2>/dev/null || true

    python3 -c "
import json
cast = {
  'preset': '$preset',
  'cast': [{
    'id': '$name',
    'role': 'protagonist',
    'source': 'local',
    'char_dir': 'characters/$name',
    'age': 'unknown',
    'height_ratio': '1:4'
  }]
}
with open('$STORY_DIR/cast.json', 'w') as f:
    json.dump(cast, f, indent=2)
"
    echo "Initialized cast.json with existing character: $name"
  else
    python3 -c "
import json
cast = {'preset': '$preset', 'cast': []}
with open('$STORY_DIR/cast.json', 'w') as f:
    json.dump(cast, f, indent=2)
"
    echo "Initialized empty cast.json"
  fi
}

add_character() {
  local char_id="$3"
  local source_dir="$4"

  ensure_dirs

  if [ ! -f "$STORY_DIR/cast.json" ]; then
    die "No cast.json found. Run 'cast.sh init' first."
  fi

  if [ ! -f "$source_dir/character/character.png" ]; then
    die "Source character not found: $source_dir/character/character.png"
  fi

  # Symlink character files (reusable across stories, saves disk space)
  mkdir -p "$STORY_DIR/characters/$char_id"
  ln -sf "$(cd "$source_dir" && pwd)/character/character.png" "$STORY_DIR/characters/$char_id/character.png" 2>/dev/null || true
  ln -sf "$(cd "$source_dir" && pwd)/character/character.md" "$STORY_DIR/characters/$char_id/character.md" 2>/dev/null || true
  # Copy just the URL file (CDN URLs can be story-specific)
  cp "$source_dir/character/character_url.txt" "$STORY_DIR/characters/$char_id/" 2>/dev/null || true

  # Extract age and ratio from character.md
  local age="unknown"
  local ratio="1:4"
  if [ -f "$STORY_DIR/characters/$char_id/character.md" ]; then
    age=$(grep -m1 'Age range' "$STORY_DIR/characters/$char_id/character.md" | sed 's/.*Age range: //' | head -1 || echo "unknown")
    ratio=$(grep -m1 'head.*:' "$STORY_DIR/characters/$char_id/character.md" | grep -o '[0-9]:[0-9]' | head -1 || echo "1:4")
  fi

  # Add to cast.json
  local source_name=$(basename "$source_dir")
  python3 -c "
import json
with open('$STORY_DIR/cast.json') as f:
    cast = json.load(f)
cast['cast'].append({
    'id': '$char_id',
    'role': 'supporting',
    'source': '$source_name',
    'char_dir': 'characters/$char_id',
    'age': '$age',
    'height_ratio': '$ratio'
})
with open('$STORY_DIR/cast.json', 'w') as f:
    json.dump(cast, f, indent=2)
"
  echo "Added $char_id from $source_name to cast"
}

remove_character() {
  local char_id="$3"

  if [ ! -f "$STORY_DIR/cast.json" ]; then
    die "No cast.json found in $STORY_DIR"
  fi

  # Remove symlinks
  rm -f "$STORY_DIR/characters/$char_id/character.png" 2>/dev/null || true
  rm -f "$STORY_DIR/characters/$char_id/character.md" 2>/dev/null || true
  rm -f "$STORY_DIR/characters/$char_id/character_url.txt" 2>/dev/null || true
  rmdir "$STORY_DIR/characters/$char_id" 2>/dev/null || true

  # Remove from cast.json
  python3 -c "
import json
with open('$STORY_DIR/cast.json') as f:
    cast = json.load(f)
cast['cast'] = [c for c in cast['cast'] if c['id'] != '$char_id']
with open('$STORY_DIR/cast.json', 'w') as f:
    json.dump(cast, f, indent=2)
"
  echo "Removed $char_id from cast"
}

list_cast() {
  if [ ! -f "$STORY_DIR/cast.json" ]; then
    die "No cast.json found in $STORY_DIR"
  fi

  if [ "${3:-}" = "--json" ]; then
    cat "$STORY_DIR/cast.json"
  else
    python3 -c "
import json
with open('$STORY_DIR/cast.json') as f:
    cast = json.load(f)
print(f\"Cast ({len(cast['cast'])} characters):\")
for c in cast['cast']:
    print(f\"  {c['id']:15s} | {c.get('role','?'):15s} | {c.get('age','?'):15s} | {c.get('height_ratio','?'):5s}\")
"
  fi
}

get_urls() {
  if [ ! -f "$STORY_DIR/cast.json" ]; then
    die "No cast.json found in $STORY_DIR"
  fi

  # Upload all character images and collect URLs
  local urls=""
  python3 -c "
import json, os, subprocess

with open('$STORY_DIR/cast.json') as f:
    cast = json.load(f)

urls = []
for c in cast['cast']:
    char_dir = os.path.join('$STORY_DIR', c['char_dir'])
    url_file = os.path.join(char_dir, 'character_url.txt')
    img_file = os.path.join(char_dir, 'character.png')

    # Try URL file first
    if os.path.exists(url_file):
        with open(url_file) as uf:
            url = uf.read().strip()
            if url:
                urls.append({'id': c['id'], 'url': url, 'source': 'cached'})
                continue

    # Try uploading
    if os.path.exists(img_file):
        result = subprocess.run(
            ['python3', '$SCRIPT_DIR/fal_upload.py', img_file],
            capture_output=True, text=True
        )
        url = result.stdout.strip()
        if url and url.startswith('http'):
            urls.append({'id': c['id'], 'url': url, 'source': 'fresh'})
            # Cache it
            with open(url_file, 'w') as uf:
                uf.write(url + '\n')

if '${3:-}' == '--json':
    print(json.dumps(urls, indent=2))
else:
    for u in urls:
        print(f\"{u['id']}: {u['url']} ({u['source']})\")
"
}

update_urls() {
  if [ ! -f "$STORY_DIR/cast.json" ]; then
    die "No cast.json found in $STORY_DIR"
  fi

  python3 -c "
import json, os, subprocess

with open('$STORY_DIR/cast.json') as f:
    cast = json.load(f)

for c in cast['cast']:
    char_dir = os.path.join('$STORY_DIR', c['char_dir'])
    img_file = os.path.join(char_dir, 'character.png')
    url_file = os.path.join(char_dir, 'character_url.txt')

    if os.path.exists(img_file):
        result = subprocess.run(
            ['python3', '$SCRIPT_DIR/fal_upload.py', img_file],
            capture_output=True, text=True
        )
        url = result.stdout.strip()
        if url and url.startswith('http'):
            with open(url_file, 'w') as uf:
                uf.write(url + '\n')
            print(f'{c[\"id\"]}: refreshed -> {url}')
        else:
            print(f'{c[\"id\"]}: upload failed')
    else:
        print(f'{c[\"id\"]}: no character.png found')
"
}

case "$COMMAND" in
  init)      init_cast "$@" ;;
  add)       add_character "$@" ;;
  remove)    remove_character "$@" ;;
  list)      list_cast "$@" ;;
  urls)      get_urls "$@" ;;
  update-urls) update_urls "$@" ;;
  *)
    echo "Usage: cast.sh {init|add|remove|list|urls|update-urls} <story_dir> [args...]"
    exit 1
    ;;
esac
