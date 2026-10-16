// ===================================================================================
// Part 2: a car - state, driving physics, rails, falls, pads, boost, drift, spin attack, bumps.
// ===================================================================================

class Car {
  constructor(slot, name, clsKey, team) {
    this.slot = slot; this.name = name; this.cls = clsKey; this.spec = CARS[clsKey] || CARS.hornet; this.team = team;
    this.isBot = false; this.bot = null; this.person = null;
    this.x = 0; this.y = 0; this.z = 0; this.yaw = 0; this.vx = 0; this.vy = 0; this.vz = 0;
    this.speed = 0; this.vf = 0; this.vl = 0;
    this.shield = this.spec.shield; this.charge = RULES.startCharge;
    this.state = 'grid';          // grid | racing | falling | finished | gone | wrecked | withdrawn
    this.cmd = { throttle: 0, steer: 0, boost: false, drift: false, spin: false };
    this.padTimer = 0; this.boosting = false; this.drifting = false; this.sliding = false; this.onCharge = false; this.slick = false;
    this.draft = null; this.spinTimer = 0; this.spinCd = 0; this.spinYaw = 0; this.hitCd = 0; this.ghost = 0;
    this.seg = 0; this.t = 0; this.d = 0; this.s = 0; this.prevS = 0; this.rawLap = 0; this.lapsDone = 0; this.nextCp = 1; this.total = 0;
    this.lapStart = 0; this.bestLap = 0; this.lastLap = 0;
    this.finishPos = 0; this.finishTime = 0; this.wreckTotal = 0; this.wreckTime = 0; this.stateTime = 0;
    this.lastHit = null;           // { slot, tic }
    this.wrongWay = 0; this.wrongWayFlag = false; this.offLine = false;
    this.fallTimer = 0; this.fx = 0;   // fx bits for the renderer: 1 hit, 2 rail, 4 pulsed, 8 pad, 16 fell
    this.pulsed = 0; this.noDamage = 0; this.calm = 0;   // seconds of no-damage after the start
    this.air = false; this.tz = 0; this.lift = 0; this.airTime = 0;   // jumps: airborne flag, track height, ramp height under the car
    this.bank = 0;                 // tan of the road's lean under the car (banked bends)
    this.gasAt = null; this.stall = 0;   // turbo start: when the gas went down on the grid; seconds of stalled engine
  }

  placeAt(x, y, z, yaw, track) {
    this.x = x; this.y = y; this.z = z; this.yaw = yaw; this.vx = 0; this.vy = 0; this.vz = 0; this.speed = 0; this.vf = 0; this.vl = 0;
    this.air = false; this.tz = z; this.lift = 0;
    const p = track.locateAll(x, y, z);
    this.seg = p.i; this.t = p.t; this.d = p.d; this.s = p.s; this.prevS = p.s;
  }

  get racing() { return this.state === 'racing' || this.state === 'falling'; }
  get solid() { return this.state === 'racing' && this.ghost <= 0; }
  get visible() { return this.state === 'racing' || this.state === 'falling' || this.state === 'grid' || this.state === 'finished' || (this.state === 'wrecked' && this.stateTime < RULES.wreckShow); }

