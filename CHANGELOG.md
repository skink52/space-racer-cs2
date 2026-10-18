# Space Racer changelog

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

## v0.3.2 (18 Oct 2026)

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
