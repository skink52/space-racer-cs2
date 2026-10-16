# Space Racer for CS2

A 32-car anti-gravity racing minigame that runs entirely inside one Counter-Strike 2 map as a cs_script, with no
server plugins. Up to 64 players in two 32-car arenas, four cars with different perks, boost pads, charge
platforms, jump ramps, spin attacks, wrecks, the Pulse, eight original tracks, real CS2 kills for the podium and a T-vs-CT round
result from the top 8. 2.5D: flat neon tracks in space, seen from a chase camera, cars drawn as voxel models.

Workshop: *(link to the Steam Workshop page)*

> **About the code:** the code in this repository (the game, the generators and the build tools) was written by an
> AI coding agent (Claude, by Anthropic). skink52 directed the project, tested it in CS2, did the Hammer work and
> publishes the map, but is not the author of the code. Please keep that in mind when reading or reusing it.

Everything here is original work: the name, cars, tracks, art, sounds and rules. The genre conventions it uses
(anti-grav racers, boost pads, drafting, laps) belong to nobody; see `docs/WORKSHOP_COMPLIANCE.md`.

![loading screen](preview/loading.png)

![tracks](preview/tracks.png)

![the cars from eight directions](preview/car_angles.png)

## Layout

| Folder | What it is |
|---|---|
| `src/core/` | The game: track maths, car physics, race rules, the driving AI, the round manager. Plain JavaScript with no engine calls, so it runs in Node for tests. |
| `src/cs2/` | The CS2 side: pawn parking and the chase camera, input, prop-pool rendering, HUD, sounds, CS2 kills, round control, chat commands. |
| `tools/` | Generators: `tracks.py` (tracks → data, road models, minimaps), `cars.py` (voxel cars, effects, renders), `loading.py` (loading screen, radar, map icon), `hud.py` (Panorama layout/css), `sounds.py` (synthesised sounds + sound events), `vmap.py` (writes the whole map into the Hammer template), `build.mjs` (assembles the script), `build_all.sh`. |
| `test/` | `sim.cjs` runs bot races on the pure game; `mock_cs2.mjs` runs the real script on a stand-in cs_script API; `tsconfig.json` + `point_script.d.ts` type-check it against Valve's API. |
| `preview/` | Pictures of the tracks, cars (`car_angles.png`), loading screen, HUD, and `chase_view.py`: a software render of the racer's view from the chase camera. |
| `docs/` | `DESIGN.md` (the game), `TESTING.md` (first run in CS2), `WORKSHOP_COMPLIANCE.md`, the notes that ship with the addon. |
| `ref/` | The Hammer map template the build writes into, and the stock sound-events file. |

## Building

Needs Python 3 with numpy and Pillow, and Node 18+.

```
sh tools/build_all.sh
```

Output lands in `out/addon/`; copy it into `content/csgo_addons/mg_space_racer/` and build the map in Hammer
(`maps/mg_space_racer.vmap`). `SPR_CURRENT_VMAP=<the map as last saved by Hammer>` makes the build layer its
entities onto that map instead of starting from the template, keeping hand edits. `SPR_NAME=<name>` renames the
map, script and HUD files.

Tests:

```
node test/sim.cjs 64 10            # ten rounds of 64 bots: durations, wrecks, car balance, team points
node test/mock_cs2.mjs 20 44 500 churn   # the real script on the mock engine with people joining and leaving
cd test && tsc -p tsconfig.json    # type check against point_script.d.ts
```

## Licence

Code: MIT (`LICENSE`). Art, sounds and track designs: CC BY 4.0. Not affiliated with Valve or any racing game.
