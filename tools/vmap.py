"""Writes the whole Space Racer map into a Hammer map (binary DMX .vmap): the six track props in their boxes in the
void, a moondome (starfield sky shell) and tools/skybox shell around each box, vis hints, the lobby, the pawn booth,
the model cache room, spawns and every entity the script needs.

usage: vmap.py <template_or_current.vmap> <out.vmap> <addon_out_dir> [script_name]

Everything written is tagged with the vis group "spr_env", so running it again on a map you have edited in Hammer
replaces only its own work and keeps your changes. Hammer's sample entities (unnamed point_script etc.) and the
default box are dropped the first time.
"""
import os, sys, json, math
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import dmx
from vmaplib import *
import vmaplib

SRC, OUTPATH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
NAME = sys.argv[4] if len(sys.argv) > 4 else 'space_racer'
GROUP = 'spr_env'
SCRIPT_PATH = 'maps/scripts/%s.vjs' % NAME
HUD_PATH = 'panorama/layout/custom_game/%s.vxml' % NAME
BOX = 7000
MOONDOME = 'materials/spr/sky/moondome.vmat'
TOOLSSKY = 'materials/tools/toolsskybox.vmat'
HINT_LOWEST, HINT_LOW = 9, 3
LZ = -12000

tracks = json.load(open(os.path.join(OUT, '_gen/track_props.json')))
cars = json.load(open(os.path.join(OUT, '_gen/car_models.json')))
SOUNDS = [l.split('"')[1][4:] for l in open(os.path.join(OUT, 'soundevents/soundevents_addon.vsndevts')) if l.strip().startswith('"spr.')]

d = dmx.DMX.load(SRC)
root = d.root
world = root.get('world')
vmaplib.init(d, OUT)

# ---------------------------------------------------------------- sky: a starfield with a faint nebula (original, generated)
def sky():
    H, W = 1024, 2048
    rng = np.random.RandomState(42)
    img = np.zeros((H, W, 3), np.float32)
    lat = (0.5 - (np.arange(H) + 0.5) / H)[:, None]
    lon = ((np.arange(W) + 0.5) / W)[None, :]
    # deep blue-black with a nebula band
    band = np.exp(-((lat - 0.08 * np.sin(lon * 2 * math.pi * 2)) / 0.22) ** 2)
    img[..., 0] = 6 + 28 * band; img[..., 1] = 8 + 14 * band; img[..., 2] = 18 + 48 * band
    blobs = rng.rand(14, 5)
    for bx, by, br, bc, bi in blobs:
        cx, cy = bx * W, (0.25 + by * 0.5) * H
        yy, xx = np.mgrid[0:H, 0:W]
        dx = np.minimum(np.abs(xx - cx), W - np.abs(xx - cx)) / (W * 0.08 * (0.5 + br)); dy = (yy - cy) / (H * 0.07 * (0.5 + br))
        g = np.exp(-(dx * dx + dy * dy)) * 40 * bi
        col = np.array([[0.9, 0.3, 0.8], [0.3, 0.6, 1.0], [1.0, 0.6, 0.3]][int(bc * 3) % 3])
        img += g[..., None] * col[None, None, :]
    # stars
    n = 9000
    sx = rng.randint(0, W, n); sy = rng.randint(0, H, n); sb = rng.rand(n) ** 3 * 255
    img[sy, sx] += sb[:, None] * np.array([0.9, 0.95, 1.0])[None, :]
    big = rng.rand(n) < 0.06
    for k in np.where(big)[0]:
        x, y = sx[k], sy[k]
        img[max(0, y - 1):y + 2, max(0, x - 1):x + 2] += sb[k] * 0.5
    dd = os.path.join(OUT, 'materials/spr/sky'); os.makedirs(dd, exist_ok=True)
    Image.fromarray(img.clip(0, 255).astype(np.uint8)).save(os.path.join(dd, 'sky_color.png'))
    open(os.path.join(dd, 'sky.vmat'), 'w', newline='\n').write('// Space Racer sky\nLayer0\n{\n\tshader "sky.vfx"\n\tF_TEXTURE_FORMAT2 1\n\tSkyTexture "materials/spr/sky/sky_color.png"\n\tg_flBrightnessExposureBias "0.000"\n}\n')
    open(os.path.join(dd, 'moondome.vmat'), 'w', newline='\n').write('''// Space Racer moondome: mesh material that shows the sky (same panorama as env_sky), unlit, no shadows, no fog
Layer0
{
	shader "csgo_moondome.vfx"
	F_DO_NOT_CAST_SHADOWS 1
	g_vColorTint "[1.000000 1.000000 1.000000 0.000000]"
	TextureColor "materials/spr/sky/moondome_color.png"
	g_flCubeParallax "0.000"
	g_bFogEnabled "0"
	TextureCubeMap "materials/spr/sky/sky_color.png"
}
''')
    Image.new('RGB', (16, 16), (255, 255, 255)).save(os.path.join(dd, 'moondome_color.png'))
