# Desert chase

A 20 s photoreal desert car chase that was never filmed: blocked out as grey boxes in Blender, cut to the beat of a music track, then rendered by Seedance 2.5 on the Livepeer agent with the blurred Blender previs as the motion guide and three character sheets as the cast.

Everything needed to make it again is here: the Blender scripts, every prompt exactly as sent, the sheets and reference images, the motion references and the assembly scripts. **Start with [`SKILL.md`](SKILL.md)**, the step-by-step runbook.

| Folder | What's in it |
|---|---|
| `blender/` | Previs pipeline: scene, beat detection, export, review render, sheet layouts. |
| `prompts/` | Sheets, probe, 20 s render, head-on patch, engine sound, the two shot fixes. |
| `refs/` | Sheets, Blender layouts, the six `@Image` crops, the `@Video1` motion reference, fix inputs. |
| `scripts/` | Layouts, reference crops, fix references, soundtrack, frame-accurate assembly. |

## How the prompt's tags map to the sheets

Seedance's reference check refuses multi-view sheets, so each `@Image` is ONE panel cropped out of a sheet:

| Tag | File | Crop |
|---|---|---|
| `@Image1` | `refs/image1_car_a_front34.jpg` | `car1_sheet.png`, top left |
| `@Image2` | `refs/image2_car_a_rear34.jpg` | `car1_sheet.png`, bottom left |
| `@Image3` | `refs/image3_car_b_front34.jpg` | `car2_sheet.png`, top left |
| `@Image4` | `refs/image4_car_b_rear34.jpg` | `car2_sheet.png`, bottom left |
| `@Image5` | `refs/image5_location_wide.jpg` | `env_sheet.png`, top left |
| `@Image6` | `refs/image6_location_road.jpg` | `env_sheet.png`, top right |
| `@Video1` | `refs/video1_motion_ref20.mp4` | the 20 s Blender previs, 640x360, blurred |

Not included: the music (bring your own track; the cuts follow its beats) and the rendered video.
