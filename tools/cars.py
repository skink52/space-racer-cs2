"""Original voxel cars for Space Racer: four classes, each as a normal and a boosting model, with T / CT colour skins;
plus the wreck explosion frames, the Pulse wave, the warp-out flash and the invisible null model. Also renders the
car pictures for the HUD car picker and a preview sheet.

usage: cars.py <addon_out_dir> [preview.png]
"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
import s2

OUT = sys.argv[1]
PREVIEW = sys.argv[2] if len(sys.argv) > 2 else None
VOX = 1.6                      # units per voxel
HOVER = 9                      # units the hull floats above the road
MDIR = 'models/spr/cars'
PAL_DIR = 'materials/spr/cars'

# ---------------------------------------------------------------- palette: 8 colours x 4 shades (top, side, end, bottom)
# colour roles: 0 primary (team), 1 secondary (team, darker), 2 trim (light), 3 dark metal, 4 canopy glass,
# 5 engine glow, 6 flame core, 7 flame outer
SHADE = [1.0, 0.78, 0.64, 0.45]
def palette(primary, secondary):
    base = [primary, secondary, (225, 228, 235), (52, 56, 66), (120, 220, 255), (255, 200, 90), (255, 250, 200), (255, 120, 20)]
    pal = np.zeros((32, 3), np.float32)
    for c, col in enumerate(base):
        for sh in range(4):
            k = SHADE[sh]
            if c in (5, 6, 7): k = 1.0 if sh == 0 else 0.92      # glowing parts barely shade
            pal[c * 4 + sh] = np.array(col, np.float32) * k
    return pal.clip(0, 255).astype(np.uint8)

SKINS = {
    'neutral': ((150, 155, 170), (90, 94, 108)),
    't': ((255, 150, 40), (170, 80, 20)),
    'ct': ((70, 150, 255), (30, 70, 170)),
    'gold': ((255, 215, 60), (180, 140, 20)),
}

def write_palettes():
    paths = {}
    for name, (p, s) in SKINS.items():
        pal = palette(p, s)
        img = np.zeros((32, 32, 3), np.uint8)
        for c in range(32):
            y, x = (c // 8) * 8, (c % 8) * 4
            img[y:y + 8, x:x + 4] = pal[c]
        paths[name] = s2.write_material(OUT, '%s/pal_%s' % (PAL_DIR, name), img, comment='Space Racer car palette ' + name)
    return paths

def pal_uv(c):
    # cell centre of colour c in the 32x32 palette image (8 columns of 4 px, 4 rows of 8 px)
    return ((c % 8) * 4 + 2) / 32.0, 1 - ((c // 8) * 8 + 4) / 32.0

# ---------------------------------------------------------------- voxel grid helpers
class Grid:
    def __init__(self, L, W, H):
        self.L, self.W, self.H = L, W, H
        self.occ = np.zeros((L, W, H), bool)
        self.col = np.zeros((L, W, H), np.int8)
        X, Y, Z = np.meshgrid(np.arange(L) + 0.5, np.arange(W) + 0.5 - W / 2, np.arange(H) + 0.5, indexing='ij')
        self.X, self.Y, self.Z = X, Y, Z          # x along the car (0 = rear), y across (0 = centre), z up (0 = bottom)
    def paint(self, mask, c):
        self.occ |= mask; self.col[mask] = c
    def cut(self, mask):
        self.occ &= ~mask
    def ellipsoid(self, cx, cy, cz, rx, ry, rz, c):
        m = ((self.X - cx) / rx) ** 2 + ((self.Y - cy) / ry) ** 2 + ((self.Z - cz) / rz) ** 2 <= 1
        self.paint(m, c); return m
    def box(self, x0, x1, y0, y1, z0, z1, c):
        m = (self.X >= x0) & (self.X < x1) & (self.Y >= y0) & (self.Y < y1) & (self.Z >= z0) & (self.Z < z1)
        self.paint(m, c); return m
    def taper(self, x0, x1, w0, w1, z0, h0, h1, c, yoff=0):
        """a hull slab from x0 to x1 whose half width goes w0 -> w1 and height h0 -> h1 (rounded cross-section)"""
        t = np.clip((self.X - x0) / max(x1 - x0, 1e-6), 0, 1)
        w = w0 + (w1 - w0) * t; h = h0 + (h1 - h0) * t
        m = (self.X >= x0) & (self.X < x1) & (((self.Y - yoff) / np.maximum(w, 0.01)) ** 2 + ((self.Z - z0) / np.maximum(h, 0.01)) ** 2 <= 1) & (self.Z >= z0)
        self.paint(m, c); return m
    def cylinder_x(self, x0, x1, cy, cz, r, c):
        m = (self.X >= x0) & (self.X < x1) & ((self.Y - cy) ** 2 + (self.Z - cz) ** 2 <= r * r)
        self.paint(m, c); return m

# ---------------------------------------------------------------- the four cars (all original designs)
def car_hornet(g, boost):
    L = g.L
    g.taper(4, L - 2, 5.5, 1.2, 1.5, 3.2, 1.6, 0)                  # dart hull, narrowing to the nose
    g.taper(10, 22, 3.0, 2.2, 3.0, 2.6, 1.8, 4)                     # canopy
    g.box(8, 11, -2.6, 2.6, 2.5, 5.8, 1)                             # canopy frame
    g.box(6, 16, -9, -5.5, 1.8, 2.6, 1); g.box(6, 16, 5.5, 9, 1.8, 2.6, 1)     # swept wings
    g.box(9, 14, -11, -8.5, 1.8, 2.4, 2); g.box(9, 14, 8.5, 11, 1.8, 2.4, 2)   # wing tips
    g.box(2, 7, -0.8, 0.8, 3.5, 7.5, 1)                              # tail fin
    for cy in (-3.2, 3.2):
        g.cylinder_x(1, 7, cy, 2.6, 1.7, 3)                           # engines
        g.cylinder_x(0, 1.5, cy, 2.6, 1.3, 5)                         # glow
        if boost: flame(g, 0, cy, 2.6, 1.4, 11)
    g.box(L - 6, L - 1, -1.2, 1.2, 1.2, 2.2, 2)                       # nose trim

def car_meteor(g, boost):
    L = g.L
    g.taper(3, L - 1, 7.5, 3.5, 1.4, 3.4, 2.4, 0)                   # wide wedge hull
    g.box(L - 8, L - 1, -7.5, 7.5, 1.0, 3.2, 3)                      # ram plate
    g.box(L - 3, L, -5, 5, 1.6, 2.8, 2)                              # plate edge trim
    g.taper(10, 20, 3.6, 2.4, 3.4, 2.4, 1.6, 4)                     # low canopy
    g.box(4, 12, -8.5, -6.5, 1.0, 4.0, 1); g.box(4, 12, 6.5, 8.5, 1.0, 4.0, 1)   # side armour
    g.cylinder_x(0, 6, 0, 3.0, 2.9, 3)                               # big engine
    g.cylinder_x(0, 1.5, 0, 3.0, 2.3, 5)
    if boost: flame(g, 0, 0, 3.0, 2.3, 14)
    g.box(2, 5, -7, -5, 3.4, 5.6, 1); g.box(2, 5, 5, 7, 3.4, 5.6, 1)   # rear fins

def car_comet(g, boost):
    L = g.L
    g.taper(2, L - 1, 4.8, 2.0, 1.5, 3.6, 1.6, 0)                   # long teardrop
    g.taper(12, 24, 3.2, 2.2, 3.4, 2.8, 1.8, 4)                     # bubble canopy
    g.box(11, 13, -3.2, 3.2, 2.5, 6.2, 1)
    g.box(1, 9, -0.7, 0.7, 3.6, 9.5, 1)                              # tall tail fin
    g.box(1, 6, -0.7, 0.7, 8.5, 9.5, 2)
    g.box(14, 26, -7, -4.6, 1.6, 2.4, 1); g.box(14, 26, 4.6, 7, 1.6, 2.4, 1)   # canards
    for cy, cz in ((-2.6, 2.4), (2.6, 2.4), (0, 4.8)):
        g.cylinder_x(0, 5, cy, cz, 1.4, 3)
        g.cylinder_x(0, 1.5, cy, cz, 1.1, 5)
        if boost: flame(g, 0, cy, cz, 1.2, 15)

def car_bastion(g, boost):
    L = g.L
    g.box(3, L - 4, -6.5, 6.5, 1.2, 5.0, 0)                          # armoured block hull
    g.taper(L - 6, L, 6.5, 3.0, 1.2, 3.6, 2.0, 0)                   # blunt nose
    g.box(3, L - 3, -7.5, -6.0, 0.8, 3.4, 1); g.box(3, L - 3, 6.0, 7.5, 0.8, 3.4, 1)   # side skirts
    g.box(14, 22, -3.0, 3.0, 5.0, 7.2, 4)                            # slit canopy
    g.box(14, 22, -3.4, 3.4, 4.6, 5.0, 1)
    g.box(6, 13, -6.0, 6.0, 5.0, 6.0, 1)                             # rear deck
    g.box(L - 12, L - 7, -6.0, 6.0, 5.0, 5.8, 2)                     # front trim bar
    for cy, cz in ((-4.2, 2.6), (-1.4, 2.6), (1.4, 2.6), (4.2, 2.6)):
        g.cylinder_x(0, 4, cy, cz, 1.2, 3)
        g.cylinder_x(0, 1.5, cy, cz, 0.9, 5)
        if boost: flame(g, 0, cy, cz, 1.0, 10)

def flame(g, x0, cy, cz, r, length):
    """a boost flame: cones of flame colours pointing backwards (negative x) from x0"""
    for k, (rr, ln, c) in enumerate(((r * 1.15, length, 7), (r * 0.85, length * 0.75, 5), (r * 0.5, length * 0.5, 6))):
        t = np.clip((x0 - g.X) / max(ln, 0.1), 0, 1)
        m = (g.X < x0) & (g.X >= x0 - ln) & ((g.Y - cy) ** 2 + (g.Z - cz) ** 2 <= (rr * (1 - t * 0.85)) ** 2)
        g.paint(m, c)

CARS = {'hornet': car_hornet, 'meteor': car_meteor, 'comet': car_comet, 'bastion': car_bastion}
DIMS = {'hornet': (34, 24, 9), 'meteor': (32, 18, 8), 'comet': (36, 16, 11), 'bastion': (31, 17, 9)}

# ---------------------------------------------------------------- greedy mesher (voxels -> quads)
def mesh_voxels(occ, col, origin, scale):
    """occ: bool [L,W,H]; col: colour index per voxel; origin: world position of voxel (0,0,0) corner; returns tris"""
    nx, ny, nz = occ.shape
    pad = np.zeros((nx + 2, ny + 2, nz + 2), bool); pad[1:-1, 1:-1, 1:-1] = occ
    dirs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    shade = [2, 2, 1, 1, 0, 3]      # end, end, side, side, top, bottom
    tris = []
    for fi, d in enumerate(dirs):
        neigh = pad[1 + d[0]:nx + 1 + d[0], 1 + d[1]:ny + 1 + d[1], 1 + d[2]:nz + 1 + d[2]]
        exposed = occ & ~neigh
        colr = np.where(exposed, col.astype(np.int32) * 4 + shade[fi], -1)
        axis = [i for i in range(3) if d[i] != 0][0]
        ua, va = [i for i in range(3) if i != axis]
        for s in range(occ.shape[axis]):
            sl = np.take(colr, s, axis=axis)
            if (sl < 0).all(): continue
            used = np.zeros(sl.shape, bool)
            U, V = sl.shape
            for i in range(U):
                for j in range(V):
                    c = sl[i, j]
                    if c < 0 or used[i, j]: continue
                    w = 1
                    while i + w < U and sl[i + w, j] == c and not used[i + w, j]: w += 1
                    h = 1
                    while j + h < V and (sl[i:i + w, j + h] == c).all() and not used[i:i + w, j + h].any(): h += 1
                    used[i:i + w, j:j + h] = True
                    plane = s + (1 if d[axis] > 0 else 0)
                    def P(a, b):
                        p = [0.0, 0.0, 0.0]
                        p[axis] = plane; p[ua] = a; p[va] = b
                        return (origin[0] + p[0] * scale, origin[1] + p[1] * scale, origin[2] + p[2] * scale)
                    corners = [P(i, j), P(i + w, j), P(i + w, j + h), P(i, j + h)]
                    n = (float(d[0]), float(d[1]), float(d[2]))
                    e1 = np.subtract(corners[1], corners[0]); e2 = np.subtract(corners[2], corners[0])
                    if np.dot(np.cross(e1, e2), n) < 0: corners = corners[::-1]
                    u, v = pal_uv(int(c))
                    cv = [(p[0], p[1], p[2], u, v) for p in corners]
                    tris.append(('spr_pal', (cv[0], cv[1], cv[2]), n))
                    tris.append(('spr_pal', (cv[0], cv[2], cv[3]), n))
    return tris

def shadow_tris(L, W):
    """a soft dark ellipse under the car (translucent material), at ground level"""
    hx, hy = L * VOX * 0.5, W * VOX * 0.5
    tris = []
    a = (-hx, -hy, 0.6, 0.0, 1.0); b = (hx, -hy, 0.6, 1.0, 1.0); c = (hx, hy, 0.6, 1.0, 0.0); d = (-hx, hy, 0.6, 0.0, 0.0)
    tris.append(('spr_shadow', (a, b, c), (0, 0, 1))); tris.append(('spr_shadow', (a, c, d), (0, 0, 1)))
    return tris

def write_shadow_material():
    S = 64
    yy, xx = np.mgrid[0:S, 0:S]
    r = np.hypot((yy - S / 2) / (S / 2), (xx - S / 2) / (S / 2))
    alpha = (np.clip(1 - r, 0, 1) ** 1.2 * 170).astype(np.uint8)
    col = np.zeros((S, S, 3), np.uint8)
    return s2.write_material(OUT, PAL_DIR + '/shadow', col, alpha, blend=1, comment='hover shadow')

def build_car(key, boost, pal_paths, shadow_mat):
    L, W, H = DIMS[key]
    g = Grid(L + (16 if boost else 0), W, H)
    # the hull sits in the front part; flames extend behind x=0 of the hull -> shift the hull when boosting
    if boost:
        g2 = Grid(L, W, H); CARS[key](g2, False)
        g.occ[16:, :, :] = g2.occ; g.col[16:, :, :] = g2.col
        CARS[key](ShiftedGrid(g, 16), True)
    else:
        CARS[key](g, False)
    origin = (-(L / 2) * VOX - (16 * VOX if boost else 0), -(W / 2) * VOX, HOVER)
    tris = mesh_voxels(g.occ, g.col, origin, VOX) + shadow_tris(L, W)
    mats = {'spr_pal': pal_paths['neutral'], 'spr_shadow': shadow_mat}
    skins = [(name, [(pal_paths['neutral'], pal_paths[name])]) for name in ('t', 'ct', 'gold')]
    name = key + ('_boost' if boost else '')
    return s2.write_model(OUT, MDIR, name, tris, mats, skins), g

class ShiftedGrid:
    """paints only the flames into a bigger grid whose hull starts at x = shift"""
    def __init__(self, g, shift): self.g = g; self.shift = shift; self.L = g.L - shift
    def __getattr__(self, k): return getattr(self.g, k)
    def paint(self, mask, c): self.g.paint(mask, c)
    # the hull functions are no-ops here (hull already copied); only flame() paints, via g.X etc.
    def taper(self, *a, **k): pass
    def box(self, *a, **k): pass
    def ellipsoid(self, *a, **k): pass
    def cylinder_x(self, *a, **k): pass

def _flame_shift_wrapper():
    # flame() uses g.X directly; for the shifted grid the hull's rear (x=0) is at X = shift
    global flame
    orig = flame
    def wrapped(g, x0, cy, cz, r, length):
        if isinstance(g, ShiftedGrid): orig(g.g, x0 + g.shift, cy, cz, r, length)
        else: orig(g, x0, cy, cz, r, length)
    flame = wrapped
_flame_shift_wrapper()

# ---------------------------------------------------------------- effects
def fireball(S, frame):
    rng = np.random.RandomState(31 + frame)
    yy, xx = np.mgrid[0:S, 0:S]
    img = np.zeros((S, S, 4), np.float32)
    n = 10 + frame * 4
    for k in range(n):
        a = rng.rand() * 2 * math.pi; d = rng.rand() * (0.15 + frame * 0.16) * S / 2
        cx, cy = S / 2 + math.cos(a) * d, S / 2 + math.sin(a) * d
        r = (0.12 + rng.rand() * 0.16) * S * (1 + frame * 0.25)
        m = np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1) ** 1.5
        heat = 1 - frame / 4.0
        col = np.array([255, 120 + 120 * heat, 40 * heat]) if frame < 3 else np.array([70, 70, 75])
        img[..., :3] = np.maximum(img[..., :3], col[None, None, :] * m[..., None] / 255 * 255)
        img[..., 3] = np.maximum(img[..., 3], m * (255 if frame < 3 else 160))
    if frame == 0:
        core = np.clip(1 - np.hypot(xx - S / 2, yy - S / 2) / (S * 0.18), 0, 1)
        img[..., :3] = np.maximum(img[..., :3], 255 * core[..., None]); img[..., 3] = np.maximum(img[..., 3], core * 255)
    return img.clip(0, 255).astype(np.uint8)

def star_tris(mat, w, h, zoff=0.0):
    """three crossed vertical planes (both faces drawn by CS2), width w, height h, centred, bottom at zoff"""
    tris = []
    for k in range(3):
        th = k * math.pi / 3
        rx, ry = math.cos(th), math.sin(th)
        p = lambda u, z, uu, vv: (rx * u, ry * u, z, uu, vv)
        a = p(-w / 2, zoff, 0, 1); b = p(w / 2, zoff, 1, 1); c = p(w / 2, zoff + h, 1, 0); d = p(-w / 2, zoff + h, 0, 0)
        n = (-ry, rx, 0.0)
        tris.append((mat, (a, b, c), n)); tris.append((mat, (a, c, d), n))
    return tris

def write_effects():
    out = {}
    for f in range(4):
        img = fireball(64, f)
        mat = s2.write_material(OUT, '%s/boom%d' % (PAL_DIR, f), img[..., :3] * (img[..., 3:4] > 0), img[..., 3], blend=1, backfaces=True, comment='wreck frame %d' % f)
        size = 70 + f * 40
        out['boom%d' % f] = s2.write_model(OUT, MDIR, 'boom%d' % f, star_tris('spr_fx', size, size, -size * 0.3), {'spr_fx': mat})
    # warp-out flash: a tall bright pillar, two frames
    for f in range(2):
        S = 32
        yy, xx = np.mgrid[0:S, 0:S]
        m = np.clip(1 - np.abs(xx - S / 2) / (S / 2), 0, 1) ** (1.0 if f == 0 else 2.5)
        img = np.zeros((S, S, 3), np.uint8); img[:] = (200, 240, 255)
        mat = s2.write_material(OUT, '%s/warp%d' % (PAL_DIR, f), img, (m * 255).astype(np.uint8), blend=1, backfaces=True, comment='warp-out %d' % f)
        out['warp%d' % f] = s2.write_model(OUT, MDIR, 'warp%d' % f, star_tris('spr_fx', 90 if f == 0 else 50, 220 if f == 0 else 320, 0), {'spr_fx': mat})
    # the Pulse: a translucent vertical wave across the track (two-sided), 760 wide, 160 tall
    S = 64
    yy, xx = np.mgrid[0:S, 0:S]
    a = (np.clip(1 - yy / S, 0, 1) ** 1.3) * (0.55 + 0.45 * np.sin(xx / S * 2 * math.pi * 3) ** 2)
    img = np.zeros((S, S, 3), np.uint8); img[:] = (90, 240, 255)
    mat = s2.write_material(OUT, PAL_DIR + '/pulse', img, (a * 200).astype(np.uint8), blend=1, backfaces=True, comment='the Pulse')
    w, h = 760, 160
    p = [(0, -w / 2, 0, 0, 1), (0, w / 2, 0, 1, 1), (0, w / 2, h, 1, 0), (0, -w / 2, h, 0, 0)]
    tris = [('spr_fx', (p[0], p[1], p[2]), (1, 0, 0)), ('spr_fx', (p[0], p[2], p[3]), (1, 0, 0))]
    out['pulse'] = s2.write_model(OUT, MDIR, 'pulse', tris, {'spr_fx': mat})
    # null model (nothing visible) for idle props and sound anchors
    tiny = [('spr_fx', ((0, 0, 0, 0, 0), (0.01, 0, 0, 0, 0), (0, 0.01, 0, 0, 0)), (0, 0, 1))]
    out['null'] = s2.write_model(OUT, 'models/spr', 'null', tiny, {'spr_fx': mat})
    return out

# ---------------------------------------------------------------- pictures (HUD car picker + preview)
def render_voxels(g, pal, size=160, yaw=0.9, pitch=0.55):
    """painter's-algorithm orthographic render of the voxel grid"""
    occ, col = g.occ, g.col
    L, W, H = occ.shape
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    px = img.load()
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    sc = size / (max(L, W) * 1.25)
    cells = []
    for x in range(L):
        for y in range(W):
            for z in range(H):
                if not occ[x, y, z]: continue
                wx, wy, wz = x - L / 2, y - W / 2, z
                rx = wx * cy_ - wy * sy_; ry = wx * sy_ + wy * cy_
                sx = rx; sy = ry * sp - wz * cp; depth = ry * cp + wz * sp
                cells.append((depth, sx, sy, int(col[x, y, z]), z))
    cells.sort()
    for depth, sx, sy, c, z in cells:
        X = int(size / 2 + sx * sc); Y = int(size * 0.6 + sy * sc)
        # shade by height a little
        base = pal[c * 4 + 1].astype(int)
        top = pal[c * 4].astype(int)
        for dx in range(int(sc) + 1):
            for dy in range(int(sc) + 1):
                xx, yy = X + dx, Y + dy
                if 0 <= xx < size and 0 <= yy < size:
                    px[xx, yy] = tuple(top if dy == 0 else base) + (255,)
    return img

