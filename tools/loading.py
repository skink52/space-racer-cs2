"""Loading screen picture, radar (overview) image, overview file and map icon for the map.
  panorama/images/map_icons/screenshots/1080p/<map>.png   loading screen
  panorama/images/overheadmaps/<map>_radar.psd             radar / overview
  panorama/images/map_icons/map_icon_<map>.svg             map icon
  resource/overviews/<map>.txt                             where the radar sits in the world (copy into the GAME addon folder)
usage: loading.py <addon_out_dir> <map name>
"""
import os, sys, json, math, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import pixfont, skies
from retro import *
import retro
from trackdefs import THEMES as RTHEMES, TRACKS as RDEFS

OUT, MAP = sys.argv[1], sys.argv[2]
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'
def font(sz, bold=True): return ImageFont.truetype(FONT_B if bold else FONT_R, sz)
tracks = json.load(open(os.path.join(OUT, '_gen/tracks.json')))
THEME = {k: tuple(v['rail']) for k, v in RTHEMES.items()}

def stars(W, H, seed=3):
    rng = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    img = np.zeros((H, W, 3), np.float32)
    img[..., 0] = 8; img[..., 1] = 10; img[..., 2] = 24
    for _ in range(9):
        cx, cy, r = rng.rand() * W, rng.rand() * H, (0.15 + rng.rand() * 0.3) * W
        col = np.array([[0.8, 0.3, 0.9], [0.3, 0.5, 1.0], [1.0, 0.5, 0.3]][rng.randint(3)])
        g = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)) * 50
        img += g[..., None] * col
    n = 2500
    sx, sy, sb = rng.randint(0, W, n), rng.randint(0, H, n), rng.rand(n) ** 3 * 255
    img[sy, sx] += sb[:, None]
    return Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert('RGBA')

def text(d, xy, s, f, fill=(255, 255, 255), anchor='la', stroke=3):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))

def track_outline(T, size, color, width=4):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ext = T['ext']; sc = (size / 2 - 6) / ext
    road = T.get('road', [1] * T['n'])
    pts = [(size / 2 + x * sc, size / 2 - y * sc) for x, y in zip(T['x'], T['y'])]
    for i in range(T['n']):
        if not road[i]: continue
        a, b = pts[i], pts[(i + 1) % T['n']]
        d.line([a, b], fill=color + (255,), width=width)
    return img

