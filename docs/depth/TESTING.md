# Depth Racer: what to test (v0.6.0, first build)

Build `maps/mg_depth_racer.vmap` in Hammer first. Then load the map with `bot_quota 8`.

## D1. Look
- All six tracks show their road, rails, pylons, deep-water sky and sea floor, with kelp, coral, ruins or rocks.
  Pick tracks with `!vote` or play a few rounds. Say if any scenery is inside the track.
- The cars have dark hulls and glowing trim in their team's colour.

## D2. Sea creatures
- Kelp Canyon and The Wreck: a sea serpent (a long glowing chain) crosses the jump. Coral Crown and Lantern Deep: a
  manta ray crosses the glide. Vent Field: a whale crosses after the second jump. Abyss Drop: a whale and a serpent in
  the glide.
- The creatures swim smoothly, with no jumping or flicker, and their segments stay joined.
- A hit shoves the car the creature's way, plays a sound and takes shield. Aegis blocks it.
- The warning shows on the bottom line before a crossing.
- Say if a creature is too hard (or too easy) to dodge.

## D3. Glides (Coral Crown, Abyss Drop, Lantern Deep)
- The bottom line says `GLIDE: W DOWN  S UP  HIT THE RINGS`. S climbs and W dives.
- Rings boost or charge, the corridor edge bounces you, and you land on the road at the end.

## D4. Speed (all three games)
- Top speed reads about 200 km/h higher on the speedo than before.
- Jumps still land on the road on every track, with no falls at full speed.
- Corners can be taken at full speed with a little braking or a drift. Say if it is too twitchy.

## D5. Music
- The lobby, both race loops and the results sting play, and the loops have no click where they repeat.