  // ---------------------------------------------------------------- one physics step
  step(track, dt, tic) {
    const sp = this.spec, c = this.cmd;
    this.fx = 0;
    if (this.spinCd > 0) this.spinCd -= dt;
    if (this.hitCd > 0) this.hitCd -= dt;
    if (this.ghost > 0) this.ghost -= dt;
    if (this.noDamage > 0) this.noDamage -= dt;
    this.stateTime += dt;
    if (this.state === 'falling') { this.fallStep(track, dt); return; }
    if (this.state !== 'racing' && this.state !== 'finished') return;
    const finished = this.state === 'finished';
    // finished cars coast on autopilot for a moment, then leave
    if (this.stall > 0) this.stall -= dt;
    const throttle = finished ? 0.4 : this.stall > 0 ? 0 : clamp(c.throttle, -1, 1);
    const steer = finished ? this.autoSteer(track) : (this.spinTimer > 0 ? 0 : clamp(c.steer, -1, 1));
    const air = this.air;
    const wantBoost = !finished && !air && c.boost && this.charge > 0;
    this.drifting = !finished && !air && c.drift && this.speed > 250;
    // spin attack
    if (!finished && c.spin && this.spinCd <= 0 && this.charge >= sp.spinCost && this.spinTimer <= 0) {
      this.charge -= sp.spinCost; this.spinTimer = RULES.spinTime; this.spinCd = RULES.spinCooldown; this.fx |= 32;
    }
    c.spin = false;
    if (this.spinTimer > 0) { this.spinTimer -= dt; this.spinYaw += dt * (4 * Math.PI / RULES.spinTime); if (this.spinTimer <= 0) this.spinYaw = 0; }
    // heading
    let fx = Math.cos(this.yaw), fy = Math.sin(this.yaw);
    this.vf = this.vx * fx + this.vy * fy;
    const absv = Math.abs(this.vf);
    let turnRate = sp.turn * clamp(absv / 220, 0, 1) / (1 + Math.max(0, absv - 450) / 1500);
    if (this.drifting) turnRate *= 1.45;
    if (this.slick) turnRate *= 0.8;
    if (this.spinTimer > 0) turnRate *= 0.3;
    if (!air) turnRate *= 1 + Math.abs(this.bank) * RULES.bankTurn;   // banked bends turn tighter
    if (air) turnRate *= RULES.airControl;
    this.yaw += turnRate * steer * dt * (this.vf < 0 ? -1 : 1);
    fx = Math.cos(this.yaw); fy = Math.sin(this.yaw);
    const lx = -fy, ly = fx;
    let vf = this.vx * fx + this.vy * fy, vl = this.vx * lx + this.vy * ly;
    // engine
    this.boosting = wantBoost;
    if (this.boosting) this.charge = Math.max(0, this.charge - RULES.boostDrain * dt);
    let mult = 1;
    if (this.boosting) mult = sp.boost;
    if (this.padTimer > 0) { this.padTimer -= dt; mult = Math.max(mult, RULES.padSpeed) + (this.boosting ? 0.1 : 0); }
    if (this.draft) mult *= RULES.draftSpeed;
    const target = sp.maxSpeed * mult;
    let acc = sp.accel * (this.boosting ? 1.6 : 1) * (this.padTimer > 0 ? 1.5 : 1) * (this.draft ? 1.15 : 1);
    if (air) {
      vf -= vf * 0.05 * dt;            // no thrust or brakes in the air
    } else if (throttle > 0) {
      if (vf < target) vf = Math.min(target, vf + acc * throttle * dt);
    } else if (throttle < 0) {
      vf = Math.max(-RULES.reverseMax, vf + sp.brake * throttle * dt);
    } else {
      vf -= vf * RULES.coastDrag * dt;
    }
    if (vf > target && !air) vf -= (vf - target) * 3 * dt;
    // grip: bleed off sideways speed
    let grip = this.drifting ? sp.driftGrip : sp.grip;
    if (this.slick) grip *= RULES.slickGrip;
    if (this.spinTimer > 0) grip *= 0.5;
    if (!air) grip *= 1 + Math.abs(this.bank) * RULES.bankGrip;        // ... and hold the car better
    const g = air ? 1 : Math.exp(-grip * dt);
    this.sliding = Math.abs(vl) > 90 && absv > 300;
    if (this.drifting && this.sliding) this.charge = Math.min(sp.charge, this.charge + RULES.driftChargeRate * sp.driftCharge * dt);
    vl *= g;
    this.vx = vf * fx + vl * lx; this.vy = vf * fy + vl * ly;
    this.vf = vf; this.vl = vl;
    this.speed = Math.hypot(this.vx, this.vy);
    this.x += this.vx * dt; this.y += this.vy * dt;
    // where on the track are we now
    const p = track.locate(this.x, this.y, this.tz, this.seg);
    this.seg = p.i; this.t = p.t; this.d = p.d; this.tz = p.z; this.bank = p.bank;
    this.prevS = this.s; this.s = p.s;
    // height: ramps lift the car, the lip of a ramp throws it, an open gap drops it
    const lift = track.rampLift(p.i, p.t);
    const ground = p.z + lift;
    const road = track.road[p.i];
    if (this.air) {
      this.airTime += dt;
      this.vz -= RULES.gravity * dt;
      this.z += this.vz * dt;
      if (this.z <= ground && road && !finished) {
        this.air = false; this.z = ground; this.fx |= 1024;
        if (this.vz < -RULES.landSafe && this.noDamage <= 0) this.damage(Math.min(RULES.contactMax, (-this.vz - RULES.landSafe) * 0.03), null, tic);
        this.vz = 0;
      } else if (!road && this.z < ground - 40 && !finished) {
        this.state = 'falling'; this.stateTime = 0; this.fallTimer = RULES.fallTime; this.fx |= 16; this.air = false;
      } else if (finished && this.z <= ground) { this.air = false; this.z = ground; this.vz = 0; }
    } else if (this.lift > 0 && lift === 0 && (!road || track.rampLift((p.i - 1 + track.n) % track.n, 0.99) > 0)) {
      // off the lip: fly with the ramp's slope
      const along = this.vx * track.tx[p.i] + this.vy * track.ty[p.i];
      const f = track.rampAt(p.i - 1);
      const slope = f ? f.h / ((f.b - f.a + 1) * track.step) : 0.3;
      this.air = true; this.airTime = 0; this.z = p.z + this.lift; this.vz = Math.max(0, along) * slope + RULES.rampKick; this.fx |= 512;
    } else if (!road && !finished) {
      this.state = 'falling'; this.stateTime = 0; this.fallTimer = RULES.fallTime; this.vz = 0; this.fx |= 16;
    } else {
      this.z = ground;
    }
    this.lift = this.air ? 0 : lift;
    if (this.state === 'falling') { this.speed = Math.hypot(this.vx, this.vy); return; }
    // rails and gaps
    const limit = p.hw - CAR_R * 0.7;
    if (Math.abs(this.d) > limit) {
      const side = this.d > 0 ? 1 : -1;
      const nx = track.nx[p.i] * side, ny = track.ny[p.i] * side;   // points out of the track on this side
      if (p.rail || finished) {
        const over = Math.abs(this.d) - limit;
        this.x -= nx * over; this.y -= ny * over; this.d = side * limit;
        const vn = this.vx * nx + this.vy * ny;
        if (vn > 0) {
          this.vx -= (1 + RULES.railRestitution) * vn * nx; this.vy -= (1 + RULES.railRestitution) * vn * ny;
          const hard = Math.max(0, vn - 140);
          if (hard > 0 && !finished) {
            if (this.noDamage <= 0) this.damage(Math.min(RULES.contactMax, hard * 0.04), null, tic);
            const k = 1 - Math.min(0.45, vn / 1400);
            this.vx *= k; this.vy *= k;
            this.fx |= 2;
          } else this.fx |= 64;   // scrape
          // turn the nose a little away from the wall so the car doesn't grind along it
          const away = Math.atan2(-ny, -nx);
          this.yaw += normRad(away - this.yaw) * Math.min(1, vn / 600) * 0.15;
        }
      } else if (Math.abs(this.d) > p.hw + CAR_R * 0.4 && !finished) {
        this.state = 'falling'; this.stateTime = 0; this.fallTimer = RULES.fallTime; this.vz = 0; this.fx |= 16;
      }
    }
    this.speed = Math.hypot(this.vx, this.vy);
    // progress bookkeeping (laps and checkpoints)
    this.progress(track, tic);
    // features under the car
    this.onCharge = false; this.slick = false;
    const feats = this.air ? null : track.featuresAt(this.seg, -this.d / Math.max(1, p.hw));
    if (feats && !finished) {
      for (const f of feats) {
        if (f.kind === 'boost') {
          if (this.padTimer <= 0) { this.vx += fx * RULES.padKick; this.vy += fy * RULES.padKick; this.fx |= 8; }
          this.padTimer = Math.max(this.padTimer, RULES.padTime * sp.padMult);
        } else if (f.kind === 'charge') {
          this.onCharge = true;
          this.charge = Math.min(sp.charge, this.charge + RULES.chargeRate * sp.chargeMult * dt);
          this.shield = Math.min(sp.shield, this.shield + RULES.chargeShield * dt);
        } else if (f.kind === 'slick') this.slick = true;
      }
    }
    // slow repair when nothing has hit us for a while
    this.calm += dt;
    if (this.calm > RULES.regenDelay && !finished) this.shield = Math.min(sp.shield, this.shield + RULES.regenRate * dt);
    // slipstream bonus (draft is set by the arena before the step)
    if (this.draft && !finished) {
      const team = this.draft.team >= 0 && this.draft.team === this.team;
      this.charge = Math.min(sp.charge, this.charge + RULES.draftCharge * sp.draftMult * (team ? 2 : 1) * dt);
      if (sp.draftRegen) this.shield = Math.min(sp.shield, this.shield + sp.draftRegen * dt);
    }
    // wrong way: moving against the track direction for a while
    const along = this.vx * track.tx[this.seg] + this.vy * track.ty[this.seg];
    if (along < -60) this.wrongWay += dt; else this.wrongWay = 0;
    this.wrongWayFlag = this.wrongWay > RULES.wrongWayTime;
  }

