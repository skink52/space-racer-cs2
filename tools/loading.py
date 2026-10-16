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

OUT, MAP = sys.argv[1], sys.argv[2]
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
FONT_R = '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf'
def font(sz, bold=True): return ImageFont.truetype(FONT_B if bold else FONT_R, sz)
tracks = json.load(open(os.path.join(OUT, '_gen/tracks.json')))
THEME = {'oval': (255, 160, 40), 'hairpin': (40, 230, 200), 'crosswire': (255, 70, 210), 'nullgap': (255, 80, 80),
         'spire': (120, 255, 80), 'ringworld': (255, 225, 110), 'skyway': (90, 170, 255), 'helix': (255, 130, 90)}

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

# ---------------------------------------------------------------- loading screen
def loading_screen():
    W, H = 1920, 1080
    base = stars(W, H)
    d = ImageDraw.Draw(base)
    text(d, (110, 70), 'SPACE RACER', font(150), (255, 210, 70), stroke=6)
    text(d, (118, 250), '32-CAR ANTI-GRAV RACING INSIDE COUNTER-STRIKE 2', font(38), (200, 230, 255))
    # the four cars
    for i, key in enumerate(['hornet', 'meteor', 'comet', 'bastion']):
        p = os.path.join(OUT, '_gen', 'big_%s.png' % key)
        if not os.path.exists(p): continue
        im = Image.open(p).convert('RGBA').resize((300, 300), Image.LANCZOS)
        x = 100 + i * 330
        base.alpha_composite(im, (x, 320))
        text(d, (x + 150, 640), key.upper(), font(36), (255, 255, 255), anchor='ma')
    perks = ['DRIFT CHARGE', 'RAM', 'AFTERBURN', 'SLIPSTREAM']
    for i, pk in enumerate(perks):
        text(d, (100 + i * 330 + 150, 686), pk, font(24, False), (128, 240, 255), anchor='ma', stroke=2)
    # tracks
    for i, T in enumerate(tracks):
        im = track_outline(T, 136, THEME.get(T['theme'], (255, 255, 255)))
        x, y = 100 + (i % 8) * 156, 780
        base.alpha_composite(im, (x, y))
        text(d, (x + 68, y + 146), T['title'], font(16), (220, 220, 230), anchor='ma', stroke=2)
    # controls
    base.alpha_composite(Image.new('RGBA', (500, 640), (0, 0, 0, 170)), (1380, 320))
    y = 345
    text(d, (1410, y), 'CONTROLS', font(40), (255, 210, 70)); y += 66
    rows = [('W / S', 'DRIVE / BRAKE'), ('A / D', 'STEER, PICK CAR'), ('MOUSE 1', 'BOOST'), ('MOUSE 2', 'SPIN ATTACK'),
            ('SPACE', 'DRIFT'), ('WATCHING', 'M1 / M2 CAR, E ARENA'), ('!CAR 1-4', 'CHOOSE CAR'), ('!CAM', 'CAMERA VIEW'),
            ('!AFK !BACK', 'SIT OUT / RETURN')]
    for a, b in rows:
        text(d, (1410, y), a, font(26), (255, 210, 70), stroke=2); text(d, (1590, y), b, font(26, False), (255, 255, 255), stroke=2); y += 44
    y += 10
    for line in ['TOP 3 SCORE THE KILLS: 50 / 30 / 20 %', 'MORE OF YOUR SIDE IN THE TOP 8 WINS']:
        text(d, (1410, y), line, font(20), (128, 240, 255), stroke=2); y += 30
    text(d, (110, 1045), 'ALL CARS, TRACKS, ART AND SOUND ORIGINAL - BY SKINK52', font(18, False), (150, 150, 165), stroke=2)
    path = os.path.join(OUT, 'panorama/images/map_icons/screenshots/1080p'); os.makedirs(path, exist_ok=True)
    base.convert('RGB').save(os.path.join(path, MAP + '.png'))

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
    for T in tracks:
        o = T['off']; x, y = px(o[0], o[1])
        text(d, (x / S, y / S), T['title'], font(22), (255, 255, 255), anchor='mm', stroke=3)
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
