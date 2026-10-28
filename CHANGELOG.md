# Space Racer changelog

## Neon Racer pixel update (28 Oct 2026, evening)

- **Pixel style, neon colours**:
  - The Tripo3D cars, pylons and gates are gone.
  - The cars are Space Racer's voxel cars again, with near-black hulls and glowing team-colour trim and edge lines.
  - Every track texture and sky is drawn in chunky dithered pixels in a neon palette.
  - Flight gates are glowing pixel rings again.
- **Start gantry**: its towers now stand clear of the track name. The letters had run into the pillars. This changes
  the generator for both games; Space Racer's tracks change too on their next build.

## Neon Racer v0.5.0 (28 Oct 2026, first build)

A second addon, `mg_neon_racer`, built from this repository (`SPR_THEME=neon`). It plays like Space Racer v0.5.0.
- **Six new tracks**: Grid Circuit, Pulse City, Void Hop, Data Stream, Skyline Dive and Overclock.
- **Flight sections** on Void Hop and Skyline Dive:
  - The road ends and you fly a corridor of gates. W climbs, S dives and A / D steer.
  - The corridor's edge bounces you like a rail. Gold rings boost you and blue rings charge you.
  - The corridor narrows onto the road at the end.
  - Bots fly through the rings, and the Seeker Bolt follows its target's height.
- **Neon look**: glowing-line roads, rails and towers, synthwave skies over an endless grid, Tripo3D pylons and
  flight gates.
- **Cars** made from skink52's Tripo3D models (about 9k triangles each). Their glowing strips show your side's colour.
  Replaced by pixel cars in the evening update.
- **Music**: four original electro pieces in place of chiptune.

Shared code changes (no effect on Space Racer's tracks):
- The track data can have flight sections and flight rings.
- A checkpoint that a long flight pushes onto the next one moves back before the flight instead.

## v0.5.0 (28 Oct 2026)

### Changed
- **Hornet: Seeker Bolt replaces Phase Dash.** E fires a bolt forward down the road. It locks on to the first car
  ahead and curves into it. The car hit is shoved sideways, skids, loses a quarter of its speed and 6 shield
  (credited to you). An Aegis shell stops it. Costs 20 charge, 6 s cooldown, range 2,500 units. Like the Shockwave,
  it unlocks 6 seconds after GO.

## v0.4.1 (18 Oct 2026)

### Changed
- **No team menu.** Players who join without a team are put on the side with fewer players after a second, so CS2's
  team menu never sits behind the race HUD. The M-key team menu is turned off (`AUTO_TEAM` in CONFIG turns this
  off); `!spec` still lets you watch.
- **No money.** Kills and rounds pay nothing, and nobody starts with money.

### Fixed
- The minimap dots didn't move: each dot was clipped by its own panel as soon as it moved down the map.
- The car picker could reopen over the results if you were tapping A / D as the race ended.

## v0.4.0 (18 Oct 2026)

### New
- **Track vote.** When a race ends, its top 3 vote on the next track from a box on the left of the screen.
  - Use W / S to pick, or type `!vote 1-4` or a track name.
  - 1st place's vote counts 3, 2nd's counts 2, 3rd's counts 1.
  - Votes can change until the next race is set up. Everyone in that race sees the box and the totals.
- **Votes work per arena.** With two or more arenas, each new arena races the track picked by the voters who end
  up in it. If two arenas want the same track, the one with more votes gets it and the other takes its next choice.
- **Colour shades.** `!shade` picks your car's colour; `!shade 1-6` or a name picks one directly. Your choice is
  remembered and your car changes straight away.
  - T: orange, red, crimson, coral, rose, maroon.
  - CT: blue, navy, cyan, teal, indigo, ice.
- **Winners' glow.** Last round's top 3 in each race drive the next race with a neon outline in their own colour.
- The loading screen and the `!help` panel list `!shade` and `!vote`.

### Fixed
- With two or more arenas, human players placed in the second (or third or fourth) arena were turned into
  spectators while it was being set up. Those arenas raced with bots only. Every arena now fills properly.

### Server settings (in the script's CONFIG)
- `VOTES`, `VOTE_WEIGHTS`, `VOTE_CHOICES` and `BOTS_VOTE` control the track vote.
- `WINNER_GLOW` and `GLOW_PLACES` control the glow. `GLOW_PLACES 1` limits it to winners only.

### Performance
- The map's script uses about a third of the server time it did, and makes about a third as many calls into CS2
  each tick. Nothing looks or plays differently.

| Server | Script time per tick, before → after | CS2 calls per tick, before → after |
|---|---|---|
| 64 players (20 humans + 44 bots) | 0.36 → 0.14 ms | 608 → 215 |
| 32 humans | 0.41 → 0.11 ms | 723 → 255 |
| 8 players | 0.055 → 0.026 ms | 63 → 25 |

These figures are from a test engine on a PC, not from a CS2 server.

### Fixed
- A car that fell off and reset at the very moment a race ended could vanish during the results.
- Some car sounds kept replaying after a race had ended.

### Server settings (in the script's CONFIG)
- `PERF_LOG` prints the script's time per tick in the console once a minute during races.
- `MINIMAP_DOT_HZ` sets how often the other cars' minimap dots move. The default of 8 is unchanged; 4 halves the
  biggest share of HUD traffic.