sky()

# lobby materials (dark panels with a thin light line)
def lobby_mats():
    dd = os.path.join(OUT, 'materials/spr'); os.makedirs(dd, exist_ok=True)
    for name, col, line in (('lobby_wall', (24, 28, 40), (60, 200, 255)), ('lobby_floor', (18, 20, 30), (40, 60, 90)), ('lobby_ceil', (12, 14, 22), (30, 40, 60))):
        img = np.zeros((256, 256, 3), np.uint8); img[:] = col
        img[::64, :] = line; img[:, ::64] = line
        Image.fromarray(img).save(os.path.join(dd, name + '_color.png'))
        open(os.path.join(dd, name + '.vmat'), 'w', newline='\n').write('// Space Racer lobby\nLayer0\n{\n\tshader "csgo_unlitgeneric.vfx"\n\tF_BLEND_MODE 0\n\tTextureColor "materials/spr/%s_color.png"\n\tg_vColorTint "[1.000000 1.000000 1.000000 0.000000]"\n}\n' % name)
lobby_mats()
WALL, FLOOR, CEIL = 'materials/spr/lobby_wall.vmat', 'materials/spr/lobby_floor.vmat', 'materials/spr/lobby_ceil.vmat'

def room(cx, cy, z, sx, sy, sz):
    x0, x1, y0, y1, z0, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z, z + sz
    v, faces = box_faces(x0, y0, z0, x1, y1, z1)
    mesh_node(polymesh(v, faces, [FLOOR, CEIL, WALL, WALL, WALL, WALL]), GROUP)

def shell(box, mat, inset):
    x0, y0, z0, x1, y1, z1 = box
    v, faces = box_faces(x0 + inset, y0 + inset, z0 + inset, x1 - inset, y1 - inset, z1 - inset)
    mesh_node(polymesh(v, faces, [mat] * 6, scale=1.0), GROUP)

