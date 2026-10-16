"""A picture of what the in-race HUD looks like (an approximation of the Panorama layout, for checking the design
without CS2). usage: hud_mock.py <addon_out_dir> <out.png>"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT, PNG = sys.argv[1], sys.argv[2]
W, H = 1920, 1080
img = Image.new('RGB', (W, H), (10, 10, 18))
dr = ImageDraw.Draw(img, 'RGBA')
def font(sz, bold=True):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf', sz)

# a fake view: a track from behind a car (just a perspective road so the HUD reads in context)
for y in range(430, H):
    k = (y - 430) / (H - 430)
    w = 180 + k * 1500
    col = (40 + int(10 * k), 44 + int(10 * k), 72 + int(20 * k))
    dr.line([(W / 2 - w, y), (W / 2 + w, y)], fill=col)
    if int(y / (10 + 40 * k)) % 2 == 0: dr.line([(W / 2 - 3, y), (W / 2 + 3, y)], fill=(255, 205, 90))
for s in [(0, 0, 0)] * 0: pass
rng = np.random.RandomState(1)
for _ in range(400):
    x, y = rng.randint(0, W), rng.randint(0, 430); dr.point((x, y), fill=(200, 210, 255))
# a few cars (from the picker pictures)
pics = os.path.join(OUT, 'panorama/images/custom_game/spr')
for name, pos, sc in (('car_comet_ct', (560, 560), 0.9), ('car_meteor_t', (1180, 640), 1.1), ('car_hornet_ct', (870, 760), 1.6)):
    p = Image.open(os.path.join(pics, name + '.png')).convert('RGBA'); p = p.resize((int(p.width * sc), int(p.height * sc)))
    img.paste(p, pos, p)
dr = ImageDraw.Draw(img, 'RGBA')

# minimap
mm = Image.open(os.path.join(pics, 'mm_hairpin.png')).convert('RGBA').resize((200, 200))
img.paste(mm, (28, 28), mm); dr = ImageDraw.Draw(img, 'RGBA')
dr.ellipse([28 + 120 - 7, 28 + 150 - 7, 28 + 120 + 7, 28 + 150 + 7], fill=(255, 255, 255)); dr.ellipse([28 + 60 - 5, 28 + 80 - 5, 28 + 60 + 5, 28 + 80 + 5], fill=(255, 208, 64))
# top block
def ctext(x, y, s, f, fill=(255, 255, 255)):
    w = dr.textlength(s, font=f); dr.text((x - w / 2, y), s, font=f, fill=fill, stroke_width=2, stroke_fill=(0, 0, 0))
ctext(W / 2 - 10, 14, '7', font(74)); dr.text((W / 2 + 30, 52), '/ 32', font=font(30), fill=(208, 212, 224), stroke_width=2, stroke_fill=(0, 0, 0))
ctext(W / 2, 100, 'LAP 2 / 4', font(26), (255, 208, 64))
dr.text((W - 30 - 90, 24), '1:12', font=font(28), fill=(208, 212, 224), stroke_width=2, stroke_fill=(0, 0, 0))
# centre message + sub
ctext(W / 2, H / 2 - 160 - 30, 'FINAL LAP', font(58), (255, 208, 64))
ctext(W / 2, H / 2 - 80, '', font(22))
ctext(W / 2, H - 120 - 26, '+40 CHARGE FROM THE PULSE', font(26), (128, 240, 255))
# bars
def bar(x, y, label, frac, col, border=(255, 255, 255, 64)):
    dr.text((x, y + 2), label, font=font(20), fill=(208, 212, 224), stroke_width=2, stroke_fill=(0, 0, 0))
    dr.rounded_rectangle([x + 100, y, x + 400, y + 24], 4, fill=(16, 20, 32, 204), outline=border, width=2)
    dr.rounded_rectangle([x + 102, y + 2, x + 102 + int(296 * frac), y + 22], 3, fill=col)
bar(40, H - 48 - 64, 'SHIELD', 0.65, (96, 255, 128))
bar(40, H - 48 - 32, 'CHARGE', 0.4, (255, 224, 96), (255, 224, 96, 255))
# speed
sp = '318'; f = font(64); w = dr.textlength(sp, font=f)
dr.text((W - 40 - w, H - 48 - 100), sp, font=f, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
f2 = font(18); w2 = dr.textlength('KM/H', font=f2); dr.text((W - 40 - w2, H - 48 - 34), 'KM/H', font=f2, fill=(208, 212, 224))
dr.rounded_rectangle([W - 40 - 300, H - 48 - 10, W - 40, H - 48 + 14], 4, fill=(16, 20, 32, 204), outline=(255, 255, 255, 64), width=2)
dr.rounded_rectangle([W - 40 - 298, H - 48 - 8, W - 40 - 298 + 200, H - 48 + 12], 3, fill=(255, 176, 48))
# standings
rows = [('1  SKINK52', 1, False), ('2  BOT14  ', 0, False), ('3  VEXIS', 1, False), ('4  BOT3', 0, False), ('5  MARLOW', 1, False), ('6  BOT28', 0, False), ('7  YOU', 1, True), ('8  BOT9', 0, False)]
for i, (t, team, me) in enumerate(rows):
    y = H / 2 - 40 - 136 + i * 34
    col = (138, 74, 16, 160) if team == 0 else (26, 74, 144, 160)
    if me: col = (42, 106, 208, 208)
    dr.rounded_rectangle([W - 30 - 330, y, W - 30, y + 30], 4, fill=col, outline=(255, 255, 255) if me else None, width=2)
    dr.text((W - 30 - 320, y + 4), t, font=font(20), fill=(255, 255, 255))
img.save(PNG)
print('hud mock ->', PNG)
