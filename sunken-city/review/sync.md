# Sync, Seedance v4 720p
- Audio music/mix.wav unchanged (AAC 192k), 24.000 s, hit at 3.998 s = frame 96. Previs v4 entry/splash is f97-100.
- Hook measured on raw c1: luma +35.7 at frame 91 (whiteout, peak 176 at 93), dark water from frame 100. Hit = 91, five frames EARLY.
- Conform: piecewise time-warp, frames 0-90 stretched x1.055 (slower), frames 91-191 compressed x0.95 (5% faster); both inside the 6% limit. Assembled cut: largest luma jump at frame 96 (+33.1).
- c2 frames 0-191, c3 frames 1-192; total 576 frames = 24.000 s at 24 fps.
- Joins (mean abs luma diff of neighbouring frames, 96x170): 192 = 21.1, 384 = 20.8, median of the cut 12.9, p90 22.3. Both joins sit inside the normal motion range of the FPV shots; no visible pop.
- Crop: i2v follows the 2:3 keyframe shape (786x1178); centre crop 662x1178 -> 720x1280 after the render (keyframe URLs are the public gpt-image outputs).
