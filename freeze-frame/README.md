# Freeze-frame

A woman in a black leather jacket walks at the camera through a rainy, dystopian 1980s Times Square. She snaps her fingers and the city freezes: people mid-step, rain and pigeons hanging in the air. She sips a frozen stranger's coffee, hands it back, snaps again, and the city crashes back to life.

The piece is one 15-second, ultra-realistic single take made entirely with AI on the Livepeer network. A 66-second narrated "full recipe" video shows every step and every cent.

| | |
|---|---|
| **The shot** | [`outputs/post1_freeze_frame.mp4`](outputs/post1_freeze_frame.mp4): 15.1 s, 1280x720, 24 fps, sound designed and mastered to −14 LUFS |
| **The recipe video** | [`outputs/post2_how_it_was_made.mp4`](outputs/post2_how_it_was_made.mp4): 66.3 s, 1280x720, 30 fps, narrated |
| **Total cost** | **$13.19** over 110 model calls, including every test and failure. Of that, $7.45 is the final render. |
| **Render time** | About 6 min for the 15 s shot |

## How it was made

1. **Location sheet.** GPT Image 2 (`gpt-image-edit`) turns a street photo into a 5-panel dystopian location sheet with invented signage. [$0.46]
2. **Character sheet from text.** GPT Image 2 designs an original woman in 4 views, using the location sheet only for place and light. [$0.23] Nano Banana then makes one street photo of her. [$0.08]
3. **The video prompt.** Five blocks: assets, summary, style, second-by-second plot and hard rules. It is in [`prompts/prompt_v4_t2v.txt`](prompts/prompt_v4_t2v.txt).
4. **Render.** Seedance 2.5 text-to-video, 15 s, 720p, 16:9, audio on. [$7.45]
5. **Sound.** Mirelo makes 15 effects plus a synced foley bed, and ffmpeg mixes and masters them. [$0.86]
6. **Approval.** The AI plans, and a human approves on one sign-off page.
7. **Cost.** Every call is logged in [`ledger/`](ledger/).

The design references are in [`refs/`](refs/): the location sheet, the character sheet and the single photo.

## Reproduce it

Install the folder as a Claude Code skill (see the [repo README](../README.md)). Then ask Claude to "make the freeze-frame video". [`SKILL.md`](SKILL.md) is the step-by-step runbook, with exact capabilities, settings, costs and QA checks. You bring your own street photo.
