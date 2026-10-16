# Space Racer for CS2 — design

A 32-car anti-gravity racing minigame that runs entirely inside one Counter-Strike 2 map as a cs_script
(JavaScript), with no server plugins. Up to 64 players in two 32-car arenas. 2.5D: flat neon tracks seen from a
low chase camera, cars drawn as voxel models, in the style of the FreeDM and bomb-arena addons.

Everything here is original: the name, cars, tracks, art, sounds and rules are ours. Nothing is taken from
F-Zero or any other racing game (see `WORKSHOP_COMPLIANCE.md`). The genre conventions we do use (anti-grav
racers, boost pads, drafting, laps) are not anyone's property.

## The pitch

Thirty-two cars line up on a glowing track hanging in space. Three laps. Every car has a **shield** (its health)
and a **charge** meter (its boost). Boost pads on the racing line give free speed; **charge platforms** sit on
slower side lanes and refill your charge and shield, so the race is a constant choice between the fast line and
the refill detour. Cars bump, ram and spin-attack each other; a car whose shield hits zero is **wrecked** and out.
Once a lap the **Pulse** sweeps the track from the back of the pack and tops up everyone it overtakes, so the
field never strings out and a bad start is never the end.

When the chequered flag drops the CS2 scoreboard settles up: the winner is credited with half the losers as
kills, second place with 30%, third with 20% — and the CS2 round goes to the side (T or CT) with more cars in the
top 8.

## Cars

Every player picks one of four cars; the choice is remembered between rounds and can be changed any time you are
not racing (A / D keys, or `!car 1-4`). The cars differ in feel and in one signature perk. Nobody gets more total
"stat"; they trade speed for armour and so on.

| | HORNET | METEOR | COMET | BASTION |
|---|---|---|---|---|
| Style | light, agile | heavy, rams | boost specialist | tank, team player |
| Top speed | 962 | 1005 | 935 | 955 |
| Acceleration | 580 | 430 | 470 | 490 |
| Turning | sharpest | widest | medium | medium |
| Shield | 90 | 110 | 100 | 130 |
| Charge capacity | 100 | 100 | 130 | 100 |
| Boost strength | +30% | +28% | +40% | +33% |
| Spin attack cost | 18 | 30 | 30 | 30 |
| Perk | **Drift charge**: drifting (hold Space) fills charge twice as fast; cheap spin attack | **Ram**: contact deals double damage to the other car and half to the Meteor; 1.6x mass, so it shoves | **Afterburn**: boost pads last 40% longer; charge platforms fill it 30% faster | **Slipstream**: drafting behind any car fills charge at double rate and repairs the shield; teammates drafting *it* get the convoy bonus |

The numbers were tuned in `test/sim.cjs` (bot races) so that every car wins some races; in bot hands the
Hornet and Meteor win most, the Comet wrecks most (it boosts into traffic), the Bastion survives most. Tune in
`CARS` in `src/core/00_defs.js`.

Speeds are CS2 units per second (a player sprinting is 250). A full-speed car crosses a 640-unit-wide track in
under a second.

## Track mechanics

- **Track**: a closed loop with walls (rails) on both sides. The rail bounces you back, costs speed and a little
  shield (scraping is cheap, a head-on hit is not). Some tracks have **gap** sections with no rail: run off and you
  fall into space, reappear at the last checkpoint 2.5 seconds later with 15 less shield and no speed.
- **Boost pads**: bright chevron strips on the racing line. Driving over one gives 1.2 s of boost (1.6 s in a Comet)
  and an instant speed kick. They cost nothing.
- **Charge platforms**: wide glowing panels, usually on the outside of a corner or on a side lane that is a bit
  longer than the racing line. While you are on one, charge refills quickly and shield slowly. The detour is the
  decision: refill now, or stay on the line and hope for the Pulse.
- **Boost** (hold Mouse 1): spends charge for about 30-45% more top speed and extra acceleration. Charge drains in
  roughly 3 seconds from full. No charge, no boost.
- **Drift** (hold Space): the car slides; sharper turning, more speed loss, and the drift fills charge a little
  (a lot in a Hornet).
- **Slipstream**: directly behind another car (within ~300 units, in a 20 degree cone) you get less drag and a
  trickle of charge. Teammates (same CS2 side) in each other's slipstream get the trickle doubled (**convoy**).
- **Spin attack** (Mouse 2): costs 25 charge, 2 second cooldown. The car spins for half a second; anything it touches
  takes 30 shield damage and is knocked sideways. The attacker is not immune to the rail.
- **Contact**: cars are solid. Bumps exchange momentum by mass and cost both cars shield in proportion to the
  closing speed (0 to about 20 per hit). Being hit never stops you outright, it pushes you.
- **Wreck**: shield 0 means a wreck — explosion, car gone, placed behind everyone still racing. If another player
  dealt the last blow within the last 2 seconds, that player gets the CS2 kill immediately (killfeed and all).
