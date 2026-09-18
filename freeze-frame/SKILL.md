---
name: freeze-frame
description: Reproduce the "freeze-frame" piece exactly with the Livepeer MCP. It is a 15 s ultra-realistic single take. A woman in a black leather jacket walks at the camera through a rainy, dystopian 1980s Times Square, snaps her fingers and freezes the city, sips a frozen stranger's coffee, snaps again and the city resumes. It also has a 66 s narrated "full recipe" explainer with a real cost ledger ($13.19). Covers the location sheet, the character sheet from text, the text-only Seedance 2.5 render, Mirelo sound design and the -14 LUFS master, the HTML→Playwright→ffmpeg explainer with Inworld narration, approval gates and cost ledger conventions. Triggers on "make the freeze-frame video", "time freeze snap video", "reproduce freeze frame", "freeze-frame recipe", "snap and the city freezes", "rebuild the freeze frame explainer".
---

# Freeze-frame: runbook

This folder is the whole recipe. The paths below are relative to it (`freeze-frame/`).

| Folder | What's in it |
|---|---|
| `prompts/` | Every prompt, verbatim. The first line of each `.txt` holds `capability \| source \| settings \| $` metadata; the rest is the prompt. |
| `refs/` | The three locked design images: `envsheet_v1.jpg`, `charsheet_v3.jpg`, `char_v3_single.jpg`. |
| `outputs/` | `post1_freeze_frame.mp4` (15.09 s, 1280x720, 24 fps, −14 LUFS) and `post2_how_it_was_made.mp4` (66.3 s, 30 fps). |
| `sound/` | `mix.sh`, `master.sh`, `fetch_sfx.sh` and `sfx_urls.txt`. |
| `explainer/` | `template.html`, `render.py`, `build_data.py`, `vo/` and `assets/`. |
| `ledger/` | `cost_log_sheets.jsonl` and `cost_log_post1.jsonl`, one line per call. |

Generic skills this recipe builds on are in `../_shared/skills/`:
- `seedance-video`: the five-block call sheet, the likeness check and timeouts.
- `video-remake`: the multi-agent process, the sign-off page, the ledger schema and the QA checklist.

Read them when a step points there.

## Hard rules

1. **Livepeer MCP only.** Never use any other media MCP server (for example a direct fal-ai one). Livepeer capabilities with a fal upstream (nano-banana, mirelo, inworld-tts) are fine.
2. **`timeout` is in SECONDS**, sized to the capability's p95 (`describe_capability`). An undersized timeout still bills and returns nothing. Long jobs use `async: true` and are polled with `get_create_media({job_id})` every 10–20 s.
3. **Durable URLs only.** Pass `persist: true` and hand downstream steps the `agent.livepeer.org/a/…` URL, never a provider URL. If persist or `upload` fails with **413** (videos over a few MB):
   1. Download the file.
   2. Call `create_upload_url({content_type, filename})`.
   3. `curl -X PUT` the bytes with the returned `headers` to `upload_url`.
   4. Log `public_url` as the durable URL.

   The returned `authorization` header is a short-lived secret. Never write it into a ledger, script or doc.
4. **No real brands** anywhere in the frame: only invented signage (OBEY. CONSUME. REPEAT., KAITO, THE IRON CROWN, NOVA COLA, RATION, PARAGON 1). No platform or tool branding on the posts except the Livepeer outro.
5. **Posts never reveal where the idea came from.** Captions, on-screen text, the sign-off page and narration contain no reference footage, reference prompts or source branding, and nothing that implies the piece derives from another video. Internal notes may.
6. **Each post stands alone.** Post 1 works without a caption and with the sound off. Post 2 explains itself without Post 1 beside it.
7. **Character drift is a hard fail.** QA every image and every clip against `refs/charsheet_v3.jpg`.
8. **Every paid call gets one ledger line**, including failures, refusals, QA rejections and voice tests (see step 7).

## Human approval gates

