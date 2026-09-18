---
name: seedance-video
description: Write and run Seedance 2.5 video generations with a five-block "call sheet" prompt (asset binding, summary, style, shot-by-shot plot, locked requirements) through the Livepeer MCP, with a 4s probe, async polling, durable URLs and a failure log. Covers single continuous takes and MULTI-SHOT sequences (several hard cuts inside one render, e.g. a chase, fight, reveal or trailer beat), where Claude turns a loose brief into a slot-by-slot call sheet. Use when the user asks for a Seedance video, a long continuous take (10-30s), a multi-reference scene where a cast, product or location must stay consistent, an action or trailer-style clip with cuts, or when a Seedance render keeps failing the same way (including likeness/moderation refusals) and credits are burning. Triggers on "seedance", "seedance 2.5", "make a seedance video", "reference to video", "one continuous take", "write me a seedance prompt", "multi-shot seedance", "seedance sequence", "hard cuts in one generation", "fill the seedance template", "write the call sheet for me".
---

# Seedance 2.5 — the five-block prompt

Consistent Seedance output comes mostly from prompt structure, not from rerolling. Write every prompt as a **call sheet**: cast, location, look, scene breakdown, and the notes nobody may ignore. Five blocks, always in this order, always labelled.

Source: ByteDance's Seedance documentation as summarised by @buck.the.aikami (Instagram, Sept 2026), extended with Livepeer parameter details.

Files in this skill:
- `references/multishot.md`: multi-shot sequences (several hard cuts in one render): intake, per-slot fill rules, camera vocabulary, two-person workarounds, QA by cut. Read it whenever the clip has cuts, or the user gives a rough idea and wants Claude to write the whole prompt.
- `templates/multishot-callsheet.txt`: the slot-by-slot template for multi-shot call sheets.

## Hard rules

1. **Livepeer MCP only.** Never use the fal-ai or higgsfield MCP servers. Livepeer capabilities with a fal upstream are fine.
2. **`timeout` is in SECONDS, not milliseconds.** A 15 s take has a p95 of about 400 s. Pass the ceiling: `680` for `seedance-25-ref2v`, `610` for `seedance-25-t2v` (check `describe_capability` for i2v and mini). Always run `async: true` and poll `get_create_media({job_id})` every 10–20 s. An undersized timeout still bills and returns nothing.
3. **`duration` is a STRING**: `"4"`–`"30"` (mini ≤ `"15"`). Never pass `"auto"` (billed per second, unpredictable length).
4. **Always pass `resolution` explicitly**: `"480p"` ($0.2315/s) or `"720p"` ($0.4967/s). The default differs between the docs and the dispatcher.
5. **Probe first:** a 4 s, 480p call (~$0.93) with the real blocks 1, 3 and 5 before any long render. It tests binding, moderation and the look before you spend $5–15.
6. **Durable URLs only.** Pass `persist: true` and hand downstream steps the `agent.livepeer.org/a/…` URL, never a provider URL. If persist fails (413 on large files), download the file and re-host it with `create_upload_url`.
7. **Character drift is a hard fail.** QA every shot against the locked reference.

## Likeness check (ref2v refusals)

`seedance-25-ref2v` runs a provider likeness check on `image_urls` and refuses with `moderation_blocked` / `content_policy_violation` / `partner_validation_failed`, even for fully AI-generated people:
- **Multi-view character sheets are refused** (turnarounds, headshot grids, 4-panel full-body). Pass ONE single full-body photo per character, made from the approved sheet with `nano-banana` (~$0.08). Keep sheets for approval and QA only.
- **Two person refs in one call are refused**, even when each passes alone. One person photo + location/prop refs is the only known-good ref2v shape.
- **The check is unpredictable.** An image pair that passed a 4 s probe was refused in a 15 s run with the full five-block prompt and audio. A passing probe does not guarantee the full render. Don't iterate on refusals; log the job IDs and escalate to the Livepeer team.

**Reliable fallback: `seedance-25-t2v`, text-only call sheet.** Write the same five blocks with no images:
- Block 1 lists every character, location and prop as a text-only entry with a handle and a full looks / behaves / sounds description (`REZA (no image) — CHARACTER: mid-30s courier, short black hair, stubble, olive bomber jacket…`).
- Blocks 2–5 refer to each asset by that handle ("REZA", "THE ALLEY") exactly where you would have written `@Image1`. Never re-describe it outside block 1.
- Keep block 1 word-for-word identical across every call so the description is the lock. Expect looser identity than ref2v, so favour medium and wide framings for characters and QA harder.
- Other text-safe option: build a keyframe with `nano-banana` and animate it with `seedance-25-i2v` (see `references/multishot.md`, two-person option C).

