"""Space Racer HUD for CS2 Panorama (custom_hud_layout): layout xml + css.

usage: hud.py <addon_out_dir> [name]
The script swaps classes and sets dialog variables (every Label shows {s:v}); see src/cs2/30_hud.js for the ids.
"""
import os, sys, re, json
import numpy as np
from PIL import Image

OUT = sys.argv[1]
NAME = sys.argv[2] if len(sys.argv) > 2 else 'space_racer'
IMG = 'file://{images}/custom_game/spr/'
FONT = 'Stratum2, "Stratum2 Bold", Arial'
css = []
def rule(sel, **props):
    body = ' '.join('%s: %s;' % (k.replace('_', '-'), v) for k, v in props.items())
    css.append('%s { %s }' % (sel, body))

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

# the car numbers for the picker's stat bars come from the game's own table
defs = open(os.path.join(os.path.dirname(__file__), '..', 'src/core/00_defs.js')).read()
cars = {}
for m in re.finditer(r"(\w+):\s*\{ key: '(\w+)',\s*name: '(\w+)',(.*?)perk: '([^']+)', desc: '([^']+)'", defs, re.S):
    key, name, body, perk, desc = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)
    kv = dict((k, float(v)) for k, v in re.findall(r"(\w+): ([\d.]+)", body))
    cars[key] = dict(name=name, perk=perk, desc=desc, **kv)
KEYS = ['hornet', 'meteor', 'comet', 'bastion']
assert all(k in cars for k in KEYS), cars.keys()

# ---------------------------------------------------------------- base
rule('.SprWrap', width='100%', height='100%')
rule('.SprOpts', width='100%', height='100%')
rule('.SprRoot', width='100%', height='100%', visibility='collapse')
rule('.SprRoot.On', visibility='visible')
rule('.SprRoot.Lobby', visibility='visible')
rule('.SprRoot.Pick', visibility='visible')
rule('.SprRoot.Help', visibility='visible')
rule('.SprRoot Label', font_family=FONT, color='#ffffff', text_shadow='0px 1px 4px #000000cc', text_transform='uppercase', letter_spacing='1px')
# which parts show in which mode (Panorama has no :not(), so parts are hidden by default and shown per mode)
for c in ('MiniMap', 'TopBlock', 'Clock', 'Bars', 'Speed', 'Stand'):
    rule('.' + c, visibility='collapse')
    rule('.SprRoot.On .' + c, visibility='visible')
rule('.LobbyLines', visibility='collapse'); rule('.SprRoot.Lobby .LobbyLines', visibility='visible')
rule('.Pick', visibility='collapse'); rule('.SprRoot.Pick .Pick', visibility='visible')
rule('.Help', visibility='collapse'); rule('.SprRoot.Help .Help', visibility='visible')
rule('.SprRoot.Spec .Bars', opacity='0.75')

# full-screen flash
rule('.Flash', width='100%', height='100%', background_color='#00000000', transition_property='background-color', transition_duration='0.08s')
rule('.Flash.hit', background_color='#ff303040')
rule('.Flash.pulse', background_color='#40e0ff38')
rule('.Flash.wreck', background_color='#ff600080')

# minimap: the track outline (per track image) with the player's dot and the leader's dot
MM = 200
rule('.MiniMap', width='%dpx' % MM, height='%dpx' % MM, margin_left='28px', margin_top='28px', background_size='100% 100%', background_repeat='no-repeat', opacity='0.9')
for tid in ('oval', 'hairpin', 'crosswire', 'nullgap', 'spire', 'ringworld'):
    rule('.MiniMap.mm_%s' % tid, background_image='url("%smm_%s.png")' % (IMG, tid))
rule('.Dot', width='14px', height='14px', border_radius='7px', background_color='#ffffff', visibility='collapse', box_shadow='0px 0px 6px #000000')
rule('.Dot.On', visibility='visible')
rule('.Dot.Lead', width='10px', height='10px', border_radius='5px', background_color='#ffd040', margin_left='2px', margin_top='2px')
for i in range(24):
    rule('.Dot.dx%d' % i, margin_left='%dpx' % int(i * MM / 23 - 7))
    rule('.Dot.dy%d' % i, margin_top='%dpx' % int(i * MM / 23 - 7))