def main():
    pal_paths = write_palettes()
    shadow_mat = write_shadow_material()
    models = {}
    grids = {}
    for key in CARS:
        models[key] = {}
        for boost in (False, True):
            path, g = build_car(key, boost, pal_paths, shadow_mat)
            models[key]['boost' if boost else 'base'] = path
            if not boost: grids[key] = g
        print(key, 'voxels', int(grids[key].occ.sum()))
    fx = write_effects()
    os.makedirs(os.path.join(OUT, '_gen'), exist_ok=True)
    json.dump(dict(cars=models, fx=fx, skins=['neutral', 't', 'ct', 'gold'], hover=HOVER), open(os.path.join(OUT, '_gen/car_models.json'), 'w'), indent=1)
    # pictures for the car picker (neutral, T, CT) and the preview sheet
    pdir = os.path.join(OUT, 'panorama/images/custom_game/spr'); os.makedirs(pdir, exist_ok=True)
    sheet = Image.new('RGBA', (4 * 170, 3 * 170), (14, 14, 22, 255)) if PREVIEW else None
    for ci, key in enumerate(CARS):
        for si, skin in enumerate(('neutral', 't', 'ct')):
            pal = palette(*SKINS[skin])
            img = render_voxels(grids[key], pal)
            img.save(os.path.join(pdir, 'car_%s_%s.png' % (key, skin)))
            if sheet: sheet.paste(img, (ci * 170 + 5, si * 170 + 5), img)
    if sheet: sheet.save(PREVIEW)
    print('car models written:', sum(len(v) for v in models.values()), 'fx', len(fx))

main()
