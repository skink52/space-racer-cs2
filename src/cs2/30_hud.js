// ---------------------------------------------------------------- the HUD (custom_hud_layout)
// panorama/layout/custom_game/space_racer.xml has fixed panels; the script swaps CSS classes (pixel-font glyphs,
// colours, bar widths) and sets dialog variables (standings names) per player. Every change is cached so only real
// changes are sent, and a per-tick budget spreads big updates over a few ticks.

let hudEnt;
let hudBudget = Infinity;
const hudCache = new Map();    // slot -> Map(key -> value)

function hud() {
  if (live(hudEnt)) return hudEnt;
  hudEnt = live(Instance.FindEntityByName(CONFIG.HUD));
  if (!hudEnt) { warnOnce('hud', 'no custom_hud_layout named ' + CONFIG.HUD + ' - no HUD'); return hudEnt; }
  for (const slot of hudCache.keys()) { try { hudEnt.ResetForPlayer(slot); } catch (err) { /* ignore */ } }
  hudCache.clear();
  return hudEnt;
}

function cacheFor(slot) {
  let c = hudCache.get(slot);
  if (!c) { c = new Map(); hudCache.set(slot, c); }
  return c;
}

// one class "slot" per panel: swapping replaces the previous class in that slot
function hudSwap(slot, panel, cls, group) {
  const c = cacheFor(slot);
  const key = group ? panel + '#' + group : panel;
  const old = c.get(key);
  if (old === cls) return true;
  if (hudBudget <= 0) return false;
  const h = hud();
  if (!h) return false;
  hudBudget -= old && cls ? 2 : 1;
  if (old) h.SetHasClassForPlayer(slot, panel, old, false);
  if (cls) h.SetHasClassForPlayer(slot, panel, cls, true);
  c.set(key, cls);
  return true;
}

function hudVar(slot, panel, text) {
  const c = cacheFor(slot);
  const key = panel + '$';
  text = String(text === undefined || text === null ? '' : text);
  if (c.get(key) === text) return;
  if (hudBudget <= 0) return;
  const h = hud();
  if (!h) return;
  hudBudget--;
  h.SetDialogVariableStringForPlayer(slot, panel, 'v', text);
  c.set(key, text);
}

// pixel text: a row of glyph panels (<id>_0 .. <id>_n-1); each gets the class g<char code>, the row a colour class.
// Characters the font lacks show as '?'; only the characters that change are sent.
const GLYPH_OK = new Set(HUD_TEXT.charset.split(''));
const TEXT_COLOR = { gold: 'cY', red: 'cR', green: 'cG', cyan: 'cC', pink: 'cP', white: 'cW' };
function glyphClass(ch) {
  if (ch === undefined) return null;
  const u = ch.toUpperCase();
  return 'g' + (GLYPH_OK.has(u) ? u : '?').charCodeAt(0);
}
const SLOT_IDS = {};
for (const id in HUD_TEXT.slots) { SLOT_IDS[id] = []; for (let k = 0; k < HUD_TEXT.slots[id]; k++) SLOT_IDS[id].push(id + '_' + k); }
function hudText(slot, id, text, color, fx) {
  const ids = SLOT_IDS[id];
  if (!ids) return;
  text = String(text === undefined || text === null ? '' : text);
  if (text.length > ids.length) text = text.slice(0, ids.length);
  // the row has a fixed number of cells: centre or right-align by padding
  const align = HUD_TEXT.align ? HUD_TEXT.align[id] : 'left';
  if (align === 'center') text = ' '.repeat(Math.floor((ids.length - text.length) / 2)) + text;
  else if (align === 'right') text = text.padStart(ids.length, ' ');
  // the whole row is cached: nothing to do when it shows this already
  const c = cacheFor(slot);
  const key = id + '@';
  const want = text + '|' + (color || '') + '|' + (fx || '');
  if (c.get(key) === want) return;
  let ok = true;
  for (let k = 0; k < ids.length; k++) if (!hudSwap(slot, ids[k], k < text.length && text[k] !== ' ' ? glyphClass(text[k]) : null)) ok = false;
  if (color !== undefined && !hudSwap(slot, id, TEXT_COLOR[color] || color || null, 'col')) ok = false;
  if (!hudSwap(slot, id, fx || null, 'fx')) ok = false;
  if (ok) c.set(key, want);       // (a row cut short by the budget is finished on a later tick)
}
// a pop (scale-in) each time a row shows something new: the class alternates pop / pop2 (two copies of the same
// animation) because Panorama only replays an animation when its name changes
const popState = new Map();     // slot + row -> { key, flip }
function popFx(slot, row, key) {
  const k = slot + row;
  const st = popState.get(k) || { key: null, flip: false };
  if (st.key !== key) { st.key = key; st.flip = !st.flip; popState.set(k, st); }
  return st.flip ? 'pop2' : 'pop';
}

