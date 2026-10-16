# Space Racer: first test in CS2

Nothing here has run in CS2 yet - the whole build was verified on the mock engine, the bot simulator and
Valve's type declarations. These are the things only the real game can show, in the order to check them.

## A. Hammer

1. Open `maps/mg_space_racer.vmap`. Expect: eight track props in two layers of 2 x 2 boxes (13,800 units each; the
   lower layer around z -5000, the upper around z +3600), each inside a moondome box (no toolsskybox shells any
   more) with a chain of Low vis hints along the road and one Lowest hint over everything; the lobby/booth/cache rooms
   at z -12,000; the entities listed in README_SPACE_RACER.md.
2. Check the `point_script` has its script and the `custom_hud_layout` its layout (keys `cs_script`, `layout`).
3. Build. Expect no missing materials (`materials/spr/...`) or models (`models/spr/...`).

## B. First run (listen server, `bot_quota 0`)

1. Console on map load: `[spr] v0.3.1 ready: 8 tracks, HUD on, prop template on`. Any `WARNING` lines matter.
2. Lobby: you should be frozen in the booth looking at a slow turn around the next track from above, with the car picker
   (four cards) and the lobby lines. A / D should move the highlight. `!car 3` should too.
3. About 2 s after the round starts (mp_freezetime 0): `RACE 1: <track> (1)` in chat, a 10-second countdown on the grid, your car on the grid
   seen from behind and above. Watch for the car model, its side colour (T orange / CT blue), the hover shadow.
4. Drive: W accelerates, A / D steer, Mouse 1 boosts (charge bar drains, flame model), Space drifts, Mouse 2
   spins. Camera: does it lag the car nicely, roll in corners, and never clip through the track? Rails bounce you.
5. HUD: position / lap top-centre, clock top-right, shield + charge bottom-left, speed bottom-right, standings on
   the right, minimap top-left with your dot and the leader's dot. Centre messages: countdown, FINAL LAP, WRONG WAY.
6. Pads: boost pads (orange chevrons) kick; charge platforms (cyan grid) fill charge and shield, with a hum.
7. Finish: "FINISHED 1ST", the car warps out, results after the window, `FireWinCondition` in the console, the CS2
   round ends with a T or CT win.

## C. With bots (`bot_quota 31`)

1. 32 cars on the grid; bots drive, bump, boost and spin. Expect some wrecks (explosion frames, "YOU WRECKED x").
2. Kill credit: when you wreck a bot by an attack, the killfeed shows it at once and your scoreboard kills tick.
   At the end of the race the losers die one every few ticks, credited to the top 3 (console: `CS2 kill: a -> b`).
   Then: does CS2 respawn the killed pawns within a couple of seconds (they must, or the camera is lost for a
   moment - console warns if kills are blocked)?
3. Watch "point_script ... thinking for" in the console; a 32-car arena should cost well under 5 ms per tick.
4. With 33+ players (bots) two arenas run on two tracks; `RACE OVER - <track>: T n - CT m | ...` names the winner.

## C2. Added in session 2 (check these too)

- Lobby: the view circles the next race's track from high up (all of it in view); bottom line says NEXT TRACK.
- Cars are bigger (about 100 units long). Seen from behind they each have their own tail: Hornet twin booms and fins,
  Meteor one big engine under a wide wing, Comet three engines and a tall fin, Bastion four engines under a light bar.
- Camera: default `high` preset sits higher and further back than before and turns into bends, so the track ahead is
  visible a long way off; `!cam` cycles high / far / near. Beacons (tall pylons with glowing caps) line every track,
  and yellow chevron signs on the outside of each real corner point the way.
- Skyway: two jump ramps over open gaps (boost pad before each). Hit one slowly and you drop into the gap.
- Helix: a stacked spiral - the upper deck is 360 units over the lower one. Check the camera on the lower deck.
- Engine hum on human-driven cars (four pitch bands, boosting = highest); jump and landing sounds.
- Loading screen picture, map icon and radar picture should show on the loading screen; copy
  `resource/overviews/mg_space_racer.txt` into the GAME addon folder for the overview position.
- `ARENA_LAYOUT 'alternate'` switches between 2 x 32 and 4 x 16 every round.