  autoSteer(track) {
    const p = track.point(this.s + 260);
    const want = Math.atan2(p.y - this.y, p.x - this.x);
    return clamp(normRad(want - this.yaw) * 2, -1, 1);
  }

  fallStep(track, dt) {
    this.fallTimer -= dt;
    this.vz -= 900 * dt;
    this.x += this.vx * dt; this.y += this.vy * dt; this.z += this.vz * dt;
    this.vx *= 0.98; this.vy *= 0.98;
    if (this.fallTimer <= 0) {
      // back to the last checkpoint we passed, on the centreline, facing forward
      const cpi = track.cp[(this.nextCp - 1 + track.cp.length) % track.cp.length];
      const s = cpi * track.step + 40;
      const p = track.point(s);
      this.x = p.x; this.y = p.y; this.z = p.z; this.yaw = Math.atan2(p.ty, p.tx);
      this.vx = 0; this.vy = 0; this.vz = 0; this.speed = 0; this.vf = 0; this.vl = 0;
      this.seg = p.i; this.s = s; this.prevS = s; this.d = 0; this.air = false; this.tz = p.z; this.lift = 0;
      this.state = 'racing'; this.stateTime = 0; this.ghost = 1.5; this.padTimer = 0;
      this.shield -= RULES.fallPenalty;
      this.fx |= 128;
    }
  }

