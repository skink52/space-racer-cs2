# Space Racer: first test in CS2

Nothing here has run in CS2 yet - the whole build was verified on the mock engine, the bot simulator and
Valve's type declarations. These are the things only the real game can show, in the order to check them.

## A. Hammer

1. Open `maps/mg_space_racer.vmap`. Expect: eight track props in a 4 x 2 grid in the void, each inside a dark
   moondome box; the lobby/booth/cache rooms 12,000 units below; the entities listed in README_SPACE_RACER.md.
2. Check the `point_script` has its script and the `custom_hud_layout` its layout (keys `cs_script`, `layout`).
3. Build. Expect no missing materials (`materials/spr/...`) or models (`models/spr/...`).

## B. First run (listen server, `bot_quota 0`)

1. Console on map load: `[spr] v0.2.0 ready: 8 tracks, HUD on, prop template on`. Any `WARNING` lines matter.
2. Lobby: you should be frozen in the booth looking at a slow turn around the next track from above, with the car picker
   (four cards) and the lobby lines. A / D should move the highlight. `!car 3` should too.
3. After freeze time: `RACE 1: <track> (1)` in chat, a 10-second countdown on the grid, your car on the grid
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

## D. Things to look at and tune

- Speed feel: `CARS[*].maxSpeed`, `RULES.padSpeed`, the camera presets in `CONFIG.CAMERAS`.
- Jumps: `RULES.gravity`, `rampKick`, `airControl`; ramp height `RAMP_H` and gap lengths in `tools/tracks.py`.
- Carnage: `RULES.contactSoft` / `contactMax` / `spinDamage` / `regenRate`; `BOT_SKILL`.
- Race length: `laps` per track in `tools/tracks.py` (or `LAPS` in CONFIG for all), `FINISH_WINDOW`.
- The Pulse: `RULES.pulseEnabled` / `pulseSpeed` / `pulseCharge`.
- Sounds too loud/quiet: `VOL` and `RANGE` in `tools/sounds.py`.

## Known unknowns (only CS2 can answer)

- Whether `Move` on 32 props every tick plus the camera `Move` looks smooth at 1000+ units/s.
- Whether the client interpolates the custom camera in CONTROLLED mode (FreeDM used it for spectators only).
- Whether Panorama renders the HUD as laid out (fonts, bar widths by class, the minimap image per track, the
  picker pictures). `HUD classes not in the css: none` is the mock's check; the look is not.
- Whether `TakeDamage` with `damageTypes: VEHICLE` shows a sensible killfeed icon (FreeDM used BULLET).
- The translucent effects (wreck, warp, the Pulse wave, hover shadow) and the alpha-blended materials.
- Sound spatialisation relative to the custom camera.
