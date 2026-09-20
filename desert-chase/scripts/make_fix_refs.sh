#!/bin/bash
# Per-shot motion references for the two shot fixes. Frame files are 1-based: f_0001.png is frame 0.
# usage: make_fix_refs.sh <blender_frames_dir> <out_dir>
set -euo pipefail
FR="$1"; OUT="$2"; mkdir -p "$OUT"; W=$(mktemp -d)
# shot 02 (behind the lead car) = previs frames f_0105..f_0189 (85 frames). f_0104 is still the drone shot and shows BOTH cars:
# starting one frame early hands Seedance the very car this fix must remove.
ffmpeg -nostdin -v error -y -start_number 105 -framerate 24 -i "$FR/f_%04d.png" -frames:v 85 -vf "scale=854:480,gblur=sigma=2" -an -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT/shot02_motion_ref.mp4"
# shot 04 (swirl) = f_0276..f_0318 (43 frames), shorter than Seedance's 1.8 s minimum, so it is slowed 2x (12 fps in, 24 out)
# and the fix render is later sped back up by keeping every 2nd frame.
# f_0301, f_0302, f_0304, f_0305 carry white headlight streaks from Blender's motion blur; Seedance draws those as floating squiggles.
# Replace them with blends of their clean neighbours (f_0300, f_0303, f_0306).
for n in $(seq 276 318); do cp "$FR/f_$(printf %04d $n).png" "$W/f_$(printf %04d $n).png"; done
bl(){ ffmpeg -nostdin -v error -y -i "$FR/f_$1.png" -i "$FR/f_$2.png" -filter_complex "[0][1]blend=all_expr='A*$3+B*(1-$3)'" "$W/f_$4.png"; }
bl 0300 0303 0.667 0301; bl 0300 0303 0.333 0302; bl 0303 0306 0.667 0304; bl 0303 0306 0.333 0305
ffmpeg -nostdin -v error -y -start_number 276 -framerate 12 -i "$W/f_%04d.png" -vf "trim=end_frame=43,scale=854:480,gblur=sigma=2,fps=24" -an -c:v libx264 -pix_fmt yuv420p -crf 18 "$OUT/shot04_motion_ref_2x_slow.mp4"
rm -rf "$W"; for f in "$OUT"/shot0*_motion_ref*.mp4; do echo "$(basename $f): $(ffprobe -v error -select_streams v -show_entries stream=nb_frames,duration -of csv=p=0 $f)"; done