  // laps and checkpoints from the change of progress this tick
  progress(track, tic) {
    const L = track.len;
    let ds = this.s - this.prevS;
    if (ds < -L / 2) { ds += L; this.rawLap++; this.crossStart(track, 1, tic); }
    else if (ds > L / 2) { ds -= L; this.rawLap--; this.crossStart(track, -1, tic); }
    // checkpoints 1..7: passed forward when progress crosses them
    if (ds > 0) {
      const k = this.nextCp;
      if (k < track.cp.length) {
        const cs = track.cpS[k];
        if (this.crossed(this.prevS, this.s, cs, L)) this.nextCp = k + 1;
      }
    } else if (ds < 0) {
      const k = this.nextCp - 1;
      if (k >= 1 && this.crossed(this.s, this.prevS, track.cpS[k], L)) this.nextCp = k;
    }
    // ranking progress: clamp to the next checkpoint so a missed one (or a crossing cut) doesn't count
    let s = this.s;
    const nextS = this.nextCp < track.cp.length ? track.cpS[this.nextCp] : L;
    this.offLine = s > nextS + track.step * 3;
    if (this.offLine) s = nextS;
    this.total = this.lapsDone * L + s;
  }

  crossed(a, b, c, L) {
    // did progress going forward from a to b pass c (a < b; a and b are not wrapped here)
    if (a <= b) return a < c && c <= b;
    return false;
  }

