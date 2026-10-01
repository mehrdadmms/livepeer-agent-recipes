# Music sync v2 (measured on the muxed mp4 files, audio decoded at 48 kHz)
Hook = picture frame index 96 (Blender frame 97) = 4.000 s at 24 fps. Frame 95 shows the kid at the waterline, 96 the first splash burst, 97 the tall crown.
Onset = first 4 ms RMS window above 35-50% of the local peak (search 3.8-4.4 s).
- final_music_only.mp4: hit onset 4.000 s (delta 0.0 ms = 0.0 frames)
- final_sfx_only.mp4: splash onset 4.000 s (delta 0.0 ms = 0.0 frames)
- final.mp4 (mix): onset 3.998 s (delta -2 ms = -0.05 frame)
Method: generated track drop found at 4.044 s in the raw 26 s track, head trimmed by 0.044 s; music ducked to 6% for 3.90-3.995 s; script `music/mix_v2.py`. Tolerance was 1 frame = 41.7 ms.

## Re-measured on the v3 (amusement pier + forum) muxed files
Same stems, new picture. final_music_only.mp4 hit 4.000 s (0 ms), final_sfx_only.mp4 splash 4.000 s (0 ms), final.mp4 mix 3.998 s (-2 ms = -0.05 frame). Hook frame index 96: kid has just entered the water beside the pier, splash bursts (frame 97 the crown, frame 100 it hits the lens).