## The five blocks

### 1. Asset binding
List every uploaded reference. For each one give:
- **Tag** — the positional handle the model uses: `@Image1`, `@Image2`, `@Video1`, `@Audio1` (order = order in `image_urls` / `video_urls` / `audio_urls`). For t2v, a text handle instead (see above).
- **Role** — character reference, location reference, prop reference, style plate, motion reference, rhythm reference.
- **Description** — how it *looks*, how it *behaves* (gait, temperament, how it moves), how it *sounds* (voice, material noise).

Everything later in the prompt refers to assets **only by tag**, never by a fresh description. A second description is a second, drifting interpretation.

### 2. Summary
Two or three lines covering the whole scene: who, where, what happens, the emotional beat. The model uses this as its anchor and keeps returning to it, so make it complete but short. No camera detail here.

### 3. Style
Camera (lens feel, handheld vs locked, format), lighting, theme/genre, colour grade, texture (film grain, photoreal, anime). This block keeps the first and last frames looking like the same film. Keep it the same, word for word, across every shot of a sequence.

### 4. Detailed plot
The real work. Break the take into beats, either by shot or by timestamp (`0–3s`, `3–7s` …). For each beat state:
- the opening framing and angle,
- the camera motion,
- exactly what happens: action, dialogue (in quotes), and sound.

Timestamps must add up to the `duration` you pass. One main action per beat; don't cram. For hard cuts inside one render, follow `references/multishot.md`.

### 5. Overall requirements
The non-negotiables for the whole video, for example:
- audio rules (`no music, SFX only`, `dialogue in Persian only`),
- what must stay locked (`@Image1's face, hair and jacket identical in every frame`, `no cuts, one continuous take`),
- banned elements (`no text, no logos, no subtitles`),
- **every failure from the previous attempt, written as a rule.**

**This is where you save credits.** Don't reroll a failed generation with the prompt unchanged. Name what broke and add it here as a constraint (`@Image2 stays in the right hand throughout; it must not duplicate or vanish`). Keep this list across iterations; it's the project's failure log.

## Template (single continuous take)

For multi-shot sequences use `templates/multishot-callsheet.txt` instead.

```
[ASSETS]
@Image1 — CHARACTER: <name>. <looks>. <behaviour>. <voice>.
@Image2 — LOCATION: <place>. <key features, time of day>. <ambient sound>.
@Image3 — PROP: <object>. <material, size>. <sound it makes>.

[SUMMARY]
<2–3 lines: who, where, what happens, emotional beat.>

[STYLE]
<camera/lens, movement philosophy>. <lighting>. <theme/genre>. <grade>. <texture>.

[PLOT]
0–3s: <framing + angle>. <camera move>. <action / "dialogue" / sound>.
3–7s: ...
7–12s: ...

[REQUIREMENTS]
- <audio rule>
- <what stays locked>
- <banned elements>
- <fix from last attempt>
```

## Running it on Livepeer

Run `describe_capability` (free) once per session before your first call, because parameter contracts, prices and SLAs drift.

| Need | Capability | Key inputs |
|---|---|---|
| Multiple locked assets (one person max, plus location / product / props) | `seedance-25-ref2v` | `prompt`, `image_urls[]` (≤30), optional `video_urls[]`, `audio_urls[]` |
| Animate one locked keyframe, optionally landing on an end frame | `seedance-25-i2v` | `prompt`, `source_url`, optional `end_image_url` |
| No references, or ref2v refused on likeness | `seedance-25-t2v` | `prompt` (text-only call sheet) |
| Cheap draft at lower cost ($0.162/s, ≤15 s) | `seedance-mini-ref2v`, `seedance-mini-i2v`, `seedance-mini-t2v` | same shape, check with `describe_capability` |

Shared inputs (see Hard rules):
- `duration`: string, matched to your plot timestamps.
- `resolution`: always explicit.
- `aspect_ratio`: `auto | 21:9 | 16:9 | 4:3 | 1:1 | 3:4 | 9:16`.
- `generate_audio`: default `true`. Turning it off does **not** reduce the price, so leave it on and use block 5 to control what you hear.
- Call-level: `async: true`, `timeout` in seconds (680 ref2v, 610 t2v), `persist: true`, `session_id`, and a fresh `idempotency_key` per attempt.

