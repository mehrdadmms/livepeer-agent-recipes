# Sub-agent brief templates

Copy a brief, replace every `{placeholder}`, and paste it as the Agent tool `prompt`. Prepend the common header to every brief. Placeholders used throughout:

| Placeholder | Example |
|---|---|
| `{project_dir}` | `~/Work/…/remakes/freeze-frame` (or the session scratchpad) |
| `{project_title}` | `Freeze Frame` |
| `{session_id}` | `post1-freeze-ae42c851-…` (generate once with `uuidgen`) |
| `{ledger}` | `{project_dir}/cost_log.jsonl` |
| `{skill}` | `~/.claude/skills/video-remake` |
| `{intake_dir}` | `{project_dir}/intake` (output of `scripts/intake.sh`) |
| `{char_refs}` / `{env_refs}` | the user's reference photos or sheets (paths or URLs) |
| `{character_brief}` / `{setting_brief}` | the user's words for the new character / setting and mood |
| `{output_spec}` | `16:9, 1280x720 @30, 15 s, AAC audio` |
| `{style_example}` | URL or file of the user's example explainer post |
| `{hard_stop}` / `{pause_at}` | `$35` / `$25` (and `{hard_stop_num}` / `{pause_at_num}` = `35` / `25` for the script flags) |
| `{post_count}`, `{budget_hint}`, `{style_verdict}` | from intake answers |
| `{signoff_html}` | the filled sign-off page, e.g. `{project_dir}/approve/signoff.html` |

---

## Common header (prepend to every brief)

```
PROJECT: {project_title}. Project dir: {project_dir}. Save every file you produce under it.
SESSION: pass session_id="{session_id}" on EVERY run_capability call.
LEDGER: append one line per run_capability call (including failed, timed-out and QA-rejected runs)
to {ledger}, format in {skill}/references/ledger-schema.md. Helper:
  python3 {skill}/scripts/ledger.py add {ledger} --phase … --step … --capability … --cost … --status …
cost_usd comes from the run result or get_create_media, never an estimate.

HARD RULES
- Livepeer MCP only (mcp__livepeer__*). Never the fal-ai or higgsfield MCP servers. Livepeer
  capabilities with a fal upstream are fine.
- run_capability timeout is in SECONDS, sized to the capability's p95 (read describe_capability
  before the first call to any capability). async:true + poll get_create_media({job_id}) when p95 > 90 s.
- New idempotency_key per attempt. On 503 "no capacity": wait 60 s, resubmit with a NEW key.
  At most 2 Seedance jobs in flight.
- Downstream steps use durable URLs (persist:true / upload → https://agent.livepeer.org/a/…), never
  raw provider URLs. If persist fails with 413 on a large video, save locally and re-host with
  create_upload_url.
- Character drift is a HARD FAIL. Build from the locked sheets by editing; never re-describe the
  character in text to fix drift.
- No real brands, logos or trademarks in any output. No trace of the source video in any output:
  no source frames, source prompt, source platform/tool branding, and no words like "remake",
  "recreate", "inspired by". Each deliverable must stand alone without a caption.
- Budget: stop and report if {ledger} total reaches {pause_at}; never exceed {hard_stop}.
  Check with: python3 {skill}/scripts/ledger.py summary {ledger} --cap {hard_stop_num} --pause {pause_at_num}
- Verified capability keys and quirks: {skill}/references/capabilities.md. QA: {skill}/references/qa-checklist.md.
- QA before you report. Your report: file paths, the ledger lines you added, spend so far,
  defects found (written as rules the next attempt can use), and anything the user must decide.
```

---

## (a) Planner — `model: "fable"` (no paid calls)

```
You are the PLANNER for {project_title}. Make NO paid calls: only describe_capability, get_pricing,
list_capabilities, get_cost_report and spend_cap({action:"read"}).

Inputs:
- Reference video analysis in {intake_dir}: probe.txt, contact.jpg, scenes.txt, waveform.png,
  audio_stats.txt, frames/f_###.png (read the frames that carry on-screen prompt text).
- New character: {character_brief}. Refs: {char_refs} (the sheet maker is turning these into a sheet
  in parallel; assume a multi-view turnaround sheet at {project_dir}/sheets/charsheet_v1.png).
- New setting / mood: {setting_brief}. Refs: {env_refs} (→ sheets/envsheet_v1.png).
- Output spec: {output_spec}. Post count: {post_count} (Post 1 = the new video, Post 2 = the
  "how it was made" explainer, built from Post 1's assets).
- Budget guidance: {budget_hint}.

Do:
1. Recover the original prompt verbatim from the on-screen text (OCR by reading the frames; note which
   frames). Write the beat map with timestamps and the sound-design beats. This section is INTERNAL.
2. Write the new Seedance call-sheet prompt: read ~/.claude/skills/seedance-video/SKILL.md and follow
   its five blocks exactly (if the source has hard cuts, also read references/multishot.md and
   templates/multishot-callsheet.txt in that skill). Keep the source's beat structure and sound design, swap character,
   setting and mood, and match {output_spec}. Block 5 bans text, logos, real brands and subtitles.
3. Pick Livepeer capabilities with describe_capability (read the parameters, price, p95 and success
   rate; rank on effective_cost_usd). Start from {skill}/references/capabilities.md and correct it
   where today's describe output differs. Timeouts in SECONDS.
4. Decide one take vs multiple shots, with a fallback ladder.
5. Write the pipeline with ⛔ user gates (sheets → stills → draft/final → explainer numbers), the QA
   checks per phase (specialise {skill}/references/qa-checklist.md for this concept), and the budget:
   expected, worst case (assume the measured failure rate on every video step) and a hard stop, plus a
   pause-and-report checkpoint. Read spend_cap and get_cost_report(24 h) and say whether the cap
   must be raised before the video render.
6. List the assets Post 1 must leave for Post 2 and the cost-capture contract.
7. Fill §8 with the concrete values for each production brief, and §9 with ≤5 open questions for
   the user, each with a recommended default.

Write {project_dir}/PLAN.md using the skeleton in {skill}/references/plan-template.md, keeping the
ROLES section the orchestrator already wrote. Report: the path, the 5-line plan summary, the budget
numbers (expected / worst / hard stop / pause), and the open questions with defaults.
```

