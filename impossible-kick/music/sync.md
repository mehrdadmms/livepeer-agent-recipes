# Sync measurement (2 ms RMS windows on the decoded audio of the muxed mp4 files)

Hook frame 96 = 4.000 s at 24 fps. Frame period 41.7 ms.

| file | pre-hit level | first onset (s) | frame | error vs 4.000 s |
|---|---|---|---|---|
| final_music_only.mp4 | 0.038 | 3.9980 | 95.95 | -2 ms |
| final_sfx_only.mp4 | 0.092 | 4.0000 | 96.00 | +0 ms |
| final.mp4 | 0.109 | 4.0000 | 96.00 | +0 ms |

Music: generated track downbeat at 4.140 s in sonilo_v2.wav, trimmed 0.140 s (build_audio_v2.py).
SFX: synthesized hit layer placed at exactly 4.000 s (search window starts at 3.99 s so the tiny can-on-cobbles clink at f95.3, 3.971 s, is not counted as the hit); bed ducked 140 ms before it.
Other cues (crossbar ring f606, net thud f618) are placed from frame numbers and listed in sfx.md; not individually measured.
