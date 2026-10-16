// ===================================================================================
// Part 5: round manager - who races where, car choices, locked rounds, spectating, AFK, the team result and
// the kill plan. Engine-agnostic: the CS2 side turns its events into cameras, HUD, sounds and CS2 kills.
// ===================================================================================

const DEFAULT_CFG = {
  arenaMax: 32, maxArenas: 2, minPlayers: 1, layout: '2x32', arenaMin: 8,
  afkWarnTics: 20 * TICRATE, afkKickTics: 30 * TICRATE, afkLobbyTics: 120 * TICRATE,
  countdownTics: 10 * TICRATE, finishWindow: 30, raceCap: 300, endHold: 6, laps: 0,
  botSkill: 0.5,
  podium: 3, shares: [50, 30, 20], koCredit: true, tiebreak: true,
  trackBlacklist: [], staggerArenas: true, defaultCar: 'hornet',
};

// layouts: '2x32' (up to 2 arenas of 32), '4x16' (up to 4 arenas of 16), 'alternate' (switches every round)
const LAYOUTS = { '2x32': { arenaMax: 32, maxArenas: 2 }, '4x16': { arenaMax: 16, maxArenas: 4 } };
function layoutFor(cfg, round) {
  const k = cfg.layout === 'alternate' ? (round % 2 ? '2x32' : '4x16') : cfg.layout;
  return Object.assign({ key: LAYOUTS[k] ? k : '2x32' }, LAYOUTS[k] || LAYOUTS['2x32']);
}

// 2x32: 1..32 players race together, more are split into equal arenas (33 -> 17 + 16).
// 4x16: one arena up to 16, then as many as needed (each at least arenaMin when there is more than one).
function arenaSizes(n, cfg) {
  if (n <= 0) return [];
  let count = Math.max(1, Math.min(cfg.maxArenas, Math.ceil(n / cfg.arenaMax)));
  while (count > 1 && n < count * (cfg.arenaMin || 1) && Math.ceil(n / (count - 1)) <= cfg.arenaMax) count--;
  const m = Math.min(n, cfg.arenaMax * count);
  const base = Math.floor(m / count), extra = m % count;
  return Array.from({ length: count }, (_, i) => base + (i < extra ? 1 : 0));
}

// split `total` kills among the podium by percentage shares (largest remainder), e.g. 29 -> 15 / 9 / 5
function splitShares(total, shares) {
  const sum = shares.reduce((a, b) => a + b, 0) || 1;
  const raw = shares.map((s) => total * s / sum);
  const out = raw.map((r) => Math.floor(r));
  let left = total - out.reduce((a, b) => a + b, 0);
  const order = raw.map((r, i) => [r - Math.floor(r), i]).sort((a, b) => b[0] - a[0]);
  for (let k = 0; left > 0 && k < order.length; k++, left--) out[order[k][1]]++;
  while (left > 0) { out[0]++; left--; }
  return out;
}

class RoundManager {
  constructor(tracks, cfg) {
    this.tracks = tracks.map((d) => new Track(d));
    this.cfg = Object.assign({}, DEFAULT_CFG, cfg || {});
    this.people = new Map();       // slot -> person
    this.arenas = []; this.pending = []; this.plan = [];
    this.state = 'idle';           // idle | running | over
    this.clock = 0;                // tics, never reset
    this.time = 0;                 // tics since the round started
    this.roundNumber = 0;
    this.lastTracks = [];
    this.upcoming = [];
    this.events = [];
    this.pickUpcoming();
  }

  // the tracks the next round will use (shown in the lobby): shuffled, none from the last round if possible
  pickUpcoming() {
    let cands = this.tracks.filter((t) => !this.lastTracks.includes(t.id) && !this.cfg.trackBlacklist.includes(t.id));
    if (cands.length < 4) cands = this.tracks.filter((t) => !this.cfg.trackBlacklist.includes(t.id));
    if (!cands.length) cands = this.tracks.slice();
    this.upcoming = shuffle(cands.slice());
  }