## C3. Added in session 3 (the retro / grander pass)

- Music: a chiptune loop in the lobby, a faster one during the race, a short fanfare at the results. Is it audible
  everywhere at the same volume (it should not pan or fade with the camera)? Does it restart cleanly at the end of
  each loop (24.6 s race, 19.2 s lobby)? Too loud: `MUSIC_VOL` in `tools/sounds.py`; off: `MUSIC: false`.
- Every sound effect is new (chiptune). Countdown: two low beeps then a higher one, then GO.
- HUD: all text is the pixel font (white / gold / cyan / red / green / pink). Check the glyphs line up in rows,
  centre messages are centred, and nothing is cut off. If letters come out blurry, the glyph pictures are 60 px
  (`GS` in `tools/hud.py`). Bars are segmented. A faint scanline + vignette overlay covers the screen: `!crt`
  toggles it for you. The lobby shows the SPACE RACER logo.
- Panorama features used for the first time here: `@keyframes` animations (blinking WRONG WAY / FINAL LAP / low
  shield, the pulsing selected car card and logo), `background-repeat: repeat` (scanlines). If the console shows
  CSS errors about them, the HUD still works without the animation.
- Tracks are about twice as big, in two layers. The skies: each track has its own pixel-art panorama on the
  moondome. If a sky shows black or stretched, the moondome shader may want a different texture layout.
- Banked bends: the road leans, the car leans with it (prop roll) and the camera leans 60% as much. If the lean
  looks backwards, flip `PROP_ROLL_SIGN` (cars) or `CAM_ROLL_SIGN` (camera) in CONFIG.
- Tubes (Solar Oval back straight, Hairpin Harbour, Ringworld under the bridge, Spire and Helix descents): the
  camera drops lower inside. Check it never pokes through the roof.
- Scenery: towers, asteroids, crystals, rings, clouds, the synth-grid floor, billboards, the voxel-letter start
  gantry and sector numbers on the checkpoint gates. Watch `cl_showfps` on the busiest views (Solar Oval and
  Hairpin Harbour cities).
- Turbo start: press W on the last beep (inside half a second of GO) - "TURBO START!" and a kick. Hold W from the
  first beep - "TOO EARLY - ENGINE STALLED".
