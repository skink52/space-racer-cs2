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
   (four cards) and the lobby lines. A / D should move the highlight. `!car 3` should too. Once you have picked, the
   cards go away; `!car` brings them back (see C6).
3. About 2 s after the round starts (mp_freezetime 0): `RACE 1: <track> (1)` in chat, a 10-second countdown on the grid, your car on the grid
   seen from behind and above. Watch for the car model, its side colour (T orange / CT blue), the hover shadow.
4. Drive: W accelerates, A / D steer, Mouse 1 boosts (charge bar drains, flame model), Space drifts, Mouse 2
   spins. Camera: does it lag the car nicely, roll in corners, and never clip through the track? Rails bounce you.
5. HUD: position / lap top-centre, minimap top-left with a dot for every car and the clock under it, standings on
   the right, shield + charge over the speed bottom-right. Centre messages: countdown, FINAL LAP, WRONG WAY.
   CS2's chat (bottom-left) and kill feed (top-right) have nothing of ours under them.
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
- Turbo start: press W on the third beep (the higher one) and hold it - "TURBO START!" and a kick. Hold W from the
  first beep - "TOO EARLY - ENGINE STALLED". (The window used to be the last 0.45 s; see C6.)
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
  with a dot for every car: T orange, CT blue, the leader gold, yours blinking white) with the clock under it,
  position + lap top-centre under CS2's own top bar, standings on the right, shield/charge over the speed
  bottom-right, a little above CS2's money / health row. Cause of the jumble: the HUD root's "Pick" state used the
  same class name as the picker panel, so the whole HUD took the picker's layout. The layout is also fixed-size now.
