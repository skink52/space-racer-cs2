// ---------------------------------------------------------------- the HUD (custom_hud_layout)
// panorama/layout/custom_game/space_racer.xml has fixed panels; the script swaps CSS classes and sets dialog
// variables per player. Every change is cached so only real changes are sent.

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
  const key = panel + (group ? '#' + group : '');
  const old = c.get(key);
  if (old === cls) return;
  if (hudBudget <= 0) return;
  const h = hud();
  if (!h) return;
  hudBudget -= old && cls ? 2 : 1;
  if (old) h.SetHasClassForPlayer(slot, panel, old, false);
  if (cls) h.SetHasClassForPlayer(slot, panel, cls, true);
  c.set(key, cls);
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
  hudSwap(slot, 'spr_mm', 'mm_' + arena.track.id, 'map');
  hudVar(slot, 'spr_clock', info.clock || '');
  hudVar(slot, 'spr_ctr', info.center || '');
  hudSwap(slot, 'spr_ctr', info.centerCls || null, 'c');
  hudVar(slot, 'spr_sub', info.sub || '');
  hudVar(slot, 'spr_msg', info.msg || '');
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
  hudVar(slot, 'spr_pos', car.pos ? String(car.pos) : '-');
  hudVar(slot, 'spr_posof', '/ ' + arena.order.filter((c) => !c.left).length);
  hudVar(slot, 'spr_lap', 'LAP ' + Math.min(arena.laps, car.lapsDone + 1) + ' / ' + arena.laps);
  hudSwap(slot, 'spr_shfill', pct(car.shield, car.spec.shield));
  hudSwap(slot, 'spr_shield', car.shield < car.spec.shield * 0.3 ? 'low' : null, 'low');
  hudSwap(slot, 'spr_chfill', pct(car.charge, car.spec.charge));
  hudSwap(slot, 'spr_charge', car.boosting ? 'boosting' : car.onCharge ? 'charging' : null, 'st');
  // "km/h" for the dial (units/s x 0.36 reads like a racing speedo), 8 updates a second in steps of 2
  if ((arena.tic & 7) === 0 || car.speed < 10) hudVar(slot, 'spr_spd', String(Math.round(car.speed * 0.18) * 2));
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
  hudVar(slot, 'spr_lob1', info.line1 || '');
  hudVar(slot, 'spr_lob2', info.line2 || '');
  hudVar(slot, 'spr_lob3', info.line3 || '');
  hudVar(slot, 'spr_ctr', info.center || '');
  hudSwap(slot, 'spr_ctr', info.centerCls || null, 'c');
  hudVar(slot, 'spr_sub', info.sub || '');
  hudVar(slot, 'spr_msg', '');
  hudSwap(slot, 'spr_flash', null);
}

function hudHelp(slot, on) { hudSwap(slot, 'spr_root', on ? 'Help' : null, 'help'); }
