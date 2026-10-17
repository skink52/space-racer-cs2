// ---------------------------------------------------------------- CS2 pawns: parking, chase camera, input
// While the map runs, every CS2 pawn stands frozen and invisible in a sealed booth. The script reads its
// buttons; the view is a custom camera the script places behind the player's car (or the car they watch).

const parked = new Map();     // slot -> { pawn, cam, booth, camMode, camYaw, lastYaw, lastPitch }
let boothEnt;

function boothPos(slot) {
  boothEnt = live(boothEnt) || live(Instance.FindEntityByName(CONFIG.BOOTH));
  const o = boothEnt ? boothEnt.GetAbsOrigin() : { x: 0, y: 0, z: -14000 };
  const col = slot % 8, row = Math.floor(slot / 8) % 8;
  return { x: o.x + (col - 3.5) * 80, y: o.y + (row - 3.5) * 80, z: o.z + 4 };
}

function park(slot) {
  const pawn = pawnOf(slot);
  if (!pawn) return undefined;
  let pk = parked.get(slot);
  if (pk && pk.pawn === pawn && live(pk.cam)) return pk;
  const booth = boothPos(slot);
  guard('park', () => {
    pawn.Teleport({ position: booth, velocity: { x: 0, y: 0, z: 0 } });
    pawn.SetMoveType(CSMoveType.NONE);
    pawn.DestroyWeapons();
  });
  if (CONFIG.HIDE_OWN_BODY) guard('hidebody', () => pawn.SetColor({ r: 255, g: 255, b: 255, a: 0 }));
  let cam;
  guard('camera', () => {
    cam = live(pawn.GetCustomCamera());
    if (cam) { cam.SetParent(undefined); cam.SetMode(CustomCameraMode.CONTROLLED); }
  });
  if (!cam) warnOnce('nocam', 'GetCustomCamera returned nothing - players will see their pawn in the booth');
  const eye = guard('eye', () => pawn.GetEyeAngles()) || { yaw: 0, pitch: 0 };
  pk = { pawn, cam, booth, camMode: CustomCameraMode.CONTROLLED, camYaw: null, lastYaw: eye.yaw, lastPitch: eye.pitch, edges: {} };
  parked.set(slot, pk);
  return pk;
}

function unpark(slot) {
  const pk = parked.get(slot);
  parked.delete(slot);
  hudOff(slot);
  if (!pk) return;
  guard('unpark', () => {
    if (live(pk.cam)) { pk.cam.SetMode(CustomCameraMode.DISABLED); if (live(pk.pawn)) pk.cam.SetParent(pk.pawn); }
    if (live(pk.pawn) && pk.pawn.IsAlive()) pk.pawn.SetMoveType(CSMoveType.WALK);
    if (CONFIG.HIDE_OWN_BODY && live(pk.pawn)) pk.pawn.SetColor({ r: 255, g: 255, b: 255, a: 255 });
  });
}

// racing input -> the car's command; returns true when the player did anything (AFK tracking)
function sampleInput(slot, car, pk) {
  const pawn = pk.pawn;
  if (!live(pawn)) return false;
  const pressed = (n) => pawn.IsInputPressed(CSInputs[n]);
  const fwd = pressed('FORWARD'), back = pressed('BACK'), left = pressed('LEFT'), right = pressed('RIGHT');
  const c = car.cmd;
  c.throttle = fwd ? 1 : back ? -1 : 0;
  c.steer = (left ? 1 : 0) - (right ? 1 : 0);      // + = turn left (yaw grows anticlockwise, seen from above)
  c.boost = pressed('ATTACK');
  c.drift = pressed('JUMP') || pressed('DUCK');
  if (pawn.WasInputJustPressed(CSInputs.ATTACK2)) c.spin = true;
  const ang = pawn.GetEyeAngles();
  const active = fwd || back || left || right || c.boost || c.drift || c.spin || Math.abs(angleDiff(pk.lastYaw, ang.yaw)) > 2 || Math.abs(ang.pitch - pk.lastPitch) > 2;
  pk.lastYaw = ang.yaw; pk.lastPitch = ang.pitch;
  return active;
}

// The car picker. It comes up by itself only for someone who has not chosen a car yet and has not raced (in the
// lobby and on the grid). After that it stays away - so it never covers the results - until !car (or /car) brings
// it back for a few seconds. A / D change the car only while the cards are on screen (hudPicker notes that in
// pe.pickShown).
function pickerAuto(pe) { return !pe.picked && !pe.raced; }
function pickerOpen(pe, now) { return (pe.pickUntil || 0) > now; }

