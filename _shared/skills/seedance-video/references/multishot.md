# Multi-shot call sheets (hard cuts inside one render)

Read this when the clip has several shots with hard cuts (a chase, fight, reveal or trailer beat in one 8–15 s generation), or when the user gives only a rough idea and wants Claude to write the whole prompt. The Hard rules, the likeness check and the Livepeer call shape in `../SKILL.md` all apply here; this file adds:
1. The **slot-level template**: what goes in each block, field by field (`../templates/multishot-callsheet.txt`).
2. **Multi-shot cutting inside one render**: several hard-cut shots, each with its own camera move.
3. **Claude as the prompt writer**: the user gives a rough idea, and Claude fills every slot, then shows the prompt and its cost.

Source: Buck (@buck.the.aikami), "Seedance 2.5 prompt structure", Instagram, 2 Sept 2026. https://www.instagram.com/p/Dcx_cj2t4MM/ He built it from ByteDance's "Dreamina Seedance 2.5 prompt guide" on BytePlus ModelArk, plus his own 1,000+ generations. The Livepeer lessons are ours. The post uses 3-view character sheets; that works on ByteDance's own app, **not on Livepeer** (see the likeness check in `../SKILL.md`).

## 1. Intake: turn a brief into a beat list

Ask only for what's missing, in one message:
- **cast** (ref photo or sheet), **location** (plate or description), **props** that must hold their design
- **story in one sentence**: who does what to whom, and how it ends
- **length** (8–15 s is the multi-shot sweet spot), **aspect**, and the **audio rule** (music? SFX only? dialogue?)

Then plan the beats yourself:
- **Shots = duration ÷ 2–3 s.** A 10 s clip holds 4 shots, a 15 s clip 5–6. The post plans 8 shots; at Livepeer prices keep to ≤ 6 per render, or split into two renders that share blocks 1, 3 and 5.
- Shot 1 is always an **establishing move** that places every asset in the location. The last shot **closes** the action; don't end mid-gesture.
- Alternate subjects between cuts (her, him, her, both). Each shot gets **one** action and **one** camera move.

## 2. Fill the slots

Copy `../templates/multishot-callsheet.txt` and fill every `{placeholder}`. What each slot needs:

**Block 1, Asset binding.** One entry per ref, in `image_urls` order (on t2v, text-only entries with handles instead of tags):
- `@imageN — {ROLE}, {NAME}.` Role is `CHARACTER REFERENCE`, `LOCATION REFERENCE` or `PROP REFERENCE`, and the name is a short handle ("THE WOMAN'S MOTORCYCLE").
- **Looks:** concrete, visual, head to toe (or front to back for a prop). Colours, materials, distinguishing marks.
- **Behaves:** one short clause of temperament or motion ("rides loose, unbothered, arrogant", "predatory focus"). For locations, the ambient motion (heat haze, blowing grit).
- **Sounds:** `Sound: …` for every asset, including props and locations. These lines become the SFX track, so they are how you get the right audio with `generate_audio` on.
- **Location only:** end with a scope line, like the post's "Drives terrain, colour, atmosphere and light throughout."
- **Ownership:** props say who owns them and where they sit ("clipped to the strap across her torso").

**Block 2, Summary.** 2–3 lines. Bind every noun to its tag with "the {noun} from @imageN" ("The woman from @image2 rides the green bike from @image4…"). State the ending explicitly ("…fires and misses"). No camera language here.

**Block 3, Style.** This formula, in prose:
- **Camera:** medium/format + lens family + **lens per shot type** ("wide lenses for the chase, long lens with shallow depth of field for close-ups")
- **Lighting:** key (direction, hardness) + practicals + shadow behaviour
- **Theme:** genre, mood, era, and "live-action" or "animated"
- **Grade:** palette + contrast + texture (grain, halation, flare, HDR)
- A **feel line** ("kinetic, weighty, practical — real vehicles at real speed") and a **realism line** ("photographic realism throughout")

**Block 4, Detailed plot.** Use timestamps, not "Shot N" labels, because the timestamps must add up to `duration`. Every beat follows this order:
`{start}-{end}s: {"Hard cut." except beat 1} {shot size} {angle}, {camera move}. {subject by tag} {one action}. {environmental motion}. {sound cue tied to a block-1 Sound}.`
- Reference assets by tag plus a short reminder ("the chrome bike from @image6"). Don't re-describe them.
- Put a micro-performance in the close-ups ("her jaw sets", "one quick look back — unhurried, dismissive").
- Build sound through the beats ("the whine climbs", "a rising charge whine builds"), so the audio has an arc.

**Block 5, Overall requirements.** Always use these four labelled lines:
- `Audio:` e.g. "No music, SFX only."
- `Keep constant:` identity + wardrobe per character, who stays on or with which prop, grade, grain, lens character, time of day **across all {N} shots**, and **"every shot carries a distinct camera move"**.
- `Strictly avoid:` headcount lock ("one woman and one man only — no other riders, vehicles or people"), warped geometry ("no warping of wheels, frames or limbs"), text and watermarks, and cuts you didn't write.
- `Fix from last run:` empty on the first render. After that, add every defect as a rule.

