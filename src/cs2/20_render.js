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
    this.shells = new Map();     // car slot -> prop: the Aegis shell round a Bastion
    this.anchors = null;
  }

  world(x, y, z) { return { x: this.off[0] + x, y: this.off[1] + y, z: this.off[2] + z }; }

  // the flames: gold and longer on a boost pad (or a turbo start), the car's own colour when it boosts (Mouse 1, Nova)
  carModel(car) {
    const m = CAR_MODELS.cars[car.cls] || CAR_MODELS.cars.hornet;
    return car.padTimer > 0 ? m.pad : car.boosting || car.novaTimer > 0 ? m.boost : m.base;
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
      // angles: yaw from the heading (+ spin), pitch from the slope, roll from the bank and the slide
      const i = car.seg;
      const rf = car.lift > 0 ? T.rampAt(i) : null;
      const rampTilt = rf ? -deg(Math.atan2(rf.h, (((rf.b - rf.a + T.n) % T.n) + 1) * T.step)) : 0;
      // on the road the car rests on its nose and tail: the slope between the road under each end, and where the road
      // curves up (the foot of a climb) it sits on its ends instead of on the road under its middle, so it doesn't sink
      let pitch, lift = 0;
      if (car.state === 'falling') pitch = Math.min(60, car.stateTime * 50);
      else if (car.air) pitch = clamp(-deg(Math.atan2(car.vz, Math.max(200, car.speed))) * 0.7, -25, 25);
      else {
        const half = CAR_LEN * 0.45, zMid = T.point(car.s).z;
        const zf = T.point(car.s + half).z, zr = T.point(car.s - half).z;
        pitch = -deg(Math.atan2(zf - zr, 2 * half)) + rampTilt;
        if (!rf) lift = Math.max(0, (zf + zr) / 2 - zMid);
      }
      // roll (+ = right side down): the lean of a banked road (bank > 0 = left side low) plus leaning into the turn
      // (turning right = yaw falling = lean right)
      const bankRoll = car.air ? 0 : -deg(Math.atan(car.bank));
      const turnRoll = clamp(-(car.yawRate || 0) * CONFIG.CAR_LEAN, -CONFIG.CAR_LEAN_MAX, CONFIG.CAR_LEAN_MAX);
      const roll = car.state === 'falling' ? 0 : CONFIG.PROP_ROLL_SIGN * (bankRoll + turnRoll);
      const yaw = deg(car.yaw + car.spinYaw);
      const pos = this.world(car.x, car.y, car.z + lift);
      if (car.state === 'wrecked') pos.z -= Math.min(8, car.stateTime * 6);
      const ang = { pitch, yaw, roll };
      // Teleport only for the first placement and real jumps (respawns); everything else Moves, the grid included
      const lp = p.lastPos;
      if (!lp || (car.fx & 128) || Math.abs(pos.x - lp.x) + Math.abs(pos.y - lp.y) + Math.abs(pos.z - lp.z) > CONFIG.TELEPORT_DIST) p.ent.Teleport({ position: pos, angles: ang });
      else p.ent.Move({ position: pos, angles: ang });
      p.lastPos = pos;
      // the Aegis shell follows the car while it is up
      let sh = this.shells.get(car.slot);
      if (car.aegis > 0 && car.state === 'racing') {
        if (!sh) { sh = takeProp(); if (sh) { this.shells.set(car.slot, sh); sh.hidden = false; sh.lastPos = null; sh.model = ''; sh.alpha = -1; } }
        if (sh && live(sh.ent)) {
          propModel(sh, CAR_MODELS.fx.aegis);
          const sa = { pitch: 0, yaw: (now * 90) % 360, roll: 0 };
          if (!sh.lastPos) sh.ent.Teleport({ position: pos, angles: sa }); else sh.ent.Move({ position: pos, angles: sa });
          sh.lastPos = pos;
        }
      } else if (sh) { releaseProp(sh); this.shells.delete(car.slot); }
    }
    for (const [slot, sh] of this.shells) if (!a.cars.get(slot) || !a.cars.get(slot).visible) { releaseProp(sh); this.shells.delete(slot); }
    // the Pulse wave
    if (a.pulse.active && RULES.pulseEnabled) {
      if (!this.pulseProp) { this.pulseProp = takeProp(); if (this.pulseProp) { this.pulseProp.hidden = false; this.pulseProp.lastPos = null; this.pulseProp.model = ''; this.pulseProp.alpha = -1; } }
      const pp = this.pulseProp;
      if (pp && live(pp.ent)) {
        propModel(pp, CAR_MODELS.fx.pulse);
        const pt = T.point(a.pulse.total);
        const pos = this.world(pt.x, pt.y, pt.z + 2);
        // follow the road: its slope and its bank (the fence and floor strip lie on the surface)
        const j = (pt.i + 1) % T.n;
        const ang = { pitch: -deg(Math.atan2(T.z[j] - T.z[pt.i], T.step)), yaw: deg(Math.atan2(pt.ty, pt.tx)), roll: CONFIG.PROP_ROLL_SIGN * -deg(Math.atan(T.bk[pt.i])) };
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
    for (const p of this.shells.values()) releaseProp(p);
    this.shells.clear();
    for (const e of this.fx) releaseProp(e.prop);
    this.fx = [];
    if (this.pulseProp) { releaseProp(this.pulseProp); this.pulseProp = null; }
    if (this.anchors) { this.anchors.release(); this.anchors = null; }
  }
}
