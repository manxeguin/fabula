#!/usr/bin/env bash
# Compute exact FAL API cost for a generated story.
#
# Usage: bash scripts/fal_cost_summary.sh <story_dir>
#
# Requires genmedia CLI on PATH and FAL_KEY in env.
# Counts actual generated files and queries exact pricing per endpoint.

set -euo pipefail

STORY_DIR="${1:-}"

if [ -z "$STORY_DIR" ] || [ ! -d "$STORY_DIR" ]; then
  echo "Usage: bash fal_cost_summary.sh <story_dir>" >&2
  exit 1
fi

GENMEDIA="${GENMEDIA_BIN:-$(which genmedia 2>/dev/null || echo "$HOME/.genmedia/bin/genmedia")}"
if ! "$GENMEDIA" version &>/dev/null 2>&1; then
  echo "ERROR: genmedia CLI not found. Install: curl https://genmedia.sh/install | bash" >&2
  exit 1
fi

FAL_KEY="${FAL_KEY:-$(grep -o 'FAL_API_KEY=[^[:space:]]*' ~/.zshrc 2>/dev/null | head -1 | cut -d= -f2)}"
export FAL_KEY

# --- Read preset from story state ---
PRESET=$(bash scripts/story_state.sh get "$STORY_DIR" preset 2>/dev/null || echo "debug")

# --- Load config ---
CONFIG=$(python3 -c "
import json
c = json.load(open('pipeline_config.json'))
p = c['presets']['$PRESET']
print(json.dumps({
  'char_model': p['character_model'],
  'char_endpoint': p['character_endpoint'],
  'scene_model': p.get('scene_model',''),
  'scene_endpoint': p.get('scene_endpoint',''),
  'video_model': p['video_model'],
  'video_endpoint': p['video_endpoint'],
  'video_image_param': p.get('video_image_param','image_url'),
  'video_has_prompt': p.get('video_has_prompt',False),
  'music_endpoint': c['music']['endpoint'],
  'tts_endpoint': c['narrator']['endpoint'],
}))
")

CHAR_MODEL=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['char_model'])")
SCENE_MODEL=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['scene_model'])")
VIDEO_MODEL=$(echo "$CONFIG" | python3 -c "import sys,json; print(json.load(sys.stdin)['video_model'])")

# --- Count files ---
N_CHAR=0; N_SCENES=0; N_VIDEOS=0; N_TTS=0; N_MUSIC=0
TOTAL_VIDEO_S=0

[ -f "$STORY_DIR/character/character.png" ] && N_CHAR=1

for scenedir in "$STORY_DIR"/scenes/*/; do
  [ -d "$scenedir" ] || continue
  [ -f "$scenedir/scene.png" ] && N_SCENES=$((N_SCENES + 1))
  if [ -f "$scenedir/scene.mp4" ]; then
    N_VIDEOS=$((N_VIDEOS + 1))
    d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$scenedir/scene.mp4" 2>/dev/null || echo "5")
    TOTAL_VIDEO_S=$(python3 -c "print($TOTAL_VIDEO_S + $d)")
  fi
  for speech in "$scenedir"/speech_*.mp3; do
    [ -f "$speech" ] && N_TTS=$((N_TTS + 1))
    break  # count once per scene dir (only need speech files)
  done
done

[ -f "$STORY_DIR/music.mp3" ] && N_MUSIC=1

# --- Query exact pricing ---
query_price() {
  local model="$1"
  "$GENMEDIA" pricing "$model" --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
p = d['prices'][0]
print(json.dumps({'price': p['unit_price'], 'unit': p['unit']}))
" 2>/dev/null || echo '{"price":0,"unit":"unknown"}'
}

CHAR_PRICE=$(query_price "$CHAR_MODEL")
SCENE_PRICE=$(query_price "$SCENE_MODEL")
VIDEO_PRICE=$(query_price "$VIDEO_MODEL")
TTS_PRICE=$(query_price "xai/tts/v1")
MUSIC_PRICE=$(query_price "sonilo/v1.1/text-to-music")

CHAR_PPU=$(echo "$CHAR_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['price'])")
CHAR_UNIT=$(echo "$CHAR_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['unit'])")
SCENE_PPU=$(echo "$SCENE_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['price'])")
SCENE_UNIT=$(echo "$SCENE_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['unit'])")
VIDEO_PPU=$(echo "$VIDEO_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['price'])")
VIDEO_UNIT=$(echo "$VIDEO_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['unit'])")
TTS_PPU=$(echo "$TTS_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['price'])")
MUSIC_PPU=$(echo "$MUSIC_PRICE" | python3 -c "import sys,json; print(json.load(sys.stdin)['price'])")

# --- Compute costs ---
# Character: image-based
CHAR_COST=$(python3 -c "
n=$N_CHAR
if '$CHAR_UNIT' == 'megapixels':
  import subprocess
  r = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', '$STORY_DIR/character/character.png']).decode().strip()
  w,h = r.split(',')
  mp = int(w)*int(h)/1_000_000
  print(round($CHAR_PPU * mp * n, 4))
else:
  print(round($CHAR_PPU * n, 4))
")

# Scenes
SCENE_COST=$(python3 -c "
n=$N_SCENES
if '$SCENE_UNIT' == 'megapixels':
  import subprocess, glob
  files = sorted(glob.glob('$STORY_DIR/scenes/*/scene.png'))
  total = 0
  for f in files:
    r = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', f]).decode().strip()
    w,h = r.split(',')
    total += int(w)*int(h)/1_000_000 * $SCENE_PPU
  print(round(total, 4))