# ---------------------------------------------------------------- loading screen (pixel art, 480 x 270 upscaled 4x)
def loading_screen():
    W, H = 1920, 1080
    # background: the Solar Oval sky, cropped round its sun, then a perspective neon grid floor
    sky = skies.make_sky('oval', RTHEMES['oval'], 'city', 5)[::4, ::4]          # 512 x 256 at 1x
    lw, lh = 480, 270
    canvas = np.zeros((lh, lw, 3), np.uint8)
    sun_x = int(np.argmax((sky[100:128, :, 0].astype(int) > 240).sum(0)))       # where the sun is
    x0 = int(np.clip(sun_x - lw * 0.62, 0, sky.shape[1] - lw))
    HZ = 128
    canvas[:HZ] = sky[:HZ, x0:x0 + lw]
    for y in range(HZ, lh):
        k = (y - HZ) / (lh - HZ)
        canvas[y] = (np.array(BLACK) * (1 - k) + np.array(INK) * k).astype(np.uint8)
    for j in range(1, 14):                     # horizontal grid lines, bunching towards the horizon
        y = HZ + int((lh - HZ) * (j / 13) ** 2.2)
        if y < lh: canvas[y] = MAGENTA
    for i in range(-30, 31):
        x_top = lw / 2 + i * 9; x_bot = lw / 2 + i * 80
        for y in range(HZ, lh):
            k = (y - HZ) / (lh - HZ)
            x = int(x_top + (x_bot - x_top) * k)
            if 0 <= x < lw: canvas[y, x] = MAGENTA
    big = up(canvas, 4).copy()
    # the logo
    lg = pixfont.logo('SPACE RACER', 10)
    pixfont.paste(big, lg, (W - lg.shape[1]) // 2, 40)
    pixfont.draw(big, W // 2, 40 + lg.shape[0] + 12, '32-CAR ANTI-GRAV RACING IN COUNTER-STRIKE 2', 4, ICE, shadow=PURPLE, align='center')
    # the four cars, pixelated, on little pads
    names = ['hornet', 'meteor', 'comet', 'bastion']; perks = ['DRIFT CHARGE', 'RAM', 'AFTERBURN', 'SLIPSTREAM']
    for i, key in enumerate(names):
        p = os.path.join(OUT, '_gen', 'big_%s.png' % key)
        if not os.path.exists(p): continue
        im = np.array(Image.open(p).convert('RGBA').resize((72, 72), Image.BILINEAR))
        q = quantize_rgba(im, 12)
        a = q[..., 3] > 0; o = np.zeros_like(a)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)): o |= np.roll(np.roll(a, dy, 0), dx, 1)
        q[o & ~a] = (0, 0, 0, 255)
        cx = 150 + i * 300
        pixfont.paste(big, up(q, 4), cx - 144 + 40, 330)
        pixfont.draw(big, cx + 40, 630, key.upper(), 5, WHITE, shadow=PURPLE, align='center')
        pixfont.draw(big, cx + 40, 680, perks[i], 3, ICE, align='center')
    # the tracks: pixel outlines in their colours
    for i, T in enumerate(tracks):
        th = RTHEMES[T['theme']]
        im = track_outline(T, 34, tuple(th['rail']), 1)
        a = np.array(im); a[..., 3] = np.where(a[..., 3] > 90, 255, 0)
        x, y = 70 + i * 160, 760
        pixfont.paste(big, up(a, 4), x, y)
        pixfont.draw(big, x + 68, y + 142, 'NULL GAP' if T['id'] == 'nullgap' else T['id'].upper(), 2, PALE, align='center')
    # controls box
    bx, by, bw, bh = 1330, 300, 540, 650
    big[by:by + bh, bx:bx + bw] = (big[by:by + bh, bx:bx + bw] * 0.25).astype(np.uint8)
    big[by:by + 6, bx:bx + bw] = TEAL; big[by + bh - 6:by + bh, bx:bx + bw] = TEAL
    big[by:by + bh, bx:bx + 6] = TEAL; big[by:by + bh, bx + bw - 6:bx + bw] = TEAL
    y = by + 26
    pixfont.draw(big, bx + bw // 2, y, 'HOW TO DRIVE', 5, GOLD, shadow=RUST, align='center'); y += 70
    rows = [('W/S', 'GAS / BRAKE'), ('A/D', 'STEER'), ('MOUSE1', 'BOOST'), ('MOUSE2', 'SPIN ATTACK'), ('SPACE', 'DRIFT'),
            ('!CAR 1-4', 'CHOOSE CAR'), ('!CAM', 'CAMERA'), ('!CRT', 'SCANLINES')]
    for k_, v in rows:
        pixfont.draw(big, bx + 30, y, k_, 3, GOLD); pixfont.draw(big, bx + 240, y, v, 3, WHITE); y += 44
    y += 16
    for line, col in (('TOP 3 TAKE THE KILLS', ICE), ('50 / 30 / 20 %', ICE), ('MOST OF YOUR SIDE IN', LIME), ('THE TOP 8 WINS', LIME)):
        pixfont.draw(big, bx + bw // 2, y, line, 3, col, align='center'); y += 38
    pixfont.draw(big, W // 2, 1040, 'ALL CARS, TRACKS, ART, MUSIC AND SOUND ORIGINAL', 2, LILAC, align='center')
    big = retro.scanlines(big, 4, 0.82)
    path = os.path.join(OUT, 'panorama/images/map_icons/screenshots/1080p'); os.makedirs(path, exist_ok=True)
    Image.fromarray(big).save(os.path.join(path, MAP + '.png'))

# ---------------------------------------------------------------- radar
def write_psd(path, img):
    arr = np.array(img.convert('RGB')); h, w = arr.shape[:2]
    with open(path, 'wb') as f:
        f.write(b'8BPS' + struct.pack('>H6xHIIHH', 1, 3, h, w, 8, 3))
        f.write(struct.pack('>I', 0)); f.write(struct.pack('>I', 0)); f.write(struct.pack('>I', 0)); f.write(struct.pack('>H', 0))
        for c in range(3): f.write(arr[..., c].tobytes())

def radar():
    xs, ys = [], []
    for T in tracks:
        o = T['off']; xs += [o[0] - T['ext'], o[0] + T['ext']]; ys += [o[1] - T['ext'], o[1] + T['ext']]
    m = 300
    minx, maxx, miny, maxy = min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m
    size = max(maxx - minx, maxy - miny)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    pos_x, pos_y = cx - size / 2, cy + size / 2
    R = 1024; scale = size / R; S = 2
    img = Image.new('RGB', (R * S, R * S), (6, 8, 18))
    d = ImageDraw.Draw(img)
    px = lambda x, y: ((x - pos_x) / scale * S, (pos_y - y) / scale * S)
    for T in tracks:
        o = T['off']; col = THEME.get(T['theme'], (255, 255, 255)); road = T.get('road', [1] * T['n'])
        w = max(2, int(T['hw'][0] * 2 / scale * S * 0.8))
        for i in range(T['n']):
            if not road[i]: continue
            j = (i + 1) % T['n']
            d.line([px(o[0] + T['x'][i], o[1] + T['y'][i]), px(o[0] + T['x'][j], o[1] + T['y'][j])], fill=tuple(int(c * 0.5) for c in col), width=w)
            d.line([px(o[0] + T['x'][i], o[1] + T['y'][i]), px(o[0] + T['x'][j], o[1] + T['y'][j])], fill=col, width=S * 2)
    img = img.resize((R, R), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    # the two layers share the same four squares: label each square with both names
    quads = {}
    for T in tracks: quads.setdefault((T['off'][0], T['off'][1]), []).append(T['title'])
    for (ox, oy), names in quads.items():
        x, y = px(ox, oy)
        for k, nm in enumerate(names):
            text(d, (x / S, y / S - 14 + k * 30), nm, font(22), (255, 255, 255), anchor='mm', stroke=3)
    path = os.path.join(OUT, 'panorama/images/overheadmaps'); os.makedirs(path, exist_ok=True)
    write_psd(os.path.join(path, MAP + '_radar.psd'), img)
    img.save(os.path.join(OUT, '_gen', 'radar_preview.png'))
    ov = os.path.join(OUT, 'resource/overviews'); os.makedirs(ov, exist_ok=True)
    open(os.path.join(ov, MAP + '.txt'), 'w', newline='\n').write(
        '"%s"\n{\n\t"material"\t"overviews/%s"\n\t"pos_x"\t"%d"\n\t"pos_y"\t"%d"\n\t"scale"\t"%.3f"\n\t"rotate"\t"0"\n\t"zoom"\t"1.0"\n}\n'
        % (MAP, MAP, round(pos_x), round(pos_y), scale))
    return pos_x, pos_y, scale

def icon():
    # a white chevron-arrow racer silhouette, like the stock map icons
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
           '<path fill="#ffffff" d="M32 4 L52 50 L40 44 L32 58 L24 44 L12 50 Z"/>'
           '<path fill="#000000" fill-opacity="0.35" d="M32 18 L42 42 L32 37 L22 42 Z"/></svg>\n')
    path = os.path.join(OUT, 'panorama/images/map_icons'); os.makedirs(path, exist_ok=True)
    open(os.path.join(path, 'map_icon_%s.svg' % MAP), 'w', newline='\n').write(svg)

loading_screen()
p = radar()
icon()
print('loading screen, radar (pos %.0f, %.0f, scale %.2f), icon' % p)
