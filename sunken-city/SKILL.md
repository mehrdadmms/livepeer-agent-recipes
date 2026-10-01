---
name: sunken-city
description: Reproduce the "sunken city" hook with the Livepeer MCP: a 24 s 9:16 take where a boy sprints down a Victorian pier at sunset, vaults the rail at exactly 4.0 s on the music hit, and the camera dives through a drowned Athens to a lit temple window where a silhouette waves. Covers the Blender previs (camera and timing only), the photoreal sheet prompts (GPT Image 2, no quality words), keyframes at the 8 s joins, three chained Seedance 2.5 clips at 720p with the splash conformed to frame 96, separate music and SFX stems, and the BLENDER | LIVEPEER side-by-side. Triggers on "sunken city recipe", "pier dive video", "drowned Athens hook", "blender previs to seedance hook", "remake the sunken city".
---

# Sunken city: runbook

Paths are relative to this folder.

| Folder | What's in it |
|---|---|
| `outputs/` | `blender_vs_livepeer.mp4` (side by side, 1440x1280), `livepeer_720p.mp4` (the take with the mix), `blender_previs_540p.mp4` |
| `blender/` | `scene_v4.py` builds the whole scene headless (pier, Ferris wheel, forum, kid, FPV camera); `render.py`, `finish.sh`; `SHOTLIST.md` (per-segment camera lines with frame numbers), `PLAN.md` |
| `prompts/charsheet/` | The three master prompts (`A1` kid, `B1` pier, `C1` drowned Athens) written with the photoreal-prompt-enricher style, plus `all_sheet_prompts.md` for the detail shots |
| `prompts/keyframes/`, `prompts/clips/` | Keyframe edit prompts and the three 8 s clip prompts |
| `prompts/music/` | The music brief (sonilo-t2m) and the SFX list |
| `refs/masters/`, `refs/keyframes/` | Generated masters and the four join keyframes (all ours) |
| `music/` | `music.m4a`, `sfx.m4a`, `mix.m4a`, `sfx.md`, `sync.md` |
| `ledger/` | Every paid call: sheets $5.30, keyframes $4.50, Seedance passes $8.55 + $8.54 (480p drafts) + $16 + $12.37 (720p) |
| `review/` | `compare_contact.jpg`, `sync.md`, the pass-4 report |

## Hard rules
1. Livepeer MCP only. `timeout` in seconds from the capability's p95; long jobs `async: true`, poll `get_create_media`.
2. Download every result immediately; provider URLs expire. Keep the previs as the timing truth.
3. No real brands, no faces (the boy is back view only), no text in frame.
4. Hook at exactly 4.000 s: the music hit, the splash SFX and the picture. Measure, don't assume.

## Steps
1. **Previs** (Blender 5.2, EEVEE, 540x960, 24 fps, 576 frames): `blender -b -P blender/scene_v4.py`, then `blender/render.py` and `finish.sh`. The previs is camera and timing only: sprint 0-4 s, vault over the side rail at frame 96, drop through bubbles, slalom between six columns, under the arch, half orbit of the statue, up the temple steps, roll through the porch, brake into the window, push-in and wave 20-24 s. Keep imperfection in the camera (speed changes, banking, wobble).
2. **Music + SFX**: `sonilo-t2m` from `prompts/music/music_prompt.txt`, trimmed so the hit lands at 4.000 s; SFX from `mirelo-sfx` or synthesised per `music/sfx.md`; three stems, hit measured on the muxed files (`music/sync.md`).
3. **Sheets** (`gpt-image`, 1024x1536): the three masters from `prompts/charsheet/`. Rules that made them read as photos: no "ultra-realistic / 8K / cinematic", a named humble device (phone, GoPro in a housing), Kodak Portra 400 response, named failures (missed focus, blown sun, tilted horizon, backscatter), named wear (peeling rail paint, gum on planks, urchins and silt on marble), an "Avoid:" sentence specific to the scene.
4. **Keyframes** (`gpt-image-edit` with `inputs.image_urls` = [master, previs frame]): K000 = A1, K192 mid-slalom, K384 porch roll, K575 the lit window with the wave. Compose them like photographs; the previs frame is for blocking only. Pixel-locking them to the render makes the output look like the render.
5. **Seedance 2.5** (`seedance-25-i2v`, 720p, `duration` "8", start + end image, `generate_audio` false): three clips, prompts in `prompts/clips/clips_v4.md`. It follows the start image's aspect, so crop keyframes to 9:16 first. Measure the splash frame in clip 1 and conform it to frame 96 (trim, stretch at most 6%).
6. **Assemble**: concat to 24.000 s, mux `music/mix`, build the compare with Pillow label PNGs ("BLENDER" left, "LIVEPEER" right; this ffmpeg has no drawtext), 12-frame contact sheet, sync check.

## What we learned (do this, not that)
- Four 4 s clips chained on fixed stills morph like a slideshow; 8 s clips with a start and end image move like footage.
- A photoreal keyframe made as a "retouch" of the render stays a render. Ask for a new photograph with the same layout.
- Seedance 2.5 cannot take a video reference; `seedance-mini-ref2v` tracked the timing but broke underwater.
- The vault, the splash crown and the wave are the weakest beats; they need the strongest keyframes and the plainest prompt sentences.