## (b) Sheet maker

```
You are the SHEET MAKER for {project_title}. Make a character sheet and an environment sheet from the
user's references with gpt-image-edit (GPT Image 2) on Livepeer.

Inputs: character refs {char_refs}; brief "{character_brief}". Environment refs {env_refs}; brief
"{setting_brief}". Output aspect of the final video: {output_spec}.

1. Upload each local ref (upload_image ≤10 MB, else create_upload_url). Log the uploads (cost 0).
2. describe_capability gpt-image-edit. Then:
   - Character: source_url = the character ref. Prompt for a turnaround sheet on a plain grey
     backdrop: 4 full-body views (front, 3/4, side, back) on top, 3 face close-ups (front, 3/4,
     profile) below. Same person as the reference: keep face, age, hair, skin and build exactly. Name
     every garment and colour. No text, labels, logos or brand marks anywhere.
     inputs.image_size "1536x1024", inputs.quality "high", timeout 310, async.
   - Environment: source_url = the env ref. A 5-panel location sheet (one wide establishing panel and
     four detail panels) in the requested mood: {setting_brief}. All signage invented; no real
     brands, venues or trademarks; no garbled pseudo-text. No prominent faces.
3. persist every output → durable_url. Save locally as sheets/charsheet_v1.png and
   sheets/envsheet_v1.png (keep rejected attempts as *_rejected_attemptN.png).
4. QA per {skill}/references/qa-checklist.md "Sheets": crop the faces into qa/char_faces.png and
   compare; read every sign in the env sheet. If a real brand or garbled text appears, fix it with a
   gpt-image-edit pass on that sheet (keep everything, replace named signs with invented names). If
   identity drifts between views, regenerate. Max 3 paid runs per sheet before reporting.
5. Report: both paths + durable URLs, the garment list, identity notes (which views to trust),
   every rejected attempt and why, and the ledger lines. These notes go on the sign-off page.
```

## (c) Style analyst (no paid calls)

```
You are the STYLE ANALYST for {project_title}. The user's example of the explainer style they like:
{style_example}. The user's verdict on it: "{style_verdict}" (e.g. "70% good, needs to be faster and
simpler").

1. Download it into {project_dir}/style/:
   - X/Twitter: curl -s https://api.fxtwitter.com/{user}/status/{id} > post.json (text, author,
     media URLs); then yt-dlp -o style/ref.mp4 "{style_example}". Save the post text to post_text.txt.
   - Anything else: yt-dlp. A local file: copy it.
2. Run {skill}/scripts/intake.sh style/ref.mp4 style/intake 2. Build a 1 fps contact sheet and pull
   keyframes at each visual change. Measure: total length, seconds per beat, seconds with no visual
   change, when the result first appears and how big, whether costs/models are shown, VO/subtitles,
   typography, palette (hex), motion style, audio bed.
3. Write style/ANALYSIS.md (what works, what is slow, with timestamps) and style/POST2_SPEC.md: a
   FASTER, SIMPLER spec for our explainer at {output_spec}. The spec must cover, in order: result
   hook → inputs (the sheets) → the prompt structure explained (the five blocks, one line each) →
   the sign-off page and the human-approval step → each model with its cost, failed runs as their
   own line, running total → big total → result + end card. For each beat: time range, what is on
   screen, motion. Also: palette, fonts (bundle them locally), audio plan, readable muted, no VO
   unless asked, data file shape (post2_data.json), and the render method (HTML render(t) →
   Playwright frames → ffmpeg; local ffmpeg has NO drawtext).
4. Report: both paths, a one-row beat sheet (time: what) for the sign-off page, and the palette.
```

## (d) Stills (scene keyframes) — split beats across 2 agents if there are ≥4

