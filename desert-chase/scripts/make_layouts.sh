#!/bin/bash
# 2x2 layouts that gpt-image-edit turns into the photoreal sheets. Run blender/sheets.py first (writes out/sheets/*.png).
# usage: make_layouts.sh <blender_out_dir>          (reproduces the original layouts bit-exactly)
set -euo pipefail
D="$1/sheets"
for t in car1 car2; do ffmpeg -nostdin -v error -y -i "$D/${t}_a_front34.png" -i "$D/${t}_b_side.png" -i "$D/${t}_c_rear34.png" -i "$D/${t}_d_front.png" -filter_complex "[0][1]hstack[t];[2][3]hstack[b];[t][b]vstack" "$D/${t}_layout.png"; done
ffmpeg -nostdin -v error -y -i "$D/env_a_wide.png" -i "$D/env_b_road.png" -i "$D/env_c_aerial.png" -i "$D/env_d_side.png" -filter_complex "[0][1]hstack[t];[2][3]hstack[b];[t][b]vstack" "$D/env_layout.png"
ls -la "$D"/*_layout.png
