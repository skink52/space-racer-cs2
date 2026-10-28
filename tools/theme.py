"""Which game the generators build: SPR_THEME=space (Space Racer, the default) or neon (Neon Racer).
Both share the game code in src/; everything that differs (tracks, look, names, music) is picked here."""
import os

THEME = os.environ.get('SPR_THEME', 'space')
NEON = THEME == 'neon'
TITLE = 'NEON RACER' if NEON else 'SPACE RACER'
NAME = 'neon_racer' if NEON else 'space_racer'
MAP = 'mg_' + NAME