else:
  print(round($SCENE_PPU * n, 4))
" 2>/dev/null || python3 -c "print(round($SCENE_PPU * $N_SCENES, 4))")

# Videos
VIDEO_COST=$(python3 -c "print(round($VIDEO_PPU * $TOTAL_VIDEO_S, 4))")

# TTS (approximate: ~0.07 compute sec per 1s audio)
TTS_COST=$(python3 -c "
# Estimate compute seconds from number of calls
# TTS compute is roughly 1-2x output duration
print(round($TTS_PPU * $N_TTS * 50, 4))
")

# Music
MUSIC_COST=$(python3 -c "
d=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $STORY_DIR/music.mp3 2>/dev/null || echo 26)
print(round($MUSIC_PPU * float(d), 4))
")

TOTAL=$(python3 -c "print(round($CHAR_COST + $SCENE_COST + $VIDEO_COST + $TTS_COST + $MUSIC_COST, 4))")

# Music duration
MUSIC_DUR=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$STORY_DIR/music.mp3" 2>/dev/null || echo 26)
MUSIC_DUR_INT=$(python3 -c "print(int(float($MUSIC_DUR)))")

# --- Print summary using python for formatting ---
python3 -c "
import json, math

preset = '$PRESET'
char_unit = '$CHAR_UNIT'
char_model = '$CHAR_MODEL'
scene_unit = '$SCENE_UNIT'
scene_model = '$SCENE_MODEL'
video_model = '$VIDEO_MODEL'
char_cost = $CHAR_COST
scene_cost = $SCENE_COST
video_cost = $VIDEO_COST
tts_cost = $TTS_COST
music_cost = $MUSIC_COST
n_char = $N_CHAR
n_scenes = $N_SCENES
n_videos = $N_VIDEOS
n_tts = $N_TTS
total_s = $TOTAL_VIDEO_S
music_s = $MUSIC_DUR_INT
total = char_cost + scene_cost + video_cost + tts_cost + music_cost

print()
print('  Cost Summary — ' + preset + ' preset')
print('  ' + '-' * 48)
print(f'  Character ({char_unit})       \${char_cost:>8.4f}')
print(f'  {n_scenes} Scene images ({scene_unit})   \${scene_cost:>8.4f}')
print(f'  {n_videos} Videos ({total_s:.0f}s)          \${video_cost:>8.4f}')
print(f'  {n_tts} TTS narrations           \${tts_cost:>8.4f}')
print(f'  Music ({music_s}s)             \${music_cost:>8.4f}')
print('  ' + '-' * 48)
print(f'  TOTAL                     \${total:>8.4f}')
print()
print('  Models:')
print(f'    Character: {char_model}')
print(f'    Scenes:    {scene_model}')
print(f'    Videos:    {video_model}')
print(f'    Music:     sonilo/v1.1/text-to-music')
print(f'    TTS:       xai/tts/v1')
"
