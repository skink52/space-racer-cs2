// ---------------------------------------------------------------- main loop and CS2 round flow

let rm = null;
const views = new Map();          // Arena -> ArenaView
let ready = false;
let lastTime = 0, acc = 0;
let phase = 'lobby';              // lobby | running | ending
let startAt = 0;
let lastPeopleScan = 0;
const pendingKills = [];          // { at, victim, killer }
const allowDamage = new Set();
const centerMsgs = new Map();     // slot -> { text, until, cls }
const subMsgs = new Map();        // slot -> { text, until }
const botMsgs = new Map();        // slot -> { text, until }  (bottom message line)
const soundCd = new Map();        // car slot + sfx -> next time
let standingsAt = 0;
const standingsCache = new Map(); // arena index -> rows
let lobbyNext = 0;

function buildCfg() {
  return {
    layout: CONFIG.ARENA_LAYOUT, arenaMin: CONFIG.ARENA_MIN, minPlayers: CONFIG.MIN_PLAYERS,
    afkWarnTics: CONFIG.AFK_WARN * TICRATE, afkKickTics: CONFIG.AFK_KICK * TICRATE,
    countdownTics: CONFIG.COUNTDOWN * TICRATE, finishWindow: CONFIG.FINISH_WINDOW, raceCap: CONFIG.RACE_CAP, endHold: CONFIG.RESULTS_HOLD, laps: CONFIG.LAPS,
    botSkill: CONFIG.BOT_SKILL, podium: CONFIG.PODIUM, shares: CONFIG.SHARES.slice(), koCredit: CONFIG.KO_CREDIT_TO_ATTACKER, tiebreak: CONFIG.TIEBREAK,
    trackBlacklist: CONFIG.TRACK_BLACKLIST.slice(), staggerArenas: true, defaultCar: CONFIG.DEFAULT_CAR,
  };
}

function cvars(list) { if (CONFIG.APPLY_CVARS) for (const c of list) Instance.ServerCommand(c); }

function init() {
  seedRandom((Date.now() & 0x7fffffff) || 1);
  rm = new RoundManager(TRACKS, buildCfg());
  findPropTemplate();
  hud();
  scanPeople(true);
  cvars(CONFIG.CVARS_ALWAYS);
  ready = true;
  lastTime = Instance.GetGameTime();
  startAt = lastTime + 1;
  log(`v${VERSION} ready: ${rm.tracks.length} tracks, HUD ${hud() ? 'on' : 'MISSING'}, prop template ${findPropTemplate() ? 'on' : 'MISSING'}`);
}

function scanPeople(force) {
  const now = Instance.GetGameTime();
  if (!force && now - lastPeopleScan < 1) return;
  lastPeopleScan = now;
  const seen = new Set();
  for (const c of Instance.GetAllPlayerControllers()) {
    if (!c || !c.IsConnected()) continue;
    const slot = c.GetPlayerSlot();
    seen.add(slot);
    const bot = c.IsBot();
    if (bot && !CONFIG.CS2_BOTS_PLAY) continue;
    rm.addPerson(slot, c.GetPlayerName(), c.GetTeamNumber(), bot);
  }
  for (const slot of Array.from(rm.people.keys())) if (!seen.has(slot)) dropPerson(slot);
}

function dropPerson(slot) {
  rm.removePerson(slot);
  parked.delete(slot);
  hudReset(slot);
  centerMsgs.delete(slot); subMsgs.delete(slot); botMsgs.delete(slot);
  for (let i = pendingKills.length - 1; i >= 0; i--) {
    const k = pendingKills[i];
    if (k.victim === slot) pendingKills.splice(i, 1);
    else if (k.killer === slot) k.killer = null;
  }
}

// ---------------------------------------------------------------- messages
function center(slot, text, secs, cls) { centerMsgs.set(slot, { text, until: Instance.GetGameTime() + secs, cls: cls || null }); }
function sub(slot, text, secs) { subMsgs.set(slot, { text, until: Instance.GetGameTime() + secs }); }
function bottom(slot, text, secs) { botMsgs.set(slot, { text, until: Instance.GetGameTime() + secs }); }
function timed(map, slot, now) { const m = map.get(slot); return m && now < m.until ? m : null; }

