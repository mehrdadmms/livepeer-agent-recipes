#!/bin/bash
# frames -> final.mp4 : CA, vignette, grade, halation-ish bloom, grain LAST, then mux audio
cd "$(dirname "$0")/.."
ffmpeg -y -v error -framerate 24 -i renders/frames/f%04d.png -i music/mix.wav \
 -filter_complex "[0:v]rgbashift=rh=-1:bh=1:edge=smear,split[a][b];[b]gblur=sigma=14,eq=brightness=-0.05[bl];[a][bl]blend=all_mode=screen:all_opacity=0.32,vignette=angle=0.55,eq=contrast=1.06:saturation=1.08,noise=alls=9:allf=t+u,format=yuv420p[v]" \
 -map "[v]" -map 1:a -c:v libx264 -crf 17 -preset slow -r 24 -c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart -t 8 final.mp4
