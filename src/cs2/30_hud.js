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
  // the whole row is cached: nothing to do when it shows this already
  const c = cacheFor(slot);
  const key = id + '@';
  const want = text + '|' + (color || '') + '|' + (fx || '');
  if (c.get(key) === want) return;
  let ok = true;
  for (let k = 0; k < ids.length; k++) if (!hudSwap(slot, ids[k], k < text.length ? glyphClass(text[k]) : null)) ok = false;
  if (color !== undefined && !hudSwap(slot, id, TEXT_COLOR[color] || color || null, 'col')) ok = false;
  if (!hudSwap(slot, id, fx || null, 'fx')) ok = false;
  if (ok) c.set(key, want);       // (a row cut short by the budget is finished on a later tick)
}
// a centre message: short ones big, long ones in the smaller row
function hudCenter(slot, text, cls) {
  text = text || '';
  const big = text.length <= (HUD_TEXT.slots.spr_ctr || 20);
  const color = cls ? TEXT_COLOR[cls] || 'cW' : 'cW';
  const blink = cls === 'red' && /WRONG|MISSED/.test(text) ? 'blink' : null;
  hudText(slot, 'spr_ctr', big ? text : '', color, blink);
  hudText(slot, 'spr_ctr2', big ? '' : text, color, blink);
}

function hudReset(slot) {
  hudCache.delete(slot);
  const h = hud();
  if (h) { try { h.ResetForPlayer(slot); } catch (err) { /* ignore */ } }
}

function hudOff(slot) { hudSwap(slot, 'spr_root', null); }

function pct(v, max) { return 'w' + clamp(Math.round(v / Math.max(1, max) * 20), 0, 20); }

// the car picker: four cards, the chosen one highlighted; pictures in the player's side colour
function hudPicker(slot, pe, show) {
  hudSwap(slot, 'spr_root', show ? 'Pick' : null, 'pick');
  if (!show) return;
  const side = pe.csTeam === 2 ? 't' : pe.csTeam === 3 ? 'ct' : 'neutral';
  CAR_KEYS.forEach((k, i) => {
    hudSwap(slot, 'spr_card' + i, pe.carChoice === k ? 'sel' : null);
    hudSwap(slot, 'spr_cimg' + i, 'pic_' + k + '_' + side);
  });
}

// minimap dot position classes for a track-local point
function dotClasses(track, x, y) {
  const mm = track.mm, half = mm.size / 2;
  const px = half + x * mm.scale, py = half - y * mm.scale;
  const gx = clamp(Math.round(px / mm.size * 23), 0, 23), gy = clamp(Math.round(py / mm.size * 23), 0, 23);
  return ['dx' + gx, 'dy' + gy];
}

function hudRaceCommon(slot, arena, info) {
  hudSwap(slot, 'spr_root', 'On', 'on');
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
  // leader dot
  const lead = arena.ranking[0];
  if (lead && lead.racing) { const dc = dotClasses(arena.track, lead.x, lead.y); hudSwap(slot, 'spr_ldot', dc[0], 'x'); hudSwap(slot, 'spr_ldot', dc[1], 'y'); hudSwap(slot, 'spr_ldot', 'On', 'on'); }
  else hudSwap(slot, 'spr_ldot', null, 'on');
}

// a racing player's own HUD (or a spectator looking through `car`)
function hudRace(slot, car, arena, info) {
  hudRaceCommon(slot, arena, info);
  // position: big digits (gold when leading), the suffix, and the field size
  const ord = car.pos ? ordinal(car.pos) : '-';
  const num = car.pos ? String(car.pos) : '-';
  const posCol = car.pos === 1 ? 'cY' : car.pos && car.pos <= 3 ? 'cG' : 'cW';
  hudText(slot, 'spr_pos', num, posCol);
  hudText(slot, 'spr_suf', ord.slice(num.length), posCol);
  hudText(slot, 'spr_posof', '/' + arena.order.filter((c) => !c.left).length, 'cP');
  const lap = Math.min(arena.laps, car.lapsDone + 1);
  if (lap === arena.laps && arena.laps > 1 && car.state === 'racing') hudText(slot, 'spr_lap', 'FINAL LAP', 'cR', 'blink');
  else hudText(slot, 'spr_lap', 'LAP ' + lap + '/' + arena.laps, 'cY');
  hudSwap(slot, 'spr_shfill', pct(car.shield, car.spec.shield));
  hudSwap(slot, 'spr_shield', car.shield < car.spec.shield * 0.3 ? 'low' : null, 'low');
  hudSwap(slot, 'spr_chfill', pct(car.charge, car.spec.charge));
  hudSwap(slot, 'spr_charge', car.boosting ? 'boosting' : car.onCharge ? 'charging' : null, 'st');
  // "km/h" for the dial (units/s x 0.36 reads like a racing speedo), 8 updates a second in steps of 2
  if ((arena.tic & 7) === 0 || car.speed < 10) hudText(slot, 'spr_spd', String(Math.round(car.speed * 0.18) * 2).padStart(4, ' '), car.boosting || car.padTimer > 0 ? 'cY' : 'cW');
  hudSwap(slot, 'spr_spfill', pct(car.speed, car.spec.maxSpeed * 1.5));
  hudSwap(slot, 'spr_speed', car.padTimer > 0 ? 'pad' : null, 'pad');
  if (car.visible) { const dc = dotClasses(arena.track, car.x, car.y); hudSwap(slot, 'spr_dot', dc[0], 'x'); hudSwap(slot, 'spr_dot', dc[1], 'y'); hudSwap(slot, 'spr_dot', 'On', 'on'); }
  else hudSwap(slot, 'spr_dot', null, 'on');
  hudSwap(slot, 'spr_root', info.spectating ? 'Spec' : null, 'spec');
  hudSwap(slot, 'spr_root', null, 'lobby');
}

// lobby: status lines only (plus the picker)
function hudLobby(slot, info) {
  hudSwap(slot, 'spr_root', 'Lobby', 'lobby');
  hudSwap(slot, 'spr_root', null, 'on');
  hudSwap(slot, 'spr_root', null, 'spec');
  hudText(slot, 'spr_lob1', info.line1 || '', 'cW', info.blink1 ? 'blink' : null);
  hudText(slot, 'spr_lob2', info.line2 || '', 'cY');
  hudText(slot, 'spr_lob3', info.line3 || '', 'cC');
  hudCenter(slot, info.center, info.centerCls);
  hudText(slot, 'spr_sub', info.sub || '', 'cW');
  hudText(slot, 'spr_msg', '');
  hudSwap(slot, 'spr_flash', null);
}

function hudHelp(slot, on) { hudSwap(slot, 'spr_root', on ? 'Help' : null, 'help'); }
// player options on the outer panel: CRT scanlines off
function hudOptions(slot, pe) { hudSwap(slot, 'spr_opts', pe.crt === false ? 'nocrt' : null, 'crt'); }
