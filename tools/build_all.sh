#!/bin/sh
# Rebuilds the whole addon into out/addon.
#   SPR_NAME=<map name>          map / script / HUD file name (default space_racer -> mg_space_racer.vmap, scripts/space_racer.js)
#   SPR_CURRENT_VMAP=<path>      the map as last saved by Hammer: our entities are layered onto it (keeps hand edits)
#   SPR_SOUNDEVENTS=<path>       the addon's soundevents_addon.vsndevts to merge into (default: the stock template)
set -e
cd "$(dirname "$0")/.."
NAME=${SPR_NAME:-space_racer}
MAP=${SPR_MAP:-mg_$NAME}
rm -rf out/addon && mkdir -p out/addon/maps build
python3 -I tools/tracks.py out/addon preview/tracks.png
python3 -I tools/cars.py out/addon preview/cars.png
python3 -I tools/hud.py out/addon "$NAME"
python3 -I tools/sounds.py out/addon "${SPR_SOUNDEVENTS:-ref/soundevents_addon_template.vsndevts}"
SPR_NAME="$NAME" node tools/build.mjs
SRC=${SPR_CURRENT_VMAP:-ref/hammer_template.vmap}
python3 -I tools/vmap.py "$SRC" "out/addon/maps/$MAP.vmap" out/addon "$NAME"
cp docs/README_ADDON.md out/addon/README_SPACE_RACER.md 2>/dev/null || true
cp docs/TESTING.md out/addon/TESTING_SPACE_RACER.md 2>/dev/null || true
cp docs/CREDITS.md out/addon/CREDITS.md 2>/dev/null || true
cp test/types/point_script.d.ts out/addon/maps/scripts/ 2>/dev/null || true
rm -rf out/addon/_gen/*.json.tmp
echo "built out/addon (map maps/$MAP.vmap, script maps/scripts/$NAME.js)"