// ---------------------------------------------------------------- round flow
function startRace() {
  scanPeople(true);
  if (!rm.startRound()) { startAt = Instance.GetGameTime() + 5; return; }
  phase = 'running';
  cvars(['mp_ignore_round_win_conditions 1', 'mp_teammates_are_enemies 1']);
  guard('roundtime', () => Instance.SetRoundRemainingTime(CONFIG.COUNTDOWN + CONFIG.RACE_CAP + CONFIG.RESULTS_HOLD + CONFIG.ROUND_SLACK));
  pendingKills.length = 0;
  const desc = rm.plan.map((it) => `${it.track.title} (${it.grp.length})`).join(', ');
  sayAll(`RACE ${rm.roundNumber}: ${desc}`);
  log(`round ${rm.roundNumber}: ${rm.plan.map((it) => it.track.id + ':' + it.grp.length).join(' ')}`);
}

function onArenaBuilt(a) {
  views.set(a, new ArenaView(a));
  for (const car of a.order) {
    const pe = car.person;
    if (!pe || (pe.bot && !CONFIG.CS2_BOTS_PLAY)) continue;
    const pk = park(pe.slot);
    if (pk) pk.camYaw = null;
    if (!pe.bot) center(pe.slot, a.track.title, 4, 'gold');
  }
}

function endRace() {
  if (phase !== 'running') return;
  phase = 'ending';
  const pts = rm.teamPoints();
  const lines = pts.detail.map((d) => `${d.track}: T ${d.t} - CT ${d.ct}`);
  const who = pts.winner === 2 ? 'T WIN' : pts.winner === 3 ? 'CT WIN' : 'DRAW';
  sayAll(`RACE OVER - ${lines.join(' | ')} - ${who}`);
  cvars(['mp_ignore_round_win_conditions 0']);
  const reason = pts.winner === 2 ? CSRoundEndReason.TERRORISTS_WIN : pts.winner === 3 ? CSRoundEndReason.CTS_WIN : CSRoundEndReason.DRAW;
  if (live(Instance.FindEntityByName(CONFIG.MAP_PARAMS))) {
    log(`FireWinCondition ${reason} (top-8: T ${pts[2]}, CT ${pts[3]})`);
    guard('wincond', () => Instance.EntFireAtName({ name: CONFIG.MAP_PARAMS, input: 'FireWinCondition', value: reason }));
  } else {
    warnOnce('nomapparams', 'no ' + CONFIG.MAP_PARAMS + ' entity: rounds end on the clock as draws');
    guard('endround', () => Instance.SetRoundRemainingTime(1));
  }
}

function cleanupRound(entitiesGone) {
  for (const v of views.values()) {
    if (entitiesGone) { v.props.clear(); v.fx = []; v.pulseProp = null; v.anchors = null; }
    else v.destroy();
  }
  views.clear();
  for (const slot of Array.from(parked.keys())) unpark(slot);
  if (entitiesGone) { freeProps.length = 0; propTemplate = undefined; hudEnt = undefined; boothEnt = undefined; soundEnts.clear(); }
  rm.endRoundCleanup();
  rm.state = 'idle';
  pendingKills.length = 0;
  standingsCache.clear();
  phase = 'lobby';
}

// ---------------------------------------------------------------- CS2 kills
function csKill(victimSlot, killerSlot) {
  const vp = pawnOf(victimSlot);
  if (!vp || !vp.IsAlive()) return false;
  let attacker = killerSlot === null || killerSlot === undefined ? undefined : killerSlot !== victimSlot ? pawnOf(killerSlot) : vp;
  if (attacker && !attacker.IsAlive()) attacker = controllerOf(killerSlot) || undefined;
  allowDamage.add(victimSlot);
  guard('cskill', () => vp.TakeDamage({
    damage: 1000, attacker, inflictor: attacker,
    damageTypes: CSDamageTypes.VEHICLE, damageFlags: CSDamageFlags.FORCE_DEATH | CSDamageFlags.IGNORE_ARMOR,
  }));
  allowDamage.delete(victimSlot);
  const died = !live(vp) || !vp.IsAlive();
  const vc = controllerOf(victimSlot), kc = killerSlot !== victimSlot ? controllerOf(killerSlot) : undefined;
  if ((vc && !vc.IsBot()) || (kc && !kc.IsBot())) guard('killlog', () => log(`CS2 kill: ${kc ? kc.GetPlayerName() : 'world'} -> ${vc ? vc.GetPlayerName() : victimSlot}${died ? '' : ' BLOCKED'}`));
  if (!died) warnOnce('killblocked', 'a scripted CS2 kill was blocked (plugin or damage settings?)');
  return died;
}