The user approves on **one ADHD-friendly page**, not in a chat thread. The page shows:
- the sheets as big images,
- the plan in 3 lines,
- 4 budget boxes (spent / expected / worst case / hard stop),
- one-click decisions with defaults pre-selected,
- a "Copy my answers" block that the user pastes back into the terminal.

Build it with `../_shared/skills/video-remake/assets/signoff_template.html` and `scripts/fill_signoff.py`, then publish it as an Artifact. `fill_signoff.py` refuses the banned source words.

| Gate | When | What was approved here |
|---|---|---|
| **A** | After steps 1–2 | Character sheet APPROVE, environment sheet APPROVE, plan and budget ($35 hard stop, pause at $25), Livepeer spend cap raised to $120 (only the user can do this), ending = fade out, failed renders shown as their own cost line, Post 2 shows the final only. |
| **B** | Before the first 720p render (budget checkpoint) | Go/no-go on the ~$7.45 spend. |
| **C** | Final | Post 1 and Post 2 before anything is published. |

`explainer/assets/approval/` holds the captured Gate A page (the plan section down) and the pasted answers. Post 2 shows both.

---

## Step 1: Location sheet

**Bring your own street photo.** The original input photo is not in this repo. Use a photo you own or have rights to, of a wide avenue with tall billboards, marquees and a vanishing point.

1. Upload it with `upload` (bytes) or `create_upload_url` + PUT to get a public URL.
2. Call:
   ```
   run_capability({capability: "gpt-image-edit",
     source_url: <your photo URL>,
     prompt: <prompts/envsheet_prompt.txt, body without the metadata line>,
     inputs: {image_size: {width: 1536, height: 1024}, quality: "high"},
     async: true, timeout: 310, persist: true, session_id, idempotency_key: "envsheet-a1"})
   ```
   - `image_size` must be the **object**. The string `"1536x1024"` is refused before dispatch because it isn't in the provider enum. That refusal is not billed.
   - The prompt keeps the list of real brand names it tells the model to REMOVE. That's intended.
3. **Optional text fix.** If real-looking or garbled lettering survives, run one more `gpt-image-edit` on the output with `prompts/envsheet_fix_prompt.txt` (same settings). The file is condensed. Name the specific signs you saw (panel, position, current text → invented replacement), keep "everything else identical", and don't add new objects or change the aspect ratio.
4. `persist` the accepted sheet. Its durable URL feeds step 2.

- **Cost:** $0.23 per call. The run took 2 calls ($0.46): the first draft was rejected for real names on a booth and a marquee, and the fix was accepted. Each call takes about 2 min.
- **QA:** 5 panels, same dusk palette and grain. Panel 2 is at eye level down the avenue (the walking-shot angle). Zoom in on every sign: no readable real brand and no garbled text. **Reference:** `refs/envsheet_v1.jpg`.

## Step 2: Character sheet from text

```
run_capability({capability: "gpt-image-edit",
  source_url: <durable URL of the step-1 sheet>,
  prompt: <prompts/charsheet_v3_prompt.txt body>,
  inputs: {image_size: "auto", quality: "high"},
  async: true, timeout: 310, persist: true, session_id, idempotency_key: "p1-charsheet-v3-a1"})
```

- The location sheet is only the **place and light reference**. The woman is designed entirely in the prompt text ("invented, not based on any real person"). Don't feed a photo of a real person.
- **Cost:** $0.23, about 2 min.
- **QA:** 4 full-length panels (front, three-quarter, profile, back) at the same scale. Same face, hair, earring and outfit in every panel. No logos, no close-ups. **Reference:** `refs/charsheet_v3.jpg`. This sheet is the drift reference for everything after it.

## Step 3: Single street photo

```
run_capability({capability: "nano-banana",
  source_url: <durable URL of the step-2 sheet>,
  prompt: <prompts/char_v3_single_prompt.txt body>,
  inputs: {aspect_ratio: "16:9"},
  async: true, timeout: 180, persist: true, session_id, idempotency_key: "p1-char-v3-single-a1"})
```

