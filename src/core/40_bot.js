// ===================================================================================
// Part 4: the driving AI (CS2 bots race with it, and it drives finished cars off the line).
// Lane discipline: every bot has a home lane (from its grid column) and keeps it; it only changes lane to pass a
// slower car, into a lane that is clear, and drifts back home afterwards. Corners pull it a little to the inside.
// ===================================================================================

const BOT_LANES = [-0.7, -0.35, 0, 0.35, 0.7];

function makeBot(skill) {
  return {
    skill: clamp(skill + (rnd() - 0.5) * 0.3, 0.05, 1),
    home: null, lane: 0, passTimer: 0, think: 0,
    aggression: rnd(), noise: 0, boostHold: 0, brakeHold: 0,
  };
}

// the nearest car just ahead of `car` near a lateral position (-1 left edge .. 1 right edge)
function laneTraffic(arena, car, lane, ahead) {
  const T = arena.track;
  let worst = null;
  for (const o of arena.order) {
    if (o === car || !o.solid) continue;
    const ds = o.total - car.total;
    if (ds < (ahead < 0 ? ahead : -60) || ds > Math.abs(ahead)) continue;
    const ol = -o.d / Math.max(1, T.hw[o.seg]);
    if (Math.abs(ol - lane) > 0.3) continue;
    if (!worst || ds < worst.ds) worst = { car: o, ds };
  }
  return worst;
}

function botThink(arena, car) {
  const b = car.bot, T = arena.track, c = car.cmd;
  if (!b || car.state !== 'racing') { c.throttle = 0; c.steer = 0; c.boost = false; c.drift = false; return; }
  if (car.air) { c.steer = 0; c.throttle = 1; c.boost = false; c.drift = false; return; }
  b.think--;
  if (b.think > 0) return;             // decisions a few times a second; the previous command keeps running
  b.think = 2 + Math.round((1 - b.skill) * 3);
  const dt = b.think * DT;
  const seg = car.seg;
  if (b.home === null) { b.home = BOT_LANES[(car.gridPos || 0) % 5]; b.lane = b.home; }
  // jumps: line up in the middle and go flat out
  const ramp = T.nextFeature(seg, 'ramp', 28);
  let lane;
  b.passTimer -= dt;
  if (ramp) {
    lane = b.lane * 0.7;                // ramps are full width: hold the lane, just keep straight
  } else {
    // pass slower traffic in our lane, otherwise return home
    const mine = laneTraffic(arena, car, b.lane, 260);
    if (mine && mine.car.speed < car.speed + 40 && b.passTimer <= 0) {
      let best = null;
      for (const l of BOT_LANES) {
        if (l === b.lane) continue;
        const t = laneTraffic(arena, car, l, 320) || laneTraffic(arena, car, l, -140);
        const score = (t ? 1000 - t.ds : 0) + Math.abs(l - b.lane) * 200;
        if (!best || score < best.score) best = { l, score };
      }
      if (best && best.score < 1000) { b.lane = best.l; b.passTimer = 2.5; }
    } else if (b.passTimer <= 0 && b.lane !== b.home && !laneTraffic(arena, car, b.home, 320)) b.lane = b.home;
    lane = b.lane;
    // low on charge: head for the next charge platform; a boost pad near our lane: take it
    if (car.charge < car.spec.charge * 0.3) {
      const nf = T.nextFeature(seg, 'charge', 24);
      if (nf && !laneTraffic(arena, car, (nf.f.l0 + nf.f.l1) / 2, 300)) lane = (nf.f.l0 + nf.f.l1) / 2;
    }
    const bp = T.nextFeature(seg, 'boost', 10);
    if (bp) { const mid = (bp.f.l0 + bp.f.l1) / 2; if (Math.abs(mid - lane) < 0.5) lane = lane * 0.4 + mid * 0.6; }
    // corners: a little towards the inside
    const k2 = (seg + 16) % T.n;
    const turn = normRad(Math.atan2(T.ty[k2], T.tx[k2]) - Math.atan2(T.ty[seg], T.tx[seg]));
    lane = clamp(lane - turn * 0, -0.85, 0.85);
    if (!T.rail[seg] || !T.rail[(seg + 6) % T.n]) lane *= 0.4;
  }
  // steer towards a point ahead on the chosen lane
  const look = clamp(140 + car.speed * 0.32, 200, 520);
  const p = T.point(car.s + look);
  const tx = p.x - p.nx * lane * p.hw * 0.92, ty = p.y - p.ny * lane * p.hw * 0.92;
  const want = Math.atan2(ty - car.y, tx - car.x);
  const diff = normRad(want - car.yaw);
  b.noise = b.noise * 0.7 + (rnd() - 0.5) * (1 - b.skill) * 0.2;
  c.steer = clamp(diff * 2.4 + b.noise, -1, 1);
  // speed control from the bend ahead
  const bend = T.curve[(seg + Math.round(look / T.step)) % T.n];
  const tight = bend > 0.55 + b.skill * 0.25;
  c.drift = !ramp && tight && car.speed > 600 && Math.abs(diff) > 0.25;
  b.brakeHold -= dt;
  // can we make the bend at this speed? (turn rate needed vs the car's turn rate at this speed, with a margin by skill)
  let worstK = 0;
  for (let k = 4; k <= 28; k += 4) worstK = Math.max(worstK, T.curve[(seg + k) % T.n] / (10 * T.step));
  const v = car.speed, omega = car.spec.turn / (1 + Math.max(0, v - 450) / 1500);
  const tooFast = v * worstK > omega * (0.72 + b.skill * 0.18);
  if (!ramp && (tooFast || (bend > 0.9 && v > 700 - b.skill * 150))) b.brakeHold = 0.2;
  // don't ram the car in front: brake if closing on it, ease off if it is just slower
  const front = laneTraffic(arena, car, lane, 220);
  const closing = front ? car.speed - front.car.speed : 0;
  const tooClose = !!front && closing > 40 && front.ds < 90 + closing * 0.35;
  c.throttle = b.brakeHold > 0 ? -0.5 : tooClose && !ramp ? (closing > 150 ? -0.6 : 0) : 1;
  // boost on straights when there is charge to spare (always before a jump)
  b.boostHold -= dt;
  const straight = bend < 0.25;
  if (ramp && car.charge > 5) b.boostHold = 0.4;
  else if ((straight && car.charge > 45 + (1 - b.aggression) * 30) || car.charge > car.spec.charge * 0.9) b.boostHold = 0.6;
  c.boost = b.boostHold > 0 && !tight && !tooClose && !tooFast;
  // spin attack only when an opponent is right alongside
  if (!ramp && car.charge > 60 && car.spinCd <= 0 && b.aggression > 0.4) {
    const fx = Math.cos(car.yaw), fy = Math.sin(car.yaw);
    for (const o of arena.order) {
      if (o === car || !o.solid || (o.team >= 0 && o.team === car.team)) continue;
      const rx = o.x - car.x, ry = o.y - car.y;
      const along = rx * fx + ry * fy, side = Math.abs(-rx * fy + ry * fx);
      if (Math.abs(along) < 50 && side < 70 && rnd() < b.aggression * 0.12) { c.spin = true; break; }
    }
  }
  // the E ability
  b.abilThink = (b.abilThink || 0) - dt;
  if (car.lock > 0 && car.spec.ability === 'quake') b.abilThink = car.lock + (1 - b.aggression) * 3;   // the calmer Meteors wait a little longer
  if (!ramp && b.abilThink <= 0 && car.abilCd <= 0 && car.charge >= car.spec.abilityCost) { b.abilThink = 0.25; botAbility(arena, car, b, c, straight); }
}

