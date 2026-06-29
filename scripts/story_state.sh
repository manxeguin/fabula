#!/usr/bin/env bash
# Read/create/update story state files.
#
# Usage:
#   bash scripts/story_state.sh init <story_dir> <preset>     # create state file
#   bash scripts/story_state.sh get <story_dir> <field>       # read a field
#   bash scripts/story_state.sh set <story_dir> <field> <val> # set a field
#   bash scripts/story_state.sh status <story_dir>            # print full status
#   bash scripts/story_state.sh scene <story_dir> <scene> <field> <val>  # set scene field
#
# Fields: preset, phase (character|story|images|videos|merged|done),
#         character_done (true/false), story_done (true/false)
# Scene fields: img, vid, img_size, vid_size

set -euo pipefail

CMD="${1:-}"
STORY_DIR="${2:-}"

[ -z "$CMD" ] && { echo "Usage: story_state.sh <cmd> ..." >&2; exit 1; }

STATE_FILE="$STORY_DIR/story_state.json"

_init() {
  local preset="${3:-testing}"
  mkdir -p "$STORY_DIR"
  cat > "$STATE_FILE" << EOF
{
  "preset": "$preset",
  "phase": "character",
  "character_done": false,
  "story_done": false,
  "scenes": {}
}
EOF
}

_get() {
  local field="${3:-}"
  [ ! -f "$STATE_FILE" ] && { echo ""; exit 0; }
  if [ -n "$field" ]; then
    python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('$field',''))" 2>/dev/null
  else
    cat "$STATE_FILE"
  fi
}

_set() {
  local field="${3:-}"
  local val="${4:-}"
  [ ! -f "$STATE_FILE" ] && { echo "ERROR: no state file. Run init first." >&2; exit 1; }
  python3 -c "
import json
d=json.load(open('$STATE_FILE'))
# Handle booleans, numbers, and strings
v = '$val'
if v == 'true': v = True
elif v == 'false': v = False
else:
    try: v = int(v)
    except: pass
d['$field'] = v
json.dump(d, open('$STATE_FILE','w'), indent=2)
" 2>/dev/null
}

_scene() {
  local scene_name="${3:-}"
  local field="${4:-}"
  local val="${5:-}"
  [ ! -f "$STATE_FILE" ] && { echo "ERROR: no state file" >&2; exit 1; }
  python3 -c "
import json
d=json.load(open('$STATE_FILE'))
if '$scene_name' not in d['scenes']:
    d['scenes']['$scene_name'] = {}
# Handle booleans, numbers, and strings
v = '$val'
if v == 'true': v = True
elif v == 'false': v = False
else:
    try: v = int(v)
    except: pass
d['scenes']['$scene_name']['$field'] = v
json.dump(d, open('$STATE_FILE','w'), indent=2)
" 2>/dev/null
}

_status() {
  [ ! -f "$STATE_FILE" ] && { echo "No state file yet."; exit 0; }
  python3 -c "
import json, os
d=json.load(open('$STATE_FILE'))
print(f'Preset: {d[\"preset\"]}')
print(f'Phase:  {d[\"phase\"]}')
print(f'Char:   {\"✅\" if d[\"character_done\"] else \"❌\"}')
print(f'Story:  {\"✅\" if d[\"story_done\"] else \"❌\"}')
print()
for sn, ss in sorted(d.get('scenes',{}).items()):
    img = '✅' if ss.get('img') else '❌'
    vid = '✅' if ss.get('vid') else '❌'
    isz = ss.get('img_size','-')
    vsz = ss.get('vid_size','-')
    print(f'  {sn:30s} img:{img} vid:{vid}  {isz:>6s}  {vsz:>6s}')
final = os.path.join('$STORY_DIR','final.mp4')
if os.path.exists(final):
    sz = os.path.getsize(final)
    print(f'\n  final.mp4: {sz/1024/1024:.0f} MB')
" 2>/dev/null
}

case "$CMD" in
  init)   _init "$@" ;;
  get)    _get "$@" ;;
  set)    _set "$@" ;;
  scene)  _scene "$@" ;;
  status) _status "$@" ;;
  *)      echo "Unknown command: $CMD" >&2; exit 1 ;;
esac
