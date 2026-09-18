# QA checklist

Every agent QAs its own output before reporting. Character drift is a **hard fail**, never a "minor note". Report defects as lines the next attempt can add to Seedance block 5.

## Every deliverable (the stand-alone rule)

- [ ] **No source leakage.** No source frames, no source prompt text, no source platform or tool branding (logos, watermarks, header text like "AI / MODEL / CHARACTER REFERENCE"), and no words like "remake", "recreate", "inspired by", "original video". Internal docs (PLAN.md, briefs) may reference the source; outputs may not.
- [ ] **No real brands.** No readable real-world brand names, logos, venue names or trademarks on signs, clothes, cups or screens. Fictional replacements only.
- [ ] **Stands alone without a caption.** A viewer with zero context, sound off, understands what they are watching.
- [ ] Livepeer-only generation: every paid call is in `cost_log.jsonl` with the project `session_id`.

## Sheets (sheet maker, before sign-off)

| Check | How |
|---|---|
| Character: one identity across all views (face shape, age, hair, eye colour, skin, build) | Crop faces and heads to one strip (`qa/char_faces.png`) and compare side by side |
| Character: wardrobe identical across views; every garment and colour named in the report | Visual read |
| Character matches the user's reference photo (not a lookalike) | Side by side with the ref |
| Environment: matches the requested setting and mood; no people's faces that could become a second lead | Visual read |
| No text or logos on the character sheet; env sheet signage fictional and legible-or-absent (no garbled pseudo-text) | Read every sign; `nemotron-omni-vision` "list every readable word" |
| Resolution: long edge ≥ 1536 | `sips -g pixelWidth -g pixelHeight` / PIL |

Known weak spots to flag on the sign-off page: 3/4 views looking younger or older than the front view; real names such as a ticket booth or cinema marquee slipping into city scenes (the first run needed an edit pass to fix "tkts" and "EMBASSY 1").

## Scene stills

- [ ] Face, hair, eye colour and outfit match the sheet in every still (side by side with the sheet's front view + close-ups)
- [ ] Environment matches the env sheet; aspect ratio = output spec; no text in frame
- [ ] Fix path: `kontext-edit` on the still (max 2 edits), else regenerate. Never re-describe the character in text to fix it.
- [ ] Contact sheet of all stills for the gate

## Video (draft and final)

| # | Check | How |
|---|---|---|
| a | Identity in every 1 s frame | `ffmpeg -vf fps=1,scale=320:-2,tile=5xN` strip, compared with the sheet |
| b | Beats land on the block-4 timestamps ±1 s | the strip + `scripts/intake.sh` on the output (scene cuts, silences) |
| c | Concept-specific invariants from PLAN §5 (e.g. total stillness between snaps; the prop returns to the same hand) | frames around each beat |
| d | Continuity: one take / no unwanted cuts | `scenes.txt` from intake.sh should be empty for a one-take piece |
| e | Audio present and hits the sound-design beats | `waveform.png` + `silencedetect`; listen via `nemotron-omni-video` |
| f | No text, subtitles, logos, watermarks | frames + `nemotron-omni-video` yes/no checklist (`inputs.video_url`, not `source_url`) |
| g | Spec: resolution, aspect, fps ≥ 24, h264 yuv420p, AAC, duration ± 0.3 s, no black > 0.3 s at the start, file < 50 MB | `ffprobe -show_streams` |

On a failure: write each defect as a rule into block 5 (REQUIREMENTS), then rerun. Max 2 attempts per phase before reporting back. Do not reroll with an unchanged prompt unless the failure is clearly random.

## Explainer post

- [ ] Output spec (e.g. 1280x720 @30, h264, AAC) and audio present
- [ ] Every figure on screen equals the ledger to the cent; the total equals the `get_cost_report` session total, or the delta is explained on screen
- [ ] Failed runs appear as their own line; nothing is rounded to "about"
- [ ] Model names shown as plain capability names; no third-party product branding beyond that
- [ ] The sign-off page capture contains nothing that reveals the source (neutral lede, no source frames)
- [ ] Readable at phone width: downscale to 640 px wide and read every label
- [ ] Muted viewing still explains result → inputs → prompt → human approval → models + costs → total
- [ ] 6 sampled frames saved and read before reporting
