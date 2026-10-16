"""Pixel-art sky panoramas, one per track theme (equirectangular 2048 x 1024, drawn at 512 x 256 and upscaled 4x).
Every picture is generated here from the palette: gradient bands, dithered nebulae, pixel stars, a big planet (or a
striped retro sun), and a skyline / mountain silhouette along the horizon."""
import math
import numpy as np
from retro import *
import retro

W, H = 512, 256

def lerp(a, b, t): return np.array(a, np.float32) * (1 - t) + np.array(b, np.float32) * t

def gradient(top, mid, hor):
    """rows: 0 = straight up, H/2 = horizon, H = straight down"""
    img = np.zeros((H, W, 3), np.float32)
    for y in range(H):
        lat = 1 - y / (H / 2)          # 1 up .. 0 horizon .. -1 down
        if lat >= 0.45: c = lerp(top, mid, (1 - lat) / 0.55)
        elif lat >= 0: c = lerp(mid, hor, (0.45 - lat) / 0.45)
        else: c = lerp(hor, BLACK, min(1, -lat / 0.25))
        img[y] = c
    return img

def stars(img, rng, n=900, big=40):
    ys = (rng.rand(n) ** 1.3 * H * 0.5).astype(int); xs = rng.randint(0, W, n)
    for y, x in zip(ys, xs):
        img[y, x] = WHITE if rng.rand() < 0.5 else PALE
    for _ in range(big):
        y, x = int(rng.rand() ** 1.2 * H * 0.45), rng.randint(2, W - 2)
        col = [WHITE, ICE, CREAM, PINK][rng.randint(4)]
        img[y, x] = WHITE
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)): img[y + dy, x + dx] = col
        if rng.rand() < 0.3:
            for dy, dx in ((0, 2), (0, -2), (2, 0), (-2, 0)):
                if 0 <= y + dy < H: img[y + dy, (x + dx) % W] = col

def nebula(img, rng, colors, strength=0.55, seed=3):
    n1 = retro.noise(H, W, seed, 24); n2 = retro.noise(H, W, seed + 7, 9)
    yy = np.arange(H)[:, None]
    band = np.exp(-((yy - H * 0.3 - 18 * np.sin(np.arange(W)[None, :] / W * 4 * math.pi)) / (H * 0.12)) ** 2)
    m = np.clip((n1 * 0.7 + n2 * 0.3 - 0.45) * 2.2, 0, 1) * band
    c0, c1 = np.array(colors[0], np.float32), np.array(colors[1], np.float32)
    col = c0[None, None, :] * (1 - n2[..., None]) + c1[None, None, :] * n2[..., None]
    img[:] = img * (1 - m[..., None] * strength) + col * m[..., None] * strength

def paste(img, sprite, cx, cy):
    h, w = sprite.shape[:2]
    y0, x0 = int(cy - h / 2), int(cx - w / 2)
    for yy in range(h):
        y = y0 + yy
        if not 0 <= y < H: continue
        for xx in range(w):
            if sprite[yy, xx, 3] > 0: img[y, (x0 + xx) % W] = sprite[yy, xx, :3]

def planet(img, rng, color, kind):
    cx, cy = rng.randint(60, W - 60), int(H * 0.26)
    if kind == 'sun':
        # a striped retro sun sitting low over the horizon
        R = 46; cy = int(H * 0.5) - 26
        for y in range(cy - R, cy + R + 1):
            for x in range(cx - R, cx + R + 1):
                d = math.hypot(x - cx, y - cy)
                if d > R: continue
                t = (y - (cy - R)) / (2 * R)
                c = lerp(GOLD, HOT, t) if t < 0.5 else lerp(HOT, MAGENTA, (t - 0.5) * 2)
                if t > 0.45 and int((y - cy) * 0.55) % 2 == 0 and (y - cy) % max(2, int(6 - t * 4)) < 2: continue
                img[y, x % W] = c
        return
    size = 84 if kind in ('ringed', 'banded') else 64
    sp = pixel_sphere(size, color, bands=6 if kind in ('banded', 'ringed') else 0, seed=rng.randint(99))
    if kind in ('moon', 'cratered'):
        for _ in range(9):
            x, y, r = rng.randint(8, size - 8), rng.randint(8, size - 8), rng.randint(2, 6)
            yy, xx = np.mgrid[0:size, 0:size]
            m = (np.hypot(xx - x, yy - y) < r) & (sp[..., 3] > 0)
            sp[m, :3] *= 0.7
    if kind == 'ringed':
        big = np.zeros((size, size * 2, 4), np.float32)
        big[:, size // 2:size // 2 + size] = sp
        yy, xx = np.mgrid[0:size, 0:size * 2]
        e = ((xx - size) / (size * 0.95)) ** 2 + ((yy - size / 2) / (size * 0.2)) ** 2
        ring = (e > 0.75) & (e < 1.0)
        front = ring & (yy > size / 2)
        back = ring & (yy <= size / 2) & (big[..., 3] == 0)
        for m in (front, back):
            big[m, :3] = np.array(CREAM if m is front else SAND, np.float32)
            big[m, 3] = 255
        sp = big
    paste(img, sp, cx, cy)
    # a small moon nearby
    paste(img, pixel_sphere(18, PALE), (cx + 90) % W, cy + 30)

def horizon(img, rng, kind, col):
    """a dark silhouette along the horizon: towers for cities, peaks otherwise"""
    hy = H // 2
    if kind in ('city', 'rings'):
        x = 0
        while x < W:
            w = rng.randint(4, 14); h = rng.randint(4, 26)
            img[hy - h:hy + 1, x:min(W, x + w)] = INK
            for wy in range(hy - h + 2, hy, 3):
                for wx in range(x + 1, x + w - 1, 2):
                    if rng.rand() < 0.3: img[wy, wx % W] = col
            x += w + rng.randint(0, 3)
    else:
        n = retro.noise(1, W, rng.randint(99), 20)[0]
        n2 = retro.noise(1, W, rng.randint(99), 5)[0]
        for x in range(W):
            h = int(6 + 22 * n[x] + 6 * n2[x])
            img[hy - h:hy + 1, x] = INK
            img[hy - h, x] = col

def make_sky(theme, th, scenery, seed):
    rng = np.random.RandomState(seed)
    top, mid, hor = th['sky']
    img = gradient(top, mid, hor)
    nebula(img, rng, (th['glow'], mid), seed=seed)
    stars(img, rng)
    planet(img, rng, th['planet'][0], th['planet'][1])
    horizon(img, rng, scenery, th['glow'])
    q = quantize(img, 30)
    return up(q, 4)
