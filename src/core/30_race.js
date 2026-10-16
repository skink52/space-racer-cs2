// ===================================================================================
// Part 3: an arena = one race on one track: grid, countdown, the field, slipstreams, bumps, the Pulse, wrecks,
// finishing order and the end of the race. Pushes events for the CS2 side (sounds, HUD, kills).
// ===================================================================================

const ARENA_DEFAULTS = {
  countdownTics: 10 * TICRATE,     // on the grid before the lights
  finishWindow: 30,                // seconds the rest get after the winner
  raceCap: 300,                    // seconds: a race never runs longer than this
  endHold: 6,                      // seconds the results stay up before the arena is over
  laps: 0,                         // 0 = the track's own setting
};

class Arena {
  constructor(index, track, cfg) {
    this.index = index; this.track = track; this.cfg = Object.assign({}, ARENA_DEFAULTS, cfg || {});
    this.laps = this.cfg.laps || track.laps;
    this.cars = new Map();          // slot -> Car
    this.order = [];                // cars in grid order
    this.events = [];
    this.tic = 0; this.time = 0;    // tics / seconds since the arena was built
    this.state = 'grid';            // grid | racing | over
    this.countdown = this.cfg.countdownTics;
    this.raceTic = 0;               // tics since the lights went green
    this.finishCount = 0; this.firstFinishTic = 0;
    this.pulse = { active: false, total: 0, prev: 0, lapsSeen: 0 };
    this.ranking = [];              // cars sorted by position (updated every few tics)
    this.result = null;
    this.finishedAt = 0;
    this.lastBeep = -1;
  }

  addCar(slot, name, clsKey, team) {
    const car = new Car(slot, name, clsKey, team);
    this.cars.set(slot, car);
    this.order.push(car);
    return car;
  }

  // put every car on the grid (call once all cars are added); order = grid order
  placeGrid() {
    this.order.forEach((car, k) => {
      const g = this.track.gridSlot(k);
      car.placeAt(g.x, g.y, g.z, g.yaw, this.track);
      car.state = 'grid'; car.lapsDone = 0; car.nextCp = 1; car.total = -1000 + k;   // grid order until the start
      car.gridPos = k;
    });
    this.ranking = this.order.slice();
  }

  // the car picker on the grid: swap a car's class (keeps its grid slot)
  setClass(car, clsKey) {
    if (!CARS[clsKey] || car.state !== 'grid') return false;
    car.cls = clsKey; car.spec = CARS[clsKey]; car.shield = car.spec.shield; car.charge = RULES.startCharge;
    return true;
  }

  removeCar(slot, why) {
    const car = this.cars.get(slot);
    if (!car) return;
    if (car.racing || car.state === 'grid') { car.state = 'withdrawn'; car.wreckTotal = car.total; car.wreckTime = this.raceTic; car.stateTime = 0; }
    car.left = why === 'left';
    this.events.push({ type: 'withdraw', car, why });
  }