// a centre message: short ones big, long ones in the smaller row; new messages pop in, warnings blink
function hudCenter(slot, text, cls) {
  text = text || '';
  const big = text.length <= (HUD_TEXT.slots.spr_ctr || 20);
  const color = cls ? TEXT_COLOR[cls] || 'cW' : 'cW';
  const fx = cls === 'red' && /WRONG|MISSED/.test(text) ? 'blink' : text ? popFx(slot, 'c', text) : null;
  hudText(slot, 'spr_ctr', big ? text : '', color, big ? fx : null);
  hudText(slot, 'spr_ctr2', big ? '' : text, color, big ? null : fx);
}

function hudReset(slot) {
  hudCache.delete(slot);
  const h = hud();
  if (h) { try { h.ResetForPlayer(slot); } catch (err) { /* ignore */ } }
}

// state classes on spr_root all start with "st" (stOn, stLobby, stPick, stHelp, stRes, stSpec, stBoost): a state
// class must never share its name with a panel's class, or the root picks up that panel's layout
function hudOff(slot) {
  for (const g of ['on', 'lobby', 'pick', 'help', 'res', 'spec', 'boost']) hudSwap(slot, 'spr_root', null, g);
}

function pct(v, max) { return 'w' + clamp(Math.round(v / Math.max(1, max) * 20), 0, 20); }

// the car picker: four cards, the chosen one highlighted; pictures in the player's side colour
function hudPicker(slot, pe, show) {
  hudSwap(slot, 'spr_root', show ? 'stPick' : null, 'pick');
  if (!show) return;
  const side = pe.csTeam === 2 ? 't' : pe.csTeam === 3 ? 'ct' : 'neutral';
  CAR_KEYS.forEach((k, i) => {
    hudSwap(slot, 'spr_card' + i, pe.carChoice === k ? 'sel' : null);
    hudSwap(slot, 'spr_cimg' + i, 'pic_' + k + '_' + side);
  });
}

// minimap: the track picture is 48 x 48 big pixels; dots snap to them. x / y position classes for a track-local point
const MM_CELLS = HUD_TEXT.mm_cells || 48;
const MAX_DOTS = HUD_TEXT.max_dots || 32;
function dotCells(track, x, y) {
  const mm = track.mm, half = mm.size / 2;
  const px = half + x * mm.scale, py = half - y * mm.scale;
  return [clamp(Math.floor(px / mm.size * MM_CELLS), 0, MM_CELLS - 1), clamp(Math.floor(py / mm.size * MM_CELLS), 0, MM_CELLS - 1)];
}
function hudDot(slot, outer, inner, car, track, colorCls, step) {
  if (!car) { hudSwap(slot, outer, null, 'on'); return; }
  const c = dotCells(track, car.x, car.y);
  if (step > 1) { c[0] -= c[0] % step; c[1] -= c[1] % step; }
  hudSwap(slot, outer, 'x' + c[0], 'x');
  hudSwap(slot, inner, 'y' + c[1], 'y');
  if (colorCls !== undefined) hudSwap(slot, inner, colorCls, 'col');
  hudSwap(slot, outer, 'On', 'on');
}
// every car in the race on the minimap (grid order = dot number), the leader in gold and the watched car blinking
// white on top. To keep the class traffic down the other cars move in 2-pixel steps and a quarter of them is
// refreshed on each HUD update.
const dotTurn = new Map();
function hudDots(slot, arena, me) {
  const T = arena.track;
  const n = (dotTurn.get(slot) || 0) + 1;
  dotTurn.set(slot, n);
  const per = Math.ceil(MAX_DOTS / 4), from = (n & 3) * per;
  for (let k = from; k < Math.min(MAX_DOTS, from + per); k++) {
    const car = arena.order[k];
    const show = car && car !== me && car.visible && !car.left;
    hudDot(slot, 'spr_md' + k, 'spr_mdy' + k, show ? car : null, T,
      show ? (car.state === 'wrecked' || car.state === 'finished' ? 'Out' : car.team === 0 ? 'T' : car.team === 1 ? 'CT' : null) : undefined, 2);
  }
  const lead = arena.ranking[0];
  hudDot(slot, 'spr_ldot', 'spr_ldoty', lead && lead !== me && lead.racing ? lead : null, T, undefined, 1);
  hudDot(slot, 'spr_dot', 'spr_doty', me && me.visible ? me : null, T, undefined, 1);
}