function queueKill(victimSlot, killerSlot, delay) {
  if (Instance.IsWarmupPeriod()) { warnOnce('warmupkills', 'warmup: race results are not sent to the CS2 scoreboard until warmup ends'); return; }
  if (!CONFIG.REAL_KILLS) {
    if (CONFIG.ADD_SCORE && killerSlot !== null && killerSlot !== undefined) { const c = controllerOf(killerSlot); if (c) guard('addscore', () => c.AddScore(1)); }
    return;
  }
  pendingKills.push({ at: Instance.GetGameTime() + delay, victim: victimSlot, killer: killerSlot });
}

function processKills(now) {
  for (let i = 0; i < pendingKills.length; i++) {
    const k = pendingKills[i];
    if (now < k.at) continue;
    pendingKills.splice(i, 1); i--;
    const pe = rm.person(k.victim);
    if (!pe) continue;
    if (csKill(k.victim, k.killer)) parked.delete(k.victim);
  }
}

// ---------------------------------------------------------------- events from the race
function sfxCar(view, sfx, car, gap) {
  const key = car.slot + sfx, now = Instance.GetGameTime();
  if (gap && (soundCd.get(key) || 0) > now) return;
  soundCd.set(key, now + (gap || 0));
  playSound(view, sfx, car);
}

function handleArenaEvents(a, now) {
  const view = views.get(a);
  const T = a.track;
  for (const e of a.events) {
    switch (e.type) {
      case 'beep': { const p = T.point(0); if (view) playSound(view, 'beep', null, p.x, p.y, p.z + 60); for (const c of a.order) if (c.person && !c.person.bot) center(c.person.slot, String(e.n), 1.1, 'red'); break; }
      case 'go': { const p = T.point(0); if (view) playSound(view, 'go', null, p.x, p.y, p.z + 60); for (const c of a.order) if (c.person && !c.person.bot) center(c.person.slot, 'GO!', 1.2, 'green'); break; }
      case 'wreck': {
        if (view) { view.wreckEffect(e.car, now); sfxCar(view, 'wreck', e.car); }
        const pe = e.car.person;
        if (pe && !pe.bot) center(pe.slot, 'WRECKED', 3, 'red');
        if (e.attacker) {
          const ap = e.attacker.person;
          if (ap && !ap.bot) bottom(ap.slot, 'YOU WRECKED ' + e.car.name.slice(0, 20).toUpperCase(), 3);
          if (CONFIG.KO_CREDIT_TO_ATTACKER && pe && ap) { e.car.koApplied = true; queueKill(pe.slot, ap.slot, 0.4); }
        }
        break;
      }
      case 'finish': {
        if (view) sfxCar(view, 'finish', e.car);
        const pe = e.car.person;
        if (pe && !pe.bot) center(pe.slot, 'FINISHED ' + ordinal(e.pos), 4, e.pos <= 3 ? 'gold' : 'green');
        break;
      }
      case 'gone': if (view) { view.warpEffect(e.car, now); sfxCar(view, 'warp', e.car); } break;
      case 'lap': {
        if (view) sfxCar(view, 'lap', e.car);
        const pe = e.car.person;
        if (pe && !pe.bot) {
          if (e.lap === a.laps - 1) center(pe.slot, 'FINAL LAP', 2, 'gold');
          else bottom(pe.slot, 'LAP ' + fmtTime(e.last), 2.5);
        }
        break;
      }
      case 'pulse': if (e.start && view) { const p = T.point(a.pulse.total); playSound(view, 'pulse', null, p.x, p.y, p.z + 40); } break;
      case 'pulsed': { const pe = e.car.person; if (pe && !pe.bot) bottom(pe.slot, '+' + RULES.pulseCharge + ' CHARGE FROM THE PULSE', 2); if (view) sfxCar(view, 'pulsed', e.car, 0.5); break; }
      case 'arenaEnd': onArenaEnd(a, e.result, now); break;
    }
  }
  a.events.length = 0;
  // per-car effect bits
  if (!view) return;
  for (const car of a.order) {
    const f = car.fx;
    if (!f && !car.boosting && !car.onCharge) { car.wasBoost = false; car.wasCharge = false; continue; }
    const pe = car.person, human = pe && !pe.bot;
    if (f & 1) { sfxCar(view, 'hit', car, 0.25); if (human) hudFlash(pe.slot, 'hit', 0.25); }
    if (f & 2) sfxCar(view, 'rail', car, 0.3);
    if (f & 64) sfxCar(view, 'scrape', car, 0.6);
    if (f & 8) sfxCar(view, 'pad', car, 0.5);
    if (f & 16) { sfxCar(view, 'fall', car); if (human) center(pe.slot, 'FELL OFF', 2, 'red'); }
    if (f & 32) sfxCar(view, 'spin', car);
    if (f & 128) { sfxCar(view, 'reset', car); const pk = pe ? parked.get(pe.slot) : null; if (pk) pk.camYaw = null; }
    if (f & 4 && human) hudFlash(pe.slot, 'pulse', 0.4);
    if (f & 512) sfxCar(view, 'jump', car, 0.3);
    if (f & 1024) sfxCar(view, 'land', car, 0.3);
    if (car.boosting && !car.wasBoost) sfxCar(view, 'boost', car, 0.8);
    if (car.onCharge && !car.wasCharge) sfxCar(view, 'charge', car, 1.0);
    car.wasBoost = car.boosting; car.wasCharge = car.onCharge;
  }
}