rule('.Dot.Lead.dx%d' % 0, margin_left='-5px')   # (the leader dot uses the same classes; offsets differ by 2px, fine)

# top block: position, of, lap
rule('.TopBlock', horizontal_align='center', margin_top='18px', flow_children='down', width='400px')
rule('.PosRow', horizontal_align='center', flow_children='right')
rule('.Pos', font_size='74px', font_weight='bold', color='#ffffff', horizontal_align='center', text_align='center')
rule('.PosOf', font_size='30px', color='#d0d4e0', margin_left='8px', margin_top='34px')
rule('.Lap', font_size='26px', color='#ffd040', horizontal_align='center', text_align='center', margin_top='-6px')
rule('.Clock', horizontal_align='right', margin_right='30px', margin_top='24px', font_size='28px', color='#d0d4e0')

# centre messages
rule('.Ctr', horizontal_align='center', vertical_align='center', margin_top='-160px', font_size='58px', font_weight='bold', color='#ffffff', text_align='center', width='1400px')
rule('.Ctr.red', color='#ff5050')
rule('.Ctr.green', color='#60ff80')
rule('.Ctr.gold', color='#ffd040')
rule('.Sub', horizontal_align='center', vertical_align='center', margin_top='-80px', font_size='22px', color='#e8ecf4', text_align='center', width='1500px')
rule('.Msg', horizontal_align='center', vertical_align='bottom', margin_bottom='120px', font_size='26px', color='#80f0ff', text_align='center', width='1200px')

# bars (bottom left)
rule('.Bars', vertical_align='bottom', margin_left='40px', margin_bottom='48px', flow_children='down', width='420px')
rule('.BarRow', flow_children='right', margin_bottom='8px')
rule('.BarName', width='100px', font_size='20px', color='#d0d4e0', margin_top='2px')
rule('.Bar', width='300px', height='24px', background_color='#101420cc', border='2px solid #ffffff40', border_radius='4px')
rule('.Fill', height='100%', width='0%', background_color='#ffffff', transition_property='width', transition_duration='0.1s')
for i in range(21): rule('.Fill.w%d' % i, width='%d%%' % (i * 5))
rule('#spr_shfill', background_color='#60ff80')
rule('#spr_shield.low #spr_shfill', background_color='#ff4040')
rule('#spr_chfill', background_color='#40c0ff')
rule('#spr_charge.boosting #spr_chfill', background_color='#ffe060')
rule('#spr_charge.boosting', border='2px solid #ffe060')
rule('#spr_charge.charging #spr_chfill', background_color='#80ffff')

# speed (bottom right)
rule('.Speed', vertical_align='bottom', horizontal_align='right', margin_right='40px', margin_bottom='48px', flow_children='down', width='320px')
rule('.Spd', font_size='64px', font_weight='bold', color='#ffffff', horizontal_align='right', text_align='right')
rule('.SpdUnit', font_size='18px', color='#d0d4e0', horizontal_align='right', text_align='right', margin_top='-10px')
rule('.Speed .Bar', margin_top='6px', horizontal_align='right')
rule('#spr_spfill', background_color='#ffffff')
rule('.Speed.pad #spr_spfill', background_color='#ffb030')

# standings (right)
rule('.Stand', horizontal_align='right', vertical_align='center', margin_right='30px', margin_top='-40px', flow_children='down', width='330px')
rule('.StRow', width='330px', height='30px', margin_bottom='4px', background_color='#10141ea0', border_radius='4px', padding_left='10px')
rule('.StRow.T', background_color='#8a4a10a0')
rule('.StRow.CT', background_color='#1a4a90a0')
rule('.StRow.me', border='2px solid #ffffff', background_color='#ffffff30')
rule('.StRow.T.me', background_color='#c06a20d0')
rule('.StRow.CT.me', background_color='#2a6ad0d0')
rule('.StName', font_size='20px', color='#ffffff', margin_top='3px')