  // ------------------------------------------------------------------ people
  person(slot) { return this.people.get(slot); }
  addPerson(slot, name, csTeam, bot) {
    let pe = this.people.get(slot);
    if (!pe) {
      pe = { slot, name, csTeam, bot: !!bot, arena: null, car: null, status: 'none', lastActive: this.clock, afk: false, spec: null,
             carChoice: bot ? CAR_KEYS[Math.floor(rnd() * CAR_KEYS.length)] : this.cfg.defaultCar, wins: 0, races: 0 };
      this.people.set(slot, pe);
    } else { pe.name = name; pe.csTeam = csTeam; pe.bot = !!bot; }
    return pe;
  }
  removePerson(slot) {
    const pe = this.people.get(slot);
    if (!pe) return;
    this.leaveArena(pe, 'left');
    this.people.delete(slot);
  }
  markActive(slot) {
    const pe = this.people.get(slot);
    if (!pe) return;
    pe.lastActive = this.clock;
    if (pe.afk) { pe.afk = false; this.events.push({ type: 'afkClear', person: pe }); }
  }
  // the car picker: any time outside a race, and on the grid until the last 3 seconds
  setCar(pe, key) {
    if (!CARS[key]) return false;
    pe.carChoice = key;
    if (pe.car && pe.arena && pe.arena.state === 'grid' && pe.arena.countdown > 3 * TICRATE) pe.arena.setClass(pe.car, key);
    else if (pe.car && pe.arena && pe.arena.state === 'grid') return false;
    this.events.push({ type: 'carPick', person: pe, key });
    return true;
  }
  cycleCar(pe, dir) {
    const i = CAR_KEYS.indexOf(pe.carChoice);
    return this.setCar(pe, CAR_KEYS[((i < 0 ? 0 : i) + dir + CAR_KEYS.length) % CAR_KEYS.length]);
  }

  // ------------------------------------------------------------------ round start
  startRound() {
    this.endRoundCleanup();
    const eligible = [];
    for (const pe of this.people.values()) {
      if (pe.csTeam !== 2 && pe.csTeam !== 3) continue;
      // idle through the whole lobby and the race before it (watching counts as idle only for this long)
      if (!pe.bot && this.clock - pe.lastActive > this.cfg.afkLobbyTics) { pe.afk = true; }
      if (pe.afk && !pe.bot) { pe.status = 'none'; continue; }
      eligible.push(pe);
    }
    this.roundNumber++; this.time = 0;
    if (eligible.length < this.cfg.minPlayers) { this.state = 'idle'; this.events.push({ type: 'notEnough', count: eligible.length }); return false; }
    this.layout = layoutFor(this.cfg, this.roundNumber);
    const sizes = arenaSizes(eligible.length, Object.assign({}, this.cfg, this.layout));
    const groups = this.splitGroups(eligible, sizes);
    // tracks: the ones the lobby showed (different per arena, none from the last round)
    if (this.upcoming.length < groups.length) this.pickUpcoming();
    const cands = this.upcoming;
    this.plan = groups.map((grp, i) => ({ grp, track: cands[i % cands.length] }));
    this.lastTracks = this.plan.map((p) => p.track.id);
    this.pickUpcoming();
    for (const item of this.plan) for (const pe of item.grp) pe.status = 'planned';
    // anyone eligible but not placed (over 64) spectates
    for (const pe of eligible) if (pe.status !== 'planned') pe.status = 'none';
    this.pending = this.plan.slice();
    this.arenas = [];
    this.state = 'running';
    if (!this.cfg.staggerArenas) while (this.pending.length) this.buildNext();
    this.events.push({ type: 'roundStart', plan: this.plan });
    return true;
  }

  // each arena gets the same share of Ts and CTs (so the top-8 count is a fair fight), random within that
  splitGroups(eligible, sizes) {
    const ts = shuffle(eligible.filter((p) => p.csTeam === 2));
    const cts = shuffle(eligible.filter((p) => p.csTeam === 3));
    const groups = sizes.map(() => []);
    const T = ts.length, N = eligible.length;
    let tLeft = ts.length, ctLeft = cts.length, cum = 0;
    sizes.forEach((sz, i) => {
      const before = Math.round(T * cum / N); cum += sz;
      let tq = i === sizes.length - 1 ? tLeft : Math.round(T * cum / N) - before;
      tq = Math.max(0, Math.min(tq, tLeft, sz));
      let cq = sz - tq;
      if (cq > ctLeft) { tq += cq - ctLeft; cq = ctLeft; }
      tq = Math.min(tq, tLeft);
      for (let k = 0; k < tq; k++) groups[i].push(ts.pop());
      for (let k = 0; k < cq; k++) groups[i].push(cts.pop());
      tLeft -= tq; ctLeft -= cq;
    });
    for (const g of groups) shuffle(g);     // random grid order
    return groups;
  }