Every URL must be public https. Upload local files with `upload_image` (≤10 MB) or `create_upload_url` first.

**Reference tags:** the API schema uses `@Image1`, while ByteDance's model page writes `[Image1]`. On a new project, use the 4s/480p probe to confirm which spelling binds, then stick with it.

**Video references cost extra:** with a `video_urls` reference, billing covers input + output duration at a multiplier. Use image refs unless you actually need motion transfer.

**Capacity:** run at most 2 Seedance jobs at once. On 503 "no capacity", wait 60 s and resubmit with a new idempotency key.

## Workflow

1. **Lock the assets first.** Character sheets, product shots and location plates must be final before any video call. If a character must hold across shots, follow the character-consistency workflow: drift is a hard fail. Derive single-photo cast refs from the sheets.
2. **Write the five blocks.** Show the user the full prompt and the cost line (`probe 4s@480p $0.93 → full {d}s@{res} ${d × rate}`) before spending anything above a draft. At ~60 % measured ref2v success, budget ~1.7× for the final.
3. **Probe.** 4 s at 480p, blocks 1, 3 and 5 unchanged, block 4 cut to the first beat and retimed to 0–4s. Check bindings and moderation. If refused on likeness, switch to the t2v text-only call sheet rather than rerolling.
4. **Draft cheap.** 480p, shortest duration that still covers the beats. Check the plot and the bindings, not polish.
5. **QA the result.** Pull frames at each beat boundary (ffmpeg or `nemotron-omni-video`) and check each against the assets: identity, wardrobe, props, location, audio rules, beat timing.
6. **Fix via block 5, not by rerolling.** Write every defect into REQUIREMENTS (or tighten the matching PLOT beat), then rerun. Only reroll unchanged when the failure is clearly random noise and not a repeatable misread.
7. **Final at 720p** once a draft passes. Reuse the exact same prompt text.
8. **For sequences**, keep blocks 1, 3 and 5 identical across shots and only change 2 and 4. Consistency across a sequence comes from shared blocks, not from luck.

## Worked example

```
[ASSETS]
@Image1 — CHARACTER: Reza, mid-30s courier. Short black hair, stubble, olive bomber jacket, grey backpack. Moves fast, economical, glances over his shoulder. Low calm voice.
@Image2 — LOCATION: narrow bazaar alley at dusk. Hanging fabric, brass lamps, wet stone floor. Distant crowd murmur, clinking metal.
@Image3 — PROP: small wooden box with brass clasp, palm-sized. Clicks when opened.

[SUMMARY]
@Image1 hurries through @Image2 clutching @Image3, stops under a lamp, checks he isn't followed, and opens the box — relief on his face.

[STYLE]
35mm handheld, shallow depth of field, follows at shoulder height. Warm tungsten practicals against cool blue dusk. Grounded thriller. Teal-orange grade, light film grain, photoreal.

[PLOT]
0–4s: medium-wide from behind @Image1 entering @Image2. Handheld follow. Footsteps on wet stone, crowd murmur.
4–8s: camera swings to a frontal medium as he stops under a brass lamp. He looks back over his shoulder. Murmur drops.
8–12s: slow push to close-up on hands. He opens @Image3 — brass clasp click. Tilt up to his face: exhale, faint smile.

[REQUIREMENTS]
- No music. Diegetic SFX only. No dialogue.
- @Image1's face, hair and jacket identical in every frame.
- @Image3 stays in his hands the whole time; it never duplicates or disappears.
- One continuous take, no cuts.
- No text, signage in Latin script, logos or subtitles.
```

Call: `seedance-25-ref2v`, `image_urls: [reza_fullbody.png, alley.png, box.png]` (Reza as one single photo, not a sheet), `inputs: { duration: "12", resolution: "480p", aspect_ratio: "9:16", generate_audio: true }`, `async: true`, `timeout: 680`, `persist: true`, then poll `get_create_media`. That comes to ~$2.78 for the draft and ~$5.96 for the 720p final, after a ~$0.93 probe.

If ref2v refuses Reza, rerun on `seedance-25-t2v` (`timeout: 610`) with block 1 rewritten as text-only entries (`REZA (no image) — CHARACTER: …`, `THE ALLEY (no image) — LOCATION: …`, `THE BOX (no image) — PROP: …`) and every `@ImageN` in blocks 2–5 replaced by that handle.
