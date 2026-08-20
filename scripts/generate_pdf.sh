#!/usr/bin/env bash
# Generate a printable storybook PDF from a Fábula story.
#
# Usage: bash generate_pdf.sh <story_dir> [output.pdf]
#
# Requires: fpdf2 (pip install fpdf2)

set -euo pipefail

STORY_DIR="${1:-}"
OUTPUT="${2:-}"

if [ -z "$STORY_DIR" ] || [ ! -d "$STORY_DIR" ]; then
  echo "Usage: bash generate_pdf.sh <story_dir> [output.pdf]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/generate_pdf.py" "$STORY_DIR" ${OUTPUT:+-o "$OUTPUT"}