  // ---------------------------------------------------------------- per tic
  step() {
    this.tic++; this.time = this.tic / TICRATE;
    if (this.state === 'grid') {
      this.countdown--;
      const secs = Math.ceil(this.countdown / TICRATE);
      if (secs <= 3 && secs !== this.lastBeep && this.countdown > 0) { this.lastBeep = secs; this.events.push({ type: 'beep', n: secs }); }
      // turbo start: remember when each driver last pressed the gas during the final beeps
      if (secs <= 3) for (const car of this.order) {
        if (car.state !== 'grid' || car.isBot) continue;
        if (car.cmd.throttle > 0) { if (car.gasAt === null) car.gasAt = this.countdown; } else car.gasAt = null;
      }
      if (this.countdown <= 0) {
        this.state = 'racing'; this.raceTic = 0;
        for (const car of this.order) if (car.state === 'grid') {
          car.state = 'racing'; car.stateTime = 0; car.lapStart = 0; car.noDamage = RULES.startProtect;
          // gas pressed in the last moment before the lights: a turbo start; held down since long before: a stall
          const g = car.isBot ? (rnd() < car.bot.skill * RULES.botLaunch ? 1 : null) : car.gasAt;
          if (g !== null && g <= RULES.launchWindow * TICRATE) {
            const fx = Math.cos(car.yaw), fy = Math.sin(car.yaw);
            car.vx += fx * RULES.launchKick; car.vy += fy * RULES.launchKick; car.padTimer = RULES.launchTime; car.fx |= 8;
            this.events.push({ type: 'launch', car });
          } else if (g !== null && g > RULES.stallAfter * TICRATE) {
            car.stall = RULES.stallTime;
            this.events.push({ type: 'stall', car });
          }
          car.gasAt = null;
        }
        this.events.push({ type: 'go' });
      }
      return;
    }
    if (this.state !== 'racing') { this.finishedAt++; return; }
    this.raceTic++;
    const dt = DT;
    const cars = this.order;
    // slipstreams: who is directly behind whom
    for (const c of cars) c.draft = null;
    for (const c of cars) {
      if (!c.solid || c.speed < 300) continue;
      const fx = Math.cos(c.yaw), fy = Math.sin(c.yaw);
      let best = null, bestAlong = 1e9;
      for (const o of cars) {
        if (o === c || !o.solid || o.speed < 350) continue;
        const rx = o.x - c.x, ry = o.y - c.y;
        const along = rx * fx + ry * fy;
        if (along < 60 || along > 360) continue;
        const side = Math.abs(-rx * fy + ry * fx);
        if (side > 70 || Math.abs(o.z - c.z) > 60) continue;
        if (along < bestAlong) { best = o; bestAlong = along; }
      }
      c.draft = best;
    }
    // drive
    for (const c of cars) c.step(this.track, dt, this.raceTic);
    // bumps
    for (let i = 0; i < cars.length; i++) {
      const a = cars[i];
      if (!a.solid) continue;
      for (let j = i + 1; j < cars.length; j++) {
        const b = cars[j];
        if (!b.solid) continue;
        if (Math.abs(a.x - b.x) > CAR_R * 2 || Math.abs(a.y - b.y) > CAR_R * 2) continue;
        collideCars(a, b, this.raceTic);
      }
    }
    // wrecks, finishes, departures
    for (const c of cars) {
      if (c.state === 'racing' || c.state === 'falling') {
        if (c.shield <= 0) {
          c.state = 'wrecked'; c.stateTime = 0; c.wreckTotal = c.total; c.wreckTime = this.raceTic; c.shield = 0;
          const attacker = c.lastHit && this.raceTic - c.lastHit.tic <= RULES.koCreditWindow * TICRATE ? this.cars.get(c.lastHit.slot) : null;
          this.events.push({ type: 'wreck', car: c, attacker: attacker && attacker !== c ? attacker : null });
        } else if (c.state === 'racing' && c.lapsDone >= this.laps) {
          c.state = 'finished'; c.stateTime = 0; c.finishPos = ++this.finishCount; c.finishTime = this.raceTic / TICRATE; c.ghost = 99;
          c.total = 1e9 - c.finishPos;
          if (this.finishCount === 1) this.firstFinishTic = this.raceTic;
          this.events.push({ type: 'finish', car: c, pos: c.finishPos });
        } else if (c.fx & 256) this.events.push({ type: 'lap', car: c, lap: c.lapsDone, last: c.lastLap });
      } else if (c.state === 'finished' && c.stateTime > 1.0) { c.state = 'gone'; this.events.push({ type: 'gone', car: c }); }
    }
    // the Pulse: once per lap of the leader, a ring sweeps from the back and tops up everyone it passes
    if (RULES.pulseEnabled) this.pulseStep(dt);
    if ((this.raceTic & 7) === 0) this.rank();
    // end of the race
    const active = cars.filter((c) => c.racing);
    const cap = this.raceTic >= this.cfg.raceCap * TICRATE;
    const window = this.firstFinishTic && this.raceTic - this.firstFinishTic >= this.cfg.finishWindow * TICRATE;
    if (!active.length || cap || window) this.end(cap ? 'time' : window ? 'window' : 'all');
  }

  pulseStep(dt) {
    const p = this.pulse;
    const racing = this.order.filter((c) => c.state === 'racing');
    if (!racing.length) { p.active = false; return; }
    let leader = -Infinity, back = Infinity;
    for (const c of racing) { if (c.total > leader) leader = c.total; if (c.total < back) back = c.total; }
    const leaderLaps = Math.floor(leader / this.track.len);
    if (!p.active && leaderLaps > p.lapsSeen && leaderLaps < this.laps) {
      p.lapsSeen = leaderLaps; p.active = true; p.total = back - 400; p.prev = p.total;
      this.events.push({ type: 'pulse', start: true });
    }
    if (!p.active) return;
    p.prev = p.total; p.total += RULES.pulseSpeed * dt;
    for (const c of racing) {
      if (c.total > p.prev && c.total <= p.total) { c.charge = Math.min(c.spec.charge, c.charge + RULES.pulseCharge); c.fx |= 4; c.pulsed = 0.6; this.events.push({ type: 'pulsed', car: c }); }
    }
    if (p.total > leader + 300) { p.active = false; this.events.push({ type: 'pulse', start: false }); }
  }

  // position order: finished by finish order, then racing by progress, then wrecked/withdrawn by progress at the time
  rank() {
    const key = (c) => {
      if (c.state === 'finished' || c.state === 'gone') return 3e9 - c.finishPos;
      if (c.racing) return 1e9 + c.total;
      if (c.left) return -2e9 + c.wreckTotal;
      return c.wreckTotal;
    };
    this.ranking = this.order.slice().sort((a, b) => key(b) - key(a));
    this.ranking.forEach((c, i) => { c.pos = i + 1; });
    return this.ranking;
  }

  end(reason) {
    if (this.state !== 'racing') return;
    this.state = 'over'; this.finishedAt = 0;
    for (const c of this.order) {
      if (c.racing) { c.state = 'dnf'; c.wreckTotal = c.total; c.wreckTime = this.raceTic; }
    }
    this.rank();
    const racers = this.ranking.filter((c) => !c.left);
    this.result = { reason, ranking: racers, winner: racers[0] || null, count: racers.length };
    this.events.push({ type: 'arenaEnd', arena: this, result: this.result });
  }

  get over() { return this.state === 'over' && this.finishedAt >= this.cfg.endHold * TICRATE; }
}
