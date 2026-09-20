#!/bin/bash
# Build the soundtrack: eight per-shot engine clips joined on the picture cuts, then mixed under your music.
#   ./make_audio.sh <sfx_dir> <music file | -> <out.wav> [music_start_sec]
# <sfx_dir> holds A..H as .wav/.mp4/.mp3 (the eight mirelo-sfx-v2v results, see prompts/v1_engine_sfx_per_shot.txt).
# "-" for music = engines only. Feed the result to assemble.sh as the audio source.
set -euo pipefail
SFX="$1"; MUSIC="$2"; OUT="$3"; START="${4:-0}"
LEN=(4.2917 3.5833 3.5833 1.7917 1.7917 1.7917 1.7917 1.4167)   # shot lengths: 103 86 86 43 43 43 43 34 frames @ 24 fps
IN=(); FC=""; LAB=""; i=0
for n in A B C D E F G H; do
  f=""; for x in wav mp4 mp3 m4a; do [ -f "$SFX/$n.$x" ] && { f="$SFX/$n.$x"; break; }; done
  [ -n "$f" ] || { echo "missing $SFX/$n.(wav|mp4|mp3|m4a)"; exit 1; }
  IN+=(-i "$f"); d=${LEN[$i]}; e=$(python3 -c "print(round($d-0.015,4))")
  fi="afade=t=in:d=0.015,"; fo=",afade=t=out:st=$e:d=0.015"; [ $i -eq 0 ] && fi=""; [ $i -eq 7 ] && fo=""
  FC+="[$i:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:$d,${fi}asetpts=N/SR/TB${fo}[s$i];"; LAB+="[s$i]"; i=$((i+1))
done
TMP=$(mktemp -d); ENG="$TMP/engines.wav"
ffmpeg -nostdin -y -loglevel error "${IN[@]}" -filter_complex "${FC}${LAB}concat=n=8:v=0:a=1,loudnorm=I=-18:TP=-2[out]" -map "[out]" -ar 48000 "$ENG"
if [ "$MUSIC" = "-" ]; then cp "$ENG" "$OUT"; else
  # music on top, engines ducked a little under it by sidechain
  ffmpeg -nostdin -y -loglevel error -ss "$START" -t 20.04 -i "$MUSIC" -i "$ENG" -filter_complex "\
[0:a]aresample=48000,afade=t=out:st=19.0:d=1.0,asplit=2[song][sc];\
[1:a]volume=0.8[eng];[eng][sc]sidechaincompress=threshold=0.08:ratio=3:attack=20:release=250[engd];\
[song][engd]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[mix]" -map "[mix]" -c:a pcm_s16le "$OUT"
fi
rm -rf "$TMP"; ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