const flashes = new Map();   // slot -> { cls, until }
function hudFlash(slot, cls, secs) { flashes.set(slot, { cls, until: Instance.GetGameTime() + secs }); }

function onArenaEnd(a, result, now) {
  const r = result.ranking;
  const top = r.slice(0, 3).map((c, i) => `${i + 1}. ${c.name}`).join('  ');
  sayAll(`${a.track.title}: ${top}`);
  // results on everyone's screen
  for (const c of a.order) {
    const pe = c.person;
    if (!pe || pe.bot) continue;
    const pos = r.indexOf(c) + 1;
    if (pos > 0) center(pe.slot, (c.state === 'wrecked' ? 'WRECKED - ' : c.state === 'dnf' ? 'DNF - ' : '') + ordinal(pos) + ' OF ' + r.length, CONFIG.RESULTS_HOLD, pos <= 3 ? 'gold' : null);
  }
  // the losers die, credited to the podium, one every few ticks
  const plan = rm.killPlan(a);
  plan.forEach((k, i) => {
    if (!k.victim.person) return;
    queueKill(k.victim.person.slot, k.killer && k.killer.person ? k.killer.person.slot : null, 1.0 + i * CONFIG.KILL_CASCADE_TICKS / 64);
  });
  log(`${a.track.id} over (${result.reason}): ${r.slice(0, 3).map((c) => c.name).join(', ')}; ${plan.length} deaths credited`);
}

function handleRoundEvents() {
  for (const e of rm.events) {
    switch (e.type) {
      case 'arenaBuilt': onArenaBuilt(e.arena); break;
      case 'afkWarn': if (!e.person.bot) sub(e.person.slot, 'MOVE OR YOU WILL BE MARKED AFK', 5); break;
      case 'afk': if (!e.person.bot) { center(e.person.slot, 'AFK', 3, 'red'); log(`${e.person.name} marked AFK`); } break;
      case 'roundOver': endRace(); break;
    }
  }
  rm.events.length = 0;
}

// ---------------------------------------------------------------- HUD text
function standingsFor(a, now) {
  let rows = standingsCache.get(a.index);
  if (rows && now < rows.at + CONFIG.STANDINGS_PERIOD) return rows.list;
  const list = a.ranking.slice(0, 8).map((c, i) => ({
    slot: c.slot, team: c.team,
    text: `${i + 1}  ${c.name.slice(0, 13).toUpperCase()}${c.state === 'gone' || c.state === 'finished' ? '  FIN' : c.state === 'wrecked' ? '  OUT' : c.state === 'withdrawn' || c.state === 'dnf' ? '  DNF' : ''}`,
  }));
  standingsCache.set(a.index, { at: now, list });
  return list;
}