Add a **physics line** when anything heavy moves: "suspension compresses, tyres deform, dust behaves as heavy particulate". Add an **outcome line** for any effect whose result matters ("the laser bolt is bright saturated green and clearly misses").

## Camera and motion vocabulary (from the post)

| Use | Phrase |
|---|---|
| Establishing | "high aerial perspective sweeping down across {location}", then "camera dives and levels out into a fast low tracking shot alongside" |
| Speed close-up | "tight close-up, camera travelling backward in front of {subject} at {their} own speed" |
| Side-by-side | "medium shot, camera tracking laterally alongside {subject}" |
| Menace / hero | "medium-close from a low front three-quarter angle" |
| Cut | "Hard cut." as the first words of the beat |
| Lens logic | wide for chase and scale, long lens + shallow DOF for faces and standoffs |
| Motion texture | "rooster tails of {colour} dust", "hair streams straight back in the wind", "heat haze shimmering off the ground" |

## Two-person scenes (Livepeer workaround)

The post binds two characters in one render. On Livepeer ref2v that gets refused. Pick one of these:
- **A. One hero ref.** Pass the hero's single photo + location + props. Describe the second person fully in block 1 **as a text-only entry** (`THE MAN (no image) — …`). Keep their shots medium or wide, so a small drift isn't a hard fail. Cheapest option, but ref2v can still refuse the hero ref unpredictably on the long render.
- **B. Split by subject.** Cut the sequence into renders that each carry one person ref, with blocks 1 (for that render), 3 and 5 word-for-word shared. Assemble with `ffmpeg-concat`.
- **C. Keyframe + i2v.** Build a two-shot keyframe with `nano-banana` multi-ref (QA it against both masters), then animate it with `seedance-25-i2v` (`source_url` = keyframe). Best identity, but only one composition to start from.
- **D. Text-only t2v (most reliable).** Run `seedance-25-t2v` with every character, location and prop written as a text-only block-1 entry, and handles in place of `@imageN` in blocks 2–5. No likeness check to fail; identity rests on block 1 staying word-for-word identical, so QA harder.

Prop and location sheets (multi-view vehicles, weapons) have not been seen to trigger the likeness check, but the probe confirms it.

## 3. Show, then run

1. Show the user the full prompt and a cost line before any paid call: `probe 4s@480p $0.93 → full {d}s@{res} ${d × rate}`. At 60 % measured ref2v success, budget ~1.7× for the final.
2. Upload local refs (`upload_image` ≤ 10 MB, else `create_upload_url`) and confirm every URL is public https.
3. Probe:
   ```
   run_capability({
     capability: "seedance-25-ref2v",
     prompt: "<blocks 1,2,3,5 unchanged; block 4 = beat 1 only, retimed 0-4s>",
     inputs: { image_urls: [...], duration: "4", resolution: "480p", aspect_ratio: "{ar}", generate_audio: true },
     async: true, timeout: 680, persist: true,
     session_id: "{project}", idempotency_key: "{project}-probe-1"
   })
   ```
   (On t2v: drop `image_urls`, `timeout: 610`.) Poll `get_create_media({job_id})`. Check that each tag bound to the right asset. If the refs were ignored, switch `@image1` to `[Image1]` and probe once more. If refused on likeness, go to option D rather than rerolling.
4. Full render: the same call with the full block 4, `duration: "{d}"`, and a **new** idempotency key. Draft at 480p, and go to 720p only after the 480p pass clears QA, reusing the exact prompt text.
5. Run at most 2 Seedance jobs at once. On 503 "no capacity", wait 60 s and resubmit with a new idempotency key.

Other lanes: `seedance-25-i2v` (keyframe start, optional `end_image_url`, p95 ≈ 442 s, 73 % success), and `seedance-mini-ref2v` / `-i2v` / `-t2v` ($0.162/s, ≤ 15 s, timeout 390 s). Run `describe_capability` (free) once per session, because prices and SLAs drift.

## 4. QA the shots, then write the fixes into block 5

- Find the cuts with `ffmpeg -i out.mp4 -vf "select='gt(scene,0.3)',showinfo" -f null -` and compare them to your beat timestamps.
- Grab the middle frame of each shot and check it against the refs: face, hair, wardrobe, prop design, headcount, which prop belongs to whom, grade, and time of day. Listen for music leaks and missing SFX.
- Rewrite every defect as a rule under `Fix from last run:` (e.g. "the man's bike keeps its solid chrome disc front wheel in every shot; it never becomes spoked"). Or tighten the one beat that misread. **Never reroll with the prompt unchanged** unless the failure is clearly random.
- Keep blocks 1, 3 and 5 word-for-word across the probe, retries, the final, and later sequence parts. Only 2 and 4 change.

## Don'ts

- Don't describe an asset anywhere except block 1.
- Don't put two camera moves or two actions in one beat, or beats shorter than ~2 s.
- Don't leave cuts implicit. Write "Hard cut." or "continuous" so the model doesn't invent cuts.
- Don't skip the Sound lines; they are free audio direction.
- Don't pass character sheets or two person photos to ref2v on Livepeer.