- **The Pulse**: once per lap a ring of light sets off from the back of the field and travels the track at 1.5x
  top speed. Every car it overtakes gets +40 charge. It is a catch-up mechanic you can see coming.
- **Jump ramps**: a full-width striped ramp rising 70 units, then open space. Off the lip the car flies with the
  ramp's slope (gravity 1150, a little steering, no thrust); land on the road beyond, or fall into the gap. A hard
  landing (falling faster than 850 u/s) costs a little shield.
- **Slick zones**: on some tracks, a strip where grip is halved (visible as a darker, wet-looking surface).
- **Shield repair**: once nothing has hit you for 4 seconds the shield repairs slowly (1.5/s), so a race is lost
  to sustained aggression, not to attrition. Bumps below a closing speed of 250 are free; the first 3 seconds after
  the lights are damage-free (the first corner is crowded).
- **Laps**: per track (3-5, about 70-100 seconds for bots, longer for people). Eight checkpoints per lap stop corner
  cutting; driving the wrong way shows a warning and does not count, and a missed checkpoint shows
  "MISSED CHECKPOINT - TURN BACK" until you go back for it.
- **Finish**: crossing the line on the last lap. Your car warps out (flash) so it does not block the others.
  The race ends when everyone is in, or 30 seconds after the winner; the rest are ranked by distance.

## Round flow (one CS2 round = one race)

1. **Lobby / freeze time.** Players spawn in the lobby room. Their CS2 bodies are parked in a sealed booth for the
   whole round and only used for input; everyone looks through a script camera. The HUD shows the car picker and
   "race starts in N".
2. **Grid.** When freeze time ends, everyone on T or CT who is not AFK is assigned to an arena and put on its grid
   in a random order, 4 abreast. 10-second countdown; the car picker stays live until 3 seconds before the start,
   so you can still swap cars on the grid.
3. **Race.** Rounds are **locked**: nobody joins a race in progress. Someone connecting mid-round watches
   (Mouse 1 / Mouse 2 change the car you follow, E changes arena) and is in the next round.
4. **Results.** Each arena shows its top 8 and your own placing for 6 seconds. The CS2 kills are applied in a
   cascade (one every few ticks, so the killfeed rolls). When every arena is done the script ends the CS2 round
   with the team result below. A race that somehow runs past 5 minutes is cut off and ranked by distance.

### Arenas

- Up to 32 cars per arena, up to 2 arenas: 1-32 players race together; 33-64 are split evenly into two arenas
  (33 → 17 + 16). The split keeps the same share of Ts and CTs in each arena.
- Each arena races on a different track, picked at random from the eight in the map, never the same track two
  rounds running. The next round's tracks are picked in advance so the lobby can show them.