function raceInfo(pe, car, a, now, spectating) {
  const info = { rows: [], spectating };
  const rows = standingsFor(a, now);
  info.rows = rows.map((r) => ({ text: r.text, team: r.team, me: r.slot === car.slot }));
  info.clock = a.state === 'grid' ? 'GRID' : a.state === 'over' ? 'RESULTS' : fmtTime(a.raceTic / TICRATE).slice(0, -3);
  const cm = timed(centerMsgs, pe.slot, now);
  if (cm) { info.center = cm.text; info.centerCls = cm.cls; }
  else if (a.state === 'grid' && a.countdown > 3 * TICRATE) info.center = '';
  else if (car.wrongWayFlag && car.state === 'racing') { info.center = 'WRONG WAY'; info.centerCls = 'red'; }
  else if (car.offLine && car.state === 'racing') { info.center = 'MISSED CHECKPOINT - TURN BACK'; info.centerCls = 'red'; }
  const sm = timed(subMsgs, pe.slot, now);
  if (sm) info.sub = sm.text;
  else if (spectating) info.sub = 'WATCHING ' + car.name.slice(0, 16).toUpperCase() + '   MOUSE 1 / 2 CHANGE CAR   E CHANGE ARENA';
  else if (a.state === 'grid') info.sub = a.countdown > 3 * TICRATE ? 'A / D CHOOSE YOUR CAR - ' + car.spec.name + ' - ' + car.spec.perk : car.spec.name;
  else if (pe.afk) info.sub = 'AFK - TYPE !BACK TO RACE NEXT ROUND';
  else if (pe.helpUntil > now) info.sub = 'W S DRIVE  A D STEER  MOUSE1 BOOST  MOUSE2 SPIN  SPACE DRIFT  !CAM VIEW';
  const bm = timed(botMsgs, pe.slot, now);
  info.msg = bm ? bm.text : '';
  const fl = flashes.get(pe.slot);
  info.flash = fl && now < fl.until ? fl.cls : null;
  return info;
}

let lobbyCycle = 0;
function lobbyInfo(pe, now) {
  const info = { line1: '', line2: '', line3: '' };
  const car = CARS[pe.carChoice] || CARS.hornet;
  info.line2 = 'YOUR CAR: ' + car.name + ' - ' + car.perk + '   (A / D TO CHANGE, !CAR 1-4)';
  const nextT = rm.upcoming[0];
  if (phase === 'running') {
    const rem = guard('remaining', () => Instance.GetRoundRemainingTime());
    const left = rem === undefined ? 0 : Math.max(0, Math.ceil(rem - CONFIG.ROUND_SLACK));
    info.line1 = `RACE IN PROGRESS - YOU ARE IN THE NEXT ONE  (${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')} LEFT AT MOST)`;
    const a = rm.arenas[lobbyCycle % Math.max(1, rm.arenas.length)];
    if (a && a.ranking[0]) info.line3 = `${a.track.title}: ${a.state === 'over' ? 'RESULTS' : 'LEADER ' + a.ranking[0].name.slice(0, 16).toUpperCase()}`;
  } else if (phase === 'ending') {
    info.line1 = 'RACE OVER - NEXT ONE SOON';
    if (nextT) info.line3 = `NEXT TRACK: ${nextT.title}`;
  } else {
    let waiting = 0;
    for (const p of rm.people.values()) if ((p.csTeam === 2 || p.csTeam === 3) && !(p.afk && !p.bot)) waiting++;
    const need = CONFIG.MIN_PLAYERS - waiting;
    if (need > 0) info.line1 = `WAITING FOR PLAYERS ${waiting}/${CONFIG.MIN_PLAYERS}`;
    else {
      const t = Math.max(0, Math.ceil(startAt - now));
      info.line1 = Instance.IsFreezePeriod() ? 'THE RACE STARTS AFTER FREEZE TIME' : t > 0 ? `THE RACE STARTS IN ${t}` : 'STARTING...';
    }
    if (nextT) info.line3 = `NEXT TRACK: ${nextT.title} - ${nextT.laps} LAPS`;
  }
  if (pe.afk) info.line3 = 'AFK - TYPE !BACK OR PRESS A KEY TO RACE';
  else if (pe.csTeam !== 2 && pe.csTeam !== 3) info.line3 = 'JOIN T OR CT TO RACE';
  if (pe.helpUntil > now) { info.center = 'W S DRIVE   A D STEER   MOUSE 1 BOOST   MOUSE 2 SPIN   SPACE DRIFT'; info.sub = 'CHAT: !CAR 1-4  !CAM  !SPEC  !AFK  !BACK  !RACE'; }
  return info;
}

