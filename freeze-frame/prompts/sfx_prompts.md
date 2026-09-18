# Sound effect prompts (step 5)

Every call below is exactly what was sent to the Livepeer MCP. The prompts, durations and idempotency keys were recovered from the run's tool-call records. Prices come from `ledger/cost_log_post1.jsonl` (phase `P5-sfx`). All calls used `session_id: "post1-freeze-ae42c851-10af-46ca-abd3-c68ab52bef9b"`. Use your own session and keys when you re-run.

`sound/sfx_urls.txt` has the durable URL of every output. `sound/fetch_sfx.sh` downloads them into `sound/gen/` under the file names that `sound/mix.sh` expects.

## One-shots: `mirelo-sfx`

Call shape: `run_capability({capability: "mirelo-sfx", prompt, inputs: {duration: <int seconds>}, session_id, idempotency_key, timeout: 120})`. Use `timeout: 150` for the 15 s bed. It runs sync. Price is $0.0105 per second.

| File in `sound/gen/` | Key | Dur | Cost | Used? | Prompt |
|---|---|---|---|---|---|
| `snap.wav` | `p1-sfx-snap-a1` | 2 s | $0.021 | no (too weak) | A single crisp, sharp finger snap, close-miked, dry studio recording, no reverb, no background noise |
| `citybed.wav` | `p1-sfx-citybed-a1` | 15 s | $0.1575 | yes: bed before and after the freeze | Steady heavy rain falling on a wet city street at dusk, water running in gutters, distant police sirens wailing, murmuring crowd, buzzing electric neon sign hum, low generator drone, 1980s downtown ambience |
| `boots.wav` | `p1-sfx-boots-a1` | 6 s | $0.063 | yes: footsteps in the frozen city | Slow, even footsteps of one woman in leather combat boots walking on wet pavement, light splashes in puddles, close-miked, no other sounds |
| `pigeons.wav` | `p1-sfx-pigeons-a1` | 3 s | $0.0315 | yes: flock at 2.3 s, burst away at snap 2 | A flock of pigeons suddenly taking off, loud flapping wing flutter passing overhead |
| `subboom.wav` | `p1-sfx-subboom-a1` | 4 s | $0.042 | yes: both snaps | Deep cinematic sub-bass boom impact, massive low-frequency thump with a long rumbling tail, trailer hit |
| `whoosh.wav` | `p1-sfx-whoosh-a1` | 3 s | $0.0315 | yes: snap 1 shockwave | Fast powerful air whoosh, a shockwave sweeping past the listener, whoosh by |
| `shimmer.wav` | `p1-sfx-shimmer-a1` | 4 s | $0.042 | yes: snap 1 glass shimmer | Glassy crystalline shimmer, resonant glass ringing and sparkling tinkle, ethereal magical shimmer fading out |
| `tinnitus.wav` | `p1-sfx-tinnitus-a1` | 9 s | $0.0945 | yes, as room tone only. The ring is synthesised (6200 + 6247 Hz sines in `mix.sh`) | High-pitched tinnitus ringing tone in an eerily silent empty space, thin hollow room tone, faint air, nothing else |
| `cup.wav` | `p1-sfx-cup-a1` | 3 s | $0.0315 | yes: clicks for the put-back at 11.05 s | Close-up paper coffee cup crinkle, fingers gripping and handling a paper cup with a plastic lid, quiet room |
| `sip.wav` | `p1-sfx-sip-a1` | 3 s | $0.0315 | yes: sip at 9.6 s | A woman takes one sip of hot coffee from a cup and swallows once, close-miked, intimate, quiet room, no music |
| `revboom.wav` | `p1-sfx-revboom-a1` | 4 s | $0.042 | yes: swell into snap 2 | Reversed cinematic boom: a sucking reverse swell rising fast into a huge heavy bass impact, trailer reverse hit |
| `rushback.wav` | `p1-sfx-rushback-a1` | 4 s | $0.042 | yes: city returns at snap 2 | Loud rush of wind whooshing in as a busy rainy city street slams back to life: traffic, car horns, crowd roar, rain, sirens |
| `tail.wav` | `p1-sfx-tail-a1` | 4 s | $0.042 | yes: under the fade | Low ominous sub-bass drone rumble, dark cinematic tail slowly fading out to silence |
| `cup2.wav` | `p1-sfx-cup-a2` | 2 s | $0.021 | yes: cup taken at 8.72 s | Loud close-up crinkle of a paper coffee cup being squeezed and lifted, cardboard cup creak and plastic lid click, foley |
| `snap2.wav` | `p1-sfx-snap-a2` | 1 s | $0.0105 | yes: BOTH snaps | One loud sharp finger snap, very crisp high click, close-up foley, the snap happens right at the start |

## Synced foley bed: `mirelo-sfx-v2v`

| File | Key | Dur | Cost | Prompt |
|---|---|---|---|---|
| `v2v.mp4` → `v2v.wav` | `p1-sfx-v2vbed-a1` | 15 s | $0.1575 | Rainy city street foley: boot footsteps on wet pavement synced to the walking woman, rain, crowd, pigeon wings, paper cup handling. No music. |

Call shape: `run_capability({capability: "mirelo-sfx-v2v", source_url: <public URL of the RAW Seedance render>, prompt, inputs: {duration: 15}, session_id, idempotency_key, timeout: 150})`. The output is a video. Pull its audio out with `ffmpeg -i v2v.mp4 -vn -c:a pcm_s16le v2v.wav` (44.1 kHz mono). Don't pass `image_url`: the capability doesn't declare it and drops it with a warning.

## Totals

There were 16 calls: 15 one-shots and 1 v2v bed. They cost **$0.861**, shown as $0.86 on screen. Two takes went unused: `snap` a1 and the tinnitus ring, of which only the room tone was kept. The first cup take (a1) was too quiet for the grab, so a second take (a2) covers it and a1 supplies the put-back clicks.

## Lessons for the next run

- Short, very specific one-shots ("the snap happens right at the start", 1 s) line up better than long takes.
- Ask for the dry source ("close-miked", "no reverb", "nothing else"). The space, echo and ducking are added in `mix.sh`.
- Mirelo would not give a clean high ring. Synthesise tonal elements locally.
