# Space Racer for CS2: setup and how it plays

A 32-car anti-gravity racer that runs inside this one CS2 map as the cs_script `maps/scripts/space_racer.js`, with
no server plugins. Up to 64 players in two arenas.

## 1. Install

The addon is `mg_space_racer`. Its map `maps/mg_space_racer.vmap` already contains everything: the six tracks, the
lobby and booth rooms, the script, HUD, sky, sounds and templates. All other files (models, materials, HUD, sounds,
script) go into the same addon folder next to `maps/`.

## 2. Build the map

Open `maps/mg_space_racer.vmap` in Hammer and build it. Everything is unlit, so there is no light bake to wait for.

The map's main entities:

| Entity | Name | Setting |
|---|---|---|
| `point_script` | `spr_script` | cs_script = `maps/scripts/space_racer.vjs` |
| `custom_hud_layout` | `spr_hud` | Layout = `panorama/layout/custom_game/space_racer.vxml` |
| `point_template` | `spr_tpl_prop` | Template01 = `spr_src_prop` |
| `prop_dynamic` | `spr_src_prop` | Model = `models/spr/null.vmdl`, not solid |
| `info_target` | `spr_booth` | Centre of the sealed room where players' bodies wait |
| `info_map_parameters` | `spr_map_params` | The script ends each CS2 round through its FireWinCondition input |
| `point_soundevent` ×17 | `spr_snd_<name>` | Sound Event Name = `spr.<name>` |
| `env_sky` | `spr_sky` | `materials/spr/sky/sky.vmat` |

Plus: `prop_static` for the six tracks (one model each) inside moondome + tools/skybox shells with vis hints,
`spr_cache_*` props that make every car and effect model available to the script, and the lobby with 32 T and
32 CT spawns about 12,000 units below the tracks.

## 3. How it plays

- Everyone spawns in the lobby; the HUD shows the car picker and the countdown. Bodies are parked in the booth
  for the whole round; the view is a chase camera behind your car.
- After freeze time, everyone on T or CT who is not AFK goes to a grid: 1-32 players race together, 33-64 are
  split evenly into two arenas (each with the same share of Ts and CTs), on different tracks. 10-second countdown;
  you can still swap cars (A / D) until 3 seconds before the lights.
- Rounds are locked: nobody joins a race in progress. Latecomers watch (Mouse 1 / 2 change car, E change arena)
  and race next round.
- Cars: HORNET (light, drift charge), METEOR (heavy, ram), COMET (afterburn), BASTION (tank, slipstream). Pick with
  A / D or `!car 1-4`; the choice is remembered.
- Shield = health, Charge = boost. Boost pads give free speed; charge platforms (on the slower lines) refill charge
  and shield; drafting behind a car trickles charge; drifting fills it a little. Mouse 1 boosts, Mouse 2 is a spin
  attack (costs charge), Space drifts. Shield 0 = wrecked and out. Falling off a rail-less section costs 15 shield
  and a 2.5 s reset. Once a lap the Pulse (a wave from the back of the field) tops up everyone it passes by 40.
- The race ends when everyone is in, 30 seconds after the winner, or at 5 minutes (ranked by distance).
- Results: the top 3 survive. Everyone else takes one CS2 death, credited as kills 50% to 1st, 30% to 2nd, 20% to
  3rd (32 cars: 15 / 9 / 5). A car wrecked by another player's attack is that player's kill at once. The CS2 round
  goes to the side with more cars in the top 8 (added over both arenas; under 8 cars the winner's side gets the
  point; ties go to the better single finish).
- AFK: 20 s without input in a race = warning, 30 s = your car withdraws and you sit out until you press a key or
  type `!back`.
- CS2 bots race using the script's own driving AI (`bot_quota 31` fills a test grid).

## Controls

| Key | Action |
|---|---|
| W / S | accelerate / brake and reverse |
| A / D | steer; pick a car when not racing |
| Mouse 1 | boost (uses charge) |
| Mouse 2 | spin attack |
| Space | drift |
| Mouse | nothing while racing - the camera follows the car |
| Mouse 1 / 2, E (watching) | next car / previous car / next arena |

Chat (`!` or `/`): `!car 1-4` (or a name), `!spec`, `!afk`, `!back`, `!race` (controls on your own screen).

## Settings

`maps/scripts/space_racer.js`, search for `const CONFIG`: arena sizes, laps, countdown, finish window, race cap,
podium size and kill shares, `KO_CREDIT_TO_ATTACKER`, tie-break, AFK times, bot skill, camera distance, and the
cvars the map applies. The four cars and the physics rules are in `const CARS` / `const RULES` just below.

When `APPLY_CVARS` is on the map sets: `mp_respawn_on_death_t/ct 1`, `mp_respawn_immunitytime 0`,
`mp_teammates_are_enemies 1` (no teamkill penalties for same-side kills), `mp_ignore_round_win_conditions 1`
while a race runs, `mp_death_drop_gun 0`, `mp_buy_anywhere 0`, `mp_buytime 0`, `sv_disable_radar 1`.