- Bots on the server race too (CS2 bots are driven by the script's own driving AI), so a test server with
  `bot_quota` fills the grid.

### Who wins the CS2 round (T vs CT)

Per arena: with 8 or more cars, count how many of the top 8 are T and how many are CT. With fewer than 8 cars, the
winner's side gets 1 point. Add the arenas up; the higher side wins the round. On a tie, the side with the better
single finishing position wins (switchable; otherwise a draw).

### Kill credit (rank plugins)

Racing has no kills, so the script makes them at the end so the CS2 scoreboard and rank plugins see the result:

- The top 3 of each arena survive. Everyone else is a loser and takes one CS2 death.
- The deaths are credited as kills: 50% to the winner, 30% to second, 20% to third (largest remainder rounding).
  32 cars → 29 losers → 15 / 9 / 5.
- A car wrecked by another player's attack during the race is a real kill for that player at that moment, and is
  left out of the end-of-race shares. (Config `KO_CREDIT_TO_ATTACKER`; off = all deaths go to the podium.)
- Everything uses the FreeDM method: `pawn.TakeDamage` with the attacker, so the killfeed, scoreboard and rank
  plugins all count it. `mp_teammates_are_enemies 1` keeps same-side kills from counting as teamkills.

### AFK

No input for 20 s during a race: warning on your own HUD. 30 s: your car withdraws (it counts as a loser), you
watch the rest, and you sit out the next round until you press a key or type `!back`. Idle through the whole
lobby: the same.

## Controls

| Key | Action |
|---|---|
| W / S | accelerate / brake and reverse |
| A / D | steer (and pick a car when not racing) |
| Mouse 1 | boost (spends charge) |
| Mouse 2 | spin attack |
| Space | drift |
| Mouse (look) | nothing — the camera follows the car |
| Mouse 1 / Mouse 2 / E (spectating) | next car / previous car / next arena |

Chat: `!car 1-4`, `!spec`, `!afk`, `!back`, `!race` (controls on your own HUD).

## HUD

Panorama custom HUD, per player: position and lap top-centre, shield and charge bars bottom-left, speed bottom-right,
the top-8 standings down the right edge (names coloured by side, you highlighted), a track outline with your dot,
centre messages (countdown, FINAL LAP, WRONG WAY, WRECKED, FINISHED 3RD), the car picker (four cards with stat
bars) in the lobby and on the grid, and lobby status lines for anyone not racing.

## Tracks (eight, all original)

| Track | Lap | Laps | Character |
|---|---|---|---|
| Solar Oval | 15.6k | 5 | wide speedway, long straights, boost lanes, slipstream heaven (easy); slick chicane |
| Hairpin Harbour | 23.4k | 3 | four straights joined by hairpins, charge platforms on the hairpins' outsides |
| Crosswire | 17.9k | 4 | a figure-8 with a flat crossing - cars cross each other's path at speed; boost pads feed the crossing |
| Null Gap | 14.4k | 5 | two long narrow sections with no rails over the void, charge platforms right before them |
| Switchback Spire | 29.0k | 2 | climbs a stack of switchbacks (2.5D height) then a long fast sweep back down; slick zone |
| Ringworld | 14.8k | 5 | a figure-8 with lobes of different sizes; one pass is a bridge (330 up), the other runs under it through a slick zone |
| Skyway | 15.9k | 4 | a fast stadium with a jump ramp on each long straight over an open gap; boost pads feed the ramps |
| Helix | 22.7k | 3 | climbs a stacked spiral (1.25 turns, upper deck 360 over the lower), then a long descent home |

(Lap lengths in units; `preview/tracks.png` shows all six with their pads, platforms, gaps and checkpoints.)

Each track sits in its own box in the void, inside a moondome (starfield sky) with a tools/skybox shell one unit
inside it and vis hints (Lowest for the void, Low in the boxes and lobby), as in the other multi-arena maps.

## Architecture (same shape as FreeDM)

```
src/core/   the race game, plain JS, no engine calls: track maths, car physics, rules, bots, round manager
src/cs2/    the CS2 side: pawn parking + chase camera, input, prop pool rendering, HUD, sounds, CS2 kills,
            round control (FireWinCondition), chat commands, cvars
tools/      generators: tracks.py (track data + road models + minimaps), cars.py (voxel car models),
            hud.py (Panorama layout/css), sounds.py (synthesised sounds + soundevents), vmap.py (writes the
            whole map into the Hammer template), build.mjs (assembles the script), build_all.sh
test/       sim.cjs (bot races on the pure game), mock_cs2.mjs (the real script on a stand-in cs_script API),
            tsconfig.json + point_script.d.ts (type check against Valve's API)
preview/    PNG renders of tracks and cars for checking without CS2
```

- The sim runs at 64 Hz, one step per CS2 server tick (64 cars cost about 0.05 ms per tick in Node), so props are moved with `Move` every tick and the client
  interpolates; no sub-tick interpolation needed.
- Cars are pooled `prop_dynamic` entities spawned from one `point_template` (model = car class + state:
  normal / boosting / wreck frames; skin = T or CT colour).
- Camera: `CustomPlayerCamera` in CONTROLLED mode. Presets per player (`!cam`): high (default, 290 back / 165 up /
  15 deg down), far (420 / 260 / 22), near (230 / 100 / 9); pulls back further at speed, yaw eases towards the car's
  heading turned 35% into the bend ahead (so the upcoming track stays in view), a few degrees of roll in corners.
  The mouse does nothing during a race.
- Readability at a distance: tall beacon pylons with glowing caps every ~430 units on alternating sides, and a
  chevron sign on the outside of every real corner, facing the approaching cars. No fog, nothing fades out.
- Cars are true 3D voxel models (about 100 units long), so every viewing angle is drawn correctly - the chase camera
  shows them from behind like a classic racer, and each car's tail has its own silhouette and lights.
  `preview/car_angles.png` shows all four from eight directions.
- Every CS2 pawn stays parked (frozen, invisible, weaponless) in the booth; all damage to pawns is aborted except
  the script's own kills.
- Tracks are `prop_static` models (road, rails, pads, platforms, scenery), unlit materials, so compiles are quick
  and the look is the same on every setting.
- Sounds: `point_soundevent` per sound, pointed at the car prop (or an anchor) and started, as in FreeDM.

## Settings (CONFIG in the script)

Laps, arena sizes, finish window, race time cap, the four car stat tables, kill shares and podium size,
`KO_CREDIT_TO_ATTACKER`, the Pulse (on/off, speed, charge), AFK times, bot skill, cvars the map applies.

## Bots

Each bot keeps a home lane (from its grid column, five lanes across the track), changes lane only to pass a slower
car into a lane that is clear ahead and just behind, brakes when it is closing on the car in front, gives room to a car
alongside, and brakes for any bend it cannot make at its current speed (turn rate needed vs. its car's turn rate).
In `test/sim.cjs` this cut car-to-car contact by about 30% and wrecks from ~110 to ~60 per 16 races of 32 cars.
