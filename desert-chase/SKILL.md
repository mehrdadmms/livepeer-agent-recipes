---
name: desert-chase
description: Recreate the "desert chase" piece with Blender and the Livepeer MCP. A 20 s photoreal two-car desert chase, blocked out as grey boxes in Blender with every cut locked to the beat of a music track, then rendered by Seedance 2.5 (seedance-25-ref2v) using the blurred Blender previs as the motion reference and single-panel crops of three character sheets as the cast. Covers the Blender previs pipeline, the sheets made from Blender layouts, the 20 s render, the head-on patch, per-shot engine sound, the two shot fixes and the frame-accurate assembly. Triggers on "desert chase recipe", "recreate the desert chase", "Blender previs to Seedance", "beat-synced car chase".
---

# Desert chase: runbook

Paths are relative to this folder. Generic Seedance rules (five-block call sheet, timeouts, reference check) are in `../_shared/skills/seedance-video`.

| Folder | What's in it |
|---|---|
| `blender/` | The whole previs: `chase.py` (scene, cars, 8 shot cameras, cuts on beats), `beats.py` (tempo and first beat from your track), `export.py` (per-frame motion data), `compose.py` (review render with HUD and overhead map), `sheets.py` (four-view grey-box renders for the sheets), `run_music.sh` (runs it all). |
| `prompts/` | Every prompt, exactly as sent. Line 1 of each file is `capability \| inputs \| settings \| cost`; the rest is the prompt. |
| `refs/` | The three sheets, the Blender layouts they came from, the six single-panel crops (`image1..6`, in `image_urls` order), the blurred 20 s motion reference (`video1_motion_ref20.mp4`), and `fixes/` (the inputs of the two shot fixes). |
| `scripts/` | ffmpeg helpers: layouts, reference crops, fix references, soundtrack, assembly. |

Not in the repo: the music (it was a commercial track, bring your own), the rendered video, and the raw Seedance clips. Seedance is generative, so a re-run gives the same shots and cuts, not the same pixels.

## Hard rules

1. **Livepeer MCP only.** `timeout` is in SECONDS (680 for `seedance-25-ref2v`), `async: true`, poll `get_create_media`. Download every result at once; `persist` fails now and then.
2. **One panel per reference.** Seedance refuses multi-view sheets. Pass the crops in `refs/image1..6`, never a whole sheet.
3. **Probe first.** Run `prompts/v1_probe_prompt.txt` (4 s, 480p, about $1.11) before the 20 s render. It also tells you whether `seedance-25-ref2v` is up.
4. **Check every reference image for the defect you are trying to remove** before you pay for a render (see step 7).
5. **Cut on frame numbers at 24 fps**, never on seconds. Render audio in its own pass, then mux.

## Steps

**1. Previs (free).** Needs Blender 5.x and ffmpeg on PATH.
```
cd blender && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./run_music.sh /path/to/your_track.mp3 0          # cuts land on YOUR track's beats
BPM_OVERRIDE=134.15 BEAT0_OVERRIDE=0.737 ./run_music.sh -     # no track: the original piece's exact beat grid
```
Output in `blender/out/`: `frames/f_0001..0480.png`, `clean20_*.mp4`, `review20_*.mp4`, `motion.json`, `chase.blend`. With the original grid the cuts fall on frames 104, 189, 275, 318, 361, 404, 447. Review the HUD render before spending anything.

**2. Sheets (3 x $0.23).** `blender -b blender/out/chase.blend -P blender/sheets.py`, then `scripts/make_layouts.sh blender/out`. Upload each layout and run `gpt-image-edit` with `prompts/sheet_car_a.txt`, `sheet_car_b.txt`, `sheet_location.txt`. Or skip this step and use `refs/*_sheet.png`.

**3. References (free).** `scripts/make_refs.sh refs blender/out/frames my_refs` makes the six crops and the blurred motion reference. Or use the ones in `refs/`. Upload all seven.

**4. Render.** `seedance-25-ref2v`, `image_urls` = image1..6 in order, `video_urls` = the motion reference, `generate_audio: true`.
- Probe: `prompts/v1_probe_prompt.txt`, `duration "4"`, `480p`, first 4 s of the motion reference.
- Full: `prompts/v1_seedance_ref2v_prompt.txt`, `duration "20"`, `720p`, `16:9`, about $11.92.

**5. Head-on patch (about $1.99).** The 20 s render leaked a grey-box car into the head-on shot (frames 318-360). `prompts/v1_head_on_patch.txt`, three image refs, no video ref. Frames 48-90 of that clip replace the shot. Only needed if your render has the same defect.

**6. Engine sound (about $0.23).** Seedance put each engine on the wrong car, so its audio was thrown away. Cut the patched picture into its eight shots (frames 0-102, 103-188, 189-274, 275-317, 318-360, 361-403, 404-446, 447-480), run `mirelo-sfx-v2v` on each with the matching prompt in `prompts/v1_engine_sfx_per_shot.txt` (`inputs.duration` is an integer), save the results as `A..H`, then `scripts/make_audio.sh sfx_dir your_track.mp3 mix.wav`.

**7. The two shot fixes (about $0.46 + $4.51 for the accepted renders).**
- Shot 02, behind the lead car: the render showed the chaser AHEAD of it. Clean the shot's first frame with `prompts/fix_shot02_clean_start_frame.txt`, measure that the other car is really gone, then render `prompts/fix_shot02_behind_lead_car.txt`. Three attempts failed here because the "clean" start frame still contained the blue car. The prompt never mentions a second vehicle or the colour blue on purpose.
- Shot 04, swirl: the lead car faced the wrong way. Keyframe from `prompts/fix_shot04_keyframe.txt`, render `prompts/fix_shot04_swirl.txt`. The shot is shorter than Seedance's minimum, so its motion reference is slowed 2x and every second output frame is kept.
- `scripts/make_fix_refs.sh blender/out/frames out_dir` rebuilds both motion references. The ones used are in `refs/fixes/`.

**8. Assemble.** `scripts/assemble.sh raw_20s.mp4 patch_4s.mp4 shot02_fix.mp4 shot04_fix.mp4 mix.wav final.mp4` (`-` skips a clip). It places everything on the frame map in its header, drops the stray last 11 frames and fades the audio over the last 0.5 s. Result: 1280x720, 24 fps, 469 frames, 19.54 s.

## Cost

About $16 for v1 at list price (sheets $0.69, probe $1.11, 20 s render $11.92, patch $1.99, engine sound $0.23), plus about $5 for the two accepted fixes. Rejected fix attempts cost roughly another $9. A video reference is billed at 0.6 x rate x (reference seconds + output seconds).
