"""Space Racer HUD for CS2 Panorama (custom_hud_layout): layout xml + css + every picture it uses.

usage: hud.py <addon_out_dir> [name] [map]

The retro look: all game text is drawn with the original 8x8 pixel font (tools/pixfont.py). A text slot is a row of
small image panels, one per character; the script sets each panel's glyph class (g65 = 'A') and the row's colour
class (cW white, cY gold, cC cyan, cR red, cG green, cP pink), so only characters that change are sent. Static text
is written straight into the layout the same way. Player names in the standings stay as Labels.
Bars are segmented pixel bars, the minimap is pixelated, and a CRT scanline overlay can be toggled with !crt.
"""
import os, sys, re, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import pixfont
from retro import *
import retro

OUT = sys.argv[1]
NAME = sys.argv[2] if len(sys.argv) > 2 else 'space_racer'
MAP = sys.argv[3] if len(sys.argv) > 3 else 'mg_' + NAME
IMG = 'file://{images}/custom_game/spr/'
IMGDIR = os.path.join(OUT, 'panorama/images/custom_game/spr')
FONT = 'Stratum2, "Stratum2 Bold", Arial'
os.makedirs(os.path.join(IMGDIR, 'f'), exist_ok=True)
css = []
def rule(sel, **props):
    body = ' '.join('%s: %s;' % (k.replace('_', '-'), v) for k, v in props.items())
    css.append('%s { %s }' % (sel, body))
def raw(text): css.append(text)

xml = []
def P(id_=None, cls=None, children=None, tag='Panel', extra=''):
    a = []
    if id_: a.append('id="%s"' % id_)
    if cls: a.append('class="%s"' % cls)
    a.append('hittest="false"')
    if extra: a.append(extra)
    if children is None: return '<%s %s />' % (tag, ' '.join(a))
    return '<%s %s>\n%s\n</%s>' % (tag, ' '.join(a), '\n'.join(children), tag)
def L(id_, cls, text='{s:v}'):
    return P(id_, cls, tag='Label', extra='text="%s"' % text)
def save(img, rel):
    Image.fromarray(np.ascontiguousarray(img)).save(os.path.join(IMGDIR, rel))
    return IMG + rel

# ---------------------------------------------------------------- the car table (picker stats) from the game's source
defs = open(os.path.join(os.path.dirname(__file__), '..', 'src/core/00_defs.js')).read()
cars = {}
for m in re.finditer(r"(\w+):\s*\{ key: '(\w+)',\s*name: '(\w+)',(.*?)perk: '([^']+)', desc: '([^']+)'", defs, re.S):
    key, name, body, perk, desc = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
    kv = dict((k, float(v)) for k, v in re.findall(r"(\w+): ([\d.]+)", body))
    cars[key] = dict(name=name, perk=perk, desc=desc, **kv)
KEYS = ['hornet', 'meteor', 'comet', 'bastion']
assert all(k in cars for k in KEYS), cars.keys()

# ---------------------------------------------------------------- glyph images
COLORS = {'W': WHITE, 'Y': GOLD, 'C': ICE, 'R': SALMON, 'G': LIME, 'P': PINK}
CHARSET = ''.join(sorted(c for c in pixfont.GLYPHS if c != '\x7f'))
GS = 6          # glyph pictures are 10 x 10 font pixels, saved 6x (60 x 60)
for ck, col in COLORS.items():
    for ch in CHARSET:
        if ch == ' ': continue
        img = pixfont.render(ch, scale=1, color=col, outline=BLACK)     # 10 x 10 with a 1-px black outline
        # a shade on the lower half of each letter for a bit of depth
        m = pixfont.glyph(ch)
        for y in range(5, 8):
            for x in range(8):
                if m[y, x]: img[y + 1, x + 1, :3] = np.array(shade(col, 0.78), np.uint8)
        save(up(img, GS), 'f/%s_%d.png' % (ck, ord(ch)))
SIZES = {'XXL': 84, 'XL': 52, 'L': 40, 'M': 30, 'S': 22, 'XS': 17}
TEXT_SLOTS = {}
TEXT_ALIGN = {}