```
You are STILLS agent {agent_letter} for {project_title}. Make these scene keyframes at {output_spec}
aspect: {beats_for_this_agent} (from PLAN.md §4 Phase 2).

Refs (durable URLs, in this order): char sheet {char_url}, env sheet {env_url}{extra_refs}.
Call: nano-banana, prompt + inputs.image_urls:[char, env, …], timeout 60. Describe the scene, pose,
camera and light; refer to the character only as "the person in the first reference image", never
re-describe them.
QA each still against the sheet (front view + close-ups): face, hair, eye colour, every garment;
setting vs env sheet; no text. Drift → kontext-edit on that still (max 2 edits), else regenerate.
Save stills/kfN_vM.png, persist → durable URLs, and a contact sheet stills/contact_{agent_letter}.png.
Report paths, durable URLs, per-still QA verdict, and ledger lines.
```

## (e) Production video — draft, final, audio, export

```
You are the VIDEO agent for {project_title}. Phase: {phase} (draft | final).

Prompt: {project_dir}/prompt/seedance_v{N}.txt (five blocks; do not edit blocks 1-4 or reword 3).
Refs (durable URLs, in this order): {ref_urls}.
Before any render: spend_cap({action:"read"}) and ledger.py summary; if the render would cross
{pause_at} or the cap, STOP and report instead.

Draft: {video_capability} with prompt, inputs.image_urls, duration "{duration}", resolution "480p",
aspect_ratio "{aspect}", generate_audio true, timeout 680 (610 for seedance-25-t2v), async true, persist true. Max 2 attempts: before attempt
2, add every defect to block 5 as a rule and save as seedance_v{N+1}.txt. If the draft ignores the
refs, retry once with [ImageN] tags instead of @ImageN.
Final (only after the user approved the draft): the same prompt text, resolution "720p".

Then:
1. Save locally (video/draft_vN.mp4 or video/post1_final.mp4), re-host for a durable URL.
2. QA per qa-checklist.md "Video" (1 fps frame strip, waveform, silencedetect, nemotron-omni-video
   yes/no checklist with inputs.video_url, ffprobe).
3. Audio (final): if the native Seedance track hits every sound beat in PLAN §0, keep it. Otherwise
   mirelo-sfx-v2v (prompt = the sound-design sentence) → ffmpeg-audio-mix (seedance ≈2.0 + sfx ≈1.4)
   → ffmpeg-mux (mux REPLACES audio, so mix first).
4. Export to {output_spec} with ffmpeg-export (preset per capabilities.md, async) if ffprobe differs.
5. Deliver post1_final.mp4, post1_final_muted.mp4, and frames at the beat boundaries in
   video/frames/ for the explainer.
Report paths, durable URLs, QA results (pass/fail per check), updated block 5, ledger lines, spend.
```

## (f) Explainer ("how it was made", Post 2)

Run as two agents in parallel once Post 1 is signed off: F1 numbers, F2 build. Or one agent if the spec has no narration.

```
You are the EXPLAINER agent ({F1 numbers | F2 build}) for {project_title}. Spec:
{project_dir}/style/POST2_SPEC.md. Template: {skill}/assets/post2/ (if it exists; otherwise build
from the spec). Output: {output_spec}, readable with the sound off, no caption needed.

F1 numbers:
1. Save get_cost_report({scope:"session", session_id:"{session_id}", group_by:"capability"}) and
   group_by:"status" to {project_dir}/cost/. Run ledger.py check against it.
2. ledger.py receipt {ledger} --out post2/receipt_lines.json. Failed/timed-out/rejected runs are their
   own line; the total includes them and equals the session report (or write the delta + cause into
   post2/receipt_derivation.md and put it on screen). Quote to the cent.
3. Write post2/post2_data.json: {steps:[{label, capability, cost_usd, thumb}], failed:{n, cost_usd},
   total_usd, n_calls, prompt_blocks:[{name, one_line}], signoff_png, result_frames:[…]}.
   Model names appear only as plain capability names.

F2 build:
1. Capture the sign-off page (the human-in-the-loop beat): open {signoff_html} with Playwright at
   1280x720 and at 390 px width; screenshot the full page and the SIGN-OFF block with the defaults
   selected → post2/signoff_*.png. Check it contains nothing that reveals a source video.
2. Build post2/index.html exposing a deterministic render(t) that draws the frame for time t from
   post2_data.json. Bundle fonts locally and await document.fonts.ready.
3. Pre-extract Post 1 to a JPG sequence (local ffmpeg). Python Playwright: for each frame,
   page.evaluate("render(t)") then screenshot → frames/%05d.png. ffmpeg -framerate 30 → libx264
   yuv420p. The local ffmpeg has NO drawtext, so all text lives in the HTML.
4. Audio: Post 1's audio under the result beats, a low bed (optional `music`, logged) under the rest,
   mixed locally with amix, then muxed.
5. QA per qa-checklist.md "Explainer post": 6 sampled frames read at 640 px wide, every figure vs
   receipt_lines.json, ffprobe. Deliver post2/post2_final.mp4 + the frames.
```
