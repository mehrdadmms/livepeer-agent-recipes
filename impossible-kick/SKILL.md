---
name: impossible-kick
description: Reproduce the "impossible kick" hook with the Livepeer MCP: a 30 s 9:16 take where a street footballer kicks a dented ZAPPO can at exactly 4.0 s on the music hit, the camera rides the spinning can over rooftops and through a window into a football-mad mural street that turns into a stadium with a goal across it. Covers the Blender previs (camera and timing only), full photoreal sheets (12 single photos, enricher prompts, humble-gear flaws), keyframes at the 8 s joins rebuilt from the can master so the can never changes, spin continuity sentences carried from clip to clip, four chained Seedance 2.5 clips at 720p, strike conformed to frame 96, separate music and SFX stems, and the BLENDER | LIVEPEER side-by-side. Triggers on "impossible kick recipe", "can kick video", "street becomes a stadium", "blender previs to seedance kick", "remake the impossible kick".
---

# Impossible kick: runbook

Paths are relative to this folder.

| Folder | What's in it |
|---|---|
| `outputs/` | `blender_vs_livepeer.mp4` (side by side, branded), `livepeer_720p.mp4` (the take with the mix), `blender_previs_540p.mp4` |
| `blender/` | the scene and animation scripts (`scene.py`, `v2_anim.py`, `make_murals.py`, `render_previs.py`, …), `SHOTLIST.md` (per-segment camera lines), `PLAN.md` |
| `prompts/charsheet/` | the 12 sheet prompts in the photoreal-enricher structure + the QA with the anti-AI tell checked per image |
| `prompts/keyframes/`, `prompts/clips/` | keyframe prompts and the clip prompts for every pass (v2 = can identity + spin sentences; v3 = 720p) |
| `prompts/music/` | the music brief (sonilo-t2m) and SFX list |
| `refs/sheets/`, `refs/keyframes/` | the 12 generated sheet photos (footballer x4, can x2, alley x2, mural street x2, street-stadium x2) and the 6 keyframes |
| `music/` | `music.m4a`, `sfx.m4a`, `mix.m4a`, `sfx.md`, `sync.md` |
| `ledger/` | every paid call: sheets $4.51, pass 1 (720p) $21, pass 2 (480p fix) $7.9, pass 3 (720p) $14.9; scene total $48.43 |
| `review/` | sync measurements |

## Hard rules
1. Livepeer MCP only; `timeout` in seconds from the capability's p95; long jobs async + `get_create_media`.
2. Download every result immediately. The previs is the timing truth: strike on frame 96 = 4.000 s, measured, not assumed.
3. No real brands, faces or readable text: the can label is the invented ZAPPO LEMON SODA, murals and flags are invented clubs.
4. The hero prop must never change: the can keeps its colours, label, dent and size in every keyframe and every clip.

## Steps
1. **Previs** (Blender 5.2, EEVEE 540x960, 720 frames): `blender/scene.py` + `v2_anim.py`; juggle 0-4 s, strike at frame 96, FPV flight through the alley, window, mural street, then the street-stadium ending.
2. **Music + SFX**: sonilo-t2m cue trimmed so the downbeat sits on 4.000 s; SFX list in `music/sfx.md`; three stems.
3. **Sheets** (gpt-image 1024x1536 via `inputs.image_size`): master + details per subject from `prompts/charsheet/`. What made them read as photos: old phone / flash compact named per shot, Portra response, missed focus, blown flash, tilted frame, mud, loose laces, mismatched socks; an "Avoid:" sentence per shot; no quality words.
4. **Keyframes** (gpt-image-edit, `image_urls` = [previous keyframe or sheet, can master B1, dent detail B2, previs frame]): one per 8 s join plus the hook; "the can is exactly this can"; check at 100% zoom.
5. **Clips** (`seedance-25-i2v`, 720p, `duration` "8" / "6" for the last, start + end image, `generate_audio` false): four clips. Measure the can's spin in the last 12 frames of each clip and open the next prompt with it ("enters already spinning end over end clockwise about once per second and keeps spinning the whole clip; the can never changes colour, label or size"). The floodlights warm up over 2 s inside clip 3, never a cut. Conform the strike to frame 96 (trim, stretch ≤ 6%).
6. **Assemble**: concat to 30.000 s, mux the mix, `build_compare` with Pillow label PNGs ("BLENDER" | "LIVEPEER"), corner lockup and end card.

## What we learned
- The first sheet set looked "AI": too composed, uniform wet sheen, teal-orange. The fix was the enricher's anti-AI pass per image and humble gear named per shot.
- Without the can master in every keyframe's refs, Seedance drifted the can to a plain silver can after the first clip.
- Spin direction and rate written as the first sentence of each clip prompt roughly holds across joins; it is not exact.
- One 720p take of clip 2 lost the label for 3 s; the 480p take of that slot was kept. Resolution does not fix identity; refs do.
