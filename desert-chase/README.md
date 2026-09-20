# Desert chase

A 20 s photoreal desert car chase that was never filmed: blocked out as grey boxes in Blender, cut to the beat of the music, then rendered by Seedance 2.5 on the Livepeer agent using the blurred Blender previs as the motion guide and these sheets as the cast.

This folder holds the two things you need to reuse the look: the character sheets and the v1 prompt.

## What is here

| File | What it is |
|---|---|
| `refs/car1_sheet.png` | CAR A, the lead car. Four views on one sheet: A front three-quarter (top left), B side (top right), C rear three-quarter (bottom left), D front (bottom right). |
| `refs/car2_sheet.png` | CAR B, the chaser. Same four views, same order. |
| `refs/env_sheet.png` | The location. A wide (top left), B road level (top right), C aerial (bottom left), D side (bottom right). |
| `prompts/v1_seedance_ref2v_prompt.txt` | The exact five-block call sheet used for the v1 render. |

All three sheets were generated with `gpt-image-edit` from a Blender 2x2 layout of grey-box renders, one call each.

## How the prompt's tags map to the sheets

Seedance's reference check refuses multi-view sheets, so each `@Image` in the prompt is ONE panel cropped out of a sheet, not the whole sheet:

| Tag | Crop |
|---|---|
| `@Image1` | `car1_sheet.png`, panel A (front three-quarter) |
| `@Image2` | `car1_sheet.png`, panel C (rear three-quarter) |
| `@Image3` | `car2_sheet.png`, panel A |
| `@Image4` | `car2_sheet.png`, panel C |
| `@Image5` | `env_sheet.png`, panel A (wide) |
| `@Image6` | `env_sheet.png`, panel B (road level) |
| `@Video1` | the 20 s Blender previs, blurred (`gblur sigma 5`), passed as `video_urls` |

Call shape: `seedance-25-ref2v`, `image_urls` = the six crops in that order, `video_urls` = the blurred previs, `duration: "20"`, `resolution: "720p"`, `aspect_ratio: "16:9"`.

See [`_shared/skills/seedance-video`](../_shared/skills/seedance-video/) for the five-block prompt format, timeouts and the reference-check rules.