  crossStart(track, dir, tic) {
    if (dir > 0) {
      if (this.nextCp >= track.cp.length) {
        this.lapsDone++; this.nextCp = 1;
        const now = tic / TICRATE;
        this.lastLap = now - this.lapStart; this.lapStart = now;
        if (!this.bestLap || this.lastLap < this.bestLap) this.bestLap = this.lastLap;
        this.fx |= 256;
      }
    } else {
      // reversing back over the line: undo a lap if it was complete
      if (this.nextCp === 1 && this.lapsDone > 0) { this.lapsDone--; this.nextCp = track.cp.length; }
    }
  }

  damage(amount, attacker, tic) {
    if (amount <= 0 || this.state !== 'racing') return;
    this.shield -= amount;
    this.fx |= 1;
    if (attacker && attacker !== this) this.lastHit = { slot: attacker.slot, tic };
    this.calm = 0;
  }
}

// ---------------------------------------------------------------- pairs
// bumps between two solid cars: separate them, swap momentum by mass, shield damage from the closing speed
function collideCars(a, b, tic) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const dist2 = dx * dx + dy * dy;
  const R = CAR_R * 2;
  if (dist2 >= R * R || Math.abs(a.z - b.z) > 60) return;
  const dist = Math.sqrt(dist2) || 0.01;
  const nx = dx / dist, ny = dy / dist;
  const ma = a.spec.mass, mb = b.spec.mass, msum = ma + mb;
  const over = R - dist;
  a.x -= nx * over * (mb / msum); a.y -= ny * over * (mb / msum);
  b.x += nx * over * (ma / msum); b.y += ny * over * (ma / msum);
  const vrel = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny;   // > 0: closing
  if (vrel > 0) {
    const j = (1 + RULES.contactRestitution) * vrel / (1 / ma + 1 / mb);
    a.vx -= j / ma * nx; a.vy -= j / ma * ny;
    b.vx += j / mb * nx; b.vy += j / mb * ny;
    let base = Math.min(RULES.contactMax, Math.max(0, vrel - RULES.contactSoft) * 0.03);
    if (a.noDamage > 0 || b.noDamage > 0) base = 0;
    let da = base, db = base;
    if (a.spec.ram > 1) { db *= a.spec.ram; da /= a.spec.ram; }
    if (b.spec.ram > 1) { da *= b.spec.ram; db /= b.spec.ram; }
    if (a.spinTimer > 0 && b.spinTimer <= 0 && b.noDamage <= 0) { db = Math.max(db, RULES.spinDamage); da = 0; b.vx += nx * RULES.spinKnock / mb; b.vy += ny * RULES.spinKnock / mb; }
    else if (b.spinTimer > 0 && a.spinTimer <= 0 && a.noDamage <= 0) { da = Math.max(da, RULES.spinDamage); db = 0; a.vx -= nx * RULES.spinKnock / ma; a.vy -= ny * RULES.spinKnock / ma; }
    else if (a.spinTimer > 0 && b.spinTimer > 0) { da = db = RULES.spinDamage; }
    if (a.hitCd <= 0 && da > 0) { a.damage(da, b, tic); a.hitCd = 0.25; }
    if (b.hitCd <= 0 && db > 0) { b.damage(db, a, tic); b.hitCd = 0.25; }
    if (da > 0 || db > 0) { a.fx |= 1; b.fx |= 1; }
  }
}
