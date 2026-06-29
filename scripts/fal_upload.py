#!/usr/bin/env python3
"""Upload a local file to FAL's CDN and print the public URL.

Single-purpose helper — the agent uses this one-liner to get URLs for local
images, then does everything else via cURL directly against FAL's HTTP API.

Usage:
    python3 scripts/fal_upload.py <file_path>
    → https://v3b.fal.media/files/...

Requires: FAL_API_KEY in environment, fal-client installed.
"""

import os
import sys

import fal_client


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fal_upload.py <file_path>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("FAL_API_KEY") or os.environ.get("FAL_KEY")
    if not api_key:
        print("ERROR: FAL_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    client = fal_client.SyncClient(key=api_key)
    url = client.upload_file(path)
    if not url:
        print("ERROR: upload returned no URL", file=sys.stderr)
        sys.exit(1)

    print(url)


if __name__ == "__main__":
    main()
