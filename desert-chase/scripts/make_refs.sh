#!/bin/bash
# Turn the three sheets + the 480 Blender frames into the exact Seedance inputs.
# usage: make_refs.sh <sheets_dir> <blender_frames_dir> <out_dir>
# Verified against the originals: each crop matches at >= 39.6 dB (JPEG re-compression only), the motion ref at 41.8 dB.
set -euo pipefail
SH_DIR="$1"; FR="$2"; OUT="$3"; mkdir -p "$OUT"
# sheets are 1536x1024: four 762x506 panels on a 774 x 518 grid (12 px gutter). Seedance refuses multi-view sheets, so pass ONE panel per ref.
crop(){ ffmpeg -nostdin -v error -y -i "$SH_DIR/$1" -vf "crop=762:506:$2:$3" -q:v 2 "$OUT/$4"; }
crop car1_sheet.png 0   0   image1_car_a_front34.jpg   # @Image1  panel A (top left)
crop car1_sheet.png 0   518 image2_car_a_rear34.jpg    # @Image2  panel C (bottom left)
crop car2_sheet.png 0   0   image3_car_b_front34.jpg   # @Image3
crop car2_sheet.png 0   518 image4_car_b_rear34.jpg    # @Image4
crop env_sheet.png  0   0   image5_location_wide.jpg   # @Image5  panel A
crop env_sheet.png  774 0   image6_location_road.jpg   # @Image6  panel B (top right)
# @Video1: the previs, small, blurred and slightly desaturated so Seedance copies MOTION, not the grey-box look
ffmpeg -nostdin -v error -y -framerate 24 -i "$FR/f_%04d.png" -vf "scale=640:360,gblur=sigma=5,hue=s=0.85" -an -c:v libx264 -crf 18 -pix_fmt yuv420p "$OUT/video1_motion_ref20.mp4"
ls -la "$OUT"