- **Cost:** $0.084, under 1 min.
- **QA:** one photo, not a sheet. Full length, walking at camera, identical to panel 1 of the sheet. **Reference:** `refs/char_v3_single.jpg`.
- **Use:** this is the approval and QA still, and it is the one person image that passes Seedance's likeness check if you want an optional `seedance-25-ref2v` probe. The final render in step 4 does NOT take it as input.

## Step 4: Seedance render (text-only)

**Prompt:** `prompts/prompt_v4_t2v.txt`, the five blocks `[ASSETS] [SUMMARY] [STYLE] [PLOT] [REQUIREMENTS]` sent as one text, verbatim.

**Call:**
```
run_capability({capability: "seedance-25-t2v",
  prompt: <prompts/prompt_v4_t2v.txt, whole file>,
  inputs: {duration: "15", resolution: "720p", aspect_ratio: "16:9", generate_audio: true},
  async: true, timeout: 610, persist: true, session_id, idempotency_key: "p1-final720-t2v-aN"})
```

Then poll `get_create_media({job_id})` every 15 s until it's done. `duration` is a **string**.

**If persist fails (413):**
1. Download the provider file.
2. Re-host it with `create_upload_url` + PUT (hard rule 3).
3. Save it locally as the raw render (for example `sound/raw_render.mp4`). The sound steps need it with its native audio.

The published run's raw render is public at `https://7y4flzpulgv4co6r.public.blob.vercel-storage.com/uploads/1789740323601-zpqhou-post1_final.mp4`.

- **Cost:** $7.4498 ($0.4967/s × 15). It takes about **6 min** (365 s measured). The run's first attempt failed upstream after 586 s and was not charged. Resubmit with a new idempotency key.
- **QA:** check a 2 fps contact sheet (`ffmpeg -i raw.mp4 -vf "fps=2,scale=320:-1,tile=6x5" -frames:v 1 sheet.jpg`) and frame strips around each beat.
  - One unbroken take, camera only moving backward.
  - The woman matches the sheet in every frame (face, shag, earring, jacket, boots).
  - Between the snaps nothing moves but her: no walkers, rain or birds.
  - Exactly one cup, returned to the same hand.
  - Fade to black at the end.
  - No readable real brands.
  - The accepted render had minor garbled marquee lettering. That was accepted, so every new defect becomes a new `[REQUIREMENTS]` line.

> **Why text-only (internal note, never in a post).** Seedance `ref2v` runs a provider likeness check on `image_urls`. It refused this project's AI-generated woman as "likenesses of real people" (`moderation_blocked` / `partner_validation_failed`) in several shapes:
> - the multi-view sheets,
> - two person refs in one call,
> - even a pair that had passed a 4 s probe, once used at 15 s.
>
> Six refusals were logged at $0. The reliable path is `seedance-25-t2v` with the character, location and coffee woman written as text in `[ASSETS]` and referred to by handle ("Vale", "the coffee woman") everywhere else. Keep `[ASSETS]` word for word across attempts. Details: `../_shared/skills/seedance-video/SKILL.md`, "Likeness check".

## Step 5: Sound design

