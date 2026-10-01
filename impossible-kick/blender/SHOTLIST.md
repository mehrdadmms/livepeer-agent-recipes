# SEEDANCE_v2 handoff: 08 the impossible kick (30 s, 9:16, 24 fps, hook = frame 96 = 4.000 s)

## 1. Shot summary
One continuous cut-free shot. A street footballer juggles a dented lemon-soda can in a narrow dusk back alley (handheld camera at knee height circling closer), flicks it high, sets up and half-volleys it exactly at 4.0 s with a burst of dust and grit. The can rockets up the alley (a cat on a ledge, a swinging lamp, laundry lines, a burst of pigeons), an FPV drone locks onto the spinning can and rides it over rooftops past cheering kids playing football on a roof, in through an open window, across a lamp-lit room, out the far window, down a football-mad market street (giant painted murals, strings of red-white and blue-yellow fan flags, low banners, lanterns, stalls), up over the dusk city, over the roof of a floodlit stadium and down into the bowl. The can dips under the crossbar, hits it (ring), drops into the net while the keeper dives late. Last image (final 2 s): the net bulging around the can, keeper on the turf, crowd erupting with confetti and flashes.

## 2. Per-segment prompt lines
- 0.0-4.0 ACTION. Camera: handheld, knee height, slow arc from behind-right to beside the player, closing from about 1.2 m to 0.7 m, small breathing shake, tilts up to follow the can when it is flicked (2.4 s) then drops back to boot level. Elements: one footballer seen knee-down and from behind (hooded dark top, worn jeans, football boots and socks, no face shown), a dented drinks can with a red circle logo on teal-and-yellow stripes juggled on the boot instep (taps about every 0.6 s), wet cobbles, brick wall with pink graffiti tag, posters, bins, crates, cables. Lighting: dusk blue hour, warm tungsten wall lamp and window glow, low warm sun raking down the alley, cool sky fill.
- 4.0 HOOK (frame 96). Camera: low, close, at boot level, side-on; boot toe hits the can dead centre, the can dents, dust and grit burst, camera jolts 3 frames then whip-tilts up. Elements: boot, sock, can only. Lighting: as above, warm rim on the dust.
- 4.0-12.0 PAYOFF. Camera: FPV drone locked 0.6 m behind the spinning can, 15-25 m/s, banking, noise shake; alley climb, over rooftops, through an open window (curtains billow), across a room (tea table, pendant lamp swinging), out the far window. Elements: cat on a ledge (near miss), hanging lamp, laundry lines, pigeons bursting off a sill, rooftop with cheering kids in football shirts and a ball, fan flags on their roof line. Lighting: dusk sky, warm interior tungsten, windows lit.
- 12.0-20.0 ESCALATION. Camera: FPV low through the market street at 12-18 m/s at 3 m height with weave, near misses under 0.5 m to low fan banners and lanterns, then a sweeping climb to 40 m over the city at dusk. Elements: giant painted football murals on both walls (red kicker "LOS ROJOS", blue keeper dive "AZUL 09", trophy "COPA", scarf stripes "ULTRAS"), red-white and blue-yellow fan flags strung across the street, produce stalls, string lights, crowds as backs and silhouettes. Lighting: blue hour, warm bulbs and lanterns, glowing windows, red beacons on tall roofs.
- 20.0-25.2 STADIUM. Camera: FPV dives over the stadium roof at 30 m/s into the bowl, past floodlight flare, over the pitch toward the goal, the can grows large in frame. Elements: floodlit stadium, crowd as a lit mass, striped pitch, ad boards (invented sponsors). Lighting: hard white floodlights with visible beams in haze, lens flare, warm crowd glow.
- 25.2-30 ENDING. Camera: chase stops at the crossbar strike; a low camera in front-left of the goal (28-30 mm) holds and slowly pulls back 1.5 m. Elements: the can hits the crossbar (ring, small camera jolt), drops into the net, net bulges with the can in the pocket, goalkeeper (orange kit, black shorts) dives late and lands on the turf, crowd erupts, confetti and phone flashes. Lighting: floodlights, haze. Final image: bulging net with the can in it.

## 3. Refs the next stage needs
Generate (single photo unless noted; Seedance refuses multi-view character sheets):
- can: "dented soda can, red circle logo ZAPPO LEMON SODA on teal and yellow diagonal stripes, scuffed, one side dent", single photo, three-quarter view. Reuse: `assets/textures/can_label.png` (flat label texture) for the design.
- footballer boot + sock + jeans knee-down, single photo, dusty worn boots. Reuse: `assets/models/boot.jpg`.
- alley location: single photo of the brick/plaster alley at dusk with graffiti KIKO. Reuse: v1 draft frame `renders/review/final/c_000.png`.
- rooftop kids in football shirts (single photo, backs and three-quarter views, no clear faces).
- stadium goal at dusk with net, keeper in orange kit (single photo); stadium bowl wide shot floodlit.
- market street with murals: single photo (murals: use `assets/textures/mural1..4.png`).
- v1 refs reusable: `assets/textures/can_label.png`, `assets/textures/graffiti_tag.png`, `poster1-3.png`, `adboards.png`, `mural1-4.png`, `flag_a.png`, `flag_b.png`, `assets/models/boot.jpg`, v1 previs `final_v1_previs_8s.mp4`.

## 4. Hook frame and files
- Hook frame: 96 (4.000 s). Music hit and key SFX both on this frame.
- Previs (video only): `<recipe>/renders/previs.mp4`
- Blurred copy (gblur sigma 2): `<recipe>/renders/previs_blur.mp4`
- Mix: `.../08-impossible-kick/final.mp4`; stems `final_music_only.mp4`, `final_sfx_only.mp4`, `music/music.wav`, `music/sfx.wav`, timestamps `music/sfx.md`.
- Scale note: the can is enlarged 1.6x during the juggle (until frame 60) and grows to 3x for the last 10 s so it reads at goal distance. Describe it as a normal soda can to the model.

## 5. STORY CHANGE (user, 2026-10-01): the city is the stadium
The separate floodlit stadium is OUT. Replace segment 20.0-25.2 STADIUM and the ENDING location:
- 12.0-20.0: as before through the market street, but as the can passes, the street reacts: people stop, turn, climb onto balconies and crowd windows and rooftops like stands, phones up, scarves out.
- 20.0-25.2 STREET-STADIUM: the FPV climbs briefly over the rooftops (packed with fans), rooftop floodlights blaze on one after another, then dives back down into the same mural street, now floodlit, balconies and windows packed, confetti in the beams, toward a full-size goal with a net standing across the far end of the street, the crowd packed around it.
- 25.2-30 ENDING: low camera front-left of that street goal; can hits the crossbar, drops into the net, keeper (orange kit) dives late, street crowd erupts, confetti and phone flashes. Final image: bulging net with the can in it, murals and packed balconies behind.
- Refs: E1 is now "street as stadium" (edit of D1). No stadium bowl, no ad boards.