- Camera shake on hits, rail strikes, landings and wrecks (`CAM_SHAKE` 0 turns it off).
- Effects are pixel art now (explosion, warp-out, the Pulse, the hover shadow).
- Lap records: after a race, the lobby's NEXT line shows a record for tracks that have one; chat announces new ones.
- Grid flyover: for the first 6 seconds on the grid the camera swoops low along the track towards the waiting
  field (the start gantry's name reads correctly from that side too), then cuts behind your car 4 seconds before
  the lights (`FLYOVER`, `FLYOVER_CUT`, `FLYOVER_FROM`).
- Results: a pulsing RESULTS banner at the top and a camera circling the start gantry.
- Boosting (or on a pad): flickering pixel speed lines round the edges of the screen.
- Two race songs take turns ("Neon Overdrive", "Starlight Circuit").

## C4. Multiplayer checks (lessons from FreeDM)

- Someone joins mid-race: they watch (Mouse 1 / 2, E) and are on the next grid. If CS2 kicks a bot to make room,
  that bot's car leaves the race. Console: `slot N: <old> -> <new>` when a slot changes hands without a disconnect
  event - the newcomer must never drive the old car or get its kills.
- Knock-out kills mid-race: the wrecked player's pawn should respawn within ~2 s. If not, the console says
  `CS2 did not respawn ... within 8 s`, and after two of those `knock-out kills now wait for the end of each race`
  (the kills are then credited in the end-of-race cascade instead). Check `mp_respawn_on_death_t/ct 1` and plugins.
- Warmup: races run, nothing reaches the scoreboard, and about 20 s after each race the next one starts by itself
  (`warmup: next race without a CS2 round change`). Same fallback if a plugin blocks the round end.
- AFK: only idling while you drive counts (20 s warning, 30 s out). Watching after you finish / wreck, or as a
  late joiner, never marks you AFK. `!afk` sits you out until `!back` or a key.
- CS2 spectators / players not on a team see the lobby lines (no camera of ours without a pawn).
- Panorama: if the console reports CSS errors about `@keyframes`, the HUD still works, just without blinking.

## C5. Fixes from the 17 Oct test (check these first)

Rebuild fully after copying the files (`disconnect`, then load the map again) so the HUD and the script recompile.

- **HUD placement.** Everything should now sit where `preview/hud_race.png` shows it: minimap top-left (all of it,
  with a dot for every car: T orange, CT blue, the leader gold, yours blinking white), position + lap top-centre
  under CS2's own top bar, clock top-right, standings on the right, shield/charge bottom-left and speed
  bottom-right, a little above CS2's money / health row. Cause of the jumble: the HUD root's "Pick" state used the
  same class name as the picker panel, so the whole HUD took the picker's layout. The layout is also fixed-size now.
- **Car picker.** Lobby (`preview/hud_lobby.png`): logo, three lines, then four cards with a picture of each car in
  your side's colour, its perk and five stat bars; A / D moves the gold highlight. Grid (`preview/hud_grid.png`):
  the track name, "YOU START 3RD OF 10 - LIGHTS IN 6", the cards; they go 3 seconds before the lights and the
  bars / speed / standings come back. Watching a race: the cards show for 4 seconds after you press A / D.
- **Countdown.** 3 / 2 / 1 in big red pixel digits in the middle of the screen, then GO!.
- **Cars on the grid.** All cars visible on the grid from the moment the flyover reaches them (they were being
  teleported every tick, which CS2 doesn't draw).
- **Steering.** A turns left, D turns right.
- **Lean.** On a banked bend the car sits level with the road (dips into the inside of the bend) and leans into
  every turn; the camera leans the same way, less. `!tilt` turns the camera lean off for you. If the cars still
  dip the wrong way, set `PROP_ROLL_SIGN: -1`; if only the camera is backwards, `CAM_ROLL_SIGN: -1`.
- **The Pulse** (the wave that sweeps from the back of the field to the front each time the leader starts a new
  lap, topping up everyone's charge): now a low pixel laser fence
  with chevrons on the road under it, instead of a tall see-through sheet that washed out the screen.

## D. Things to look at and tune

- Speed feel: `CARS[*].maxSpeed`, `RULES.padSpeed`, the camera presets in `CONFIG.CAMERAS`.
- Jumps: `RULES.gravity`, `rampKick`, `airControl`, `landSafe`; ramp heights and gap lengths (`jumps`) in
  `tools/trackdefs.py`.
- Banking: `bank` per track in `tools/trackdefs.py`; how much it helps: `RULES.bankGrip` / `bankTurn`.
- Turbo start: `RULES.launchWindow` / `launchKick` / `stallAfter`.
- Carnage: `RULES.contactSoft` / `contactMax` / `spinDamage` / `regenRate`; `BOT_SKILL`.
- Race length: `laps` per track in `tools/trackdefs.py` (or `LAPS` in CONFIG for all), `FINISH_WINDOW`.
- The Pulse: `RULES.pulseEnabled` / `pulseSpeed` / `pulseCharge`.
- Sounds too loud/quiet: `VOL`, `RANGE` and `MUSIC_VOL` in `tools/sounds.py`.

## Known unknowns (only CS2 can answer)

- Whether `Move` on 32 props every tick plus the camera `Move` looks smooth at 1000+ units/s.
- Whether the client interpolates the custom camera in CONTROLLED mode (FreeDM used it for spectators only).
- Whether Panorama renders the HUD exactly like `preview/hud_render.py` lays it out (the 17 Oct fixes below).
  `HUD classes not in the css: none` and `switched HUD classes with a rule of their own: none` are the mock's checks.
- Whether `TakeDamage` with `damageTypes: VEHICLE` shows a sensible killfeed icon (FreeDM used BULLET).
- The translucent effects (wreck, warp, the Pulse wave, hover shadow) and the alpha-blended materials.
- Sound spatialisation relative to the custom camera, and whether the music events stay un-positioned.
- Whether `csgo_moondome` accepts the equirectangular sky pictures as its `TextureCubeMap`.