// A / D while the picker is up; returns true on any input (AFK tracking)
function pickerInput(pe, pk) {
  const pawn = pk.pawn;
  if (!live(pawn)) return false;
  const l = pawn.WasInputJustPressed(CSInputs.LEFT), r = pawn.WasInputJustPressed(CSInputs.RIGHT);
  let any = l || r;
  if (any && pe.pickShown) {
    rm.cycleCar(pe, l ? -1 : 1);
    pe.picked = true;
    pe.pickUntil = Instance.GetGameTime() + CONFIG.PICK_SHOW;      // the cards stay up while they keep choosing
  }
  if (pawn.IsInputPressed(CSInputs.FORWARD | CSInputs.BACK | CSInputs.ATTACK | CSInputs.JUMP | CSInputs.USE)) any = true;
  const ang = pawn.GetEyeAngles();
  if (Math.abs(angleDiff(pk.lastYaw, ang.yaw)) > 2) any = true;
  pk.lastYaw = ang.yaw; pk.lastPitch = ang.pitch;
  return any;
}

function spectatorInput(pe, pk) {
  const pawn = pk.pawn;
  if (!live(pawn)) return false;
  let any = false;
  if (pawn.WasInputJustPressed(CSInputs.ATTACK)) { rm.fixSpectate(pe, 1); any = true; }
  if (pawn.WasInputJustPressed(CSInputs.ATTACK2)) { rm.fixSpectate(pe, -1); any = true; }
  if (pawn.WasInputJustPressed(CSInputs.USE) || pawn.WasInputJustPressed(CSInputs.JUMP)) { rm.fixSpectate(pe, 'arena'); any = true; }
  return pickerInput(pe, pk) || any;
}

// camera shake (hits, landings, wrecks): a few units of jitter that dies away
function shake(slot, secs, amp) {
  const pk = parked.get(slot);
  if (!pk || !CONFIG.CAM_SHAKE) return;
  const now = Instance.GetGameTime();
  if (pk.shakeUntil && now < pk.shakeUntil && pk.shakeAmp > amp) return;
  pk.shakeUntil = now + secs; pk.shakeLen = secs; pk.shakeAmp = amp * CONFIG.CAM_SHAKE;
}
function shakeOffset(pk) {
  if (!pk.shakeUntil) return null;
  const now = Instance.GetGameTime();
  const left = pk.shakeUntil - now;
  if (left <= 0) { pk.shakeUntil = 0; return null; }
  const k = pk.shakeAmp * (left / pk.shakeLen);
  return { x: Math.sin(now * 91) * k, y: Math.sin(now * 77 + 1) * k, z: Math.sin(now * 103 + 2) * k * 0.7 };
}

// chase camera behind a car (own or watched). The yaw eases towards the car's heading, turned a little into the bend
// ahead so the upcoming track stays in view; it pulls back at speed; a little roll in corners.
function placeCamera(pk, car, view, dt, preset, tilt) {
  if (!live(pk.cam)) return;
  const cp = CONFIG.CAMERAS[preset] || CONFIG.CAMERAS[CONFIG.CAM_DEFAULT] || { back: 300, up: 175, pitch: 16, speedBack: 70 };
  const T = view.arena.track;
  const ahead = T.point(car.s + 500 + car.speed * 0.5);
  const toAhead = Math.atan2(ahead.y - car.y, ahead.x - car.x);
  const target = car.state === 'falling' ? car.yaw : car.yaw + normRad(toAhead - car.yaw) * CONFIG.CAM_LOOKAHEAD;
  if (pk.camYaw === null || car.fx & 128 || car.state === 'grid') pk.camYaw = target;
  else pk.camYaw += normRad(target - pk.camYaw) * Math.min(1, CONFIG.CAM_TURN * dt);
  const cy = pk.camYaw;
  const sp = clamp(car.speed / Math.max(1, car.spec.maxSpeed), 0, 1.5);
  let back = cp.back + cp.speedBack * sp, up = cp.up;
  // inside a tube the camera drops and closes in so it stays under the roof
  const inTube = T.tube[car.seg] || T.tube[(car.seg + T.n - 4) % T.n];
  pk.tubeK = (pk.tubeK || 0) + ((inTube ? 1 : 0) - (pk.tubeK || 0)) * Math.min(1, dt * 3);
  if (pk.tubeK > 0.001) { up = lerp(up, Math.min(up, CONFIG.CAM_TUBE_UP), pk.tubeK); back = lerp(back, Math.min(back, CONFIG.CAM_TUBE_BACK), pk.tubeK); }
  // in the air the camera follows the car's height but not its bounces
  const cz = car.air ? Math.max(car.tz, car.z - 40) : car.z;
  const pos = view.world(car.x - Math.cos(cy) * back, car.y - Math.sin(cy) * back, cz + up);
  const sh = shakeOffset(pk);
  if (sh) { pos.x += sh.x; pos.y += sh.y; pos.z += sh.z; }
  // lean (+ = tilt right): a share of a banked road's angle plus a little into the turn, smoothed; !tilt turns it off
  const lean = car.air || car.state === 'falling' || car.spinTimer > 0 || tilt === false ? 0
    : -deg(Math.atan(car.bank)) * CONFIG.CAM_BANK + clamp(-(car.yawRate || 0) * CONFIG.CAM_LEAN, -CONFIG.CAM_ROLL, CONFIG.CAM_ROLL);
  pk.bankRoll = (pk.bankRoll || 0) + (lean - (pk.bankRoll || 0)) * Math.min(1, dt * 4);
  const roll = pk.bankRoll * CONFIG.CAM_ROLL_SIGN;
  const pitch = cp.pitch + (car.state === 'falling' ? Math.min(40, car.stateTime * 30) : 0);
  if (pk.camMode !== CustomCameraMode.CONTROLLED) { pk.cam.SetMode(CustomCameraMode.CONTROLLED); pk.camMode = CustomCameraMode.CONTROLLED; }
  pk.cam.Move({ position: pos, angles: { pitch, yaw: deg(cy), roll } });
}

