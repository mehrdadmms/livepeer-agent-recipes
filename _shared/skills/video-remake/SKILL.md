---
name: video-remake
description: Take a reference video (typically a viral AI-video showcase) and produce a new version with a different character, setting or mood and output spec, plus a companion "how it was made" explainer post showing the inputs, prompt structure, human sign-off step, every model and its real cost. Runs a repeatable multi-agent process on the Livepeer MCP (planner, sheet maker, style analyst, then production agents) with one ADHD-friendly approval page and a cost ledger. Use when the user shares a video and says "remake this video", "recreate this with a different character", "do this video differently", "make our own version of this", or "remake + how it was made".
---

# Video remake + "how it was made"

You are the **orchestrator**. You dispatch sub-agents, merge their reports, build the sign-off page, record decisions and talk to the user. You make no generation calls yourself. Keep chat replies short: the user has ADHD, so ask only what is missing, and show approvals as one page.

References (read when you reach that step):
- `references/briefs.md`: copy-paste sub-agent briefs with `{placeholders}` and the common header
- `references/plan-template.md`: PLAN.md skeleton, including the ROLES section
- `references/qa-checklist.md`: per-phase QA, including the stand-alone and no-source rules
- `references/ledger-schema.md`: `cost_log.jsonl` format and reconciliation
- `references/capabilities.md`: verified Livepeer capability keys, prices, timeouts and quirks
- `scripts/intake.sh`, `scripts/fill_signoff.py`, `scripts/ledger.py`; `assets/signoff_template.html`, `assets/signoff_example.json`

## Hard rules

1. **Livepeer MCP only.** Never the fal-ai or higgsfield MCP servers. Livepeer capabilities with a fal upstream are fine.
2. **Seedance refuses character SHEETS.** `seedance-25-ref2v` blocks multi-view character sheets (turnarounds, headshot grids, even 4-panel full-body) as "likeness of real people" (`moderation_blocked`, `partner_validation_failed`), even when the face is fully AI-generated. Feed Seedance ONE single full-body photo of the character, made from the approved sheet with `nano-banana` (~$0.08). Keep the sheet for approval and QA only. Run a 4s 480p probe (~$0.93) before the 15s render. The check is unpredictable (a pair that passed the probe was refused at 15 s); if ref2v refuses, fall back to `seedance-25-t2v` with a text-only call sheet, per the `seedance-video` skill's likeness section.
2b. **Character drift is a hard fail.** Lock the sheets, derive every frame by editing locked masters (`gpt-image-edit` for sheets, `kontext-edit` for single-frame fixes), and QA every still and every clip against the sheet.
3. **`run_capability` timeout is in SECONDS**, sized to p95 (a 15 s Seedance take has p95 ≈ 400 s; pass `680` for `seedance-25-ref2v`, `610` for `seedance-25-t2v`), with `async: true` and `get_create_media` polling. Same rule as the `seedance-video` skill.
4. **Durable URLs only.** Downstream steps get `persist`/`upload` URLs (`agent.livepeer.org/a/…`), never provider URLs. If a large video fails with 413, save it locally and re-host it with `create_upload_url`.
5. **Param quirks** are in `references/capabilities.md` (for example: mux replaces audio, amix halves levels, `nemotron-omni-video` takes `inputs.video_url`, `duration` is a string for Seedance).
6. **No real brands** in any output, and no source-platform or tool branding.
7. **Never reveal the source.** Final outputs (both posts, captions, and anything shown inside the explainer, including the sign-off page) contain no source frames, no source prompt, no source branding, and no words like "remake", "recreate", "inspired by" or "original video". Internal docs (PLAN.md, briefs) may reference the source. `fill_signoff.py` refuses such words. Keep the page lede neutral: "{project title}: {one-line concept}".
8. **Each post stands alone** without a caption and with the sound off.
9. **Budget checkpoint.** Every paid call goes into `cost_log.jsonl` with the shared `session_id`. Pause and report at the checkpoint (about 70 % of the hard stop, and always before the first 720p render). Never pass the hard stop. Only the user can raise the Livepeer spend cap.

## 1. Intake

1. Create `{project_dir}` (default: the session scratchpad) and a session id: `echo "{slug}-$(uuidgen | tr A-Z a-z)" > {project_dir}/SESSION_ID`.
2. `bash ~/.claude/skills/video-remake/scripts/intake.sh <video-or-URL> {project_dir}/intake 2` gives the probe, contact sheet, scene cuts, 2 fps frames, waveform and silences.
3. Look at `contact.jpg` and `waveform.png`, and read the frames that carry on-screen prompt text (this is the OCR step: there is no tesseract, so read the frames yourself or use `nemotron-omni-vision`).
4. Tell the user in ≤6 lines: the beats with timestamps, the sound design, and the spec.
5. Ask only for what is missing, in one message:
   - the new character (sheet or reference photo),
   - the setting and mood (sheet or reference photo),
   - the output spec (aspect and resolution),
   - the post count (default: 2, the video plus the explainer),
   - an example explainer post whose style they like, if they have one.

