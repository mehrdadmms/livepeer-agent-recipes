#!/bin/bash
# finish: PNG sequence -> graded, lens-treated, grained mp4 (video only). usage: finish.sh <frames_dir> <out.mp4> [frame_pattern]
# PREVIS MODE: lens distortion and vignette dropped (ffmpeg filters darkened/cropped the previs); order was: lens distortion -> chromatic aberration -> halation/bloom -> vignette -> grade -> film grain (LAST, per frame, output res)
IN="$1"; OUT="$2"; PAT="${3:-f_%04d.png}"
ffmpeg -v error -y -framerate 24 -i "$IN/$PAT" -vf "\
format=gbrp16le,\
rgbashift=rh=-1:bh=1:edge=smear,\
split[a][b];\
[b]curves=all='0/0 0.86/0 0.95/0.45 1/1',gblur=sigma=16,colorchannelmixer=rr=1.0:gg=0.62:bb=0.38[glow];\
[a][glow]blend=all_mode=screen:all_opacity=0.5,\
split[c][d];[d]gblur=sigma=3,format=gbrp16le[soft];[c][soft]blend=all_mode=normal:all_opacity=0.22,\
eq=contrast=1.04:saturation=1.0:gamma=1.45,\
colorbalance=rs=-0.03:bs=0.05:rh=0.05:bh=-0.04,\
format=yuv444p,noise=alls=6:allf=t+u,format=yuv420p" \
-c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p -movflags +faststart "$OUT"