  buildNext() {
    const item = this.pending.shift();
    if (!item) return null;
    const grp = item.grp.filter((pe) => this.people.get(pe.slot) === pe && pe.status === 'planned');
    const arena = new Arena(this.arenas.length, item.track, {
      countdownTics: this.cfg.countdownTics, finishWindow: this.cfg.finishWindow, raceCap: this.cfg.raceCap, endHold: this.cfg.endHold, laps: this.cfg.laps,
    });
    this.arenas.push(arena);
    for (const pe of grp) {
      const car = arena.addCar(pe.slot, pe.name, pe.carChoice, pe.csTeam === 3 ? 1 : 0);
      car.person = pe; car.isBot = pe.bot;
      if (pe.bot) car.bot = makeBot(this.cfg.botSkill);
      pe.arena = arena; pe.car = car; pe.status = 'racing'; pe.spec = null; pe.lastActive = this.clock; pe.races++;
    }
    arena.placeGrid();
    this.events.push({ type: 'arenaBuilt', arena });
    return arena;
  }

  leaveArena(pe, why) {
    const a = pe.arena;
    if (a && pe.car) { a.removeCar(pe.slot, why); this.events.push({ type: 'leave', person: pe, arena: a, why }); }
    pe.arena = null; pe.car = null; pe.status = 'none'; pe.spec = null;
  }

  // rounds are locked: anyone arriving mid-round watches until the next one
  lateJoin(pe) {
    if (this.state !== 'running') return false;
    if (pe.arena) return true;
    this.spectate(pe);
    return false;
  }

  spectate(pe, arena) {
    pe.status = 'spectating';
    if (!pe.spec) pe.spec = { arena: arena ? arena.index : (pe.arena ? pe.arena.index : 0), target: null };
    this.fixSpectate(pe, 0);
  }
  // a car to watch: dir 0 = keep if still valid, 1/-1 = next/previous in the standings, 'arena' = next arena
  fixSpectate(pe, dir) {
    if (!pe.spec) pe.spec = { arena: 0, target: null };
    const live = this.arenas.filter((a) => a.state !== 'over' || a.finishedAt < a.cfg.endHold * TICRATE);
    const pool = live.length ? live : this.arenas;
    if (!pool.length) { pe.spec.target = null; return; }
    let ai = pool.findIndex((a) => a.index === pe.spec.arena);
    if (ai < 0) ai = 0;
    if (dir === 'arena') { ai = (ai + 1) % pool.length; pe.spec.target = null; dir = 0; }
    const arena = pool[ai];
    pe.spec.arena = arena.index;
    const vis = arena.ranking.filter((c) => c.visible && c.state !== 'withdrawn');
    if (!vis.length) { pe.spec.target = null; return; }
    let i = vis.findIndex((c) => c.slot === pe.spec.target);
    if (i < 0) i = 0;
    else if (dir) i = (i + dir + vis.length) % vis.length;
    pe.spec.target = vis[i].slot;
  }

  // ------------------------------------------------------------------ per tic
  tic() {
    this.clock++;
    if (this.state !== 'running') return;
    this.time++;
    if (this.pending.length) this.buildNext();
    for (const a of this.arenas) {
      if (a.state === 'over' && a.finishedAt >= a.cfg.endHold * TICRATE) continue;
      for (const c of a.order) if (c.isBot) botThink(a, c);
      a.step();
    }
    this.checkAfk();
    this.checkEnds();
  }

