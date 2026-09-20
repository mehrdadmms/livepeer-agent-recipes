#!/bin/bash
# Picture assembly. Everything is cut on FRAME numbers at 24 fps so the beat-locked edit never drifts.
# usage: assemble.sh <raw_20s_render.mp4> <head_on_patch_4s.mp4> <shot02_fix_4s.mp4> <shot04_fix_4s_slowmo.mp4> <audio_source> <out.mp4>
#   pass "-" for a clip you do not have; that shot then stays as it is in the raw render.
#   pass "-" as the audio source for a SILENT picture (that is what you cut into shots for the engine-sound step).
# Frame map of the edit (0-based): shot cuts at 103, 188, 276, 318, 361, 403, 448; the usable cut ends at 468.
#   318-360  head-on shot      <- patch clip frames 48-90   (the raw render leaked a grey-box car into this shot)
#   103-187  behind lead car   <- fix clip frames 0-84      (raw render showed the chaser AHEAD of the lead car)
#   276-317  swirl             <- fix clip, every 2nd frame, frames 1-42 (fix was rendered at half speed from a 2x-slowed previs)
#   469-479  dropped           (the raw render ends on a stray aerial of one car that is not in the previs)
set -euo pipefail
RAW="$1"; PATCH="$2"; S2="$3"; S4="$4"; AUD="$5"; OUT="$6"
W=$(mktemp -d); mkdir -p "$W/base" "$W/c"
ffmpeg -nostdin -v error -i "$RAW" -vf "fps=24,scale=1280:720:flags=lanczos" -start_number 0 "$W/base/%04d.png"
put(){ # clip, filter, first clip frame, count, first target frame
  [ "$1" = "-" ] && return 0
  rm -f "$W"/c/*.png; ffmpeg -nostdin -v error -i "$1" -vf "$2" -vsync 0 -start_number 0 "$W/c/%04d.png"
  for ((i=0;i<$4;i++)); do cp "$W/c/$(printf %04d $(($3+i))).png" "$W/base/$(printf %04d $(($5+i))).png"; done; }
put "$PATCH" "fps=24,scale=1280:720:flags=lanczos" 48 43 318
put "$S2"    "fps=24,scale=1280:720:flags=lanczos" 0  85 103
put "$S4"    "fps=24,select='not(mod(n,2))',scale=1280:720:flags=lanczos" 1 42 276
for f in "$W"/base/*.png; do n=$((10#$(basename "$f" .png))); [ $n -ge 469 ] && rm -f "$f"; done   # drop 469 and everything after it
N=$(ls "$W/base" | wc -l | tr -d ' '); DUR=$(python3 -c "print($N/24)"); FST=$(python3 -c "print($N/24-0.5)")
ffmpeg -nostdin -v error -y -framerate 24 -start_number 0 -i "$W/base/%04d.png" -an -c:v libx264 -pix_fmt yuv420p -crf 16 -preset slow "$W/v.mp4"
# audio in its OWN pass, then mux (mixing audio inside a frame-capped video pass truncates it)
if [ "$AUD" = "-" ]; then cp "$W/v.mp4" "$OUT"; else
  ffmpeg -nostdin -v error -y -i "$AUD" -vn -af "atrim=0:${DUR},afade=t=out:st=${FST}:d=0.5" -ar 48000 -ac 2 -c:a pcm_s16le "$W/a.wav"
  ffmpeg -nostdin -v error -y -i "$W/v.mp4" -i "$W/a.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart "$OUT"
fi
rm -rf "$W"; ffprobe -v error -show_entries stream=codec_type,nb_frames,duration -of csv=p=0 "$OUT"