// engine sound: short overlapping hum grains on every human-driven car, the band (pitch) following its speed
const humNext = new Map();
function engineHum(now) {
  for (const [a, view] of views) {
    if (a.state !== 'racing' && a.state !== 'grid') continue;
    for (const car of a.order) {
      if (car.isBot || !car.visible || car.state === 'wrecked') continue;
      const due = humNext.get(car.slot) || 0;
      if (now < due) continue;
      const k = car.speed / Math.max(1, car.spec.maxSpeed);
      const band = car.boosting || car.padTimer > 0 ? 3 : k < 0.15 ? 0 : k < 0.55 ? 1 : 2;
      humNext.set(car.slot, now + 0.38);
      playSound(view, 'hum' + band, car);
    }
  }
}

// ---------------------------------------------------------------- per tick
function lobbyFrame(now, dt) {
  if (now < lobbyNext) return;
  lobbyNext = now + 0.05;
  lobbyCycle = Math.floor(now / 3);
  const a0 = rm.arenas[0];
  for (const pe of rm.people.values()) {
    if (pe.bot) { if (!parked.has(pe.slot)) park(pe.slot); continue; }   // bots stand frozen in the booth too
    const pk = park(pe.slot);
    if (!pk) continue;
    if (pickerInput(pe, pk)) rm.markActive(pe.slot);
    guard('lobbyhud', () => { hudLobby(pe.slot, lobbyInfo(pe, now)); hudPicker(pe.slot, pe, true); });
    // nothing to look at yet: a slow look around the first track from above
    if (!a0) guard('lobbycam', () => {
      if (!live(pk.cam)) return;
      // the track of the next race, the whole of it in view: a slow circle high above its edge, looking in
      const T = rm.upcoming[0] || rm.tracks[0];
      const off = T.off || [0, 0, 0];
      const ang = now * 0.06;
      const r = T.ext * 0.92, h = T.ext * 0.8;
      const pitch = deg(Math.atan2(h, r));
      if (pk.camMode !== CustomCameraMode.CONTROLLED) { pk.cam.SetMode(CustomCameraMode.CONTROLLED); pk.camMode = CustomCameraMode.CONTROLLED; }
      pk.cam.Move({ position: { x: off[0] + Math.cos(ang) * r, y: off[1] + Math.sin(ang) * r, z: off[2] + h }, angles: { pitch, yaw: deg(ang + Math.PI), roll: 0 } });
    });
  }
}