// grid flyover: before the last seconds of the countdown the camera swoops low along the track towards the grid,
// looking back at the waiting field, then cuts to the chase camera
function placeFlyover(pk, arena, view, now) {
  if (!live(pk.cam)) return;
  const T = arena.track;
  const total = arena.cfg.countdownTics, left = arena.countdown;
  const span = total - CONFIG.FLYOVER_CUT * TICRATE;
  const t = clamp((total - left) / Math.max(1, span), 0, 1);
  const e = 1 - (1 - t) * (1 - t) * (1 - t);             // ease out: fast at first, settling over the grid
  const s = CONFIG.FLYOVER_FROM * (1 - e) + 250;         // progress ahead of the start line
  const p = T.point(s), q = T.point(s - 600);
  let hT = 160 + 520 * (1 - e);
  // stay under the roof where the road runs through a tube
  for (let k = -10; k <= 10; k += 2) if (T.tube[((p.i + k) % T.n + T.n) % T.n]) { hT = Math.min(hT, 170); break; }
  if (pk.flyH === undefined || left >= total - 1) pk.flyH = hT;
  pk.flyH += (hT - pk.flyH) * 0.12;
  const h = pk.flyH;
  const pos = view.world(p.x, p.y, p.z + h);
  const look = Math.atan2(q.y - p.y, q.x - p.x);
  const pitch = deg(Math.atan2(h - 40, 900));
  if (pk.camMode !== CustomCameraMode.CONTROLLED) { pk.cam.SetMode(CustomCameraMode.CONTROLLED); pk.camMode = CustomCameraMode.CONTROLLED; }
  pk.cam.Move({ position: pos, angles: { pitch, yaw: deg(look), roll: Math.sin(now * 0.7) * 3 } });
  pk.camYaw = null;
}

// results / nothing to follow: a slow circle round the start gantry, high enough to see the field warp out, rising
// over any road the circle passes (Crosswire's loop is close to its start). Heights per track, worked out once.
const OV_R = 1500, OV_N = 64;
const ovHeights = new Map();
function overviewHeights(T) {
  let hs = ovHeights.get(T.id);
  if (hs) return hs;
  const p = T.point(0);
  hs = [];
  for (let k = 0; k < OV_N; k++) {
    const a = 2 * Math.PI * k / OV_N, cx = p.x + Math.cos(a) * OV_R, cy = p.y + Math.sin(a) * OV_R;
    let h = 650;
    for (let i = 0; i < T.n; i++) if (Math.hypot(T.x[i] - cx, T.y[i] - cy) - T.hw[i] < 500) h = Math.max(h, T.z[i] - p.z + 380);
    hs.push(h);
  }
  // widen the rises a little, then smooth them so the camera eases up and down
  hs = hs.map((_, k) => Math.max(hs[(k + OV_N - 2) % OV_N], hs[(k + OV_N - 1) % OV_N], hs[k], hs[(k + 1) % OV_N], hs[(k + 2) % OV_N]));
  for (let pass = 0; pass < 4; pass++) hs = hs.map((v, k) => (hs[(k + OV_N - 1) % OV_N] + 2 * v + hs[(k + 1) % OV_N]) / 4);
  ovHeights.set(T.id, hs);
  return hs;
}
function placeOverviewCamera(pk, arena, view) {
  if (!live(pk.cam)) return;
  const T = arena.track;
  const p = T.point(0);
  const ang = Instance.GetGameTime() * 0.12;
  const hs = overviewHeights(T);
  const f = (((ang / (2 * Math.PI)) % 1) + 1) % 1 * OV_N, k0 = Math.floor(f) % OV_N, w = f - Math.floor(f);
  const h = hs[k0] + (hs[(k0 + 1) % OV_N] - hs[k0]) * w;
  const r = OV_R;
  const pos = view.world(p.x + Math.cos(ang) * r, p.y + Math.sin(ang) * r, p.z + h);
  if (pk.camMode !== CustomCameraMode.CONTROLLED) { pk.cam.SetMode(CustomCameraMode.CONTROLLED); pk.camMode = CustomCameraMode.CONTROLLED; }
  pk.cam.Move({ position: pos, angles: { pitch: deg(Math.atan2(h - 250, r)), yaw: deg(ang + Math.PI), roll: 0 } });
  pk.camYaw = null;
}
