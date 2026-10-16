// ---------------------------------------------------------------- drawing the race with pooled props
// Every car is a prop_dynamic from the pool (model = car class, or its boosting variant; skin = side colour), moved
// every tick with Move so the client interpolates. Wrecks, warp-outs and the Pulse are pooled effect props.

const NULL_MODEL = 'models/spr/null.vmdl';
const HIDE_POS = { x: 0, y: 0, z: -15000 };
const SKIN_INDEX = { neutral: 0, t: 1, ct: 2, gold: 3 };

let propTemplate;
let propSerial = 0;
const freeProps = [];
let spawnBudget = 0;

function findPropTemplate() {
  propTemplate = live(propTemplate) || live(Instance.FindEntityByName(CONFIG.PROP_TEMPLATE));
  if (!propTemplate) warnOnce('tpl', 'no point_template named ' + CONFIG.PROP_TEMPLATE + ' - nothing can be drawn');
  return propTemplate;
}

function newProp() {
  if (spawnBudget <= 0) return undefined;
  const tpl = findPropTemplate();
  if (!tpl) return undefined;
  spawnBudget--;
  const ents = /** @type {any} */ (tpl).ForceSpawn(HIDE_POS, { pitch: 0, yaw: 0, roll: 0 });
  if (!ents || !ents.length) { warnOnce('spawnfail', 'the prop template spawned nothing'); return undefined; }
  const ent = ents[0];
  const name = 'spr_p' + (++propSerial);
  try { ent.SetEntityName(name); } catch (err) { /* ignore */ }
  return { ent, name, model: '', skin: -1, hidden: true, lastPos: null, alpha: -1 };
}

function takeProp() {
  while (freeProps.length) {
    const p = freeProps.pop();
    if (live(p.ent)) return p;
  }
  return newProp();
}

function releaseProp(p) {
  if (!p || !live(p.ent)) return;
  if (!p.hidden) {
    try { p.ent.SetModel(NULL_MODEL); p.ent.Teleport({ position: HIDE_POS }); } catch (err) { /* ignore */ }
    p.model = NULL_MODEL; p.hidden = true;
  }
  freeProps.push(p);
}

function propModel(p, model) {
  if (p.model === model || !live(p.ent)) return;
  p.ent.SetModel(model); p.model = model;
}
function propSkin(p, skin) {
  if (p.skin === skin || !live(p.ent)) return;
  Instance.EntFireAtTarget({ target: p.ent, input: 'Skin', value: skin }); p.skin = skin;
}
function propAlpha(p, a) {
  if (p.alpha === a || !live(p.ent)) return;
  p.ent.SetColor({ r: 255, g: 255, b: 255, a }); p.alpha = a;
}

class ArenaView {
  constructor(arena) {
    this.arena = arena;
    this.off = arena.track.off || [0, 0, 0];
    this.props = new Map();      // car slot -> prop
    this.fx = [];                // { prop, kind, until, frames, start, x, y, z, yaw }
    this.pulseProp = null;
    this.anchors = null;
  }

  world(x, y, z) { return { x: this.off[0] + x, y: this.off[1] + y, z: this.off[2] + z }; }

  carModel(car) {
    const m = CAR_MODELS.cars[car.cls] || CAR_MODELS.cars.hornet;
    return car.boosting || car.padTimer > 0 ? m.boost : m.base;
  }

