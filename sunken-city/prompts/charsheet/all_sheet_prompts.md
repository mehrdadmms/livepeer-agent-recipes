# Scene 01 character / environment sheet prompts (GPT Image 2, realism style)

The agent's manifest only kept summaries of the prompts it used; these are the clean, reusable versions written in the style that produced the believable images (no quality words, humble gear, named failures, named wear). Masters are text-to-image (`gpt-image`); details are edits of the master (`gpt-image-edit`, source = master) so light and materials stay locked. Portrait 1024x1536 for masters and full-figure shots, square 1024x1024 for close-ups.

## STYLE BLOCK (append to every above-water prompt)
Candid photo taken on a phone, Kodak Portra 400 look, fine grain, natural colour, slight chromatic aberration at the edges, slightly missed focus, harsh low sun straight into the lens with veiling flare, horizon a degree off level, no fill light. No text, no logos, no signs, no faces. Not a render.

## STYLE BLOCK UNDERWATER (append to every underwater prompt)
Underwater photograph by a scuba diver on a wide GoPro-style action camera in a dive housing, natural light with a small video light, visibility 15-20 m, green-blue cast, backscatter particles lit by the camera, slightly missed focus, dark vignetted corners, fine grain. No text, no logos, no faces. Not a render.

## A · Kid (never show the face)
Identity line to reuse everywhere: a 6-year-old boy seen from behind, blond curly hair whipped by the wind, navy-and-white striped short-sleeve tee half untucked and creased, faded blue jeans rolled to mid-calf and dirty at the knee, barefoot with sand on his feet.

- A1 master (portrait): Low phone photo from 0.4 m above the planks, 1.5 m behind [identity line], mid-sprint down a Victorian seaside pier toward a big Ferris wheel and domed pavilions at the far end, silhouetted against a low orange sun; cream-painted iron railings and lamp posts both sides, peeling paint and rust on the rails, gum and bird droppings on the grey planks, long shadow toward the camera, motion blur on his legs. + STYLE BLOCK
- A2 tee (square, edit of A1): Close-up of the same boy's back at chest height: the striped tee's weave, faded navy dye, a creased hem half untucked, the sleeve edge, curls touching the collar, same low sun rim light. + STYLE BLOCK
- A3 jeans and feet (square, edit of A1): The same rolled faded jeans and bare calves mid-stride on the weathered planks, sand and grit on the soles, dirty rolled cuffs, plank gaps and nail heads, same light. + STYLE BLOCK
- A4 hair (square, edit of A1): The back of the same boy's head: blond curls rim-lit by the sun, flyaway strands, ear, nape, tee collar, background pier falling out of focus. + STYLE BLOCK
- A5 jump (portrait, edit of B1): Keep this exact pier; add the same boy mid-air just past the cream side rail near the far end, tucked cannonball, arms round his shins, back/side-rear view, the Ferris wheel looming behind him against the sun, motion blur on his feet. + STYLE BLOCK
- A6 underwater (portrait, edit of A5): The same boy a moment after entry, sinking feet-down in a ring of bubbles, camera slightly above him, striped tee and jeans dark and wet, curls floating, back to camera, pale surface glare above, blue-green murk below. + STYLE BLOCK UNDERWATER

## B · Pier, above water
- B1 master (portrait): From 0.4 m above the planks looking down a Victorian seaside amusement pier at sunset: long grey timber deck, cream-painted ornate iron railings and lamp posts both sides with peeling chalky paint and rust weeping from the bolts, at the far end a cluster of domed pavilions and a big Ferris wheel silhouetted against the low sun, wide wet sandy beach visible below through the rails, sky deep blue overhead to burning orange at the horizon, a crisp packet and cigarette butts on the planks, tired bulbs in the lamps, a few gulls. + STYLE BLOCK
- B2 planks (square, edit of B1): Close-up of the plank surface: grey weathered grain, gaps, rusted nail heads, dried salt bloom, green algae in the shade, chewing gum, a wet patch reflecting orange. + STYLE BLOCK
- B3 rail and lamp (square, edit of B1): A cream cast-iron railing panel with a lamp post, peeling paint and rust, a rope coil on a mooring post, a plastic bag caught on the rail, sea and sun behind. + STYLE BLOCK
- B4 pier end (portrait, edit of B1): The last planks and the drop to the water beside the pavilions, the sun path on the sea, small waves against tarred iron piles, barnacles at the waterline. + STYLE BLOCK
- B5 sky plate (portrait, edit of B1): Only sky and sea from the pier: sun near the horizon, orange to deep blue, thin cloud glow, no pier. + STYLE BLOCK

## C · Drowned Athens, below water (lights still on)
- C1 master (portrait): Looking along a marble stoa colonnade toward a Parthenon-like Doric temple, 30 m under the sea: fluted columns and pediment, marble gone brown-green with algae, hydroids and sponges, sea urchins in the joints, silt on every ledge, sand between the flagstones, fallen column drums, a snagged fishing net, warm amber light glowing from inside the temple doorway and from bronze lanterns on a few columns, sun rays from the surface, small silver fish. + STYLE BLOCK UNDERWATER
- C2 temple facade (square, edit of C1): The temple front close: fluted Doric columns, the pediment, encrusted marble, urchins, the glowing doorway, a lantern on the nearest column. + STYLE BLOCK UNDERWATER
- C3 fallen statue (square, edit of C1): A toppled marble statue and column drums half buried in silt, a fishing net snagged across them, a lost rope, one lantern glowing in the haze behind. + STYLE BLOCK UNDERWATER
- C4 floor (square, edit of C1): The flagstone floor from 1 m: sand drifts, urchins, a plastic bottle, broken paving, backscatter, a fish crossing. + STYLE BLOCK UNDERWATER
- C5 caryatid porch (square, edit of C1): A porch of caryatid figures encrusted with algae and sponges, a lantern glowing beside them, columns receding into the murk. + STYLE BLOCK UNDERWATER
- C6 ending window (portrait, edit of C1): From 2.5 m outside, one warm lit window in encrusted marble; inside, a person's dark silhouette facing out with one arm raised in a wave, sheer curtains drifting, bubbles on the glass, the glow hazed by particles. This is the last image of the film. + STYLE BLOCK UNDERWATER

## Keyframes (composition-locked)
Same style blocks, with `image_urls` = [previs frame, matching master] and this lead sentence: "Keep exactly this composition and camera: where every column, rail, figure and the window sit in the frame. Make it a new photograph with the same layout, not a retouch: ..." then the scene description.
