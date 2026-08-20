#!/usr/bin/env bash
# Read generation_log.jsonl and print a per-asset report with aggregate stats.
#
# Usage:
#   bash scripts/generation_report.sh <story_dir> [--json] [--aggregate]

set -euo pipefail

STORY_DIR="${1:-}"
MODE="${2:---table}"

if [ -z "$STORY_DIR" ] || [ ! -d "$STORY_DIR" ]; then
  echo "Usage: generation_report.sh <story_dir> [--json] [--aggregate]" >&2
  exit 1
fi

LOG_FILE="$STORY_DIR/generation_log.jsonl"
if [ ! -f "$LOG_FILE" ]; then
  echo "No generation log found at $LOG_FILE"
  exit 0
fi

if [ "$MODE" = "--json" ]; then
  python3 -c "
import json
with open('$LOG_FILE') as f:
    entries = [json.loads(line) for line in f if line.strip()]
print(json.dumps(entries, indent=2, ensure_ascii=False))
"
  exit 0
fi

if [ "$MODE" = "--aggregate" ]; then
  python3 -c "
import json
from collections import Counter

entries = []
with open('$LOG_FILE') as f:
    for line in f:
        if line.strip():
            entries.append(json.loads(line))

if not entries:
    print('No entries.')
    exit()

# Counts by asset type
type_counts = Counter(e['asset'] for e in entries)
model_counts = Counter(e['model'] for e in entries)

# Costs
total_cost = sum(e['cost']['price'] for e in entries if e['cost'].get('price'))
cost_by_type = {}
for e in entries:
    t = e['asset']
    cost_by_type[t] = cost_by_type.get(t, 0) + e['cost'].get('price', 0)

# Resolution stats
resolutions = Counter()
sizes_bytes = []
for e in entries:
    o = e.get('output', {})
    w = o.get('width'); h = o.get('height')
    if w and h:
        resolutions[f'{w}x{h}'] += 1
    s = o.get('size')
    if s:
        sizes_bytes.append(s)

# Duration stats
gen_times = [e['duration_ms'] for e in entries if e.get('duration_ms', 0) > 0]
retry_count = sum(e.get('retries', 0) for e in entries)

print()
print(f'  Generation Report — {entries[0][\"preset\"]} preset')
print(f'  Story: {entries[0][\"path\"].split(\"/\")[0] if \"/\" in entries[0][\"path\"] else \"?\" }')
print(f'  ' + '-' * 55)
print(f'  Total generations: {len(entries)}')
print(f'  Total cost:        \${total_cost:.4f}')
print(f'  Total retries:     {retry_count}')
print()
print('  By asset type:')
for t in ['character_image', 'background_image', 'scene_image', 'scene_video', 'narration_audio', 'music_audio']:
    c = type_counts.get(t, 0)
    if c > 0:
        print(f'    {t:20s} {c:3d}  \${cost_by_type.get(t, 0):.4f}')
print()
print('  By model:')
for m, c in model_counts.most_common():
    print(f'    {m:45s} {c:3d}')
print()
if resolutions:
    print('  Resolutions:')
    for r, c in resolutions.most_common():
        print(f'    {r:20s} {c:3d}')
print()
if sizes_bytes:
    avg_size = sum(sizes_bytes) / len(sizes_bytes)
    print(f'  Average file size: {avg_size/1024/1024:.1f} MB')
print()
if gen_times:
    avg_time = sum(gen_times) / len(gen_times)
    print(f'  Average gen time:  {avg_time/1000:.1f}s (min: {min(gen_times)/1000:.1f}s, max: {max(gen_times)/1000:.1f}s)')
"
  exit 0
fi

# Default: table mode
python3 -c "
import json

with open('$LOG_FILE') as f:
    entries = [json.loads(line) for line in f if line.strip()]

if not entries:
    print('No entries.')
    exit()

print()
print(f'  Generation Log — {len(entries)} entries')
print(f'  ' + '-' * 95)
print(f'  {\"Asset\":<20s} {\"Model\":<35s} {\"Size\":>8s} {\"Res\":>10s} {\"Cost\":>7s} {\"Time\":>7s}')
print(f'  ' + '-' * 95)

total_cost = 0
for e in entries:
    path = e['path'].rsplit('/', 1)[-1] if '/' in e['path'] else e['path']
    model = e['model'].split('/')[-1] if '/' in e['model'] else e['model']
    o = e['output']
    size = o.get('size', 0)
    w = o.get('width', 0); h = o.get('height', 0)
    dur = o.get('duration', 0)
    cost = e['cost'].get('price', 0)
    ms = e.get('duration_ms', 0)
    
    size_str = f'{size/1024/1024:.1f}MB' if size else '-'
    res_str = f'{w}x{h}' if w and h else (f'{dur:.0f}s' if dur else '-')
    cost_str = f'\${cost:.3f}' if cost else '-'
    time_str = f'{ms/1000:.0f}s' if ms else '-'
    total_cost += cost
    
    print(f'  {e[\"asset\"]:<20s} {model:<35s} {size_str:>8s} {res_str:>10s} {cost_str:>7s} {time_str:>7s}')

print(f'  ' + '-' * 95)
print(f'  Total: \${total_cost:.4f}')
"