def hint(box, kind):
    x0, y0, z0, x1, y1, z1 = box
    c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2); h = ((x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2)
    ent('visibility_hint', c, group=GROUP, hintType=str(kind), box_mins='%g %g %g' % (-h[0], -h[1], -h[2]), box_maxs='%g %g %g' % (h[0], h[1], h[2]))

# ---------------------------------------------------------------- the tracks in their boxes
boxes = []
for tp in tracks:
    ox, oy, oz = tp['off']
    ent('prop_static', (ox, oy, oz), group=GROUP, model=tp['model'], solid='0', disableshadows='1', fademindist='-1', fademaxdist='0',
        rendertocubemaps='0', bakelighting='0', visoccluder='0')
    box = (ox - BOX / 2, oy - BOX / 2, oz + tp['zmin'] - 900, ox + BOX / 2, oy + BOX / 2, oz + tp['zmax'] + 1900)
    boxes.append(box)
    shell(box, MOONDOME, 0)
    shell(box, TOOLSSKY, 1)
    hint(box, HINT_LOW)
for i, a in enumerate(boxes):
    for b in boxes[i + 1:]:
        assert a[3] <= b[0] or b[3] <= a[0] or a[4] <= b[1] or b[4] <= a[1] or a[5] <= b[2] or b[5] <= a[2], (a, b)

# ---------------------------------------------------------------- lobby, booth, model cache
room(0, 0, LZ, 1536, 1536, 384)        # lobby (CS2 spawn room)
room(0, 2600, LZ, 800, 800, 256)       # pawn booth (sealed)
room(0, 4200, LZ, 2048, 1024, 256)     # model cache (sealed)
lobby_boxes = [(-768 - 64, -768 - 64, LZ - 64, 768 + 64, 768 + 64, LZ + 384 + 64),
               (-400 - 64, 2600 - 400 - 64, LZ - 64, 400 + 64, 2600 + 400 + 64, LZ + 256 + 64),
               (-1024 - 64, 4200 - 512 - 64, LZ - 64, 1024 + 64, 4200 + 512 + 64, LZ + 256 + 64)]
for b in lobby_boxes: hint(b, HINT_LOW)
allb = boxes + lobby_boxes
whole = (min(b[0] for b in allb) - 256, min(b[1] for b in allb) - 256, min(b[2] for b in allb) - 256,
         max(b[3] for b in allb) + 256, max(b[4] for b in allb) + 256, max(b[5] for b in allb) + 256)
hint(whole, HINT_LOWEST)

for i in range(32):
    x = -640 + (i % 8) * 180; y = -620 + (i // 8) * 90
    ent('info_player_terrorist', (x, y, LZ + 8), (0, 90, 0), group=GROUP, enabled='1', priority='0')
    ent('info_player_counterterrorist', (x, y + 900, LZ + 8), (0, 270, 0), group=GROUP, enabled='1', priority='0')
ent('info_target', (0, 2600, LZ), group=GROUP, targetname='spr_booth')
ent('point_script', (0, 0, LZ + 64), group=GROUP, targetname='spr_script', cs_script=SCRIPT_PATH)
ent('custom_hud_layout', (32, 0, LZ + 64), group=GROUP, targetname='spr_hud', layout=HUD_PATH, observable='1')
ent('env_sky', (64, 0, LZ + 64), group=GROUP, targetname='spr_sky', skyname='materials/spr/sky/sky.vmat', tint_color='255 255 255',
    brightnessscale='1.0', StartDisabled='0')
ent('info_map_parameters', (-32, 0, LZ + 64), group=GROUP, targetname='spr_map_params', buying='3', usenormalspawnsfordm='1', disableautogenerateddmspawns='1')
ent('prop_dynamic', (0, 2600, LZ + 32), group=GROUP, targetname='spr_src_prop', model=cars['fx']['null'], solid='0', disableshadows='1',
    fademindist='-1', fademaxdist='0', skin='default', rendercolor='255 255 255', renderamt='255')
ent('point_template', (0, 2600, LZ + 48), group=GROUP, targetname='spr_tpl_prop', Template01='spr_src_prop', spawnflags='2',
    asynchronous='0', timeoutInterval='0', spawnGroupType='INSERT_INTO_POINT_TEMPLATE_SPAWN_GROUP',
    clientOnlyEntityBehavior='CREATE_FOR_CURRENTLY_CONNECTED_CLIENTS_ONLY')
# every model the script may SetModel to must be in the map: one prop per model in the cache room
models = []
for key, m in cars['cars'].items(): models += [m['base'], m['boost']]
models += [v for k, v in cars['fx'].items() if k != 'null']
for k, mpath in enumerate(models):
    x = -900 + (k % 16) * 120; y = 4200 - 380 + (k // 16) * 160
    ent('prop_dynamic', (x, y, LZ + 8), group=GROUP, targetname='spr_cache_%d' % k, model=mpath, solid='0', disableshadows='1')
for k, s in enumerate(SOUNDS):
    ent('point_soundevent', (-600 + (k % 12) * 100, 600 + (k // 12) * 100, LZ + 64), group=GROUP, targetname='spr_snd_' + s, soundName='spr.' + s,
        startOnSpawn='0', toLocalPlayer='0', stopOnNew='0', saveAndRestore='0')
# bots need a walkable seed for nav generation
seed = ent('func_nav_markup', (0, 0, 0), group=GROUP, navProperty_NavGen='WALKABLESEED', flags='1')
v, faces = box_faces(-704, -704, LZ + 1, 704, 704, LZ + 40, inward=False)
seed.attr('children')[2].append(mesh_node(polymesh(v, faces, ['materials/tools/toolsnavattribute.vmat'] * 6, scale=1.0), GROUP, attach=False))

# ---------------------------------------------------------------- swap into the world: drop our old nodes, Hammer samples, the default box
SAMPLE = {'point_script', 'custom_hud_layout', 'point_soundevent', 'point_template', 'prop_dynamic'}
kids = world.attr('children')
kept = []
for c in kids[2]:
    if c.get('customVisGroup', '') == GROUP: continue
    if c.type == 'CMapMesh' and SRC.endswith('hammer_template.vmap'): continue
    if c.type == 'CMapEntity':
        ep = c.get('entity_properties'); cls = ep.get('classname')
        if cls in SAMPLE and not ep.get('targetname'): continue
    kept.append(c)
removed = len(kids[2]) - len(kept)
kids[2] = kept + vmaplib.new_children
for c in kept:
    if c.type == 'CMapEntity':
        cls = c.get('entity_properties').get('classname'); counts[cls] = counts.get(cls, 0) + 1

pre = {a[0]: a for a in d.prefix[0]}
refs = pre['map_asset_references'][2]
for m in list(materials_used) + [TOOLSSKY, 'materials/tools/toolsnavattribute.vmat']:
    if m not in refs: refs.append(m)
names = sorted(counts)
pre['map_subasset_reference_types'][2] = ['entity'] * len(names)
pre['map_subasset_reference_names'][2] = names
pre['map_subasset_reference_counts'][2] = [counts[n] for n in names]

d.elements = [root]
d.save(OUTPATH)
# a plain list for the test harness
ents = []
for c in kids[2]:
    if c.type != 'CMapEntity': continue
    ep = c.get('entity_properties')
    ents.append(dict(classname=ep.get('classname'), targetname=ep.get('targetname', ''), origin=list(c.get('origin'))))
os.makedirs('build', exist_ok=True)
json.dump(ents, open('build/entities.json', 'w'))
print('vmap: %d entities, %d track boxes, replaced %d old nodes, world %s..%s -> %s' % (
    sum(counts.values()), len(boxes), removed, tuple(int(x) for x in whole[:3]), tuple(int(x) for x in whole[3:]), OUTPATH))