  checkAfk() {
    for (const pe of this.people.values()) {
      // people waiting for the next race (finished, wrecked, joined mid-race and watching) aren't idle: only an idle
      // driver, or someone idle through a whole lobby, sits out. (!afk and an AFK verdict while driving still stick.)
      if (!pe.bot && !pe.afk && (!pe.car || (!pe.car.racing && pe.car.state !== 'grid'))) pe.lastActive = this.clock;
      if (pe.bot || pe.status !== 'racing' || !pe.arena || pe.arena.state !== 'racing' || !pe.car || !pe.car.racing) continue;
      const idle = this.clock - pe.lastActive;
      if (idle === this.cfg.afkWarnTics) this.events.push({ type: 'afkWarn', person: pe });
      if (idle >= this.cfg.afkKickTics) {
        pe.afk = true;
        const a = pe.arena;
        this.leaveArena(pe, 'afk');
        this.events.push({ type: 'afk', person: pe });
        this.spectate(pe, a);
      }
    }
  }

  checkEnds() {
    for (const a of this.arenas) {
      if (a.state !== 'over' || a.finishedAt < a.cfg.endHold * TICRATE) continue;
      for (const c of a.order) {
        const pe = c.person;
        if (pe && pe.status === 'racing') { pe.status = 'spectating'; pe.spec = { arena: a.index, target: null }; this.fixSpectate(pe, 'arena'); }
      }
    }
    if (this.arenas.length && !this.pending.length && this.arenas.every((a) => a.over)) {
      this.state = 'over';
      this.events.push({ type: 'roundOver', arenas: this.arenas, points: this.teamPoints() });
    }
  }

  // ------------------------------------------------------------------ results
  // per arena: with 8+ cars, how many of the top 8 are T / CT; with fewer, 1 point to the winner's side
  teamPoints() {
    const pts = { 2: 0, 3: 0, best: { 2: 99, 3: 99 }, detail: [] };
    for (const a of this.arenas) {
      if (!a.result) continue;
      const r = a.result.ranking;
      const d = { track: a.track.title, t: 0, ct: 0 };
      if (r.length >= 8) {
        r.slice(0, 8).forEach((c) => { if (c.team === 0) d.t++; else if (c.team === 1) d.ct++; });
      } else if (r.length) {
        if (r[0].team === 0) d.t = 1; else if (r[0].team === 1) d.ct = 1;
      }
      r.forEach((c, i) => { const cs = c.team === 0 ? 2 : c.team === 1 ? 3 : 0; if (cs) pts.best[cs] = Math.min(pts.best[cs], i + 1); });
      pts[2] += d.t; pts[3] += d.ct; pts.detail.push(d);
    }
    let winner = pts[2] > pts[3] ? 2 : pts[3] > pts[2] ? 3 : 0;
    if (!winner && this.cfg.tiebreak) winner = pts.best[2] < pts.best[3] ? 2 : pts.best[3] < pts.best[2] ? 3 : 0;
    pts.winner = winner;
    return pts;
  }

  // who dies and who gets the credit when an arena's results are in
  killPlan(a) {
    const r = a.result ? a.result.ranking : [];
    const podium = r.slice(0, this.cfg.podium).filter((c) => c);
    const plan = [];
    // wrecked by someone's attack but not credited yet: the attacker gets that kill now (if still in the race's result)
    const deferred = r.slice(this.cfg.podium).filter((c) => !c.koApplied && !c.left && c.koBy && r.includes(c.koBy));
    for (const c of deferred) plan.push({ victim: c, killer: c.koBy });
    const losers = r.slice(this.cfg.podium).filter((c) => !c.koApplied && !c.left && !deferred.includes(c));
    const counts = splitShares(losers.length, this.cfg.shares.slice(0, Math.max(1, podium.length)));
    let k = 0;
    counts.forEach((n, i) => { for (let j = 0; j < n && k < losers.length; j++, k++) plan.push({ victim: losers[k], killer: podium[i] || null }); });
    while (k < losers.length) plan.push({ victim: losers[k++], killer: podium[0] || null });
    return plan;
  }

  endRoundCleanup() {
    for (const pe of this.people.values()) { pe.arena = null; pe.car = null; pe.status = 'none'; pe.spec = null; }
    this.arenas = []; this.pending = []; this.plan = [];
  }
}
