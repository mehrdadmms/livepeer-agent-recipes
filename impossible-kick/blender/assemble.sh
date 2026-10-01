#!/bin/bash
# frames -> graded video -> mux with the pre-mixed audio -> final.mp4 ; run from the scene folder
set -e
bash blender/finish.sh renders/frames renders/video_only.mp4
ffmpeg -v error -y -i renders/video_only.mp4 -i music/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -t 8.0 -movflags +faststart final.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,sample_rate,channels,duration -of default=nw=1 final.mp4