function hudRaceCommon(slot, arena, info, car) {
  hudSwap(slot, 'spr_root', 'stOn', 'on');
  hudSwap(slot, 'spr_root', arena.state === 'over' ? 'stRes' : null, 'res');
  hudSwap(slot, 'spr_mmimg', 'mm_' + arena.track.id, 'map');
  hudText(slot, 'spr_clock', info.clock || '', info.clock === 'GRID' || info.clock === 'RESULTS' ? 'cY' : 'cW');
  hudCenter(slot, info.center, info.centerCls);
  hudText(slot, 'spr_sub', info.sub || '', 'cW');
  hudText(slot, 'spr_msg', info.msg || '', 'cC');
  hudSwap(slot, 'spr_flash', info.flash || null);
  // standings (8 rows): the names, their side, and which row is the watched car
  const rows = info.rows || [];
  for (let i = 0; i < 8; i++) {
    const r = rows[i];
    hudVar(slot, 'spr_stn' + i, r ? r.text : '');
    hudSwap(slot, 'spr_st' + i, r ? (r.team === 0 ? 'T' : r.team === 1 ? 'CT' : 'N') : null, 'side');
    hudSwap(slot, 'spr_st' + i, r && r.me ? 'me' : null, 'me');
  }
  if (arena.state === 'over') hudResults(slot, arena, car);
}

// the results board: the top 8 (your own line instead of the 8th if you placed lower), with finish times and gaps
function hudResults(slot, arena, me) {
  const r = (arena.result && arena.result.ranking) || arena.ranking;
  const rows = r.slice(0, 8);
  const mine = me ? r.indexOf(me) : -1;
  if (mine >= 8) rows[7] = me;
  const win = r[0];
  for (let i = 0; i < 8; i++) {
    const c = rows[i];
    const pos = c ? r.indexOf(c) + 1 : 0;
    let time = '';
    if (c) {
      if (c.finishPos) time = c === win || !win || !win.finishPos ? fmtTime(c.finishTime) : '+' + fmtTime(c.finishTime - win.finishTime);
      else time = c.state === 'wrecked' ? 'WRECKED' : c.state === 'withdrawn' || c.left ? 'OUT' : 'DNF';
    }
    hudVar(slot, 'spr_rbp' + i, c ? ordinal(pos) : '');
    hudVar(slot, 'spr_rbn' + i, c ? c.name.slice(0, 20).toUpperCase() : '');
    hudVar(slot, 'spr_rbt' + i, time);
    hudSwap(slot, 'spr_rb' + i, c ? (c.team === 0 ? 'T' : c.team === 1 ? 'CT' : null) : null, 'side');
    hudSwap(slot, 'spr_rb' + i, c && c === me ? 'me' : null, 'me');
    hudSwap(slot, 'spr_rb' + i, pos >= 1 && pos <= 3 ? 'p' + pos : null, 'pod');
  }
}

// lap timer and best lap (tenths), under the race clock
function lapText(sec) { return sec > 0 ? fmtTime(sec).slice(0, -1) : '-'; }

