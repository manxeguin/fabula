#!/usr/bin/env bash
# Resolve a story/scene reference to an absolute scene directory path.
#
# Usage:
#   bash scripts/resolve_scene.sh <story-slug>/<scene-ref>
#   bash scripts/resolve_scene.sh <story-slug>             # returns story dir
#   bash scripts/resolve_scene.sh --list <story-slug>       # list all scene dirs
#   bash scripts/resolve_scene.sh --slug <prompt>           # generate slug from prompt
#
# Scene refs supported:
#   3              → scene number 3, 03, or name starting with "03-"
#   03             → zero-padded number
#   lost           → partial name match (first match)
#   lost-in-the    → longer partial match
#
# Returns: absolute scene directory path (or 1 if not found)

set -euo pipefail

STORIES_BASE="${STORIES_BASE:-stories}"

# --- Slug generation ---
if [ "${1:-}" = "--slug" ]; then
  prompt="${2:-}"
  slug=$(echo "$prompt" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/-\+/-/g' | sed 's/^-//' | sed 's/-$//' | cut -c1-40)
  echo "$slug"
  exit 0
fi

STORY_REF="${1:-}"
if [ -z "$STORY_REF" ]; then
  echo "Usage: bash scripts/resolve_scene.sh <story-slug>/<scene-ref>" >&2
  exit 1
fi

# Split story and scene
if [[ "$STORY_REF" == */* ]]; then
  STORY_SLUG="${STORY_REF%%/*}"
  SCENE_REF="${STORY_REF#*/}"
else
  STORY_SLUG="$STORY_REF"
  SCENE_REF=""
fi

# Find the story directory (check all preset prefixes)
STORY_DIR=""
for d in "$STORIES_BASE"/*_"$STORY_SLUG" "$STORIES_BASE"/"$STORY_SLUG"; do
  if [ -d "$d" ]; then
    STORY_DIR="$d"
    break
  fi
done

if [ -z "$STORY_DIR" ]; then
  # Try glob
  STORY_DIR=$(find "$STORIES_BASE" -maxdepth 1 -type d -name "*$STORY_SLUG*" 2>/dev/null | head -1)
fi

if [ -z "$STORY_DIR" ] || [ ! -d "$STORY_DIR" ]; then
  echo "ERROR: story not found: $STORY_SLUG" >&2
  exit 1
fi

# If no scene ref, return story dir
if [ -z "$SCENE_REF" ]; then
  echo "$STORY_DIR"
  exit 0
fi

# --list flag
if [ "$SCENE_REF" = "--list" ]; then
  for d in "$STORY_DIR/scenes"/*/; do
    basename "$d"
  done | sort
  exit 0
fi

# Resolve scene ref to directory
SCENES_DIR="$STORY_DIR/scenes"

# Try exact number match (1-9, 01-09)
SCENE_DIR=""
if [[ "$SCENE_REF" =~ ^[0-9]+$ ]]; then
  num=$(printf "%02d" "$SCENE_REF")
  SCENE_DIR=$(find "$SCENES_DIR" -maxdepth 1 -type d -name "${num}-*" 2>/dev/null | head -1)
  if [ -z "$SCENE_DIR" ]; then
    SCENE_DIR=$(find "$SCENES_DIR" -maxdepth 1 -type d -name "$SCENE_REF-*" 2>/dev/null | head -1)
  fi
fi

# Try partial name match
if [ -z "$SCENE_DIR" ]; then
  SCENE_DIR=$(find "$SCENES_DIR" -maxdepth 1 -type d -name "*${SCENE_REF}*" 2>/dev/null | head -1)
fi

if [ -z "$SCENE_DIR" ] || [ ! -d "$SCENE_DIR" ]; then
  echo "ERROR: scene not found in $STORY_DIR: $SCENE_REF" >&2
  echo "Available scenes:" >&2
  for d in "$SCENES_DIR"/*/; do
    echo "  $(basename "$d")" >&2
  done
  exit 1
fi

echo "$SCENE_DIR"
