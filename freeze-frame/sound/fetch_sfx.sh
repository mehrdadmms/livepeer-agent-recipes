#!/bin/bash
# Download the exact mirelo outputs used in the published mix into sound/gen/ (or $1),
# and pull the foley bed's audio out of the mirelo-sfx-v2v video as v2v.wav.
# Use this to re-run mix.sh on the original render without paying for new SFX calls.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; G="${1:-$HERE/gen}"; mkdir -p "$G"
grep -v '^#' "$HERE/sfx_urls.txt" | while read -r name url _; do
  [ -n "$name" ] || continue
  [ -s "$G/$name" ] || curl -fsSL -o "$G/$name" "$url"
  echo "ok $name"
done
ffmpeg -v error -y -i "$G/v2v.mp4" -vn -c:a pcm_s16le "$G/v2v.wav"
echo "done -> $G"
