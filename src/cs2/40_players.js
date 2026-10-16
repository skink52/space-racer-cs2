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
  c.steer = (right ? 1 : 0) - (left ? 1 : 0);
  c.boost = pressed('ATTACK');
  c.drift = pressed('JUMP') || pressed('DUCK');
  if (pawn.WasInputJustPressed(CSInputs.ATTACK2)) c.spin = true;
  const ang = pawn.GetEyeAngles();
  const active = fwd || back || left || right || c.boost || c.drift || c.spin || Math.abs(angleDiff(pk.lastYaw, ang.yaw)) > 2 || Math.abs(ang.pitch - pk.lastPitch) > 2;
  pk.lastYaw = ang.yaw; pk.lastPitch = ang.pitch;
  return active;
}

// the car picker (lobby, spectating, on the grid): A / D cycle; returns true on any input
function pickerInput(pe, pk) {
  const pawn = pk.pawn;
  if (!live(pawn)) return false;
  let any = false;
  if (pawn.WasInputJustPressed(CSInputs.LEFT)) { rm.cycleCar(pe, -1); any = true; }
  if (pawn.WasInputJustPressed(CSInputs.RIGHT)) { rm.cycleCar(pe, 1); any = true; }
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

// chase camera behind a car (own or watched). The yaw eases towards the car's heading; a little roll in corners.
function placeCamera(pk, car, view, dt) {
  if (!live(pk.cam)) return;
  const target = car.yaw;
  if (pk.camYaw === null || car.fx & 128 || car.state === 'grid') pk.camYaw = target;
  else pk.camYaw += normRad(target - pk.camYaw) * Math.min(1, CONFIG.CAM_TURN * dt);
  const cy = pk.camYaw;
  const back = CONFIG.CAM_BACK, up = CONFIG.CAM_UP;
  const pos = view.world(car.x - Math.cos(cy) * back, car.y - Math.sin(cy) * back, car.z + up);
  let roll = car.state === 'falling' ? 0 : clamp(-car.vl / 30, -CONFIG.CAM_ROLL, CONFIG.CAM_ROLL);
  if (car.spinTimer > 0) roll = 0;
  const pitch = CONFIG.CAM_PITCH + (car.state === 'falling' ? Math.min(40, car.stateTime * 30) : 0);
  if (pk.camMode !== CustomCameraMode.CONTROLLED) { pk.cam.SetMode(CustomCameraMode.CONTROLLED); pk.camMode = CustomCameraMode.CONTROLLED; }
  pk.cam.Move({ position: pos, angles: { pitch, yaw: deg(cy), roll } });
}

// a fixed overview of an arena (results / nothing to follow): high above the start line
function placeOverviewCamera(pk, arena, view) {
  if (!live(pk.cam)) return;
  const T = arena.track;
  const p = T.point(0);
  const pos = view.world(p.x - p.tx * 900, p.y - p.ty * 900, p.z + 700);
  if (pk.camMode !== CustomCameraMode.CONTROLLED) { pk.cam.SetMode(CustomCameraMode.CONTROLLED); pk.camMode = CustomCameraMode.CONTROLLED; }
  pk.cam.Move({ position: pos, angles: { pitch: 35, yaw: deg(Math.atan2(p.ty, p.tx)), roll: 0 } });
  pk.camYaw = null;
}
