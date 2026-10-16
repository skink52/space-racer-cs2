"""Space Racer tracks: hand-designed control-point loops -> sampled centreline data for the game, road / rail /
pad / scenery models for the map, minimap outlines for the HUD and a preview picture.

usage: tracks.py <addon_out_dir> [preview.png]

Track space: x east, y north, z up, CS2 units. Each track is centred on (0, 0) and must fit inside its box
(see BOX); vmap.py places the boxes in a 3 x 2 grid in the void.
"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import s2

OUT = sys.argv[1]
PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
SPACING = 48.0          # distance between centreline samples
BOX = 7000              # each track's box (vmap.py); the track must stay inside +-BOX/2 - 300
BOX_DX, BOX_DY = 7200, 7600   # box spacing in the world (3 x 2 grid)

def box_origin(ti):
    """world position of track ti's box centre (the track's local origin)"""
    return [(ti % 3 - 1) * BOX_DX, (ti // 3) * BOX_DY - BOX_DY / 2, 0]

RAIL_H = 28
SKIRT = 56
CHECKPOINTS = 8

# ---------------------------------------------------------------- track definitions
# pts: control points (x, y, z, half-width) in driving order; the loop closes back to the first point, which is
# the start/finish line, so keep the ~1000 units before it straight (the grid sits there).
# feats: (kind, from, to, lat0, lat1) with from/to as fractions of the lap and lat as -1 (left edge) .. 1 (right)
# gaps: (from, to) fractions with no rails on either side.

def stadium(cx, cy, hx, hy, r, n=7):
    """control points of a rounded rectangle, counter-clockwise, starting mid-bottom (driving east)"""
    pts = []
    def arc(ccx, ccy, a0, a1):
        for k in range(n + 1):
            a = a0 + (a1 - a0) * k / n
            pts.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    pts.append((cx, cy - hy))
    pts.append((cx + hx - r, cy - hy))
    arc(cx + hx - r, cy - hy + r, -math.pi / 2, 0)
    arc(cx + hx - r, cy + hy - r, 0, math.pi / 2)
    pts.append((cx, cy + hy))
    pts.append((cx - hx + r, cy + hy))
    arc(cx - hx + r, cy + hy - r, math.pi / 2, math.pi)
    arc(cx - hx + r, cy - hy + r, math.pi, 3 * math.pi / 2)
    # drop duplicates
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1: out.append(p)
    return out

def with_zw(pts, z=0.0, hw=320.0):
    return [(x, y, z, hw) for x, y in pts]

TRACKS = []

# 1. Solar Oval: a stadium with a chicane on the back straight. Easy, fast, draft-heavy.
p = stadium(0, 0, 2900, 1500, 1200, n=5)
oval = []
for x, y in p:
    oval.append((x, y))
    if abs(y - 1500) < 1 and abs(x) < 1:
        oval[-1] = (800, 1500)
        oval.append((300, 1300)); oval.append((-300, 1300)); oval.append((-800, 1500))
TRACKS.append(dict(id='oval', title='SOLAR OVAL', laps=5, theme='oval', pts=with_zw(oval, 0, 330),
    feats=[('boost', 0.06, 0.09, -0.6, 0.6), ('boost', 0.15, 0.18, -0.6, 0.6),
           ('boost', 0.57, 0.60, -0.6, 0.6), ('boost', 0.66, 0.69, -0.6, 0.6),
           ('charge', 0.27, 0.36, 0.45, 1.0), ('charge', 0.77, 0.86, 0.45, 1.0),
           ('slick', 0.46, 0.49, -1.0, 1.0)],
    gaps=[]))

# 2. Hairpin Harbour: five straights joined by four hairpins (a zigzag climbing north), then a wide loop
# around the outside back to the start.
def arc(cx, cy, r, a0, a1, n, z0=0.0, z1=0.0):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n), z0 + (z1 - z0) * k / n)
            for k in range(n + 1)]
hp = []
X = 2000; y0 = -1800; r = 380
hp += [(-1100, y0, 0), (X, y0, 0)]
for i in range(3):
    yA = y0 + 2 * r * i; yB = yA + 2 * r; cy = yA + r
    if i % 2 == 0:
        hp += arc(X, cy, r, -math.pi / 2, math.pi / 2, 6)[1:-1]       # east end: turn north then west
        hp += [(X, yB, 0), (-X, yB, 0)]
    else:
        hp += arc(-X, cy, r, -math.pi / 2, -3 * math.pi / 2, 6)[1:-1]  # west end: turn north then east
        hp += [(-X, yB, 0), (X, yB, 0)]
# heading west at y0 + 6r = 480: round the west side (radius 420) and back along the bottom to the start
hp += arc(-2500, 20, 460, math.pi / 2, math.pi, 4)[1:]
hp += [(-2960, -400, 0), (-2960, -1000, 0)]
hp += arc(-2500, -1340, 460, math.pi, 3 * math.pi / 2, 4)[1:]
hp += [(-1900, y0, 0)]
TRACKS.append(dict(id='hairpin', title='HAIRPIN HARBOUR', laps=4, theme='hairpin', pts=[(x, y, z, 250) for x, y, z in hp],
    feats=[('boost', 0.02, 0.05, -0.5, 0.5), ('boost', 0.175, 0.205, -0.5, 0.5), ('boost', 0.335, 0.365, -0.5, 0.5),
           ('boost', 0.495, 0.525, -0.5, 0.5),
           ('charge', 0.10, 0.125, -1.0, -0.35), ('charge', 0.26, 0.285, 0.35, 1.0), ('charge', 0.42, 0.445, -1.0, -0.35),
           ('charge', 0.58, 0.605, 0.35, 1.0),
           ('boost', 0.70, 0.73, -0.6, 0.6), ('charge', 0.80, 0.85, 0.4, 1.0), ('boost', 0.92, 0.95, -0.6, 0.6)],
    gaps=[]))

# 3. Crosswire: a figure-8 with a flat crossing in the middle (a lemniscate).
cw = []
a = 3000
for k in range(40):
    t = 2 * math.pi * k / 40 + math.pi / 4
    den = 1 + math.sin(t) ** 2
    cw.append((a * math.cos(t) / den, a * math.sin(t) * math.cos(t) / den * 1.35))
TRACKS.append(dict(id='crosswire', title='CROSSWIRE', laps=4, theme='crosswire', pts=with_zw(cw, 0, 280),
    feats=[('boost', 0.065, 0.095, -0.6, 0.6), ('boost', 0.565, 0.595, -0.6, 0.6),
           ('charge', 0.30, 0.37, 0.4, 1.0), ('charge', 0.80, 0.87, -1.0, -0.4),
           ('boost', 0.44, 0.465, -0.5, 0.5), ('boost', 0.94, 0.965, -0.5, 0.5)],
    gaps=[], crossing=True))

# 4. Null Gap: a kidney-shaped loop; two long sections have no rails and a narrower road over the void.
ngz = []
for i in range(36):
    t = 2 * math.pi * i / 36
    rr = 2150 + 400 * math.cos(2 * t) - 220 * math.cos(3 * t)
    f = i / 36
    hw = 300
    if 0.17 < f < 0.36 or 0.6 < f < 0.78: hw = 210
    ngz.append((rr * math.cos(t) * 1.05, rr * math.sin(t) * 0.95, 0, hw))
TRACKS.append(dict(id='nullgap', title='NULL GAP', laps=5, theme='nullgap', pts=ngz,
    feats=[('charge', 0.10, 0.16, -1.0, -0.45), ('charge', 0.53, 0.59, 0.45, 1.0),
           ('boost', 0.04, 0.07, -0.5, 0.5), ('boost', 0.47, 0.50, -0.5, 0.5),
           ('boost', 0.26, 0.285, -0.4, 0.4), ('boost', 0.68, 0.705, -0.4, 0.4),
           ('boost', 0.90, 0.93, -0.6, 0.6)],
    gaps=[(0.19, 0.345), (0.615, 0.765)]))

# 5. Switchback Spire: a climb up four stacked switchbacks (z rising), then a long fast sweep back down.
sp = [(-2200, -2300, 0), (900, -2300, 0)]
rows = [-2300, -1500, -700, 100, 900]
heights = [0, 90, 180, 270, 360]
r = 400
for i in range(4):
    yA, yB = rows[i], rows[i + 1]
    zA, zB = heights[i], heights[i + 1]
    cy = (yA + yB) / 2
    if i % 2 == 0:
        sp += arc(900, cy, r, -math.pi / 2, math.pi / 2, 6, zA, zB)[1:-1]
        sp += [(900, yB, zB), (-900, yB, zB)]
    else:
        sp += arc(-900, cy, r, -math.pi / 2, -3 * math.pi / 2, 6, zA, zB)[1:-1]
        sp += [(-900, yB, zB), (900, yB, zB)]
sp += [(1800, 1050, 355), (2500, 1500, 340), (2900, 2150, 320), (2700, 2650, 300), (1900, 2900, 280), (0, 2950, 250),
       (-1900, 2800, 210), (-2750, 2300, 180), (-2950, 1500, 150), (-3000, 400, 110), (-2950, -800, 70), (-2780, -1700, 35),
       (-2500, -2200, 10)]
TRACKS.append(dict(id='spire', title='SWITCHBACK SPIRE', laps=3, theme='spire',
    pts=[(x, y, z, 270) for x, y, z in sp],
    feats=[('boost', 0.02, 0.045, -0.5, 0.5), ('charge', 0.095, 0.125, 0.4, 1.0), ('charge', 0.265, 0.295, -1.0, -0.4),
           ('charge', 0.435, 0.465, 0.4, 1.0), ('boost', 0.56, 0.59, -0.5, 0.5), ('boost', 0.70, 0.73, -0.6, 0.6),
           ('boost', 0.84, 0.87, -0.6, 0.6), ('slick', 0.76, 0.79, -1.0, 1.0)],
    gaps=[]))

# 6. Ringworld: a figure-8 with a big and a small lobe; one pass through the crossing is a bridge 220 units up,
# the other runs under it through a slick zone.
rw = []
a = 2950
n = 44
for k in range(n):
    t = 2 * math.pi * k / n + math.pi + 0.9
    den = 1 + math.sin(t) ** 2
    x = a * math.cos(t) / den; y = a * math.sin(t) * math.cos(t) / den * 1.3
    if x > 0: x *= 0.72; y *= 0.72                        # the small lobe
    # the bridge: the pass through the origin at t ~ pi/2 (going from the small lobe to the big lobe)
    tt = (t - math.pi / 2 + math.pi) % (2 * math.pi) - math.pi
    u = abs(tt)
    z = 220.0 if u < 0.27 else (220 * (0.5 - 0.5 * math.cos(math.pi * (1 - (u - 0.27) / 0.33))) if u < 0.6 else 0.0)
    rw.append((x, y, z, 290))
TRACKS.append(dict(id='ringworld', title='RINGWORLD', laps=5, theme='ringworld', pts=rw,
    feats=[('boost', 0.04, 0.07, -0.6, 0.6), ('slick', 0.095, 0.125, -1.0, 1.0), ('charge', 0.20, 0.26, 0.4, 1.0),
           ('boost', 0.33, 0.36, -0.5, 0.5), ('charge', 0.42, 0.47, -1.0, -0.4), ('boost', 0.48, 0.505, -0.5, 0.5),
           ('boost', 0.70, 0.73, -0.5, 0.5), ('charge', 0.80, 0.86, 0.4, 1.0), ('boost', 0.92, 0.95, -0.6, 0.6)],
    gaps=[], crossing=True))

# ---------------------------------------------------------------- themes (colours)
THEMES = {
    'oval':      dict(road=(40, 44, 72), line=(255, 205, 90), rail=(255, 160, 40), post=(255, 120, 20), gate=(255, 220, 120)),
    'hairpin':   dict(road=(36, 54, 62), line=(130, 255, 225), rail=(40, 230, 200), post=(20, 200, 170), gate=(170, 255, 240)),
    'crosswire': dict(road=(58, 38, 72), line=(255, 140, 240), rail=(255, 70, 210), post=(230, 40, 190), gate=(255, 180, 250)),
    'nullgap':   dict(road=(30, 30, 46), line=(255, 110, 110), rail=(255, 80, 80), post=(240, 60, 60), gate=(255, 170, 170)),
    'spire':     dict(road=(42, 56, 40), line=(150, 255, 110), rail=(120, 255, 80), post=(90, 230, 50), gate=(200, 255, 170)),
    'ringworld': dict(road=(52, 46, 36), line=(255, 232, 130), rail=(255, 225, 110), post=(240, 200, 80), gate=(255, 245, 190)),
}

# ---------------------------------------------------------------- spline sampling
def catmull(p0, p1, p2, p3, t, alpha=0.5):
    """centripetal Catmull-Rom (no cusps or overshoot on unevenly spaced points); t in 0..1 between p1 and p2"""
    def kn(ti, pa, pb): return ti + max(np.linalg.norm(pb[:2] - pa[:2]), 1e-6) ** alpha
    t0 = 0.0; t1 = kn(t0, p0, p1); t2 = kn(t1, p1, p2); t3 = kn(t2, p2, p3)
    tt = t1 + (t2 - t1) * t
    A1 = (t1 - tt) / (t1 - t0) * p0 + (tt - t0) / (t1 - t0) * p1
    A2 = (t2 - tt) / (t2 - t1) * p1 + (tt - t1) / (t2 - t1) * p2
    A3 = (t3 - tt) / (t3 - t2) * p2 + (tt - t2) / (t3 - t2) * p3
    B1 = (t2 - tt) / (t2 - t0) * A1 + (tt - t0) / (t2 - t0) * A2
    B2 = (t3 - tt) / (t3 - t1) * A2 + (tt - t1) / (t3 - t1) * A3
    return (t2 - tt) / (t2 - t1) * B1 + (tt - t1) / (t2 - t1) * B2

def sample(track):
    P = np.array([(x, y, z) for x, y, z, w in track['pts']], np.float64)
    W = np.array([w for x, y, z, w in track['pts']], np.float64)
    n = len(P)
    dense = []; dw = []
    STEPS = 24
    for i in range(n):
        p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        w1, w2 = W[i], W[(i + 1) % n]
        for k in range(STEPS):
            t = k / STEPS
            dense.append(catmull(p0, p1, p2, p3, t))
            dw.append(w1 + (w2 - w1) * t)
    dense = np.array(dense); dw = np.array(dw)
    seg = np.linalg.norm(np.diff(np.vstack([dense, dense[:1]])[:, :2], axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1]
    N = int(round(L / SPACING))
    targets = np.arange(N) * (L / N)
    idx = np.searchsorted(cum, targets, side='right') - 1
    idx = np.clip(idx, 0, len(dense) - 1)
    frac = (targets - cum[idx]) / np.maximum(seg[idx], 1e-9)
    nxt = (idx + 1) % len(dense)
    pos = dense[idx] + (dense[nxt] - dense[idx]) * frac[:, None]
    hw = dw[idx] + (dw[nxt] - dw[idx]) * frac
    # tangents (central difference, closed loop)
    fwd = np.roll(pos, -1, 0) - np.roll(pos, 1, 0)
    t2 = fwd[:, :2] / np.linalg.norm(fwd[:, :2], axis=1)[:, None]
    return dict(pos=pos, hw=hw, tan=t2, N=N, L=L, step=L / N)

def validate(track, S):
    pos, hw, tan, N = S['pos'], S['hw'], S['tan'], S['N']
    problems = []
    # edge crossing on tight corners
    ang = np.arccos(np.clip((tan * np.roll(tan, -1, 0)).sum(1), -1, 1))
    curv = ang / S['step']
    bad = np.where(hw * curv > 0.95)[0]
    if len(bad): print('   max hw*curv %.2f' % (hw * curv).max())
    if len(bad): problems.append('tight corners (edge folds) at samples %s' % bad[:10].tolist())
    # self overlap: non-neighbouring samples closer than the two half widths at a similar height
    crossings = []
    for i in range(N):
        d = pos[:, :2] - pos[i, :2]
        along = d[:, 0] * tan[i, 0] + d[:, 1] * tan[i, 1]
        across = np.abs(d[:, 0] * tan[i, 1] - d[:, 1] * tan[i, 0])
        far = np.minimum(np.abs(np.arange(N) - i), N - np.abs(np.arange(N) - i)) > 12
        hit = np.where(far & (np.abs(along) < S['step'] * 0.75) & (across < hw + hw[i] + 40) & (np.abs(pos[:, 2] - pos[i, 2]) < 150))[0]
        for j in hit:
            if j < i: continue
            cosang = abs(float((tan[i] * tan[j]).sum()))
            if cosang < 0.5 and track.get('crossing'): crossings.append((i, j))
            else: problems.append('overlap between samples %d and %d (angle cos %.2f)' % (i, j, cosang))
    ext = np.abs(pos[:, :2]).max()
    if ext + hw.max() + 200 > BOX / 2: problems.append('track too big: extent %.0f' % (ext + hw.max()))
    return problems, crossings

# ---------------------------------------------------------------- textures
def noise(h, w, seed, scale=8):
    rng = np.random.RandomState(seed)
    small = rng.rand(h // scale + 1, w // scale + 1)
    y = np.linspace(0, small.shape[0] - 1, h); x = np.linspace(0, small.shape[1] - 1, w)
    yi = np.floor(y).astype(int); xi = np.floor(x).astype(int)
    fy = (y - yi)[:, None]; fx = (x - xi)[None, :]
    yi1 = np.minimum(yi + 1, small.shape[0] - 1); xi1 = np.minimum(xi + 1, small.shape[1] - 1)
    a = small[yi][:, xi]; b = small[yi][:, xi1]; c = small[yi1][:, xi]; d = small[yi1][:, xi1]
    return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy

def road_texture(th):
    """512x512: u along the track (x), v across (y). Centre dashed line, edge lines, faint grid, darker edges."""
    S = 512
    img = np.zeros((S, S, 3), np.float32)
    base = np.array(th['road'], np.float32)
    n = noise(S, S, 7, 32)
    img[:] = base * (0.85 + 0.3 * n)[..., None]
    # faint panel grid every 64 px
    for k in range(0, S, 64):
        img[k:k + 2, :] *= 1.25; img[:, k:k + 2] *= 1.25
    # edge darkening across (v)
    v = np.abs(np.linspace(-1, 1, S))[:, None, None]
    img *= (1 - 0.35 * v ** 3)
    line = np.array(th['line'], np.float32)
    # edge lines (v near 0 and 1)
    img[6:14, :] = line * 0.8; img[S - 14:S - 6, :] = line * 0.8
    # centre dashes along u
    for u0 in range(0, S, 128):
        img[S // 2 - 3:S // 2 + 3, u0:u0 + 64] = line
    return img.clip(0, 255).astype(np.uint8)

def chevron_texture(color, bg, S=256, up=True):
    """boost pad: bright chevrons pointing along +u (the direction of travel)"""
    img = np.zeros((S, S, 3), np.float32); img[:] = bg
    yy, xx = np.mgrid[0:S, 0:S]
    v = np.abs(yy - S / 2) / (S / 2)          # 0 centre .. 1 edge
    phase = ((xx - v * S * 0.45) / (S / 4)) % 1.0
    mask = phase < 0.45
    glow = 0.55 + 0.45 * (1 - v)
    img[mask] = np.array(color, np.float32) * glow[mask][:, None]
    # soft edge fade so the pad looks inset
    e = np.minimum(np.minimum(yy, S - 1 - yy) / 12.0, 1)[..., None]
    img = img * e + np.array(bg, np.float32) * (1 - e)
    return img.clip(0, 255).astype(np.uint8)

def grid_texture(color, bg, S=256):
    img = np.zeros((S, S, 3), np.float32); img[:] = bg
    c = np.array(color, np.float32)
    for k in range(0, S, 32):
        img[k:k + 3, :] = c * 0.8; img[:, k:k + 3] = c * 0.8
    yy, xx = np.mgrid[0:S, 0:S]
    nodes = ((yy % 32) < 8) & ((xx % 32) < 8)
    img[nodes] = c
    # pulsing glow centre
    r = np.hypot(yy - S / 2, xx - S / 2) / (S / 2)
    img = img * (1.15 - 0.3 * r)[..., None]
    return img.clip(0, 255).astype(np.uint8)

def slick_texture(bg, S=256):
    img = np.zeros((S, S, 3), np.float32); img[:] = np.array(bg, np.float32) * 0.6
    n = noise(S, S, 3, 16)
    img += (n[..., None] ** 3) * 120
    img[:, :, 2] += 25
    return img.clip(0, 255).astype(np.uint8)

def rail_texture(color, S=128):
    img = np.zeros((S, S, 3), np.float32)
    c = np.array(color, np.float32)
    v = np.linspace(1, 0, S)[:, None, None]
    img[:] = c * (0.35 + 0.65 * v)
    img[::16, :] *= 0.5
    img[:12, :] = c
    return img.clip(0, 255).astype(np.uint8)

def skirt_texture(bg, S=128):
    img = np.zeros((S, S, 3), np.float32); img[:] = np.array(bg, np.float32) * 0.45
    img[:, ::32] *= 1.6; img[::32, :] *= 1.6
    return img.clip(0, 255).astype(np.uint8)

def post_texture(color, S=64):
    img = np.zeros((S * 4, S, 3), np.float32); img[:] = (22, 24, 34)
    img[20:44, :] = color
    img[150:160, :] = np.array(color) * 0.7
    return img.clip(0, 255).astype(np.uint8)

def start_texture(S=256):
    img = np.zeros((S, S, 3), np.uint8)
    yy, xx = np.mgrid[0:S, 0:S]
    chk = ((yy // 32) + (xx // 64)) % 2 == 0
    img[chk] = (235, 235, 235); img[~chk] = (25, 25, 30)
    return img

def gate_texture(color, S=64):
    img = np.zeros((S, S, 3), np.float32); img[:] = color
    img[::8, :] *= 0.5
    return img.clip(0, 255).astype(np.uint8)

def edge_texture(S=128):
    """yellow / black hazard stripe for rail-less edges"""
    img = np.zeros((S, S, 3), np.uint8)
    yy, xx = np.mgrid[0:S, 0:S]
    st = ((xx + yy) // 24) % 2 == 0
    img[st] = (255, 210, 40); img[~st] = (20, 20, 24)
    return img

# ---------------------------------------------------------------- model building
def build_models(track, S, crossings):
    th = THEMES[track['theme']]
    tid = track['id']
    mats = {}
    mdir = 'materials/spr/track'
    mats['road'] = s2.write_material(OUT, '%s/road_%s' % (mdir, tid), road_texture(th), comment='Space Racer road ' + tid)
    mats['rail'] = s2.write_material(OUT, '%s/rail_%s' % (mdir, tid), rail_texture(th['rail']), comment='rail ' + tid)
    mats['skirt'] = s2.write_material(OUT, '%s/skirt_%s' % (mdir, tid), skirt_texture(th['road']), comment='skirt ' + tid)
    mats['post'] = s2.write_material(OUT, '%s/post_%s' % (mdir, tid), post_texture(th['post']), comment='post ' + tid)
    mats['gate'] = s2.write_material(OUT, '%s/gate_%s' % (mdir, tid), gate_texture(th['gate']), comment='gate ' + tid)
    return mats

SHARED = {}
def shared_materials():
    mdir = 'materials/spr/track'
    SHARED['boost'] = s2.write_material(OUT, mdir + '/pad_boost', chevron_texture((255, 190, 40), (40, 30, 10)), comment='boost pad')
    SHARED['charge'] = s2.write_material(OUT, mdir + '/pad_charge', grid_texture((60, 240, 255), (10, 30, 50)), comment='charge platform')
    SHARED['slick'] = s2.write_material(OUT, mdir + '/pad_slick', slick_texture((40, 44, 60)), comment='slick zone')
    SHARED['start'] = s2.write_material(OUT, mdir + '/startline', start_texture(), comment='start line')
    SHARED['edge'] = s2.write_material(OUT, mdir + '/edge_hazard', edge_texture(), comment='rail-less edge stripe')

def lerp3(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def track_tris(track, S, feats, gaps_idx, cps):
    pos, hw, tan, N, step = S['pos'], S['hw'], S['tan'], S['N'], S['step']
    nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)
    def L(i, k=1.0): i %= N; return (pos[i, 0] + nrm[i, 0] * hw[i] * k, pos[i, 1] + nrm[i, 1] * hw[i] * k, pos[i, 2])
    def R(i, k=1.0): i %= N; return (pos[i, 0] - nrm[i, 0] * hw[i] * k, pos[i, 1] - nrm[i, 1] * hw[i] * k, pos[i, 2])
    def Z(p, dz): return (p[0], p[1], p[2] + dz)
    tris = []
    UL = 640.0
    gapset = set()
    for a, b in gaps_idx:
        i = a
        while True:
            gapset.add(i % N)
            if i % N == b % N: break
            i += 1
    for i in range(N):
        j = i + 1
        u0, u1 = i * step / UL, (i + 1) * step / UL
        l0, r0, l1, r1 = L(i), R(i), L(j), R(j)
        # road surface (seen from above)
        tris += s2.quad('road', r0, r1, l1, l0, (u0, 1), (u1, 1), (u1, 0), (u0, 0), (0, 0, 1))
        # skirts + bottom
        tris += s2.quad('skirt', Z(l0, -SKIRT), Z(l1, -SKIRT), l1, l0, (u0, 1), (u1, 1), (u1, 0), (u0, 0), (nrm[i, 0], nrm[i, 1], 0))
        tris += s2.quad('skirt', r0, r1, Z(r1, -SKIRT), Z(r0, -SKIRT), (u0, 0), (u1, 0), (u1, 1), (u0, 1), (-nrm[i, 0], -nrm[i, 1], 0))
        tris += s2.quad('skirt', Z(l0, -SKIRT), Z(l1, -SKIRT), Z(r1, -SKIRT), Z(r0, -SKIRT), (u0, 0), (u1, 0), (u1, 1), (u0, 1), (0, 0, -1))
        if i in gapset:
            # hazard stripes along the open edges
            for side, pa, pb, k in (('l', l0, l1, 1.0), ('r', r0, r1, 1.0)):
                ia, ib = (L(i, 0.93), L(j, 0.93)) if side == 'l' else (R(i, 0.93), R(j, 0.93))
                if side == 'l': tris += s2.quad('edge', Z(ia, 0.6), Z(ib, 0.6), Z(pb, 0.6), Z(pa, 0.6), (u0 * 4, 0), (u1 * 4, 0), (u1 * 4, 1), (u0 * 4, 1), (0, 0, 1))
                else: tris += s2.quad('edge', Z(pa, 0.6), Z(pb, 0.6), Z(ib, 0.6), Z(ia, 0.6), (u0 * 4, 0), (u1 * 4, 0), (u1 * 4, 1), (u0 * 4, 1), (0, 0, 1))
        else:
            ur0, ur1 = i * step / 256.0, (i + 1) * step / 256.0
            # left rail: inner face (seen from the road), top cap, outer face
            lt0, lt1 = Z(l0, RAIL_H), Z(l1, RAIL_H)
            lo0, lo1 = L(i, 1.0 + 10 / max(hw[i], 1)), L(j, 1.0 + 10 / max(hw[j % N], 1))
            # (SMD v = 1 is the top of the texture: the bright strip sits along the top edge of the rail)
            tris += s2.quad('rail', l0, l1, lt1, lt0, (ur0, 0), (ur1, 0), (ur1, 1), (ur0, 1), (-nrm[i, 0], -nrm[i, 1], 0))
            tris += s2.quad('rail', lt0, lt1, Z(lo1, RAIL_H), Z(lo0, RAIL_H), (ur0, 1), (ur1, 1), (ur1, 0.9), (ur0, 0.9), (0, 0, 1))
            tris += s2.quad('rail', Z(lo0, RAIL_H), Z(lo1, RAIL_H), Z(lo1, -SKIRT), Z(lo0, -SKIRT), (ur0, 1), (ur1, 1), (ur1, 0), (ur0, 0), (nrm[i, 0], nrm[i, 1], 0))
            rt0, rt1 = Z(r0, RAIL_H), Z(r1, RAIL_H)
            ro0, ro1 = R(i, 1.0 + 10 / max(hw[i], 1)), R(j, 1.0 + 10 / max(hw[j % N], 1))
            tris += s2.quad('rail', r1, r0, rt0, rt1, (ur1, 0), (ur0, 0), (ur0, 1), (ur1, 1), (nrm[i, 0], nrm[i, 1], 0))
            tris += s2.quad('rail', rt1, rt0, Z(ro0, RAIL_H), Z(ro1, RAIL_H), (ur1, 1), (ur0, 1), (ur0, 0.9), (ur1, 0.9), (0, 0, 1))
            tris += s2.quad('rail', Z(ro1, RAIL_H), Z(ro0, RAIL_H), Z(ro0, -SKIRT), Z(ro1, -SKIRT), (ur1, 1), (ur0, 1), (ur0, 0), (ur1, 0), (-nrm[i, 0], -nrm[i, 1], 0))
    # pads: quads 0.5 above the road between lateral fractions
    def lat(i, f): i %= N; return (pos[i, 0] - nrm[i, 0] * hw[i] * f, pos[i, 1] - nrm[i, 1] * hw[i] * f, pos[i, 2] + 0.5)
    for ft in feats:
        kind, a, b, l0f, l1f = ft['kind'], ft['a'], ft['b'], ft['l0'], ft['l1']
        i = a; k = 0
        while True:
            j = i + 1
            uu = 1.0 if kind == 'boost' else 0.5
            u0, u1 = k * step / 256.0 * uu, (k + 1) * step / 256.0 * uu
            # lateral fraction f: -1 left .. 1 right; lat() uses "right = -nrm"
            p00, p01, p11, p10 = lat(i, l1f), lat(j, l1f), lat(j, l0f), lat(i, l0f)
            tris += s2.quad(kind, p00, p01, p11, p10, (u0, 1), (u1, 1), (u1, 0), (u0, 0), (0, 0, 1))
            if i % N == b % N: break
            i += 1; k += 1
    # start line across the track just after sample 0
    tris += s2.quad('start', Z(R(0), 0.7), Z(R(1), 0.7), Z(L(1), 0.7), Z(L(0), 0.7), (0, 1), (1, 1), (1, 0), (0, 0), (0, 0, 1))
    # checkpoint gates (not at the start): two pylons and a crossbar
    for ci in cps[1:]:
        for side in ('l', 'r'):
            p = L(ci, 1.0 + 70 / hw[ci]) if side == 'l' else R(ci, 1.0 + 70 / hw[ci])
            tris += s2.box_tris('gate', p[0] - 14, p[1] - 14, p[2] - SKIRT, p[0] + 14, p[1] + 14, p[2] + 230)
        l, r = L(ci, 1.0 + 70 / hw[ci]), R(ci, 1.0 + 70 / hw[ci])
        # crossbar as a thin box along the gate direction: approximate with a quad pair (both faces visible anyway)
        d = (r[0] - l[0], r[1] - l[1]); ln = math.hypot(*d); dx, dy = d[0] / ln, d[1] / ln
        t = (-dy * 12, dx * 12)
        a0 = (l[0] + t[0], l[1] + t[1], l[2] + 210); a1 = (r[0] + t[0], r[1] + t[1], r[2] + 210)
        b0 = (l[0] - t[0], l[1] - t[1], l[2] + 210); b1 = (r[0] - t[0], r[1] - t[1], r[2] + 210)
        for dz in (0, 24):
            tris += s2.quad('gate', Z(a0, dz), Z(a1, dz), Z(b1, dz), Z(b0, dz), (0, 0), (ln / 64, 0), (ln / 64, 1), (0, 1), (0, 0, 1))
        tris += s2.quad('gate', a0, a1, Z(a1, 24), Z(a0, 24), (0, 0), (ln / 64, 0), (ln / 64, 1), (0, 1), (-dy, dx, 0))
        tris += s2.quad('gate', b1, b0, Z(b0, 24), Z(b1, 24), (0, 0), (ln / 64, 0), (ln / 64, 1), (0, 1), (dy, -dx, 0))
    # scenery posts
    rng = np.random.RandomState(hash(track['id']) & 0xffff)
    for k, i in enumerate(range(3, N, 14)):
        side = 1.0 if k % 2 == 0 else -1.0
        off = hw[i] + 120
        p = (pos[i, 0] + nrm[i, 0] * off * side, pos[i, 1] + nrm[i, 1] * off * side, pos[i, 2])
        h = 260 + rng.randint(0, 200)
        tris += s2.box_tris('post', p[0] - 14, p[1] - 14, p[2] - SKIRT - 40, p[0] + 14, p[1] + 14, p[2] + h, uscale=1 / 256.0)
    return tris

def minimap(track, S, path, size=192):
    pos, hw = S['pos'], S['hw']
    ext = max(np.abs(pos[:, :2]).max() + hw.max(), 1)
    scale = (size / 2 - 6) / ext
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    th = THEMES[track['theme']]
    pts = [(size / 2 + x * scale, size / 2 - y * scale) for x, y in pos[:, :2]]
    w = max(2, int(hw.mean() * 2 * scale))
    dr.line(pts + pts[:1], fill=(255, 255, 255, 110), width=w + 2, joint='curve')
    dr.line(pts + pts[:1], fill=tuple(th['rail']) + (255,), width=w, joint='curve')
    # start line
    x0, y0 = pts[0]
    dr.ellipse([x0 - 3, y0 - 3, x0 + 3, y0 + 3], fill=(255, 255, 255, 255))
    img.save(path)
    return dict(scale=scale, size=size)

def preview_draw(dr, S, feats, gaps_idx, cps, ox, oy, sc, th, title):
    pos, hw, tan, N = S['pos'], S['hw'], S['tan'], S['N']
    nrm = np.stack([-tan[:, 1], tan[:, 0]], 1)
    def P(x, y): return (ox + x * sc, oy - y * sc)
    gapset = set()
    for a, b in gaps_idx:
        i = a
        while True:
            gapset.add(i % N)
            if i % N == b % N: break
            i += 1
    for i in range(N):
        j = (i + 1) % N
        l0 = pos[i, :2] + nrm[i] * hw[i]; r0 = pos[i, :2] - nrm[i] * hw[i]
        l1 = pos[j, :2] + nrm[j] * hw[j]; r1 = pos[j, :2] - nrm[j] * hw[j]
        shade = 0.6 + 0.4 * min(1, pos[i, 2] / 400)
        col = tuple(int(c * shade) for c in th['road'])
        dr.polygon([P(*r0), P(*r1), P(*l1), P(*l0)], fill=col)
    for i in range(N):
        j = (i + 1) % N
        if i in gapset: continue
        l0 = pos[i, :2] + nrm[i] * hw[i]; l1 = pos[j, :2] + nrm[j] * hw[j]
        r0 = pos[i, :2] - nrm[i] * hw[i]; r1 = pos[j, :2] - nrm[j] * hw[j]
        dr.line([P(*l0), P(*l1)], fill=th['rail'], width=2); dr.line([P(*r0), P(*r1)], fill=th['rail'], width=2)
    colors = {'boost': (255, 190, 40), 'charge': (60, 240, 255), 'slick': (90, 90, 140)}
    for ft in feats:
        i = ft['a']
        while True:
            j = (i + 1) % N
            def lat(k, f): return pos[k % N, :2] - nrm[k % N] * hw[k % N] * f
            dr.polygon([P(*lat(i, ft['l1'])), P(*lat(j, ft['l1'])), P(*lat(j, ft['l0'])), P(*lat(i, ft['l0']))], fill=colors[ft['kind']])
            if i % N == ft['b'] % N: break
            i += 1
    for ci in cps:
        l = pos[ci, :2] + nrm[ci] * hw[ci]; r = pos[ci, :2] - nrm[ci] * hw[ci]
        dr.line([P(*l), P(*r)], fill=(255, 255, 255) if ci == 0 else th['gate'], width=3 if ci == 0 else 2)
    # direction arrow at sample 6
    i = 6
    tip = pos[i, :2] + tan[i] * 160; base = pos[i, :2]
    dr.line([P(*base), P(*tip)], fill=(255, 255, 255), width=3)
    dr.text((ox - 150, oy - 3300 * sc), title, fill=(255, 255, 255))

# ---------------------------------------------------------------- main
def main():
    os.makedirs(os.path.join(OUT, '_gen'), exist_ok=True)
    mmdir = os.path.join(OUT, 'panorama/images/custom_game/spr'); os.makedirs(mmdir, exist_ok=True)
    shared_materials()
    runtime = []
    props = []
    prev = Image.new('RGB', (3 * 700, 2 * 700), (12, 12, 18)) if PREVIEW else None
    dr = ImageDraw.Draw(prev) if prev else None
    ok = True
    for ti, track in enumerate(TRACKS):
        S = sample(track)
        problems, crossings = validate(track, S)
        N, L = S['N'], S['L']
        for p in problems: print('  %s: %s' % (track['id'], p)); ok = False
        def frac_idx(f): return int(round(f * N)) % N
        feats = [dict(kind=k, a=frac_idx(a), b=frac_idx(b), l0=l0, l1=l1) for k, a, b, l0, l1 in track['feats']]
        gaps_idx = [(frac_idx(a), frac_idx(b)) for a, b in track['gaps']]
        cps = [int(round(k * N / CHECKPOINTS)) % N for k in range(CHECKPOINTS)]
        mats = build_models(track, S, crossings)
        tris = track_tris(track, S, feats, gaps_idx, cps)
        allmats = dict(mats); allmats.update(SHARED)
        model = s2.write_model(OUT, 'models/spr/track', track['id'], tris, allmats)
        mm = minimap(track, S, os.path.join(mmdir, 'mm_%s.png' % track['id']))
        pos, hw, tan = S['pos'], S['hw'], S['tan']
        # rails per sample: 0 none, 1 both (per-side gaps are not used yet)
        rail = np.ones(N, np.int8)
        for a, b in gaps_idx:
            i = a
            while True:
                rail[i % N] = 0
                if i % N == b % N: break
                i += 1
        runtime.append(dict(
            id=track['id'], title=track['title'], laps=track['laps'], theme=track['theme'], index=ti,
            n=N, length=round(L, 1), step=round(S['step'], 4),
            x=[round(float(v), 1) for v in pos[:, 0]], y=[round(float(v), 1) for v in pos[:, 1]], z=[round(float(v), 1) for v in pos[:, 2]],
            tx=[round(float(v), 4) for v in tan[:, 0]], ty=[round(float(v), 4) for v in tan[:, 1]],
            hw=[round(float(v), 1) for v in hw], rail=[int(v) for v in rail],
            cp=cps, feats=feats, crossing=bool(track.get('crossing')),
            mm=dict(scale=round(mm['scale'], 5), size=mm['size']),
            ext=round(float(np.abs(pos[:, :2]).max() + hw.max()), 1),
            zmin=round(float(pos[:, 2].min()), 1), zmax=round(float(pos[:, 2].max()), 1),
            off=box_origin(ti),
        ))
        props.append(dict(id=track['id'], model=model, index=ti, off=box_origin(ti), ext=runtime[-1]['ext'], zmin=runtime[-1]['zmin'], zmax=runtime[-1]['zmax']))
        print('%-10s %4d samples, lap %6.0f, hw %3.0f-%3.0f, z %3.0f-%3.0f, feats %d, gaps %d, crossings %d, tris %d' % (
            track['id'], N, L, hw.min(), hw.max(), pos[:, 2].min(), pos[:, 2].max(), len(feats), len(gaps_idx), len(crossings), len(tris)))
        if dr:
            ox = 350 + (ti % 3) * 700; oy = 350 + (ti // 3) * 700
            preview_draw(dr, S, feats, gaps_idx, cps, ox, oy, 330 / 3300, THEMES[track['theme']], track['title'] + '  lap %.0f' % L)
    json.dump(runtime, open(os.path.join(OUT, '_gen/tracks.json'), 'w'), separators=(',', ':'))
    json.dump(props, open(os.path.join(OUT, '_gen/track_props.json'), 'w'))
    if prev: prev.save(PREVIEW)
    if not ok: sys.exit('track problems found')

main()
