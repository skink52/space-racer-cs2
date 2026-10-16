// ===================================================================================
// Part 4: the driving AI (CS2 bots race with it, and it drives finished cars off the line).
// ===================================================================================

function makeBot(skill) {
  return {
    skill: clamp(skill + (rnd() - 0.5) * 0.3, 0.05, 1),
    lane: (rnd() - 0.5) * 1.2,        // preferred lateral position, -1 left .. 1 right
    laneTimer: 0, avoidTimer: 0, avoid: 0, think: 0,
    aggression: rnd(), noise: 0, boostHold: 0, brakeHold: 0,
  };
}

function botThink(arena, car) {
  const b = car.bot, T = arena.track, c = car.cmd;
  if (!b || car.state !== 'racing') { c.throttle = 0; c.steer = 0; c.boost = false; c.drift = false; return; }
  b.think--;
  if (b.think > 0) return;             // decisions a few times a second; the previous command keeps running
  b.think = 2 + Math.round((1 - b.skill) * 4);
  const dt = b.think * DT;
  const seg = car.seg;
  const hw = T.hw[seg];
  // lane: wander a little; head for a charge platform when low; take boost pads that are near the lane
  b.laneTimer -= dt;
  if (b.laneTimer <= 0) { b.laneTimer = 2 + rnd() * 4; b.lane = clamp(b.lane + (rnd() - 0.5) * 0.6, -0.8, 0.8); }
  let lane = b.lane;
  const ahead = 24;
  if (car.charge < car.spec.charge * 0.35) {
    const nf = T.nextFeature(seg, 'charge', ahead);
    if (nf) lane = (nf.f.l0 + nf.f.l1) / 2;
  }
  const bp = T.nextFeature(seg, 'boost', 10);
  if (bp) { const mid = (bp.f.l0 + bp.f.l1) / 2; if (Math.abs(mid - lane) < 0.7) lane = lane * 0.3 + mid * 0.7; }
  // keep off the edges over a gap
  if (!T.rail[seg] || !T.rail[(seg + 6) % T.n]) lane *= 0.5;
  // avoid the car right in front
  b.avoidTimer -= dt;
  if (b.avoidTimer <= 0) {
    b.avoid = 0;
    const fx = Math.cos(car.yaw), fy = Math.sin(car.yaw);
    for (const o of arena.order) {
      if (o === car || !o.solid) continue;
      const rx = o.x - car.x, ry = o.y - car.y;
      const along = rx * fx + ry * fy, side = -rx * fy + ry * fx;
      if (along > 30 && along < 170 && Math.abs(side) < 60 && o.speed < car.speed + 60) {
        b.avoid = side > 0 ? 0.45 : -0.45; b.avoidTimer = 0.8; break;
      }
    }
  }
  lane = clamp(lane + b.avoid, -0.85, 0.85);
  // steer towards a point ahead on the chosen lane
  const look = clamp(140 + car.speed * 0.32, 200, 520);
  const p = T.point(car.s + look);
  const tx = p.x - p.nx * lane * p.hw * 0.75, ty = p.y - p.ny * lane * p.hw * 0.75;
  const want = Math.atan2(ty - car.y, tx - car.x);
  let diff = normRad(want - car.yaw);
  b.noise = b.noise * 0.7 + (rnd() - 0.5) * (1 - b.skill) * 0.25;
  c.steer = clamp(diff * 2.4 + b.noise, -1, 1);
  // speed control from the bend ahead
  const bend = T.curve[(seg + Math.round(look / T.step)) % T.n];        // radians of heading change over the next 10 samples
  const tight = bend > 0.55 + b.skill * 0.25;
  c.drift = tight && car.speed > 600 && Math.abs(diff) > 0.25;
  b.brakeHold -= dt;
  if (bend > 0.9 && car.speed > 700 - b.skill * 150) b.brakeHold = 0.25;
  c.throttle = b.brakeHold > 0 ? -0.5 : 1;
  // boost on the straights when there is charge to spare (and always when nearly full)
  b.boostHold -= dt;
  const straight = bend < 0.25;
  if ((straight && car.charge > 45 + (1 - b.aggression) * 30) || car.charge > car.spec.charge * 0.9) b.boostHold = 0.6;
  c.boost = b.boostHold > 0 && !tight;
  // spin attack when someone is right beside us
  if (car.charge > 60 && car.spinCd <= 0 && b.aggression > 0.3) {
    const fx = Math.cos(car.yaw), fy = Math.sin(car.yaw);
    for (const o of arena.order) {
      if (o === car || !o.solid || (o.team >= 0 && o.team === car.team)) continue;
      const rx = o.x - car.x, ry = o.y - car.y;
      const along = rx * fx + ry * fy, side = Math.abs(-rx * fy + ry * fx);
      if (Math.abs(along) < 70 && side < 70 && rnd() < b.aggression * 0.12) { c.spin = true; break; }
    }
  }
}
