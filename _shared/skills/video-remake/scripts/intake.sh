#!/usr/bin/env bash
# Intake for a reference video: probe, contact sheet, scene cuts, OCR frames, waveform.
# Usage: intake.sh <video-file-or-URL> <out-dir> [fps_for_ocr=2]
# URLs (x.com, tiktok, youtube, instagram) are fetched with yt-dlp first.
# Outputs (all local, internal-only: NEVER reuse these in a deliverable):
#   ref.mp4 probe.json probe.txt contact.jpg frames/f_###.png scenes.txt waveform.png audio_stats.txt
set -euo pipefail
SRC="$1"; OUT="$2"; FPS="${3:-2}"
mkdir -p "$OUT/frames"
if [[ "$SRC" =~ ^https?:// ]]; then
  yt-dlp -q -f "bv*+ba/b" --merge-output-format mp4 -o "$OUT/ref.%(ext)s" "$SRC"
  SRC="$OUT/ref.mp4"
elif [[ "$SRC" != "$OUT/ref.mp4" ]]; then
  cp "$SRC" "$OUT/ref.mp4"; SRC="$OUT/ref.mp4"
fi

ffprobe -v error -show_format -show_streams -of json "$SRC" > "$OUT/probe.json"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,codec_name,pix_fmt:format=duration,size \
  -of default=nw=1 "$SRC" > "$OUT/probe.txt"
ffprobe -v error -select_streams a -show_entries stream=codec_name,sample_rate,channels -of default=nw=1 "$SRC" >> "$OUT/probe.txt" || true
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")

# Contact sheet: 1 frame per second, 5 columns, 320 px wide tiles
N=$(python3 -c "import math;print(max(1,math.ceil($DUR)))")
ROWS=$(( (N + 4) / 5 ))
ffmpeg -v error -y -i "$SRC" -vf "fps=1,scale=320:-2,tile=5x${ROWS}:padding=4:color=black" -frames:v 1 -q:v 3 "$OUT/contact.jpg"

# Dense frames for OCR of on-screen prompt text (read them with the Read tool, or nemotron-omni-vision on Livepeer)
ffmpeg -v error -y -i "$SRC" -vf "fps=${FPS}" "$OUT/frames/f_%03d.png"

# Scene cuts (scdet score >= 10). One timestamp per line.
ffmpeg -v info -i "$SRC" -vf "scdet=threshold=10" -an -f null - 2>&1 \
  | grep -o 'lavfi.scd.time: [0-9.]*' | awk '{print $2}' > "$OUT/scenes.txt" || true

# Sound design: waveform picture + loudness stats (silence gaps = beats)
if ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$SRC" | grep -q .; then
  ffmpeg -v error -y -i "$SRC" -filter_complex "showwavespic=s=1600x240:split_channels=0" -frames:v 1 "$OUT/waveform.png"
  ffmpeg -v info -i "$SRC" -af "silencedetect=noise=-40dB:d=0.4" -f null - 2>&1 | grep -E "silence_(start|end)" > "$OUT/audio_stats.txt" || true
else
  echo "no audio stream" > "$OUT/audio_stats.txt"
fi

echo "duration: ${DUR}s"; cat "$OUT/probe.txt"
echo "scene cuts: $(wc -l < "$OUT/scenes.txt" | tr -d ' ')  ($(tr '\n' ' ' < "$OUT/scenes.txt"))"
echo "frames for OCR: $(ls "$OUT/frames" | wc -l | tr -d ' ') at ${FPS} fps"
echo "silences:"; cat "$OUT/audio_stats.txt"