def gtext(id_, n, size, color='W', static=None, extra_cls='', align='center'):
    """a pixel-text row: n glyph panels (ids id_0..id_n-1); `static` text fixes the glyph classes in the layout"""
    kids = []
    for k in range(n):
        g = ''
        if static is not None and k < len(static):
            ch = static[k].upper()
            g = ' g%d' % ord(ch if ch in CHARSET else '?')
        kids.append(P('%s_%d' % (id_, k) if id_ and static is None else None, 'G' + g))
    if id_ and static is None: TEXT_SLOTS[id_] = n; TEXT_ALIGN[id_] = align
    return P(id_, ('Txt s%s c%s %s a%s' % (size, color, extra_cls, align)).strip(), kids)

def stext(text, size, color='W', extra_cls='', align='center'):
    return gtext(None, len(text), size, color, static=text, extra_cls=extra_cls, align=align)

# glyph css
rule('.Txt', flow_children='right', height='fit-children')
rule('.Txt.acenter', horizontal_align='center')
rule('.Txt.aleft', horizontal_align='left')
rule('.Txt.aright', horizontal_align='right')
# every cell is always there (blank without a glyph class), so a row never changes size: Panorama doesn't always
# re-place panels when a class changes their layout, but it always redraws a changed background picture.
# Centring / right-aligning is done by the script, padding the text with spaces.
rule('.G', background_size='100% 100%', background_repeat='no-repeat')
for s, px in SIZES.items():
    rule('.s%s .G' % s, width='%dpx' % px, height='%dpx' % px, margin_right='-%dpx' % (px // 10))
for ck in COLORS:
    for ch in CHARSET:
        if ch != ' ': rule('.c%s .G.g%d' % (ck, ord(ch)), background_image='url("%sf/%s_%d.png")' % (IMG, ck, ord(ch)))
raw("@keyframes 'sprblink' { 0% { opacity: 1; } 55% { opacity: 1; } 56% { opacity: 0; } 100% { opacity: 0; } }")
raw("@keyframes 'sprpulse' { 0% { transform: scale3d(1.0, 1.0, 1); } 50% { transform: scale3d(1.06, 1.06, 1); } 100% { transform: scale3d(1.0, 1.0, 1); } }")
raw("@keyframes 'sprpop' { 0% { transform: scale3d(1.6, 1.6, 1); opacity: 0.2; } 100% { transform: scale3d(1.0, 1.0, 1); opacity: 1; } }")
rule('.Txt.blink', animation_name='sprblink', animation_duration='0.6s', animation_iteration_count='infinite', animation_timing_function='linear')
rule('.Txt.pulse', animation_name='sprpulse', animation_duration='0.5s', animation_iteration_count='infinite')

# ---------------------------------------------------------------- pictures: bars, scanlines, frames, logo, minimap dots
def seg_bar(color, segs=20, h=6, w=4):
    """a segmented bar at font-pixel scale: `segs` blocks with 1-px dark gaps and a lighter top row; saved 4x"""
    W_ = segs * (w + 1) + 1
    img = np.zeros((h, W_, 4), np.uint8)
    for k in range(segs):
        x0 = 1 + k * (w + 1)
        img[1:h - 1, x0:x0 + w, :3] = color; img[1:h - 1, x0:x0 + w, 3] = 255
        img[1, x0:x0 + w, :3] = shade(color, 1.35)
        img[h - 2, x0:x0 + w, :3] = shade(color, 0.7)
    return up(img, 4)
BAR_W, BAR_H = 404, 24     # (20 * 5 + 1) * 4 = 404 x 6 * 4
for key, col in (('green', LIME), ('red', RED), ('cyan', ICE), ('gold', GOLD), ('white', WHITE), ('orange', ORANGE), ('pink', PINK), ('dark', INK)):
    save(seg_bar(col), 'bar_%s.png' % key)
# scanlines: every 3rd row dark, alpha
sl = np.zeros((6, 6, 4), np.uint8); sl[0:2, :, 3] = 70
save(sl, 'scan.png')
# a soft vignette in pixel steps
V = 64
yy, xx = np.mgrid[0:V, 0:V]
r = np.hypot((xx + 0.5) / V - 0.5, (yy + 0.5) / V - 0.5) * 2
vg = np.zeros((V, V, 4), np.uint8); vg[..., 3] = (np.clip((r - 0.75) / 0.6, 0, 1) * 160).astype(np.uint8) // 32 * 32
save(up(vg, 4), 'vignette.png')
# boost speed lines: pixel streaks radiating from the centre, only round the edges of the screen (two frames)
def speedlines(seed):
    W_, H_ = 480, 270
    rng = np.random.RandomState(seed)
    img = np.zeros((H_, W_, 4), np.uint8)
    cx, cy = W_ / 2, H_ / 2
    for _ in range(70):
        a = rng.rand() * 2 * np.pi
        r0 = rng.uniform(0.62, 0.85); r1 = r0 + rng.uniform(0.15, 0.45)
        col = (WHITE, ICE, FROST)[rng.randint(3)]
        for k in np.linspace(r0, r1, 120):
            x = int(cx + np.cos(a) * k * W_ * 0.62); y = int(cy + np.sin(a) * k * H_ * 0.62)
            if 0 <= x < W_ and 0 <= y < H_: img[y, x, :3] = col; img[y, x, 3] = 150
    return up(img, 4)
save(speedlines(1), 'speed0.png'); save(speedlines(2), 'speed1.png')

# turn-ahead arrows: one or two chevrons, left or right, blinking for hairpins
def turn_arrow(n, right, col):
    G = 16
    img = np.zeros((G, G * n, 4), np.uint8)
    for k in range(n):
        for y in range(G):
            dx = abs(y - (G - 1) / 2)
            for t in range(4):
                x = int(k * G + 4 + dx * 0.7 + t)
                if x < (k + 1) * G:
                    img[y, x, :3] = col; img[y, x, 3] = 255
    # outline
    a_ = img[..., 3] > 0
    o = np.zeros_like(a_)
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)): o |= np.roll(np.roll(a_, dy, 0), dx, 1)
    img[o & ~a_] = (0, 0, 0, 255)
    if right: img = img[:, ::-1]
    return up(img, 4)