// a racing player's own HUD (or a spectator looking through `car`)
function hudRace(slot, car, arena, info) {
  hudRaceCommon(slot, arena, info, car);
  // position: big digits (gold when leading), the suffix, and the field size
  const ord = car.pos ? ordinal(car.pos) : '-';
  const num = car.pos ? String(car.pos) : '-';
  const posCol = car.pos === 1 ? 'cY' : car.pos && car.pos <= 3 ? 'cG' : 'cW';
  // the big number pops when you gain a place (or start watching another car)
  let ps = popState.get(slot + 'pos');
  if (!ps) { ps = { car: -1, pos: 99, flip: false }; popState.set(slot + 'pos', ps); }
  const pos = car.pos || 99;
  if (ps.car !== car.slot || pos < ps.pos) ps.flip = !ps.flip;
  ps.car = car.slot; ps.pos = pos;
  hudText(slot, 'spr_pos', num, posCol, ps.flip ? 'pop2' : 'pop');
  hudText(slot, 'spr_suf', ord.slice(num.length), posCol);
  hudText(slot, 'spr_posof', '/' + arena.order.filter((c) => !c.left).length, 'cP');
  const lap = Math.min(arena.laps, car.lapsDone + 1);
  if (lap === arena.laps && arena.laps > 1 && car.state === 'racing') hudText(slot, 'spr_lap', 'FINAL LAP', 'cR', 'blink');
  else hudText(slot, 'spr_lap', 'LAP ' + lap + '/' + arena.laps, 'cY');
  // the running lap time ticks about 5 times a second (fewer class changes than every tenth)
  if (car.state !== 'racing' || arena.tic % 12 < 2) hudText(slot, 'spr_laptime', arena.state === 'grid' ? '-' : car.state === 'racing' ? lapText(arena.raceTic / TICRATE - car.lapStart) : lapText(car.lastLap), 'cW');
  hudText(slot, 'spr_best', lapText(car.bestLap), 'cY');
  hudSwap(slot, 'spr_shfill', pct(car.shield, car.spec.shield));
  hudSwap(slot, 'spr_shield', car.shield < car.spec.shield * 0.3 ? 'low' : null, 'low');
  hudSwap(slot, 'spr_chfill', pct(car.charge, car.spec.charge));
  hudSwap(slot, 'spr_charge', car.boosting ? 'boosting' : car.onCharge ? 'charging' : null, 'st');
  // "km/h" for the dial (units/s x 0.36 reads like a racing speedo), 8 updates a second in steps of 2
  if ((arena.tic & 7) < 2 || car.speed < 10) hudText(slot, 'spr_spd', String(Math.round(car.speed * 0.18) * 2).padStart(4, ' '), car.boosting || car.padTimer > 0 ? 'cY' : 'cW');
  hudSwap(slot, 'spr_spfill', pct(car.speed, car.spec.maxSpeed * 1.5));
  hudSwap(slot, 'spr_speed', car.padTimer > 0 ? 'pad' : null, 'pad');
  // the bend ahead: an arrow (two blinking ones for a hairpin), looking further ahead the faster the car goes
  let turnCls = null;
  if (car.state === 'racing' && (arena.tic & 3) < 2) {
    const look = 500 + car.speed * 0.9;
    const turn = arena.track.turnAhead(car.s, look * 0.3, look + 900);
    const a = Math.abs(turn);
    if (a > 0.75) turnCls = (turn > 0 ? 'l' : 'r') + (a > 1.9 ? '2' : '1');
    hudSwap(slot, 'spr_turn', turnCls, 'dir');
  } else if (car.state !== 'racing') hudSwap(slot, 'spr_turn', null, 'dir');
  hudSwap(slot, 'spr_root', (car.boosting || car.padTimer > 0) && car.state === 'racing' && !info.spectating ? 'stBoost' : null, 'boost');
  hudDots(slot, arena, car);
  hudSwap(slot, 'spr_root', info.spectating ? 'stSpec' : null, 'spec');
  hudSwap(slot, 'spr_root', null, 'lobby');
}

// lobby: status lines only (plus the picker)
function hudLobby(slot, info) {
  hudSwap(slot, 'spr_root', 'stLobby', 'lobby');
  hudSwap(slot, 'spr_root', null, 'on');
  hudSwap(slot, 'spr_root', null, 'res');
  hudSwap(slot, 'spr_root', null, 'boost');
  hudSwap(slot, 'spr_root', null, 'spec');
  hudText(slot, 'spr_lob1', info.line1 || '', 'cW', info.blink1 ? 'blink' : null);
  hudText(slot, 'spr_lob2', info.line2 || '', 'cY');
  hudText(slot, 'spr_lob3', info.line3 || '', 'cC');
  hudCenter(slot, info.center, info.centerCls);
  hudText(slot, 'spr_sub', info.sub || '', 'cW');
  hudText(slot, 'spr_msg', '');
  hudSwap(slot, 'spr_flash', null);
}

function hudHelp(slot, on) { hudSwap(slot, 'spr_root', on ? 'stHelp' : null, 'help'); }
// player options on the outer panel: CRT scanlines off
function hudOptions(slot, pe) { hudSwap(slot, 'spr_opts', pe.crt === false ? 'nocrt' : null, 'crt'); }