// when a bot uses its car's E ability: dodge a spin or slip past a blocker (Phase Dash), a Shockwave into a crowd,
// Nova Burn down a straight, Aegis when hurt in traffic or boxed in
function botAbility(arena, car, b, c, straight) {
  const kind = car.spec.ability;
  const fx = Math.cos(car.yaw), fy = Math.sin(car.yaw);
  let near = 0, alongside = null, ahead = null;
  for (const o of arena.order) {
    if (o === car || !o.solid) continue;
    const rx = o.x - car.x, ry = o.y - car.y;
    if (Math.abs(rx) > 600 || Math.abs(ry) > 600) continue;
    const along = rx * fx + ry * fy, side = -rx * fy + ry * fx;     // side > 0: on our left
    const foe = !(o.team >= 0 && o.team === car.team);
    if (foe && Math.hypot(rx, ry) < RULES.quakeRadius * 0.8) near++;
    if (foe && Math.abs(along) < 70 && Math.abs(side) < 120 && (!alongside || Math.abs(side) < Math.abs(alongside.side))) alongside = { o, side };
    if (along > 40 && along < 220 && Math.abs(side) < 70 && (!ahead || along < ahead.along)) ahead = { o, along };
  }
  const roll = rnd();
  if (kind === 'dash') {
    if (alongside && alongside.o.spinTimer > 0 && roll < 0.6) { c.ability = true; c.abilityDir = alongside.side > 0 ? -1 : 1; }
    else if (ahead && car.speed - ahead.o.speed > 80 && roll < 0.4 * b.aggression) c.ability = true;
  } else if (kind === 'quake') {
    if (near >= 2 && roll < 0.1) c.ability = true;
    else if (near === 1 && alongside && roll < 0.05 * b.aggression) c.ability = true;
  } else if (kind === 'nova') {
    if (straight && car.charge >= 80 && roll < 0.1) c.ability = true;
  } else if (kind === 'aegis') {
    if ((car.shield < car.spec.shield * 0.5 && near >= 1 && roll < 0.5) || (near >= 3 && roll < 0.08)) c.ability = true;
  }
}
