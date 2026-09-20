#!/bin/bash
# Build the 20 s previs with every cut locked to the beat grid of YOUR music track.
#   ./run_music.sh <audio file> [start_sec]      beat grid detected from the track (librosa)
#   ./run_music.sh -                             no track: uses BPM_OVERRIDE / BEAT0_OVERRIDE, silent outputs only
# Overrides (either mode):  BPM_OVERRIDE=134.15 BEAT0_OVERRIDE=0.737 ./run_music.sh -
#   = the exact grid of the original piece; reproduces its camera path to the millimetre.
# Needs: blender (5.x) and ffmpeg on PATH, and  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
set -euo pipefail
cd "$(dirname "$0")"
AUD="${1:?usage: ./run_music.sh <audio file | -> [start_sec]}"; START="${2:-0}"; PY="${PY:-./venv/bin/python}"
if [ "$AUD" != "-" ]; then
  J=$("$PY" beats.py "$AUD" "$START"); echo "$J"
  DET_BPM=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['bpm'])")
  DET_B0=$(echo "$J" | python3 -c "import sys,json;print(json.load(sys.stdin)['beat0'])")
fi
export BPM="${BPM_OVERRIDE:-${DET_BPM:?no track given: set BPM_OVERRIDE}}"
export BEAT0="${BEAT0_OVERRIDE:-${DET_B0:-0}}"
echo "beat grid: BPM=$BPM BEAT0=$BEAT0"
rm -rf out/frames out/comp; mkdir -p out
blender -b -P chase.py -- "$PWD/out" preview > out/blender_build.log 2>&1 || { tail -30 out/blender_build.log; exit 1; }
grep -E "^shots" out/blender_build.log || true
blender -b out/chase.blend -P export.py > out/blender_export.log 2>&1 || { tail -30 out/blender_export.log; exit 1; }
"$PY" compose.py
cd out
ffmpeg -nostdin -y -loglevel error -framerate 24 -i frames/f_%04d.png -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart clean20_silent.mp4
if [ "$AUD" != "-" ]; then
  ffmpeg -nostdin -y -loglevel error -ss "$START" -t 20 -i "$AUD" -vn -af "afade=t=out:st=19:d=1" -c:a aac -b:a 192k song20.m4a
  ffmpeg -nostdin -y -loglevel error -framerate 24 -i comp/c_%04d.jpg -i song20.m4a -c:v libx264 -pix_fmt yuv420p -crf 25 -c:a copy -shortest -movflags +faststart review20_music.mp4
  ffmpeg -nostdin -y -loglevel error -i clean20_silent.mp4 -i song20.m4a -c:v copy -c:a copy -shortest -movflags +faststart clean20_music.mp4
else
  ffmpeg -nostdin -y -loglevel error -framerate 24 -i comp/c_%04d.jpg -c:v libx264 -pix_fmt yuv420p -crf 25 -movflags +faststart review20_silent.mp4
fi
ls -la *.mp4