  update(now) {
    const a = this.arena, T = a.track;
    // cars
    for (const car of a.order) {
      let p = this.props.get(car.slot);
      if (!car.visible) {
        if (p) { this.props.delete(car.slot); releaseProp(p); }
        continue;
      }
      if (!p) { p = takeProp(); if (!p) continue; this.props.set(car.slot, p); p.hidden = false; p.lastPos = null; p.model = ''; p.skin = -1; p.alpha = -1; }
      if (!live(p.ent)) { this.props.delete(car.slot); continue; }
      propModel(p, car.state === 'wrecked' ? CAR_MODELS.cars[car.cls].base : this.carModel(car));
      propSkin(p, car.team === 0 ? SKIN_INDEX.t : car.team === 1 ? SKIN_INDEX.ct : SKIN_INDEX.neutral);
      propAlpha(p, car.state === 'wrecked' ? 90 : car.ghost > 0 && car.state === 'racing' ? 140 : car.state === 'finished' ? 160 : 255);
      // angles: yaw from the heading (+ spin), pitch from the slope, roll from the slide
      const i = car.seg, j = (i + 1) % T.n;
      const pitch = car.state === 'falling' ? Math.min(60, car.stateTime * 50) : -deg(Math.atan2(T.z[j] - T.z[i], T.step));
      const roll = car.state === 'falling' ? 0 : clamp(-car.vl / 14, -18, 18);
      const yaw = deg(car.yaw + car.spinYaw);
      const pos = this.world(car.x, car.y, car.z);
      if (car.state === 'wrecked') pos.z -= Math.min(8, car.stateTime * 6);
      const ang = { pitch, yaw, roll };
      if (!p.lastPos || car.state === 'grid' || (car.fx & 128)) { p.ent.Teleport({ position: pos, angles: ang }); }
      else p.ent.Move({ position: pos, angles: ang });
      p.lastPos = pos;
    }
    // the Pulse wave
    if (a.pulse.active && RULES.pulseEnabled) {
      if (!this.pulseProp) { this.pulseProp = takeProp(); if (this.pulseProp) { this.pulseProp.hidden = false; this.pulseProp.lastPos = null; this.pulseProp.model = ''; this.pulseProp.alpha = -1; } }
      const pp = this.pulseProp;
      if (pp && live(pp.ent)) {
        propModel(pp, CAR_MODELS.fx.pulse);
        const pt = T.point(a.pulse.total);
        const pos = this.world(pt.x, pt.y, pt.z + 2);
        const ang = { pitch: 0, yaw: deg(Math.atan2(pt.ty, pt.tx)), roll: 0 };
        if (!pp.lastPos) pp.ent.Teleport({ position: pos, angles: ang }); else pp.ent.Move({ position: pos, angles: ang });
        pp.lastPos = pos;
      }
    } else if (this.pulseProp) { releaseProp(this.pulseProp); this.pulseProp = null; }
    // effects
    for (let k = this.fx.length - 1; k >= 0; k--) {
      const e = this.fx[k];
      if (now >= e.until || !live(e.prop.ent)) { releaseProp(e.prop); this.fx.splice(k, 1); continue; }
      const frame = Math.min(e.frames.length - 1, Math.floor((now - e.start) / (e.until - e.start) * e.frames.length));
      propModel(e.prop, e.frames[frame]);
    }
  }

  // an effect at a track position: frames = list of models, shown over `seconds`
  effect(x, y, z, yaw, frames, seconds, now) {
    if (this.fx.length >= CONFIG.MAX_EFFECT_PROPS) return;
    const prop = takeProp();
    if (!prop) return;
    prop.hidden = false; prop.lastPos = null; prop.model = ''; prop.alpha = -1;
    propModel(prop, frames[0]);
    propAlpha(prop, 255);
    prop.ent.Teleport({ position: this.world(x, y, z), angles: { pitch: 0, yaw: deg(yaw), roll: 0 } });
    this.fx.push({ prop, frames, start: now, until: now + seconds });
  }

  wreckEffect(car, now) {
    const fx = CAR_MODELS.fx;
    this.effect(car.x, car.y, car.z + 20, car.yaw, [fx.boom0, fx.boom1, fx.boom2, fx.boom3], RULES.wreckShow, now);
  }
  warpEffect(car, now) {
    const fx = CAR_MODELS.fx;
    this.effect(car.x, car.y, car.z, car.yaw, [fx.warp0, fx.warp1], 0.5, now);
  }

  destroy() {
    for (const p of this.props.values()) releaseProp(p);
    this.props.clear();
    for (const e of this.fx) releaseProp(e.prop);
    this.fx = [];
    if (this.pulseProp) { releaseProp(this.pulseProp); this.pulseProp = null; }
    if (this.anchors) { this.anchors.release(); this.anchors = null; }
  }
}