for n in (1, 2):
    for right in (0, 1):
        save(turn_arrow(n, right, GOLD if n == 1 else SALMON), 'turn_%s%d.png' % ('r' if right else 'l', n))

# the SPACE RACER logo: chrome-gradient pixel letters with an outline and a deep drop shadow, synthwave stripes
logo = pixfont.logo
LOGO = logo('SPACE RACER')
save(LOGO, 'logo.png')

# picker car pictures: pixelated versions of cars.py's renders (they are smooth); quantised to the palette
for k in KEYS:
    for side in ('neutral', 't', 'ct'):
        p = os.path.join(IMGDIR, 'car_%s_%s.png' % (k, side))
        if not os.path.exists(p): continue
        im = Image.open(p).convert('RGBA')
        small = np.array(im.resize((64, 64), Image.NEAREST if False else Image.BILINEAR))
        q = quantize_rgba(small, 14)
        # 1-px black outline round the car
        a = q[..., 3] > 0
        o = np.zeros_like(a)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)): o |= np.roll(np.roll(a, dy, 0), dx, 1)
        edge = o & ~a
        q[edge, :3] = BLACK; q[edge, 3] = 255
        save(up(q, 4), 'pcar_%s_%s.png' % (k, side))

# ---------------------------------------------------------------- base
rule('.SprWrap', width='100%', height='100%')
rule('.SprOpts', width='100%', height='100%')
rule('.SprRoot', width='100%', height='100%', visibility='collapse')
rule('.SprRoot.On', visibility='visible')
rule('.SprRoot.Lobby', visibility='visible')
rule('.SprRoot.Pick', visibility='visible')
rule('.SprRoot.Help', visibility='visible')
rule('.SprRoot Label', font_family=FONT, color='#ffffff', text_shadow='2px 2px 0px #000000', text_transform='uppercase', letter_spacing='2px', font_weight='bold')
for c in ('MiniMap', 'TopBlock', 'ClockBox', 'Bars', 'Speed', 'Stand'):
    rule('.' + c, visibility='collapse')
    rule('.SprRoot.On .' + c, visibility='visible')
rule('.LobbyLines', visibility='collapse'); rule('.SprRoot.Lobby .LobbyLines', visibility='visible')
rule('.Logo', visibility='collapse'); rule('.SprRoot.Lobby .Logo', visibility='visible')
rule('.Pick', visibility='collapse'); rule('.SprRoot.Pick .Pick', visibility='visible')
rule('.Help', visibility='collapse'); rule('.SprRoot.Help .Help', visibility='visible')
rule('.SprRoot.Spec .Bars', opacity='0.75')
# CRT overlay (on unless the player turns it off with !crt)
rule('.Crt', width='100%', height='100%', background_image='url("%sscan.png")' % IMG, background_size='6px 6px', background_repeat='repeat', opacity='0.55')
rule('.Vig', width='100%', height='100%', background_image='url("%svignette.png")' % IMG, background_size='100% 100%', opacity='0.9')
rule('.SprOpts.nocrt .Crt', visibility='collapse')
for k in (0, 1):
    rule('.Speed%d' % k, width='100%', height='100%', background_image='url("%sspeed%d.png")' % (IMG, k), background_size='100% 100%',
         visibility='collapse', animation_name='sprblink', animation_duration='0.16s', animation_iteration_count='infinite',
         animation_delay='%.2fs' % (k * 0.08))
    rule('.SprRoot.Boost .Speed%d' % k, visibility='visible')
