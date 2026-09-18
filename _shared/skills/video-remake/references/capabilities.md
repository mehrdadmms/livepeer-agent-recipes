# Livepeer capabilities and quirks for this pipeline

Verified on 2026-09-18 (first run). Prices, SLAs and health drift: the planner must re-run `describe_capability` for every capability it picks and update the table in PLAN.md §2. When a verified key below disagrees with `describe_capability`, the key below is what actually ran.

## Global rules

- **Livepeer MCP only.** Never the fal-ai or higgsfield MCP servers. Livepeer capabilities with a fal upstream (nano-banana, kling, music…) are fine.
- **`run_capability.timeout` is in SECONDS.** Size it to the capability's p95 plus margin (a 15 s Seedance take has p95 ≈ 400 s; pass `680` for `seedance-25-ref2v`, `610` for `seedance-25-t2v`), matching the `seedance-video` skill. A timeout below the real runtime still bills and returns nothing.
- `async: true` plus polling `get_create_media({job_id})` for anything with p95 > 90 s.
- Pass `session_id` (the project session) and a fresh `idempotency_key` per attempt on every call.
- On 503 "no capacity": wait 60 s and resubmit with a **new** idempotency key. At most 2 Seedance jobs at once.
- **Durable URLs only downstream.** Hand later steps the `durable_url` from `persist: true` / `upload` (`https://agent.livepeer.org/a/…`), never a raw provider URL (`fal.media`, etc.), which expires. `persist`/`upload(source_url)` can fail with 413 on videos over a few MB: then download the file locally and re-host it with `create_upload_url` (signed PUT), and log that URL as the durable one.
- Every capability input URL must be public https. Local files go through `upload_image` (≤10 MB), `upload` or `create_upload_url`.
- `spend_cap({action:"read"})` before any video render. Only the user can authorise `spend_cap({action:"set", …})`, and it goes on the sign-off page as a quick decision.

## Table

| Step | Capability | Verified inputs | Price (09-18) | p95 → timeout (s) |
|---|---|---|---|---|
| Char/env sheets from refs | `gpt-image-edit` (GPT Image 2) | `prompt`, `source_url`, `inputs.image_size:"1536x1024"`, `inputs.quality:"high"` | $0.23/img | p95 ~110 s → `310`, async |
| Scene stills (multi-ref) | `nano-banana` | `prompt`, `inputs.image_urls:[char, env, …]` | $0.084/img | 27 s → `60` |
| Identity fix on a still | `kontext-edit` | `prompt`, `source_url` | $0.042/img | 30 s → `61` |
| Hero video, multi-ref | `seedance-25-ref2v` | `prompt`, `inputs.image_urls[]` (≤30), `duration` STRING "4"–"30", `resolution` "480p"/"720p" (always pass it), `aspect_ratio`, `generate_audio` | $0.2315/s @480p, $0.4967/s @720p | p95 ≈ 400 s for 15 s → `680` (t2v: `610`), async |
| Hero video from one keyframe | `seedance-25-i2v` | `prompt`, `source_url`, `inputs.end_image_url`, same others | same | 442 s → `600`; was 73 % success, failures billed |
| Cheap draft / overflow | `seedance-mini-ref2v`, `seedance-mini-i2v` | same shape, duration ≤ "15", no audio | $0.162/s | 240 s → `390` |
| Exact keyframes fallback | `flux-3-keyframes` | `prompt`, `inputs.keyframes:[{image_url, frame_index}]`, `duration` int 5–20, `resolution:"720p"` | $0.1785/s | 330 s → `685` |
| Video QA | `nemotron-omni-video` | `prompt`, `inputs.video_url` (NOT `source_url`) | ~$0.01/call | 6 s |
| Image QA / OCR | `nemotron-omni-vision` | `prompt`, image URL (check describe) | ~$0.01 | fast |
| SFX bed | `mirelo-sfx-v2v` | `prompt`, `source_url` (video), `inputs.duration` int | $0.0105/s | 85 s → `115` |
| Mix | `ffmpeg-audio-mix` | `inputs.tracks:[{url, volume, delay_ms}]` (≤8, mp4 OK); amix halves levels, so use volume ≈2 on each of 2 tracks | ~$0 | 6 s |
| Put audio on video | `ffmpeg-mux` | `inputs.video_url`, `inputs.audio_url`. **Replaces** audio; `mode:"mix"` is silently ignored, so pre-mix first | ~$0 | 9 s |
| Trim | `ffmpeg-trim` | `source_url`, `inputs.start_sec` + exactly one of `end_sec` / `duration_sec` | ~$0 | 16 s |
| Concat | `ffmpeg-concat` | `inputs.clips:[urls]`; keeps audio, normalises resolution; was degraded (65 %), so retry with a new key | ~$0 | 26 s |
| Export | `ffmpeg-export` | `inputs.preset` ∈ instagram-square, instagram-portrait, tiktok-portrait, youtube-landscape, youtube-shorts, twitter, 720p, 1080p, mp3, aac, wav; use `async:true` | ~$0 | 42 s |
| Narration (if any) | `inworld-tts` | `prompt`, `inputs.voice:"Mortimer (en)"` style | $0.0105/1k chars | 4 s (avoid `gemini-tts`: degraded, 15× price) |
| Music bed (optional) | `music` | `prompt` | $0.0315/track | 119 s → `700` |
| Transition | `flux-3-transition` | `inputs.start_image_url`, `end_image_url`, `duration` int ≥ 5 | — | — |
| i2v alternative | `kling-o3-i2v` | `source_url`, `inputs.duration` string; follows image aspect; can stretch characters late in a clip, so trim the drifted tail | — | — |

## Character consistency (hard rule)

- Lock one master per character (the approved sheet). Derive every keyframe by editing locked masters; never re-describe the character in text beyond Seedance block 1.
- `gpt-image-edit` is best for sheets and material changes on a multi-view sheet. `kontext-edit` preserves identity best for pose, expression and lighting edits of one frame. `nano-banana` sheet edits broke badly on an earlier project; use it for new multi-ref compositions only, and QA every output against the master.
- QA every keyframe and every clip visually before moving on.

## Seedance specifics

- Write the prompt with the `seedance-video` skill's five-block call sheet. Blocks 1, 3 and 5 stay word-for-word identical across draft, retries and final; fixes go into block 5 as rules.
- Tag spelling: the API schema uses `@Image1`, ByteDance's page `[Image1]`. The 480p draft doubles as the binding probe: if it ignores the references, rerun the draft once with `[ImageN]`.
- `generate_audio:false` does not reduce the price, so leave it on and steer the sound in block 5.
- Video references (`video_urls`) bill input + output duration; use image refs unless you need motion transfer.
