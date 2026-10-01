#!/bin/bash
# v2 assembly (run from the scene folder, ONE queued job):
#   ../_shared/render_slot.sh 08-impossible-kick bash blender/assemble_v2.sh
set -e
mkdir -p renders/review
# 1. clean previs (no grade, no grain) = the reference for the video model
ffmpeg -v error -y -framerate 24 -i renders/frames/f_%04d.png -c:v libx264 -crf 16 -preset veryfast -pix_fmt yuv420p -movflags +faststart renders/previs.mp4
# 2. blurred copy, same length
ffmpeg -v error -y -i renders/previs.mp4 -vf "gblur=sigma=2" -c:v libx264 -crf 18 -preset veryfast -pix_fmt yuv420p -movflags +faststart renders/previs_blur.mp4
# 3. finished picture (halation, CA, grade, grain last) for the deliverable
bash blender/finish.sh renders/frames renders/video_only.mp4
# 4. three muxes: mix, music only, sfx only (all 30.0 s)
ffmpeg -v error -y -i renders/video_only.mp4 -i music/mix.wav   -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -t 30.0 -movflags +faststart final.mp4
ffmpeg -v error -y -i renders/video_only.mp4 -i music/music.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -t 30.0 -movflags +faststart final_music_only.mp4
ffmpeg -v error -y -i renders/video_only.mp4 -i music/sfx.wav   -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 -t 30.0 -movflags +faststart final_sfx_only.mp4
# 5. contact sheet from the FINAL file: frames 0,40,80,95,96,97,180,300,460,600,672(last 2 s start),719
ffmpeg -v error -y -i final.mp4 -vf "select='eq(n,0)+eq(n,40)+eq(n,80)+eq(n,95)+eq(n,96)+eq(n,97)+eq(n,180)+eq(n,300)+eq(n,460)+eq(n,600)+eq(n,672)+eq(n,719)',scale=270:480,tile=6x2" -frames:v 1 renders/review/contact_v2.png
# 6. decode audio of the muxed files for the sync measurement
for n in final final_music_only final_sfx_only; do ffmpeg -v error -y -i $n.mp4 -vn -ar 48000 -ac 1 renders/review/$n.audio.wav; done
for n in final final_music_only final_sfx_only; do ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,sample_rate,channels,duration -of default=nw=1 $n.mp4; done