rule('.SprOpts.nocrt .Vig', visibility='collapse')

# full-screen flash
rule('.Flash', width='100%', height='100%', background_color='#00000000', transition_property='background-color', transition_duration='0.08s')
rule('.Flash.hit', background_color='#ff303040')
rule('.Flash.pulse', background_color='#40e0ff38')
rule('.Flash.wreck', background_color='#ff600080')

FRAME = {'cyan': TEAL, 'gold': GOLD, 'pink': MAGENTA, 'white': LILAC, 'orange': ORANGE, 'blue': SKYBLUE}
def hexc(c, a=None): return '#%02x%02x%02x' % tuple(c) + ('%02x' % a if a is not None else '')
def framed(key):
    """a hard pixel frame: a 4-px border in a palette colour round a dark see-through box"""
    return dict(border='4px solid %s' % hexc(FRAME[key]), background_color=hexc(INK, 216))

# minimap: the pixel track (per track image) with a square dot for the player and the leader
MM = 200
rule('.MiniMap', width='%dpx' % (MM + 16), height='%dpx' % (MM + 16), margin_left='24px', margin_top='24px', **framed('cyan'))
rule('.MapImg', width='%dpx' % MM, height='%dpx' % MM, margin='8px', background_size='100% 100%', background_repeat='no-repeat')
for tid in [t['id'] for t in json.load(open(os.path.join(OUT, '_gen/tracks.json')))]:
    rule('.MapImg.mm_%s' % tid, background_image='url("%smm_%s.png")' % (IMG, tid))
# dots are moved with transforms (a margin change through a class isn't always re-laid out): x on the outer panel,
# y on the inner square
rule('.Dot', width='12px', height='12px', visibility='collapse')
rule('.Dot.On', visibility='visible')
rule('.DotSq', width='12px', height='12px', background_color='#ffffff', border='2px solid #000000')
rule('.Dot.me .DotSq', animation_name='sprblink', animation_duration='0.5s', animation_iteration_count='infinite')
rule('.Dot.Lead .DotSq', background_color='#ffbe28')
for i in range(24):
    rule('.Dot.dx%d' % i, transform='translatex(%dpx)' % int(i * MM / 23 - 6))
    rule('.DotSq.dy%d' % i, transform='translatey(%dpx)' % int(i * MM / 23 - 6))

# top block: big position + suffix + of, and the lap line
rule('.TopBlock', horizontal_align='center', margin_top='14px', flow_children='down', width='620px')
rule('.PosRow', horizontal_align='center', flow_children='right')
rule('.PosRow .Txt', vertical_align='bottom')
rule('#spr_suf', margin_bottom='12px', margin_left='4px')
rule('#spr_posof', margin_bottom='12px', margin_left='12px')
rule('#spr_pos', animation_name='sprpop', animation_duration='0.25s')
rule('#spr_lap', margin_top='4px')
rule('.Turn', horizontal_align='center', margin_top='6px', height='64px', width='128px', background_size='contain', background_repeat='no-repeat', background_position='center', visibility='collapse')
for side in ('l', 'r'):
    for n in (1, 2):
        rule('.Turn.%s%d' % (side, n), visibility='visible', background_image='url("%sturn_%s%d.png")' % (IMG, side, n))
rule('.Turn.l2', animation_name='sprblink', animation_duration='0.4s', animation_iteration_count='infinite')
rule('.Turn.r2', animation_name='sprblink', animation_duration='0.4s', animation_iteration_count='infinite')
rule('.ClockBox', horizontal_align='right', margin_right='26px', margin_top='22px', flow_children='down', padding='10px 14px 8px 14px', **framed('pink'))
rule('.ClockBox .Txt', horizontal_align='right')