# the car picker
rule('.Pick', horizontal_align='center', vertical_align='bottom', margin_bottom='170px', flow_children='down', width='1100px')
rule('.PickTitle', horizontal_align='center', font_size='26px', color='#ffd040', text_align='center', margin_bottom='10px')
rule('.Cards', horizontal_align='center', flow_children='right')
rule('.Card', width='250px', height='330px', margin_left='8px', margin_right='8px', background_color='#10141ec0', border='2px solid #ffffff30', border_radius='8px', flow_children='down', padding='10px', transition_property='transform, border', transition_duration='0.12s')
rule('.Card.sel', border='3px solid #ffd040', background_color='#2a2a10e0', transform='scale3d(1.06, 1.06, 1)')
rule('.CarPic', width='220px', height='160px', horizontal_align='center', background_size='contain', background_repeat='no-repeat', background_position='center')
for k in KEYS:
    for side in ('neutral', 't', 'ct'):
        rule('.CarPic.pic_%s_%s' % (k, side), background_image='url("%scar_%s_%s.png")' % (IMG, k, side))
rule('.CarName', font_size='26px', font_weight='bold', color='#ffffff', horizontal_align='center', text_align='center')
rule('.CarPerk', font_size='16px', color='#80f0ff', horizontal_align='center', text_align='center', margin_bottom='6px')
rule('.StatRow', flow_children='right', margin_top='3px')
rule('.StatName', width='70px', font_size='14px', color='#d0d4e0')
rule('.StatBar', width='150px', height='10px', background_color='#00000080', border_radius='3px', margin_top='3px')
rule('.StatFill', height='100%', background_color='#ffd040', border_radius='3px')
def stat(k, lo, hi, v):
    return int(100 * (v - lo) / (hi - lo))
maxes = {}
for k in KEYS:
    c = cars[k]
    c['s_speed'] = stat(k, 880, 1040, c['maxSpeed'] * c['boost'] / 1.3)
    c['s_accel'] = stat(k, 380, 620, c['accel'])
    c['s_turn'] = stat(k, 1.9, 2.9, c['turn'])
    c['s_shield'] = stat(k, 70, 140, c['shield'])
    c['s_charge'] = stat(k, 90, 150, c['charge'])
for k in KEYS:
    for nm in ('speed', 'accel', 'turn', 'shield', 'charge'):
        rule('.StatFill.%s_%s' % (k, nm), width='%d%%' % max(8, min(100, cars[k]['s_' + nm])))

# lobby lines
rule('.LobbyLines', horizontal_align='center', vertical_align='bottom', margin_bottom='40px', flow_children='down', width='1600px')
rule('.Lob1', font_size='28px', color='#ffffff', horizontal_align='center', text_align='center', margin_bottom='4px')
rule('.Lob2', font_size='22px', color='#ffd040', horizontal_align='center', text_align='center', margin_bottom='4px')
rule('.Lob3', font_size='22px', color='#80f0ff', horizontal_align='center', text_align='center')

# help box
rule('.Help', horizontal_align='center', vertical_align='center', margin_top='120px', width='760px', background_color='#10141ed8', border='2px solid #ffffff40', border_radius='8px', padding='16px', flow_children='down')
rule('.HelpLine', font_size='20px', color='#ffffff', margin_bottom='4px')
rule('.HelpTitle', font_size='26px', color='#ffd040', margin_bottom='8px', horizontal_align='center')

# ---------------------------------------------------------------- xml
cards = []
for i, k in enumerate(KEYS):
    c = cars[k]
    cards.append(P('spr_card%d' % i, 'Card', [
        P('spr_cimg%d' % i, 'CarPic pic_%s_neutral' % k),
        L(None, 'CarName', c['name']),
        L(None, 'CarPerk', c['perk']),
    ] + [P(None, 'StatRow', [L(None, 'StatName', nm.upper()), P(None, 'StatBar', [P(None, 'StatFill %s_%s' % (k, nm))])])
         for nm in ('speed', 'accel', 'turn', 'shield', 'charge')]))