**Prompts and costs:** `prompts/sfx_prompts.md`. It lists 15 `mirelo-sfx` one-shots (`inputs.duration` in whole seconds, `timeout` 120, or 150 for 15 s) and 1 `mirelo-sfx-v2v` synced foley bed (`source_url` = the raw render's public URL, `inputs.duration: 15`, `timeout: 150`; its output is a video, so extract the audio). All 16 cost $0.861.

**Event timeline of the published render:**

| Event | Time (s) | Frame at 24 fps |
|---|---|---|
| snap 1 | 3.95 | f95 (native boom peak 3.99) |
| freeze | 3.96 → 12.13 | |
| cup taken | 8.75 | f210 |
| sip | 9.85 (swallow 10.3) | |
| cup returned | 11.2 | f267–269 |
| snap 2 | 12.13 | f291 |
| fade | 14.17 → 15.04 | |

**Mix and master:**
```
sound/fetch_sfx.sh                          # exact published SFX -> sound/gen/ (skip the paid calls)
sound/mix.sh  sound/raw_render.mp4          # 22-input ffmpeg amix -> sound/premaster.wav
sound/master.sh sound/raw_render.mp4        # alimiter -> 2-pass loudnorm -14 LUFS / -1 dBTP -> +0.9 dB -> mux
```

- `mix.sh` ducks the native audio to −30 dB (×0.03) during the freeze.
- It synthesises a 6.2 kHz ring (6200 + 6247 Hz beating sines, tremolo) and a pitch-drop thump for each snap.
- It pans the city bed and rush-back with a Haas delay of 11–14 ms.
- It adds echo to the footsteps and the foley bed during the freeze.

Run on the published raw render, these two scripts reproduce `premaster.wav` and `master2.wav` **bit-for-bit** (verified).

**Timings must be re-detected on every new render.** Every `adelay`, every `if(lt(t,…))` envelope and the `Event times (s):` header in `mix.sh` belong to this one render. `build_data.py` reads that header line. Seedance output is 24 fps, and the method is:
1. **Overview:** `ffmpeg -i raw.mp4 -vf "fps=2,scale=320:-1,tile=6x5" -frames:v 1 overview.jpg`
2. **Frame-exact strips** around each beat, where tile position = frame offset:
   ```
   ffmpeg -i raw.mp4 -vf "select='between(n,72,119)',scale=320:-1,tile=8x6" -vsync 0 -frames:v 1 snap1.jpg
   ```
   Zoom on the hand with `crop=640:720:320:0` for the snap frame. The event time is the frame number divided by 24.
3. **Native audio peaks** (the boom lands a few frames after the click):
   ```
   ffmpeg -i raw.mp4 -vn native.wav
   ffmpeg -i native.wav -af "asetnsamples=2400,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=rms.txt" -f null -
   ```
4. **Fade start** from mean luma:
   ```
   ffmpeg -i raw.mp4 -vf "select='gte(n,300)',signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=yavg.txt" -f null -
   ```
5. **SFX onsets:** the same `astats` pass per wav (0.05 s windows), so each hit is trimmed (`atrim=start=`) to its transient before `adelay`.

- **Cost:** $0.861 in total. Mixing is local and free.
- **QA:**
  - `ffmpeg -i master2.wav -af ebur128=peak=true -f null -` should read I ≈ −14 LUFS with peaks below −1 dBTP.
  - Snap transients should land within ±1 frame of the hand.
  - The freeze should be near-silent except for her steps and the ring.
  - The city should slam back on snap 2.
  - Listen once on headphones and once on a phone speaker.

## Step 6: Explainer (Post 2)

The pipeline is HTML `render(t)` → Playwright screenshots → ffmpeg. Full detail is in `explainer/README.md`.

```
cd explainer
python3 vo/process_vo.py   # fetch narration takes, trim silence, atempo 1.15, write durations
python3 render.py          # build_data -> frames -> audio -> post2_final.mp4
```

**Narration:**
- Call: `run_capability({capability: "inworld-tts", prompt: <line>, inputs: {voice: "Dennis (en)"}, timeout: 34, session_id, idempotency_key})`.
- A `speed` input is ignored (undeclared), so the speed-up is `atempo=1.15` in `process_vo.py`.
- There are 17 lines in `vo/lines.json`. Each line **fills its card**: the card lasts exactly the line + 0.15 s (0.05 s lead, 0.10 s tail), so there's no dead air.
- Lines follow the tabs 1 Location … 7 Cost.
- The bed ducks 10 dB under speech, and the mix is loudnormed to −14 LUFS.
- A line costs about $0.0004–0.0015. The run spent $0.0242 over 50 calls, including voice tests and superseded takes, all ledgered with `vo/log_vo.py`.

**Numbers:**
- `build_data.py` reads `ledger/*.jsonl` and folds every paid line into the on-screen rows.
- **The spoken total must equal the on-screen total** ("thirteen dollars and nineteen cents" = $13.19). build_data.py warns if they differ.
- Adding a narration take changes the ledger, so re-check it and re-record the `total` line if the rounded total moves.

**Your street photo:** put it at `refs/street_photo.jpg` for the "input" thumbnail. It is blurred on screen. Without it the location sheet stands in.

- **Cost:** about $0.02 of narration. Rendering is local.
- **QA:**
  - `render.py` prints a contact sheet (1 frame/s). Check every card for overflow and for the PLACEHOLDER tag (dry run).
  - `reconciliation` in `post2_data.json` must be all true.
  - `total_usd` should match `get_cost_report({scope: "session"})` net.
  - Watch it muted once: every card must read without sound.

## Step 7: Cost ledger conventions

The schema is in `../_shared/skills/video-remake/references/ledger-schema.md`, and the two files are in `ledger/`.

- **One JSON line per `run_capability` call**, including failures, timeouts, QA rejections, refusals ($0) and voice tests. Fields: `ts, phase, session_id, step, capability, model_id, job_id, idempotency_key, inputs, cost_usd, status, duration_s, durable_url, output_url, local_path`.
- `cost_usd` is copied from the run result or `get_create_media`, never estimated. `reserved_usd` holds that were released are never shown on screen.
- `step` carries the verdict in caps, for example `(ACCEPTED -> …)`, `(REJECTED: reason)`, `(REFUSED …)` or `(FAILED …)`. `build_data.py` classifies rows by these words.
- Name steps with stable prefixes (`envsheet…`, `charsheet_v3…`, `char_v3_single…`, `probe…`, `Sound effects: …`, `Narration line '…'`) so rows land on the right screen line.
- Use **one `session_id` for the whole project**, starting with the first sheet call. This run used two (`sheets-freeze-nyc` and `post1-freeze-…`), and the $0.69 of sheets had to be reconciled by hand. That's why the sheets ledger has a `TOTAL` line; don't add TOTAL lines to new ledgers.
- `upload` / `create_upload_url` rows are free and are skipped on screen. **Never** store signed upload URLs or their `authorization` headers.
- At each phase end, run `get_cost_report({scope: "session", session_id, group_by: "capability"})` and compare it with the ledger.

## Final cost: $13.19

| Row on screen | Capability | Calls | Cost |
|---|---|---|---|
| Location sheet (draft + text fix) | gpt-image-edit | 2 | $0.46 |
| Character sheet, from text | gpt-image-edit | 1 | $0.23 |
| Character street photo | nano-banana | 1 | $0.08 |
| Early tests (unused character + scene stills) | gpt-image-edit · nano-banana · kontext-edit · qwen | 31 | $2.23 |
| Seedance test clips (4 s 480p probes) | seedance-25-ref2v | 2 | $1.85 |
| Final 15 s render · 720p | seedance-25-t2v | 1 | $7.45 |
| Sound effects | mirelo-sfx · mirelo-sfx-v2v | 16 | $0.86 |
| Narration voice | inworld-tts | 50 | $0.03 |
| Failed attempts (not charged) | seedance-25-* | 6 | $0.00 |
| **Total** | | **110** | **$13.19** (ledger net $13.1852) |

**Straight-path reproduction** (steps 1–6 with no early tests or probes, one sheet fix, new SFX and narration) costs about **$9.10**:

| Item | Cost |
|---|---|
| Sheets | $0.46 + $0.23 + $0.08 |
| Render | $7.45 |
| SFX | $0.86 |
| Voice | ~$0.02 |

Reusing the published SFX with `fetch_sfx.sh` brings it to about $8.25.