# centre messages
rule('.Ctr', horizontal_align='center', vertical_align='center', margin_top='-170px')
rule('.Ctr2', horizontal_align='center', vertical_align='center', margin_top='-150px')
rule('.Sub', horizontal_align='center', vertical_align='center', margin_top='-90px')
rule('.Msg', horizontal_align='center', vertical_align='bottom', margin_bottom='128px')

# bars (bottom left): segmented pixel bars, clipped by width classes
rule('.Bars', vertical_align='bottom', margin_left='30px', margin_bottom='36px', flow_children='down', padding='12px 14px 6px 14px', **framed('cyan'))
rule('.BarRow', flow_children='down', margin_bottom='8px')
rule('.Bar', width='%dpx' % BAR_W, height='%dpx' % BAR_H, background_image='url("%sbar_dark.png")' % IMG, background_size='%dpx %dpx' % (BAR_W, BAR_H), margin_top='3px')
rule('.Fill', height='100%', width='0%', background_size='%dpx %dpx' % (BAR_W, BAR_H), background_repeat='no-repeat', background_position='0px 0px')
for i in range(21): rule('.Fill.w%d' % i, width='%dpx' % (20 * i + 2) if i else '0px')     # whole segments: 20 px each at 4x
def barimg(key): return 'url("%sbar_%s.png")' % (IMG, key)
rule('#spr_shfill', background_image=barimg('green'))
rule('#spr_shield.low #spr_shfill', background_image=barimg('red'))
rule('#spr_shield.low', animation_name='sprblink', animation_duration='0.8s', animation_iteration_count='infinite')
rule('#spr_chfill', background_image=barimg('cyan'))
rule('#spr_charge.boosting #spr_chfill', background_image=barimg('gold'))
rule('#spr_charge.charging #spr_chfill', background_image=barimg('pink'))

# speed (bottom right)
rule('.Speed', vertical_align='bottom', horizontal_align='right', margin_right='30px', margin_bottom='36px', flow_children='down', padding='12px 14px 8px 14px', **framed('gold'))
rule('.SpdRow', flow_children='right', horizontal_align='right')
rule('.SpdRow .Txt', vertical_align='bottom')
rule('#spr_spfill', background_image=barimg('white'))
rule('.Speed.pad #spr_spfill', background_image=barimg('orange'))
rule('.Speed.pad', **framed('orange'))

# standings (right): rows with a side-coloured tab; names are Labels
rule('.Stand', horizontal_align='right', vertical_align='center', margin_right='24px', margin_top='-30px', flow_children='down', width='340px', padding='10px', **framed('white'))
rule('.StRow', width='320px', height='32px', margin_bottom='3px', flow_children='right', background_color='#14102480')
rule('.StTab', width='8px', height='100%', background_color='#5a4670')
rule('.StRow.T .StTab', background_color='#dc781e')
rule('.StRow.CT .StTab', background_color='#3c78dc')
rule('.StRow.me', background_color='#ffffff38')
rule('.StRow.me .StTab', background_color='#ffffff')
rule('.StName', font_size='19px', color='#ffffff', margin_top='5px', margin_left='8px')
rule('.StRow.me .StName', color='#ffbe28')

# the car picker
rule('.Pick', horizontal_align='center', vertical_align='bottom', margin_bottom='160px', flow_children='down', width='1180px')
rule('.Cards', horizontal_align='center', flow_children='right', margin_top='10px')
rule('.Card', width='270px', height='350px', margin_left='8px', margin_right='8px', flow_children='down', padding='12px', **framed('white'))
rule('.Card.sel', transform='scale3d(1.07, 1.07, 1)', **framed('gold'))
rule('.Card.sel .CarPic', animation_name='sprpulse', animation_duration='0.9s', animation_iteration_count='infinite')
rule('.CarPic', width='200px', height='200px', horizontal_align='center', background_size='100% 100%', background_repeat='no-repeat')
for k in KEYS:
    for side in ('neutral', 't', 'ct'):
        rule('.CarPic.pic_%s_%s' % (k, side), background_image='url("%spcar_%s_%s.png")' % (IMG, k, side))