function frame(dt) {
  const now = Instance.GetGameTime();
  soundsThisTick = 0;
  spawnBudget = CONFIG.SPAWN_BUDGET;
  scanPeople(false);
  if (phase === 'lobby') {
    lobbyFrame(now, dt);
    if (now >= startAt && !Instance.IsFreezePeriod()) startRace();
    return;
  }
  if (phase !== 'running' && phase !== 'ending') return;
  // input
  for (const pe of rm.people.values()) {
    if (pe.bot) { if (!parked.has(pe.slot)) park(pe.slot); continue; }
    const pk = park(pe.slot);
    if (!pk) continue;
    if (pe.status === 'racing' && pe.car && pe.arena) {
      if (pe.car.state === 'grid') { if (pe.arena.countdown > 3 * TICRATE ? pickerInput(pe, pk) : sampleInput(pe.slot, pe.car, pk)) rm.markActive(pe.slot); }
      else if (pe.car.racing) { if (sampleInput(pe.slot, pe.car, pk)) rm.markActive(pe.slot); }
      else {
        // wrecked / finished / withdrawn: watch the others after a moment
        if (pe.car.stateTime > RULES.wreckShow || pe.car.state === 'gone' || pe.car.state === 'withdrawn') {
          pe.status = 'spectating'; pe.spec = { arena: pe.arena.index, target: null }; rm.fixSpectate(pe, 0);
        }
      }
    } else if (pe.status === 'spectating' || pe.status === 'none') {
      if (spectatorInput(pe, pk)) rm.markActive(pe.slot);
    }
  }
  // the race, one step per server tick
  acc += dt;
  let ran = 0;
  while (acc >= DT && ran < 3) {
    acc -= DT; ran++;
    rm.tic();
    for (const a of rm.arenas) handleArenaEvents(a, now);
    handleRoundEvents();
  }
  if (acc > 3 * DT) acc = 0;
  processKills(now);
  for (const v of views.values()) guard('render', () => v.update(now));
  if (CONFIG.ENGINE_HUM) guard('hum', () => engineHum(now));
  // cameras and HUD
  for (const pe of rm.people.values()) {
    if (pe.bot) continue;
    const pk = parked.get(pe.slot);
    if (!pk) continue;
    guard('view', () => {
      if (pe.status === 'racing' && pe.car && pe.arena) {
        const a = pe.arena, v = views.get(a);
        if (!v) return;
        if (a.state === 'over') placeOverviewCamera(pk, a, v); else placeCamera(pk, pe.car, v, dt, pe.cam);
        hudRace(pe.slot, pe.car, a, raceInfo(pe, pe.car, a, now, false));
        hudPicker(pe.slot, pe, a.state === 'grid' && a.countdown > 3 * TICRATE);
      } else {
        // spectators and people waiting for the next race
        if (!pe.spec) rm.spectate(pe);
        const a = rm.arenas[pe.spec ? pe.spec.arena : 0], v = a && views.get(a);
        const t = a && pe.spec && pe.spec.target !== null ? a.cars.get(pe.spec.target) : null;
        if (!a || !v) { hudLobby(pe.slot, lobbyInfo(pe, now)); hudPicker(pe.slot, pe, true); return; }
        if (t && t.visible && a.state !== 'over') { placeCamera(pk, t, v, dt, pe.cam); hudRace(pe.slot, t, a, raceInfo(pe, t, a, now, true)); }
        else { placeOverviewCamera(pk, a, v); if (pe.car && pe.arena === a) hudRace(pe.slot, pe.car, a, raceInfo(pe, pe.car, a, now, false)); else { hudLobby(pe.slot, lobbyInfo(pe, now)); } rm.fixSpectate(pe, 0); }
        hudPicker(pe.slot, pe, pe.status !== 'racing' && (!pe.car || a.state === 'over'));
      }
    });
  }
}

function think() {
  hudBudget = CONFIG.HUD_BUDGET;
  flushSays();
  const now = Instance.GetGameTime();
  let dt = now - lastTime;
  lastTime = now;
  if (!(dt > 0) || dt > 0.25) dt = DT;
  if (ready) guard('frame', () => frame(dt));
  Instance.SetNextThink(now);
}

