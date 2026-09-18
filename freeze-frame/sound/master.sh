#!/bin/bash
# Master the SFX premix and mux it onto the video.
#
# Usage:  sound/master.sh <raw_seedance_render.mp4> [out.mp4]
#   reads  sound/premaster.wav (from mix.sh)
#   writes sound/limited.wav, sound/master.wav, sound/master2.wav and the final mp4
#          (default: outputs/post1_freeze_frame.mp4 next to this folder)
# Chain: alimiter (limit 0.5) -> two-pass loudnorm to -14 LUFS / -1 dBTP (linear) -> +0.9 dB trim
#        -> ebur128 check -> video stream copied, audio AAC 256k 48 kHz stereo.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cd "$(dirname "${1:?usage: master.sh <raw_render.mp4> [out.mp4]}")" && pwd)/$(basename "$1")"
OUT="${2:-$HERE/../outputs/post1_freeze_frame.mp4}"
cd "$HERE"
ffmpeg -v error -y -i premaster.wav -af "alimiter=limit=0.5:attack=0.5:release=40:level=disabled" -c:a pcm_f32le limited.wav
J=$(ffmpeg -hide_banner -i limited.wav -af loudnorm=I=-14:TP=-1:LRA=20:print_format=json -f null - 2>&1 | sed -n '/{/,/}/p')
gv(){ echo "$J" | grep "\"$1\"" | sed 's/.*: "\(.*\)".*/\1/'; }
echo "pass1: I=$(gv input_i) TP=$(gv input_tp) LRA=$(gv input_lra) thr=$(gv input_thresh) off=$(gv target_offset)"
ffmpeg -hide_banner -y -i limited.wav -af "loudnorm=I=-14:TP=-1:LRA=20:measured_I=$(gv input_i):measured_TP=$(gv input_tp):measured_LRA=$(gv input_lra):measured_thresh=$(gv input_thresh):offset=$(gv target_offset):linear=true:print_format=json,aresample=48000" -c:a pcm_f32le master.wav 2>&1 | grep -E "normalization_type|output_i|output_tp"
ffmpeg -hide_banner -i master.wav -af ebur128=peak=true -f null - 2>&1 | grep -A12 Summary | grep -E " I:|Peak"
ffmpeg -v error -y -i master.wav -af "volume=0.9dB" -c:a pcm_f32le master2.wav
ffmpeg -v error -y -i "$V" -i master2.wav -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k -ar 48000 -ac 2 -movflags +faststart "$OUT"
echo "wrote $OUT"
