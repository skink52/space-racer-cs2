"""Pictures of the HUD (an approximation of the Panorama layout drawn with the real HUD pictures: pixel-font glyphs,
segmented bars, minimap, logo, car cards) over a chase-camera render, for checking the design without CS2.
usage: hud_mock.py <addon_out_dir> <race background.png> <out_race.png> <out_lobby.png>"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT, BG, PNG, PNG2 = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
W, H = 1920, 1080
IMG = os.path.join(OUT, 'panorama/images/custom_game/spr')
SIZES = {'XXL': 84, 'XL': 52, 'L': 40, 'M': 30, 'S': 22, 'XS': 17}
INK = (24, 20, 37)
FR = {'cyan': (20, 200, 170), 'gold': (255, 190, 40), 'pink': (220, 60, 200), 'white': (140, 110, 150), 'orange': (220, 120, 30)}
_cache = {}
def glyph(ch, col, px):
    key = (ch, col, px)
    if key not in _cache:
        p = os.path.join(IMG, 'f/%s_%d.png' % (col, ord(ch)))
        _cache[key] = Image.open(p).convert('RGBA').resize((px, px), Image.NEAREST) if os.path.exists(p) else None
    return _cache[key]
def text_w(t, size): px = SIZES[size]; return len(t) * (px - px // 10)
def gtext(img, x, y, t, size, col='W', align='left'):
    px = SIZES[size]; adv = px - px // 10
    if align == 'center': x -= text_w(t, size) // 2
    elif align == 'right': x -= text_w(t, size)
    for k, ch in enumerate(t.upper()):
        if ch == ' ': continue
        g = glyph(ch, col, px)
        if g: img.alpha_composite(g, (int(x + k * adv), int(y)))
    return px
def box(img, x0, y0, x1, y1, key):
    d = ImageDraw.Draw(img, 'RGBA')
    d.rectangle([x0, y0, x1, y1], fill=INK + (216,))
    d.rectangle([x0, y0, x1, y1], outline=FR[key] + (255,), width=4)
def pic(img, name, x, y, w, h):
    p = Image.open(os.path.join(IMG, name)).convert('RGBA').resize((int(w), int(h)), Image.NEAREST)
    img.alpha_composite(p, (int(x), int(y)))
def bar(img, x, y, color, frac, w=404, h=24):
    pic(img, 'bar_dark.png', x, y, w, h)
    full = Image.open(os.path.join(IMG, 'bar_%s.png' % color)).convert('RGBA').resize((w, h), Image.NEAREST)
    segs = int(round(frac * 20))
    if segs: img.alpha_composite(full.crop((0, 0, min(w, int(round(segs * w / 20.2)) + 2), h)), (int(x), int(y)))
def crt(img):
    a = np.array(img).astype(np.float32)
    a[::3, :, :3] *= 0.85
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot((xx + 0.5) / W - 0.5, (yy + 0.5) / H - 0.5) * 2
    v = np.clip((r - 0.75) / 0.6, 0, 1) * 0.55
    a[..., :3] *= (1 - v)[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))

# ---------------------------------------------------------------- race
bg = Image.open(BG).convert('RGBA').resize((W, H), Image.NEAREST)
img = bg.copy()
# minimap
box(img, 24, 24, 24 + 216, 24 + 216, 'cyan')
pic(img, 'mm_oval.png', 32, 32, 200, 200)
d = ImageDraw.Draw(img)
for (x, y, c) in ((32 + 150, 32 + 140, (255, 255, 255)), (32 + 80, 32 + 60, (255, 190, 40))):
    d.rectangle([x - 6, y - 6, x + 6, y + 6], fill=c, outline=(0, 0, 0), width=2)
# position
gtext(img, W / 2 - 120, 14, '3', 'XXL', 'G')
gtext(img, W / 2 - 120 + 76, 14 + 84 - 40 - 12, 'RD', 'L', 'G')
gtext(img, W / 2 - 120 + 76 + 72 + 12, 14 + 84 - 30 - 12, '/32', 'M', 'P')
gtext(img, W / 2, 106, 'FINAL LAP', 'M', 'R', 'center')
# clock
cw = text_w('1:42', 'M') + 28
box(img, W - 26 - cw - 40, 22, W - 26, 22 + 70, 'pink')
gtext(img, W - 26 - 14, 32, 'TIME', 'XS', 'P', 'right')
gtext(img, W - 26 - 14, 52, '1:42', 'M', 'W', 'right')
# centre + messages
gtext(img, W / 2, H / 2 - 170 - 26, 'WRONG WAY', 'XL', 'R', 'center')
gtext(img, W / 2, H - 128 - 22, '+40 CHARGE FROM THE PULSE', 'S', 'C', 'center')
# bars
box(img, 30, H - 36 - 136, 30 + 432, H - 36, 'cyan')
gtext(img, 44, H - 36 - 124, 'SHIELD', 'S', 'G'); bar(img, 44, H - 36 - 98, 'green', 0.7)
gtext(img, 44, H - 36 - 66, 'CHARGE', 'S', 'C'); bar(img, 44, H - 36 - 40, 'gold', 0.45)
# speed
box(img, W - 30 - 432, H - 36 - 110, W - 30, H - 36, 'orange')
gtext(img, W - 30 - 14 - text_w(' KM/H', 'S'), H - 36 - 100, '1286', 'XL', 'Y', 'right')
gtext(img, W - 30 - 14, H - 36 - 72, ' KM/H', 'S', 'Y', 'right')
bar(img, W - 30 - 14 - 404, H - 36 - 38, 'orange', 0.85)
# standings
box(img, W - 24 - 340, H / 2 - 30 - 150, W - 24, H / 2 - 30 + 150, 'white')
d = ImageDraw.Draw(img, 'RGBA')
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf', 19)
names = [('1. SKINK52', 1), ('2. BOT14', 0), ('3. YOU', 1), ('4. BOT3', 0), ('5. MARLOW', 1), ('6. BOT28', 0), ('7. VEXIS', 1), ('8. BOT9', 0)]
for i, (t, team) in enumerate(names):
    y = H / 2 - 30 - 140 + i * 35
    me = i == 2
    d.rectangle([W - 24 - 330, y, W - 24 - 10, y + 32], fill=(255, 255, 255, 56) if me else (20, 16, 36, 128))
    d.rectangle([W - 24 - 330, y, W - 24 - 322, y + 32], fill=(255, 255, 255) if me else (220, 120, 30) if team == 0 else (60, 120, 220))
    d.text((W - 24 - 314 + 2, y + 7), t, font=f, fill=(0, 0, 0))
    d.text((W - 24 - 314, y + 5), t, font=f, fill=(255, 190, 40) if me else (255, 255, 255))
crt(img).save(PNG)

# ---------------------------------------------------------------- lobby + picker
img = bg.copy()
img.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, 90)))
lg = Image.open(os.path.join(IMG, 'logo.png'))
pic(img, 'logo.png', W / 2 - lg.width * 1.1 / 2, 80, lg.width * 1.1, lg.height * 1.1)
cars = ['hornet', 'meteor', 'comet', 'bastion']
perks = ['DRIFT CHARGE', 'RAM', 'AFTERBURN', 'SLIPSTREAM']
cw, chh = 270 + 24, 350 + 24
x0 = W / 2 - (4 * (cw + 16)) / 2
ytop = H - 160 - chh
gtext(img, W / 2, ytop - 46, 'CHOOSE YOUR MACHINE   A / D', 'M', 'Y', 'center')
for i, k in enumerate(cars):
    x = x0 + i * (cw + 16) + 8
    sel = i == 1
    box(img, x, ytop, x + cw, ytop + chh, 'gold' if sel else 'white')
    pic(img, 'pcar_%s_t.png' % k, x + cw / 2 - 100, ytop + 12, 200, 200)
    gtext(img, x + cw / 2, ytop + 214, k.upper(), 'L', 'W', 'center')
    gtext(img, x + cw / 2, ytop + 258, perks[i], 'XS', 'C', 'center')
    for j, nm in enumerate(('SPEED', 'ACCEL', 'TURN')):
        gtext(img, x + 20, ytop + 284 + j * 20, nm.ljust(6), 'XS', 'C')
        bar(img, x + 20 + text_w('SPEED ', 'XS') + 6, ytop + 286 + j * 20, 'gold', [0.6, 0.8, 0.5][(i + j) % 3], w=135, h=12)
gtext(img, W / 2, H - 34 - 3 * 30, 'THE RACE STARTS IN 7', 'S', 'W', 'center')
gtext(img, W / 2, H - 34 - 2 * 30, 'YOUR CAR: METEOR - RAM  (A/D OR !CAR 1-4)', 'S', 'Y', 'center')
gtext(img, W / 2, H - 34 - 1 * 30, 'NEXT TRACK: SOLAR OVAL - 3 LAPS', 'S', 'C', 'center')
crt(img).save(PNG2)
print('hud mock ->', PNG, PNG2)