// ---------------------------------------------------------------- CS2 hooks
Instance.SetThink(think);
Instance.OnActivate(() => { guard('init', init); Instance.SetNextThink(Instance.GetGameTime()); });
Instance.OnScriptReload({
  before: () => { guard('reload', () => cleanupRound(false)); return null; },
  after: () => { guard('init', init); Instance.SetNextThink(Instance.GetGameTime()); },
});
Instance.OnRoundStart(() => guard('roundstart', () => {
  if (phase !== 'lobby') cleanupRound(true);
  startAt = Instance.GetGameTime() + 0.5;
  cvars(['mp_ignore_round_win_conditions 1']);
}));
Instance.OnRoundEnd((ev) => guard('roundend', () => {
  if (phase === 'running') endRace();
  const w = ev && ev.winningTeam;
  log(`CS2 round ended: ${w === 2 ? 'T win' : w === 3 ? 'CT win' : 'no winner (team ' + w + ')'}, reason ${ev ? ev.reason : '?'}`);
}));
Instance.OnBeginRoundRestart(() => guard('restart', () => cleanupRound(true)));
Instance.OnPlayerDisconnect(({ playerSlot }) => guard('disconnect', () => dropPerson(playerSlot)));
Instance.OnPlayerActivate(() => guard('activate', () => scanPeople(true)));
Instance.OnPlayerTeamChanged(({ player }) => guard('team', () => {
  const slot = slotOfEntity(player);
  if (slot === undefined) return;
  const pe = rm.person(slot);
  if (pe && pe.status === 'racing') { rm.leaveArena(pe, 'team change'); unpark(slot); }
  for (let i = pendingKills.length - 1; i >= 0; i--) if (pendingKills[i].victim === slot) pendingKills.splice(i, 1);
  scanPeople(true);
}));
Instance.OnPlayerReset(({ player }) => guard('reset', () => {
  const slot = slotOfEntity(player);
  if (slot === undefined) return;
  const pe = rm.person(slot);
  if (!pe) return;
  // a fresh pawn (spawn, or the respawn after a scripted kill): park it again and keep the camera
  parked.delete(slot);
  park(slot);
  if (phase === 'running' && pe.status === 'none') rm.lateJoin(pe);
}));
Instance.OnPlayerKill(({ player }) => guard('cskilled', () => {
  const slot = slotOfEntity(player);
  if (slot === undefined) return;
  parked.delete(slot);
  const pe = rm.person(slot);
  if (!pe || allowDamage.has(slot)) return;
  // killed by something outside the race (admin slay): the car withdraws
  if (pe.status === 'racing' && pe.car && pe.car.racing && pe.arena) { rm.leaveArena(pe, 'slain'); rm.spectate(pe, pe.arena); }
}));
Instance.OnModifyPlayerDamage((event) => {
  const slot = slotOfEntity(event.player);
  if (slot !== undefined && allowDamage.has(slot)) return;
  return { abort: true };
});
Instance.OnPlayerChat(({ player, text }) => guard('chat', () => {
  if (!CONFIG.CHAT_COMMANDS || !player) return;
  const slot = player.GetPlayerSlot();
  const pe = rm.person(slot);
  let t = text.trim().toLowerCase();
  if (t.startsWith('/')) t = '!' + t.slice(1);
  if (!player.IsBot()) sayHold();
  if (!t.startsWith('!') || !pe) return;
  log(`chat command "${t}" from slot ${slot}`);
  if (t === '!car' || t.startsWith('!car ')) {
    const arg = t.slice(4).trim();
    const n = parseInt(arg, 10);
    const key = CAR_KEYS[n - 1] || CAR_KEYS.find((k) => k === arg || CARS[k].name.toLowerCase() === arg);
    if (key) { if (!rm.setCar(pe, key)) bottom(slot, 'TOO LATE TO SWAP - NEXT ROUND', 3); }
    else bottom(slot, 'CARS: 1 HORNET  2 METEOR  3 COMET  4 BASTION', 5);
  } else if (t === '!cam' || t.startsWith('!cam ')) {
    const names = Object.keys(CONFIG.CAMERAS);
    const want = t.slice(4).trim();
    const cur = pe.cam || CONFIG.CAM_DEFAULT;
    pe.cam = names.includes(want) ? want : names[(names.indexOf(cur) + 1) % names.length];
    bottom(slot, 'CAMERA: ' + pe.cam.toUpperCase() + '   (!CAM ' + names.join(' / ').toUpperCase() + ')', 3);
  } else if (t === '!spec' || t === '!spectate') {
    if (pe.status === 'racing' && pe.arena) { const a = pe.arena; rm.leaveArena(pe, 'spectate'); rm.spectate(pe, a); }
  } else if (t === '!afk') {
    pe.afk = true;
    if (pe.status === 'racing' && pe.arena) { const a = pe.arena; rm.leaveArena(pe, 'afk'); rm.spectate(pe, a); }
  } else if (t === '!back') {
    pe.afk = false; rm.markActive(slot);
  } else if (t === '!race' || t === '!help' || t === '!spr') {
    pe.helpUntil = Instance.GetGameTime() + CONFIG.HELP_SECONDS;
    hudHelp(slot, true);
    guard('helpoff', () => { Instance.Delay(CONFIG.HELP_SECONDS).then(() => hudHelp(slot, false)); });
  }
}));