pick = P('spr_pick', 'Pick', [L(None, 'PickTitle', 'CHOOSE YOUR CAR:  A / D   (OR !CAR 1-4)'), P(None, 'Cards', cards)])
stand = P(None, 'Stand', [P('spr_st%d' % i, 'StRow', [L('spr_stn%d' % i, 'StName')]) for i in range(8)])
help_ = P('spr_help', 'Help', [L(None, 'HelpTitle', 'SPACE RACER - CONTROLS')] + [L(None, 'HelpLine', t) for t in (
    'W / S  ACCELERATE / BRAKE AND REVERSE', 'A / D  STEER (PICK A CAR WHEN NOT RACING)', 'MOUSE 1  BOOST (USES CHARGE)',
    'MOUSE 2  SPIN ATTACK (COSTS CHARGE)', 'SPACE  DRIFT', 'BOOST PADS: FREE SPEED.  CHARGE PLATFORMS: REFILL CHARGE AND SHIELD',
    'THE PULSE: A WAVE FROM THE BACK OF THE FIELD TOPS UP EVERYONE IT PASSES', 'SPECTATING: MOUSE 1 / 2 CHANGE CAR, E CHANGE ARENA',
    'CHAT: !CAR 1-4   !SPEC   !AFK   !BACK   !RACE')])
root = P('spr_root', 'SprRoot', [
    P('spr_flash', 'Flash'),
    P('spr_mm', 'MiniMap', [P('spr_dot', 'Dot'), P('spr_ldot', 'Dot Lead')]),
    P(None, 'TopBlock', [P(None, 'PosRow', [L('spr_pos', 'Pos'), L('spr_posof', 'PosOf')]), L('spr_lap', 'Lap')]),
    L('spr_clock', 'Clock'),
    L('spr_ctr', 'Ctr'),
    L('spr_sub', 'Sub'),
    L('spr_msg', 'Msg'),
    P(None, 'Bars', [
        P(None, 'BarRow', [L(None, 'BarName', 'SHIELD'), P('spr_shield', 'Bar', [P('spr_shfill', 'Fill')])]),
        P(None, 'BarRow', [L(None, 'BarName', 'CHARGE'), P('spr_charge', 'Bar', [P('spr_chfill', 'Fill')])]),
    ]),
    P('spr_speed', 'Speed', [L('spr_spd', 'Spd'), L(None, 'SpdUnit', 'KM/H'), P(None, 'Bar', [P('spr_spfill', 'Fill')])]),
    stand,
    pick,
    P(None, 'LobbyLines', [L('spr_lob1', 'Lob1'), L('spr_lob2', 'Lob2'), L('spr_lob3', 'Lob3')]),
    help_,
])
doc = ('<root>\n\t<styles>\n\t\t<include src="file://{resources}/styles/custom_game/%s.css" />\n\t</styles>\n'
       '\t<Panel class="SprWrap" hittest="false">\n' % NAME + P('spr_opts', 'SprOpts', [root]) + '\n\t</Panel>\n</root>\n')
os.makedirs(os.path.join(OUT, 'panorama/layout/custom_game'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'panorama/styles/custom_game'), exist_ok=True)
open(os.path.join(OUT, 'panorama/layout/custom_game/%s.xml' % NAME), 'w', newline='\n').write(doc)
open(os.path.join(OUT, 'panorama/styles/custom_game/%s.css' % NAME), 'w', newline='\n').write('\n'.join(css) + '\n')
ids = re.findall(r'id="([^"]+)"', doc)
json.dump(sorted(set(ids)), open(os.path.join(OUT, '_gen/hud_ids.json'), 'w'))
print('hud: %d css rules, %d panel ids' % (len(css), len(set(ids))))
