#!/bin/bash
# SFX mix for post1. Event times (s): SNAP1=3.95 (f95; native boom peak 3.99), FREEZE 3.96-12.13, TAKE CUP 8.75 (f210), SIP 9.85/swallow 10.3, RETURN 11.2 (f267-269), SNAP2=12.13 (f291), FADE 14.17-15.04
#
# Usage:  sound/mix.sh <raw_seedance_render.mp4> [sfx_dir]
#   raw_seedance_render.mp4  the untouched seedance-25-t2v output (24 fps, with its native audio)
#   sfx_dir                  folder with the mirelo wavs, default sound/gen (fill it with sound/fetch_sfx.sh)
# Writes sound/premaster.wav (48 kHz stereo float). Then run sound/master.sh.
#
# Every time below (adelay / volume envelopes / "if(lt(t,...))") is tied to THIS render's events, frame
# numbers at 24 fps. A new render has different beats: re-detect them (see SKILL.md step 5) and
# update the numbers, the header line above (build_data.py reads it) and the envelopes.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
V="$(cd "$(dirname "${1:?usage: mix.sh <raw_render.mp4> [sfx_dir]}")" && pwd)/$(basename "$1")"
G="${2:-$HERE/gen}"
cd "$HERE"
ms(){ python3 -c "print(int(round(($1)*1000)))"; }
ffmpeg -v warning -y \
 -i "$V" -i "$G/citybed.wav" -i "$G/v2v.wav" -i "$G/snap2.wav" -i "$G/subboom.wav" -i "$G/whoosh.wav" -i "$G/shimmer.wav" \
 -i "$G/pigeons.wav" -i "$G/boots.wav" -i "$G/tinnitus.wav" -i "$G/cup2.wav" -i "$G/cup.wav" -i "$G/sip.wav" \
 -i "$G/revboom.wav" -i "$G/rushback.wav" -i "$G/tail.wav" \
 -f lavfi -t 16 -i "sine=f=6200:r=48000" -f lavfi -t 16 -i "sine=f=6247:r=48000" \
 -f lavfi -t 2 -i "aevalsrc='0.9*sin(2*PI*(34*t+30*(1-exp(-t*3))/3)*1)*exp(-t*2.2)':s=48000" \
 -filter_complex "
 [0:a]aresample=48000,aformat=channel_layouts=stereo,volume=eval=frame:volume='if(isnan(t),1.1,if(lt(t,3.95),1.1, if(lt(t,4.6),0.55, if(lt(t,5.2),0.55-0.52*(t-4.6)/0.6, if(lt(t,12.12),0.03, if(lt(t,14.17),1.0, max(0,1-(t-14.17)/0.87)))))))'[nat];
 [1:a]aresample=48000,asplit=2[cbL][cbR0];[cbR0]adelay=14[cbR];[cbL][cbR]join=inputs=2:channel_layout=stereo,volume=eval=frame:volume='2.0*if(isnan(t),1,if(lt(t,3.96),1, if(lt(t,12.13),0.008, if(lt(t,14.17),1.15, max(0,1.15-1.15*(t-14.17)/0.87)))))'[bed];
 [2:a]aresample=48000,volume=eval=frame:volume='if(isnan(t),1.3,if(lt(t,3.86),1.3, if(lt(t,6.0),0.2, if(lt(t,8.9),2.6, if(lt(t,12.1),0.6, if(lt(t,12.3),0.25, if(lt(t,14.2),0.5, 0.06)))))))',aecho=0.8:0.55:70|130:0.25|0.15,volume=eval=frame:volume='1',aformat=channel_layouts=stereo[v2v];
 [3:a]aresample=48000,highpass=f=300,highshelf=f=4000:g=4,volume=5.5,asplit=2[sn1][sn2];
 [sn1]adelay=$(ms 3.95-0.26):all=1[snapA];
 [sn2]adelay=$(ms 12.13-0.26):all=1[snapB];
 [4:a]aresample=48000,atrim=start=1.55,asetpts=PTS-STARTPTS,lowpass=f=180,afade=t=in:d=0.02,afade=t=out:st=1.2:d=1.2,asplit=2[sb1][sb2];
 [sb1]volume=0.7,adelay=$(ms 3.97):all=1[subA];
 [sb2]volume=0.9,adelay=$(ms 12.15):all=1[subB];
 [18:a]asplit=2[dr1][dr2];[dr1]volume=0.55,adelay=$(ms 3.97):all=1[dropA];[dr2]volume=0.7,adelay=$(ms 12.15):all=1[dropB];
 [5:a]aresample=48000,volume=0.6,afade=t=out:st=1.4:d=1.5,adelay=$(ms 3.97-0.2):all=1,apulsator=hz=0.35:amount=0.6[whoosh];
 [6:a]aresample=48000,highpass=f=1500,volume=0.45,adelay=$(ms 3.97-0.3):all=1[shim];
 [7:a]aresample=48000,atrim=start=1.3,asetpts=PTS-STARTPTS,asplit=2[pg1][pg2];
 [pg1]atrim=end=1.55,afade=t=in:d=0.5,afade=t=out:st=1.35:d=0.2,volume=0.75,adelay=$(ms 2.29):all=1,pan=stereo|c0=0.55*c0|c1=1.0*c0[pigA];
 [pg2]volume=1.6,afade=t=out:st=1.2:d=0.5,adelay=$(ms 12.2):all=1,pan=stereo|c0=1.0*c0|c1=0.6*c0[pigB];
 [8:a]aresample=48000,atrim=start=0.8:end=2.8,asetpts=PTS-STARTPTS,afade=t=in:d=0.1,afade=t=out:st=1.6:d=0.4,volume=1.3,aecho=0.8:0.55:70|130:0.25|0.15,adelay=$(ms 4.25):all=1[boots];
 [9:a]aresample=48000,atrim=start=2.6,asetpts=PTS-STARTPTS,atempo=0.82,volume=18,afade=t=in:st=0:d=0.8,afade=t=out:st=7.3:d=0.4,atrim=end=7.8,adelay=$(ms 4.3):all=1[room];
 [16:a][17:a]amix=inputs=2:normalize=0,volume=0.012,tremolo=f=5:d=0.15,atrim=end=8.2,afade=t=in:st=0:d=0.9,afade=t=out:st=7.9:d=0.25,adelay=$(ms 3.98):all=1,aformat=channel_layouts=stereo[ring];
 [10:a]aresample=48000,atrim=start=0.35:end=1.2,asetpts=PTS-STARTPTS,highpass=f=250,volume=36,afade=t=in:d=0.03,afade=t=out:st=0.7:d=0.15,adelay=$(ms 8.72):all=1[cupA];
 [11:a]aresample=48000,atrim=start=1.05:end=1.5,asetpts=PTS-STARTPTS,highpass=f=250,volume=14,afade=t=out:st=0.3:d=0.15,adelay=$(ms 11.05):all=1[cupB];
 [12:a]aresample=48000,atrim=start=1.75:end=2.9,asetpts=PTS-STARTPTS,highpass=f=120,volume=0.28,afade=t=in:d=0.05,afade=t=out:st=0.95:d=0.2,adelay=$(ms 9.6):all=1[sip];
 [13:a]aresample=48000,atrim=start=1.6:end=3.03,asetpts=PTS-STARTPTS,afade=t=in:d=1.1:curve=exp,volume=0.3,afade=t=out:st=1.39:d=0.04,adelay=$(ms 10.75):all=1[rev];
 [14:a]aresample=48000,volume=0.6,afade=t=out:st=0.9:d=2.0,adelay=$(ms 12.1):all=1,asplit=2[rbL][rbR0];[rbR0]adelay=11[rbR];[rbL][rbR]join=inputs=2:channel_layout=stereo[rush];
 [15:a]aresample=48000,lowpass=f=220,volume=0.8,afade=t=in:d=0.6,afade=t=out:st=0.9:d=0.75,adelay=$(ms 13.4):all=1[tail];
 [nat][bed][v2v][snapA][snapB][subA][subB][dropA][dropB][whoosh][shim][pigA][pigB][boots][room][ring][cupA][cupB][sip][rev][rush][tail]amix=inputs=22:normalize=0:duration=first,atrim=end=15.093,aformat=channel_layouts=stereo:sample_rates=48000[out]" \
 -map "[out]" -c:a pcm_f32le premaster.wav
echo done