## 2. Define roles (before any dispatch)

Write the ROLES section of `{project_dir}/PLAN.md` (skeleton in `references/plan-template.md`) and show the user a 4-line version:
- **You provide:** character sheet or ref photo, environment sheet or ref photo, a style example for the explainer, and approvals at each gate (plus any spend-cap change).
- **The orchestrator (me):** dispatches, merges, builds the sign-off page and talks to you. No generation.
- **Sub-agents:** a planner (plans, no spend), a sheet maker, a style analyst, then stills, video and explainer agents.
- **Gates:** sheets + plan → scene stills → final video → explainer numbers.

## 3. Parallel sub-agents (one message, three Agent calls)

Fill the briefs from `references/briefs.md` (common header + role brief):
- **(a) Planner** with `model: "fable"`. Recovers the original prompt, writes the new five-block Seedance call sheet (defers to the `seedance-video` skill), picks capabilities via `describe_capability`, and writes the pipeline, gates, QA and budget (expected, worst, hard stop) into PLAN.md. No paid calls.
- **(b) Sheet maker.** Builds the char + env sheets from the user's refs with `gpt-image-edit` (GPT Image 2), QAs identity, removes real brands, and logs every run to the ledger.
- **(c) Style analyst.** Downloads the example post (`yt-dlp`, or `api.fxtwitter.com/{user}/status/{id}` for X) and writes `ANALYSIS.md` plus a faster, simpler `POST2_SPEC.md`.

Wait for all three. Don't redo their work. Check their outputs against the QA checklist.

## 4. Sign-off page (one page, Gate A)

1. Copy `assets/signoff_example.json` to `{project_dir}/approve/signoff.json` and fill it:
   - one sheet entry per sheet, with the sheet maker's watch-outs as `note`,
   - the plan in ≤5 lines, with gates marked `"gate": true`,
   - cost tiles: spent (from `ledger.py summary`), expected, worst, and hard stop with the pause point,
   - the explainer beat sheet in one row,
   - ≤5 quick decisions, each with a default preselected (the planner's §9, plus the spend cap if it has to rise).
2. `python3 scripts/fill_signoff.py signoff.json signoff.html`, then publish it with the Artifact tool (`icon: "check"`). Tell the user: "Defaults are set. Press Copy my answers and paste here."
3. When the SIGN-OFF block comes back, write `{project_dir}/DECISIONS.md` (one line per answer, plus any change the user typed). Apply it:
   - "Redo" on a sheet sends it back to the sheet maker with the note.
   - Update the PLAN budget and the explainer spec.
   - Set the spend cap only if the user approved it.

## 5. Production (sub-agents, from `references/briefs.md` d–e)

1. **Scene stills.** `nano-banana` multi-ref from the durable sheet URLs; use 2 agents in parallel if there are ≥4 beats. QA them, make a contact sheet, then **⛔ user gate** (a short page or the contact image with 1-line questions).
2. **Before any video render:** `spend_cap({action:"read"})` and `ledger.py summary --cap … --pause …`. If the checkpoint is hit, pause and report the spend so far.
3. **Draft.** Seedance at 480p, max 2 attempts; defects go into block 5 as rules, never an unchanged reroll. Then the **720p final** with the same prompt text. **⛔ user gate** on the final (show the draft too if it saves a 720p attempt).
4. **Audio.** Keep native Seedance audio if it hits every sound beat; otherwise `mirelo-sfx-v2v` → `ffmpeg-audio-mix` → `ffmpeg-mux`.
5. **Export** to the spec. Keep a muted copy and beat-boundary frames for the explainer.
6. After each phase: save `get_cost_report({scope:"session", session_id, group_by:"capability"})` and run `ledger.py check`.

## 6. Explainer post (brief f)

An educational "how it was made" video built from Post 1's assets; no new generation beyond an optional music bed. Beats: the result → the inputs (the sheets) → the prompt structure explained (the five blocks) → **the sign-off page itself**, captured with Playwright, and the human-in-the-loop step → each model with its cost, failed runs as their own line → the total → the result and the end card.

Render path: an HTML `render(t)` → Playwright screenshots per frame → ffmpeg libx264. The local ffmpeg has **no drawtext**, so all text goes in the HTML. Figures come only from `ledger.py receipt` and must match the session report to the cent. **⛔ user gate** on the numbers and script before the full render.

Template: a Post 2 template is being finalised at `/private/tmp/claude-501/-Users-mehrdad-Work-livepeer-livepeer-agent-mcp/09733e1f-3ac0-4be9-b523-b7bce31b2781/scratchpad/post2/`. Copy it into `assets/post2/` once it is final. Until `assets/post2/` exists, build from the style analyst's `POST2_SPEC.md`.

## 7. Deliver

Send the user:
- both files (paths and durable URLs),
- the receipt: the `get_cost_report` total versus expected,
- one line per post confirming it stands alone and shows no source or brand.

Append new failures to `references/capabilities.md` if a capability quirk was learned.
