# Explainer: "the full recipe" (Post 2)

The output is a 16:9 1280x720 30 fps H.264 + AAC video, 66.3 s long, narrated. It is published as `../outputs/post2_how_it_was_made.mp4`. Everything on screen comes from `post2_data.json`, and `build_data.py` writes that file from the recipe folder.

## Re-render (no manual edits)

```
cd freeze-frame/explainer
python3 vo/process_vo.py      # downloads the narration takes (durable URLs in vo/lines.json), trims them, atempo 1.15
python3 render.py             # -> post2_final.mp4 + post2_final_contact.jpg
```

You need python3 with `playwright` (`pip install playwright && playwright install chromium`), Pillow and ffmpeg. The local ffmpeg doesn't need drawtext, because all text is HTML.

`render.py` runs these steps:
1. **Brand.** It uses the shipped Livepeer wordmark and badge in `assets/brand/`.
2. **Approval.** It uses the shipped sign-off page captures in `assets/approval/`. If you build your own page, save it as `approve/freeze-frame-signoff.html` and it is re-captured with Playwright.
3. **Data.** It runs `build_data.py` and writes `post2_data.js`.
4. **Clip.** It turns `../outputs/post1_freeze_frame.mp4` into a JPG sequence in `assets/clip/`.
5. **Frames.** It captures one frame per `render(t)` call in headless Chromium, into `frames/`.
6. **Audio.** It synthesises a bed with ticks, whooshes and a thump on the template's cues. It lays the narration on its cues and ducks the bed by 10 dB under speech. It ducks the clip's own audio under the hook and outro. It then runs a two-pass loudnorm to −14 LUFS / −1.5 dBTP.
7. **Encode.** H.264 CRF 18 yuv420p, AAC 192k.
8. **Contact sheet.** One frame per second.

Other entry points:
- `python3 build_data.py` checks the numbers without rendering.
- `python3 render.py --preview 3 12.5 40` writes single PNG frames for a layout check.

## Where the content comes from (paths relative to `freeze-frame/`)

| What | Source | Notes |
|---|---|---|
| Cost rows, total, call count | `ledger/cost_log*.jsonl` | Retries fold into their parent row. Moderation refusals go on a $0 "not charged" row. Rows are rounded by largest remainder so they add up exactly to the ledgers' net `cost_usd` ($13.19). |
| Prompt blocks and key lines | `prompts/prompt_v4_t2v.txt` | The 5 `[BLOCK]` headers are parsed and the key lines are chosen by keyword. |
| Recipe cards (steps 1–2) | `prompts/envsheet_prompt*.txt`, `charsheet_v3_prompt.txt`, `char_v3_single_prompt.txt` | The first line of each file is `capability \| source \| settings \| $` metadata. The rest is the prompt text. |
| Sound card | `prompts` + the `Event times (s):` header line in `sound/mix.sh` + the `P5-sfx` ledger rows | |
| Final clip | `outputs/post1_freeze_frame.mp4` | The hook starts at 3.2 s and the outro at 9.0 s (`clip.hook_start_s` / `outro_start_s` in build_data.py). |
| Sheets | `refs/envsheet_v1.jpg`, `refs/charsheet_v3.jpg`, `refs/char_v3_single.jpg` | |
| Input street photo | `refs/street_photo.jpg` (you supply it, not shipped) | It is blurred (`ENV_BLUR_PX`) so real brands don't show. Without it the location sheet stands in, so the published version differs on this one thumbnail. |
| Narration | `vo/lines.json` → `vo/proc/*.wav` | Voice `Dennis (en)` on `inworld-tts`, atempo 1.15. Each card lasts its line + 0.15 s (0.05 s lead, 0.10 s tail), so there's no dead air. |
| On-screen copy | `text` in build_data.py, `CAPS` / `STEP_TABS` in template.html | Keep lines short. |

## Rules

- **The spoken total must equal the on-screen total.** build_data.py prints `WARN spoken total …` if the `total` line in `vo/lines.json` doesn't say `total_spoken`. If the ledger changes, write a new line (for example "Total: thirteen dollars and nineteen cents."), run it through `inworld-tts`, put the URL in `vo/lines.json` and run `vo/log_vo.py` to bill it into the ledger. The total then moves by a fraction of a cent, so re-check it.
- Before publishing, check that `reconciliation` in post2_data.json is all true, and compare `total_usd` with `get_cost_report(scope=session)`.
- **Never show the unused first character.** The "Early tests" row has no thumbnail, and only the part of the sign-off page from "The plan" down is shown.
- **Dry run.** Until a billed final Seedance line exists in a ledger, the final row uses the `est` value, marked PLACEHOLDER in magenta, and the clip is a looping still of the location sheet.