rule('.StatRow', flow_children='right', margin_top='4px', horizontal_align='center')
rule('.StatBar', width='130px', height='12px', margin_top='4px', margin_left='6px', background_image='url("%sbar_dark.png")' % IMG, background_size='%dpx 12px' % (BAR_W // 3 + 1))
rule('.StatFill', height='100%', background_image=barimg('gold'), background_size='%dpx 12px' % (BAR_W // 3 + 1), background_repeat='no-repeat')
def stat(lo, hi, v): return int(100 * (v - lo) / (hi - lo))
for k in KEYS:
    c = cars[k]
    c['s_speed'] = stat(950, 1150, c['maxSpeed'] * c['boost'] / 1.3)
    c['s_accel'] = stat(420, 690, c['accel'])
    c['s_turn'] = stat(1.9, 2.9, c['turn'])
    c['s_shield'] = stat(70, 140, c['shield'])
    c['s_charge'] = stat(90, 150, c['charge'])
for k in KEYS:
    for nm in ('speed', 'accel', 'turn', 'shield', 'charge'):
        v = max(10, min(100, cars[k]['s_' + nm]))
        rule('.StatFill.%s_%s' % (k, nm), width='%dpx' % int(round(v / 5) * 5 * 1.3))

# lobby: the logo and three pixel lines
rule('.Logo', horizontal_align='center', vertical_align='top', margin_top='80px', width='%dpx' % (LOGO.shape[1] * 1.1), height='%dpx' % (LOGO.shape[0] * 1.1),
     background_image='url("%slogo.png")' % IMG, background_size='100% 100%', background_repeat='no-repeat',
     animation_name='sprpulse', animation_duration='2.4s', animation_iteration_count='infinite')
RES = pixfont.logo('RESULTS', 6)
save(RES, 'logo_results.png')
rule('.ResLogo', visibility='collapse', horizontal_align='center', vertical_align='top', margin_top='150px', width='%dpx' % RES.shape[1], height='%dpx' % RES.shape[0],
     background_image='url("%slogo_results.png")' % IMG, background_size='100% 100%', animation_name='sprpulse', animation_duration='1.2s', animation_iteration_count='infinite')
rule('.SprRoot.Res .ResLogo', visibility='visible')
rule('.SprRoot.Res .TopBlock', visibility='collapse')
rule('.LobbyLines', horizontal_align='center', vertical_align='bottom', margin_bottom='34px', flow_children='down', width='1600px')
rule('.LobbyLines .Txt', margin_bottom='8px')

# help box
rule('.Help', horizontal_align='center', vertical_align='center', margin_top='110px', flow_children='down', padding='22px', **framed('cyan'))
rule('.Help .Txt', margin_bottom='6px')

# ---------------------------------------------------------------- xml
cards = []
for i, k in enumerate(KEYS):
    c = cars[k]
    cards.append(P('spr_card%d' % i, 'Card', [
        P('spr_cimg%d' % i, 'CarPic pic_%s_neutral' % k),
        stext(c['name'], 'L', 'W'),
        stext(c['perk'], 'XS', 'C'),
    ] + [P(None, 'StatRow', [stext(nm.upper().ljust(6), 'XS', 'C'), P(None, 'StatBar', [P(None, 'StatFill %s_%s' % (k, nm))])])
         for nm in ('speed', 'accel', 'turn', 'shield', 'charge')]))
pick = P('spr_pick', 'Pick', [stext('CHOOSE YOUR MACHINE   A / D', 'M', 'Y', 'blink'), P(None, 'Cards', cards)])
stand = P(None, 'Stand', [P('spr_st%d' % i, 'StRow', [P(None, 'StTab'), L('spr_stn%d' % i, 'StName')]) for i in range(8)])
HELP = [('SPACE RACER - HOW TO DRIVE', 'Y'), ('W / S    GAS / BRAKE', 'W'), ('A / D    STEER', 'W'), ('MOUSE 1  BOOST (USES CHARGE)', 'W'),
        ('MOUSE 2  SPIN ATTACK', 'W'), ('SPACE    DRIFT (FILLS CHARGE)', 'W'), ('', 'W'), ('GOLD PADS: FREE SPEED', 'Y'), ('CYAN PADS: CHARGE + SHIELD', 'C'),
        ('RAMPS: HIT THEM FAST!', 'R'), ('BANKED BENDS GRIP HARDER', 'G'), ('', 'W'), ('!CAR 1-4  !CAM  !CRT  !MUSIC', 'P'), ('!SPEC  !AFK  !BACK  !RACE', 'P')]
help_ = P('spr_help', 'Help', [stext(t or ' ', 'S', c, align='left') for t, c in HELP])
# never shown: these make CS2 compile the loading screen picture, the radar and the map icon along with the HUD
for cls, src in (('SprPre1', 'map_icons/screenshots/1080p/%s.png' % MAP), ('SprPre2', 'overheadmaps/%s_radar.psd' % MAP),
                 ('SprPre3', 'map_icons/map_icon_%s.svg' % MAP)):
    rule('.' + cls, width='1px', height='1px', opacity='0', visibility='collapse', background_image='url("file://{images}/%s")' % src)
rule('.SprPreload', width='1px', height='1px', visibility='collapse')
root = P('spr_root', 'SprRoot', [
    P(None, 'SprPreload', [P(None, 'SprPre1'), P(None, 'SprPre2'), P(None, 'SprPre3')]),
    P('spr_flash', 'Flash'),
    P(None, 'Speed0'), P(None, 'Speed1'),
    P(None, 'Logo'),
    P(None, 'ResLogo'),
    P('spr_mm', 'MiniMap', [P('spr_mmimg', 'MapImg', [P('spr_ldot', 'Dot Lead', [P('spr_ldoty', 'DotSq')]), P('spr_dot', 'Dot me', [P('spr_doty', 'DotSq')])])]),
    P(None, 'TopBlock', [
        P(None, 'PosRow', [gtext('spr_pos', 2, 'XXL', 'W', align='right'), gtext('spr_suf', 2, 'L', 'W', align='left'), gtext('spr_posof', 3, 'M', 'P', align='left')]),
        gtext('spr_lap', 9, 'M', 'Y'),
        P('spr_turn', 'Turn'),
    ]),
    P(None, 'ClockBox', [stext('TIME', 'XS', 'P', align='right'), gtext('spr_clock', 7, 'M', 'W', align='right')]),
    gtext('spr_ctr', 20, 'XL', 'W', extra_cls='Ctr'),
    gtext('spr_ctr2', 40, 'M', 'W', extra_cls='Ctr2'),
    gtext('spr_sub', 52, 'S', 'W', extra_cls='Sub'),
    gtext('spr_msg', 48, 'S', 'C', extra_cls='Msg'),
    P(None, 'Bars', [
        P(None, 'BarRow', [stext('SHIELD', 'S', 'G', align='left'), P('spr_shield', 'Bar', [P('spr_shfill', 'Fill')])]),
        P(None, 'BarRow', [stext('CHARGE', 'S', 'C', align='left'), P('spr_charge', 'Bar', [P('spr_chfill', 'Fill')])]),
    ]),
    P('spr_speed', 'Speed', [P(None, 'SpdRow', [gtext('spr_spd', 4, 'XL', 'W', align='right'), stext(' KM/H', 'S', 'Y')]), P(None, 'Bar', [P('spr_spfill', 'Fill')])]),
    stand,
    pick,
    P(None, 'LobbyLines', [gtext('spr_lob1', 60, 'S', 'W'), gtext('spr_lob2', 60, 'S', 'Y'), gtext('spr_lob3', 60, 'S', 'C')]),
    help_,
    P(None, 'Vig'),
    P(None, 'Crt'),
])
doc = ('<root>\n\t<styles>\n\t\t<include src="file://{resources}/styles/custom_game/%s.css" />\n\t</styles>\n'
       '\t<Panel class="SprWrap" hittest="false">\n' % NAME + P('spr_opts', 'SprOpts', [root]) + '\n\t</Panel>\n</root>\n')
os.makedirs(os.path.join(OUT, 'panorama/layout/custom_game'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'panorama/styles/custom_game'), exist_ok=True)
open(os.path.join(OUT, 'panorama/layout/custom_game/%s.xml' % NAME), 'w', newline='\n').write(doc)
open(os.path.join(OUT, 'panorama/styles/custom_game/%s.css' % NAME), 'w', newline='\n').write('\n'.join(css) + '\n')
ids = re.findall(r'id="([^"]+)"', doc)
json.dump(sorted(set(ids)), open(os.path.join(OUT, '_gen/hud_ids.json'), 'w'))
json.dump(dict(slots=TEXT_SLOTS, align=TEXT_ALIGN, charset=CHARSET, colors=sorted(COLORS)), open(os.path.join(OUT, '_gen/hud_text.json'), 'w'))
print('hud: %d css rules, %d panel ids, %d text rows, %d glyph pictures' % (len(css), len(set(ids)), len(TEXT_SLOTS), len(COLORS) * (len(CHARSET) - 1)))