- **CS2 chat stays readable** (`preview/hud_cs2.png` marks CS2's own places). Say something in chat while racing,
  on the grid and in the lobby: the lines bottom-left should have nothing of ours behind them (in the lobby the
  last five or six lines show under the cards; with chat open the box covers the first card's corner, which is
  fine). Wreck someone: the kill feed top-right has nothing of ours under it either. `!cam` in the lobby now
  answers on the bottom line.
- **Car picker.** Lobby (`preview/hud_lobby.png`): logo, three lines, then four cards with a picture of each car in
  your side's colour, its perk and five stat bars; A / D moves the gold highlight. Grid (`preview/hud_grid.png`):
  the track name, "YOU START 3RD OF 10 - LIGHTS IN 6", and a row of four small cards bottom-right (the flyover's
  view of the field stays clear, and chat too); they go 3 seconds before the lights and the bars / speed /
  standings come back in the same corner. (Since then the cards only come up by themselves until you have picked a
  car or raced once - see C6.)
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
- **Crosswire's crossing** (the pink figure-8; `preview/chase_crosswire.png`). No level crossing any more (the two
  decks z-fought and each road's rails ran across the other): the second pass climbs into a full banked spiral loop
  round the middle, and the first pass dives under it twice, threading through the loop just after the start.
  Check: no flicker or rails across the road anywhere; the camera stays clear under the decks (try `!cam far`);
  bots get round the loop; the results camera rises over the loop as it circles the start. This one changes the
  map file (the track model and its vis hints), so compile the map in Hammer after copying.

## C6. Loading screen and car picker (17 Oct, evening)

- **Loading screen.** Four slides now (`preview/loading_all.png`); CS2 never shows a map's loading picture when it
  has only one, which is why there was none before. While the map loads they change every 4 seconds, starting on a
  random one. The logo and the CONTROLS panel (driving keys, watching keys, chat commands) stay put; the panel under
  it changes (cars, tracks, how to win, what is on the track). CS2's own column on the right (map name, icon,
  loading bar) should cover only sky, never text; on a 4:3 screen nothing of ours should be cut off at the sides.
  The slides compile along with the HUD (the first load after copying compiles them, so they show from the second
  load on): `game\csgo_addons\mg_space_racer\panorama\images\map_icons\screenshots\1080p\` should then hold
  `mg_space_racer_png.vtex_c` and `mg_space_racer_1_png.vtex_c` to `_3_png.vtex_c`.
- **Car picker.** First time in the lobby the cards are up; pick with A / D and they go 6 seconds after your last
  press. From then on they stay away - in the lobby, on the grid and over the results. `!car` (or `/car`, `!pick`)
  brings them back for 6 seconds (each A / D press keeps them up); `!car 2` picks the Meteor straight away and says
  `YOUR CAR: METEOR - RAM` on the bottom line. On your first grid the small cards come up by themselves; after that
  only with `!car`. `!car` while driving answers with the numbers (A / D steer). At the end of a race the results
  board has nothing over it, even if the cards were open when the race ended. When the cards are hidden, A / D do
  nothing to your car.
- **A / D in the lobby** are read every tick now (before, the lobby read the keys 20 times a second and could miss
  a quick tap).
- **`!help`** goes away by itself after 10 seconds (it now comes off with the HUD refresh, not a timer).
- **Spin attack.** Mouse 2 next to someone: they should be shoved well across the road (a Meteor or Bastion shoves
  a Hornet or Comet into the rail from the middle) and fishtail for half a second, with a hard camera shake for
  them. It now hits a car alongside even when you are not moving into it. If it is too much or too little:
  `spinKnock` / `spinStagger` in `const RULES`.
- **Turbo start** (secret now: the grid line no longer mentions it). Press W on the third beep - the higher one -
  and hold it: "TURBO START!" and a kick. Pressing a little after the beep works too (up to GO); holding W from
  before the second beep stalls. The window used to be the last 0.45 s before GO, so a press on the beep did
  nothing - that was why it didn't seem to work.
- **Balance** (sims, 400 races): the Hornet and Comet win a little more often (3.4 and 3.8 per 100 starts against
  2.8 and 2.6), the Meteor and Bastion wreck two to three times as many rivals and make the top 8 more often; the
  light cars get wrecked in about 1 race in 8. Changes: Hornet shield 90 -> 105 and boost +30% -> +32%, Comet
  shield 100 -> 105, Meteor acceleration 495 -> 515, Bastion top speed 1035 -> 1043, shield repair 1.5 -> 2.2/s.

## C7. Abilities, flames, jumps (17 Oct, night)

- **E abilities** (DESIGN.md "E abilities"): Hornet Phase Dash (steer + E: a sideways dash, see-through for a moment),
  Meteor Shockwave (a ring on the road, nearby cars shoved sideways, a hard shake for them), Comet Nova Burn (all
  charge into a long overdrive and a trail of blue fire), Bastion Aegis (a spinning hexagon shell; teammates near get
  +20 shield). The HUD's third bar (under charge) is the cooldown: gold and pulsing when ready, red when short of
  charge. Check the new sounds (dash, quake, nova, aegis) and the effects (shockwave ring, fire, shell) show.
- **Flames**: each car has its own animated flames (Hornet pink needles, Meteor one fat red-orange flame, Comet three
  long blue tails, Bastion four short green thrusters) and a boost pad / turbo start gives longer gold flames and gold
  speed lines (Mouse 1 boost: white speed lines). The animation is the material's own (`F_TEXTURE_ANIMATION`, as on
  Valve's animated TV-static material): bright pulses running down the flame. If a flame shows a striped
  rainbow-ish block instead of flickering, the animation settings didn't take - tell me.
- **Steep roads**: cars at the foot of a climb (Spire, Helix, the Crosswire loop) should ride on their nose and tail,
  not sink into the road.
- **Picker**: A / D move through the cars, **E confirms** (the cards go, the bottom line says your car and its E
  ability); **R** brings them back when you're not driving; `!car` still works. Watching a race, E changes arena unless
  the cards are up.
- **Hornet**: holding drift and flicking left-right while boosting no longer refills charge.
- **Jumps** (DESIGN.md "Jumps everywhere"): new gap jumps on Oval, Hairpin (2), Crosswire, Spire (2), Helix and two
  kickers on Skyway. Take one slowly and you drop in (-20 shield). A clean long jump says BIG AIR! +15 CHARGE.
  These change the track models: copy, then compile the map in Hammer.
- **Balance** (18 Oct, bot races at three skill levels, 1,200 on the final numbers): per 100 starts the Hornet and
  Comet win 3.3 and 3.8, the Meteor and Bastion 2.8 and 2.6; podiums are close to even (9.1-10.0); the Meteor wrecks
  13 rivals and the Bastion 11 (Hornet 5, Comet 6); about 3 wrecks a race; the light cars are wrecked in about 1 race
  in 5, the heavy ones almost never. Changes: Hornet shield 105 -> 108, top speed 1065 -> 1064; Comet shield
  105 -> 110, boost +40% -> +38%, pads 1.4x -> 1.38x; Meteor ram 2x -> 1.8x, acceleration 530 -> 535; Bastion
  shield 130 -> 115, drafting repair 3 -> 1.5/s.

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
