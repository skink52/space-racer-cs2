"""Neon Racer's look for the track pieces: the same texture functions as tracks.py, drawn as glowing lines on
near-black surfaces, then turned into Space Racer-style pixel art: shrunk 4x, dithered to a neon palette and blown
back up with chunky pixels. tracks.py imports these over its own when SPR_THEME=neon. Every material is unlit, so
the bright lines read as light."""
import math
import numpy as np
from retro import WHITE, BLACK, INK, quantize, up

def _neon_palette():
    hues = [(0, 235, 255), (255, 40, 200), (255, 140, 20), (110, 255, 60), (150, 80, 255), (255, 40, 70), (255, 210, 60),
            (60, 120, 255)]
    pal = [(0, 0, 0), (6, 8, 16), (14, 16, 30), (26, 28, 48), (255, 255, 255), (200, 240, 255), (255, 230, 245)]
    for h in hues:
        for k in (1.0, 0.6, 0.3, 0.14):
            pal.append(tuple(int(c * k) for c in h))
    return pal
NEON_PAL = _neon_palette()

def pixelate(img, k=4, spread=14.0):
    """full-size float image -> shrink k x (box average), dither to the neon palette, nearest-neighbour back up"""
    a = np.asarray(img, np.float32)
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    small = a[:h, :w].reshape(h // k, k, w // k, k, 3).mean((1, 3))
    return up(quantize(small, spread, NEON_PAL), k)

DARK = np.array((6, 8, 16), np.float32)

def _f(c): return np.array(c, np.float32)

def glow_line(dist, width=0.6, halo=4.0):
    """intensity for a line at distance `dist` (texels): solid core, soft halo"""
    return np.clip(np.maximum(1.0 - np.maximum(dist - width, 0) / 0.8, 0.55 * np.exp(-np.maximum(dist - width, 0) / halo)), 0, 1)

def add(img, color, k):
    img += _f(color)[None, None, :] * k[..., None]

def finish(img):
    return pixelate(np.clip(img, 0, 255))

def road_texture(th):
    """256 along x 256 across: black glass with a faint grid, glowing edge lines and centre dashes"""
    S = 256
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    img = np.zeros((S, S, 3), np.float32); img[:] = DARK + _f(th['road2']) * 0.06
    gx = np.minimum(xx % 64, 64 - xx % 64); gy = np.minimum(yy % 64, 64 - yy % 64)
    add(img, th['road2'], glow_line(np.minimum(gx, gy), 0.4, 3) * 0.35)
    line = th['line']
    for e in (6, S - 7):
        add(img, line, glow_line(np.abs(yy - e), 1.2, 5))
    for e in (14, S - 15):
        add(img, th['rail'], glow_line(np.abs(yy - e), 0.4, 2) * 0.6)
    dash = (xx % 128) < 56
    add(img, line, glow_line(np.abs(yy - (S - 1) / 2), 0.9, 3) * dash * 0.8)
    return finish(img)

def chevron_texture(color, bg, S=64, k=4):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    v = np.abs(yy - (S - 1) / 2) / (S / 2)
    ph = ((xx + v * S * 0.45) / (S / 4)) % 1.0
    d = np.minimum(np.abs(ph - 0.2), 1 - np.abs(ph - 0.2)) * (S / 4)
    img = np.zeros((S, S, 3), np.float32); img[:] = DARK + _f(bg) * 0.15
    add(img, color, glow_line(d, 1.0, 3))
    add(img, WHITE, glow_line(d, 0.2, 1) * 0.5)
    return finish(np.repeat(np.repeat(img, k, 0), k, 1))

def grid_texture(color, bg, S=64):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    img = np.zeros((S, S, 3), np.float32); img[:] = DARK + _f(bg) * 0.2
    g = np.minimum(np.minimum(xx % 16, 16 - xx % 16), np.minimum(yy % 16, 16 - yy % 16))
    add(img, color, glow_line(g, 0.5, 2.5))
    r = np.hypot(yy - S / 2, xx - S / 2) / (S / 2)
    add(img, color, np.clip(1 - r, 0, 1) * 0.25)
    return finish(np.repeat(np.repeat(img, 4, 0), 4, 1))

def slick_texture(S=64):
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    w = np.sin((xx + 6 * np.sin(yy / S * 2 * math.pi * 2)) / S * 2 * math.pi * 3)
    img = np.zeros((S, S, 3), np.float32); img[:] = DARK
    add(img, (220, 60, 200), glow_line(np.abs(w - 0.7) * 6, 0.4, 2))
    return finish(np.repeat(np.repeat(img, 4, 0), 4, 1))

def rail_texture(color):
    """128 along x 64 up: a dark rail with a bright light bar along its top and a thin one lower down"""
    yy, xx = np.mgrid[0:64, 0:128].astype(np.float32)
    img = np.zeros((64, 128, 3), np.float32); img[:] = DARK
    add(img, color, glow_line(np.abs(yy - 6), 3.0, 6))
    add(img, WHITE, glow_line(np.abs(yy - 6), 0.8, 1.5) * 0.6)
    add(img, color, glow_line(np.abs(yy - 40), 0.5, 3) * 0.5)
    return finish(img)

def skirt_texture(th):
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    img = np.zeros((64, 64, 3), np.float32); img[:] = DARK
    add(img, th['post'], glow_line(np.minimum(xx % 32, 32 - xx % 32), 0.4, 2) * 0.5)
    return finish(img)

def post_texture(color):
    yy, xx = np.mgrid[0:256, 0:32].astype(np.float32)
    img = np.zeros((256, 32, 3), np.float32); img[:] = DARK
    add(img, color, glow_line(np.minimum(xx, 31 - xx), 1.0, 3))
    for y in (20, 26, 140):
        add(img, color, glow_line(np.abs(yy - y), 1.5, 3))
    return finish(img)

def gate_texture(color):
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    img = np.zeros((64, 64, 3), np.float32); img[:] = _f(color) * 0.35
    add(img, color, glow_line(np.minimum(yy, 63 - yy), 2.0, 6))
    add(img, WHITE, glow_line(np.abs(yy - 31.5), 1.0, 3) * 0.8)
    return finish(np.repeat(np.repeat(img, 2, 0), 2, 1))

def beacon_texture(color):
    img = np.zeros((32, 32, 3), np.float32); img[:] = color
    yy, xx = np.mgrid[0:32, 0:32].astype(np.float32)
    add(img, WHITE, np.clip(1 - np.hypot(yy - 16, xx - 16) / 10, 0, 1))
    return finish(img)

def tube_texture(th, light):
    S = 128
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    img = np.zeros((S, S, 3), np.float32); img[:] = DARK
    add(img, th['road2'], glow_line(np.minimum(xx % 64, 64 - xx % 64), 0.5, 3) * 0.6)
    if light:
        add(img, th['glow'], glow_line(np.abs(yy - S / 2), 4, 8) * ((xx % 64) < 40))
        add(img, WHITE, glow_line(np.abs(yy - S / 2), 1, 2) * ((xx % 64) < 40) * 0.6)
    return finish(img)

def tube_out_texture(th):
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    img = np.zeros((64, 64, 3), np.float32); img[:] = DARK
    add(img, th['glow'], glow_line(np.minimum(xx % 32, 32 - xx % 32), 0.5, 2) * 0.7)
    return finish(img)

def floor_texture(th):
    """the endless grid far below"""
    S = 128
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    d = np.minimum(np.minimum(yy, S - 1 - yy), np.minimum(xx, S - 1 - xx))
    img = np.zeros((S, S, 3), np.float32); img[:] = BLACK
    add(img, th['floor'], glow_line(d, 1.0, 6))
    return finish(img)

def window_texture(th, seed, dark=1.0):
    """towers: black glass with glowing horizontal bands and a few lit cells"""
    rng = np.random.RandomState(seed)
    S = 128
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    img = np.zeros((S, S, 3), np.float32); img[:] = DARK
    wins = th['win']
    for k, y in enumerate(range(8, S, 24)):
        add(img, wins[k % len(wins)], glow_line(np.abs(yy - y), 0.6, 3) * dark * (0.5 + 0.5 * rng.rand()))
    for _ in range(18):
        x, y = rng.randint(0, S - 12), rng.randint(0, S - 8)
        img[y:y + 5, x:x + 10] += _f(wins[rng.randint(len(wins))]) * 0.6 * dark
    add(img, th['glow'], glow_line(np.minimum(xx, S - 1 - xx), 0.8, 3) * dark)
    return finish(img)

def roof_texture(th):
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    img = np.zeros((64, 64, 3), np.float32); img[:] = DARK
    add(img, th['glow'], glow_line(np.minimum(np.minimum(xx, 63 - xx), np.minimum(yy, 63 - yy)), 1.0, 4))
    return finish(img)

def ring_texture(color, hi):
    yy, xx = np.mgrid[0:32, 0:128].astype(np.float32)
    img = np.zeros((32, 128, 3), np.float32); img[:] = _f(color) * 0.5
    ph = (xx + np.abs(yy - 15.5) * 0.8) % 32
    add(img, hi, glow_line(np.minimum(ph, 32 - ph), 2, 4))
    add(img, color, glow_line(np.minimum(yy, 31 - yy), 2, 4))
    return finish(img)

def crystal_texture(color, k):
    yy, xx = np.mgrid[0:64, 0:64].astype(np.float32)
    img = np.zeros((64, 64, 3), np.float32); img[:] = _f(color) * 0.12 * k
    add(img, color, glow_line(np.minimum(np.minimum(xx, 63 - xx), np.minimum(yy, 63 - yy)), 1.0, 4) * min(1.0, k))
    return finish(img)

def rock_texture(base, k, seed):
    """Neon Racer has no rocks: data blocks - dark cubes with glowing edges"""
    return crystal_texture(base, k + 0.3)
