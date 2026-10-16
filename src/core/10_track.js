// ===================================================================================
// Part 1: track geometry. A track is a closed centreline of n uniformly spaced samples (step units apart) with
// a half width, height, banking, rails flag and features (boost pads, charge platforms, slick zones) by sample range.
// ===================================================================================

class Track {
  constructor(data) {
    this.id = data.id; this.title = data.title; this.laps = data.laps; this.index = data.index;
    this.n = data.n; this.len = data.length; this.step = data.step;
    this.x = data.x; this.y = data.y; this.z = data.z; this.tx = data.tx; this.ty = data.ty; this.hw = data.hw;
    this.rail = data.rail; this.cp = data.cp; this.feats = data.feats; this.crossing = !!data.crossing;
    this.mm = data.mm; this.ext = data.ext; this.off = data.off;
    this.road = data.road || new Array(this.n).fill(1);
    this.bk = data.bk || new Array(this.n).fill(0);       // banking: tan of the lean (positive = left side low)
    this.tube = data.tube || new Array(this.n).fill(0);   // 1 inside a tube
    this.zmin = data.zmin || 0; this.zmax = data.zmax || 0;
    this.ramps = this.feats.filter((f) => f.kind === 'ramp');
    this.rampOf = new Array(this.n).fill(null);
    for (const f of this.ramps) for (let i = f.a, g = 0; g < this.n; g++, i++) { this.rampOf[i % this.n] = f; if (i % this.n === f.b % this.n) break; }
    // left normal
    this.nx = new Array(this.n); this.ny = new Array(this.n);
    for (let i = 0; i < this.n; i++) { this.nx[i] = -this.ty[i]; this.ny[i] = this.tx[i]; }
    // checkpoint progress values
    this.cpS = this.cp.map((i) => i * this.step);
    // features per sample for a quick lookup: featAt[i] = list of feature indices
    this.featAt = new Array(this.n);
    for (let i = 0; i < this.n; i++) this.featAt[i] = null;
    this.feats.forEach((f, k) => {
      let i = f.a;
      for (let guard = 0; guard < this.n; guard++) {
        const j = i % this.n;
        (this.featAt[j] || (this.featAt[j] = [])).push(k);
        if (j === f.b % this.n) break;
        i++;
      }
    });
    // upcoming curvature per sample (sum of heading change over the next 10 samples), for bots
    this.curve = new Array(this.n);
    for (let i = 0; i < this.n; i++) {
      let s = 0;
      for (let k = 0; k < 10; k++) {
        const a = (i + k) % this.n, b = (i + k + 1) % this.n;
        s += Math.abs(normRad(Math.atan2(this.ty[b], this.tx[b]) - Math.atan2(this.ty[a], this.tx[a])));
      }
      this.curve[i] = s;
    }
  }

  // project a point onto segment i (from sample i to i+1); returns null when the point is not beside it
  project(i, x, y) {
    i = ((i % this.n) + this.n) % this.n;
    const dx = x - this.x[i], dy = y - this.y[i];
    const t = (dx * this.tx[i] + dy * this.ty[i]) / this.step;
    const d = dx * this.nx[i] + dy * this.ny[i];
    return { i, t, d };
  }

  // closest point on segment i to (x, y, z): t clamped to the segment, distance includes height (weighted)
  closest(i, x, y, z) {
    const p = this.project(i, x, y);
    const tc = clamp(p.t, 0, 1);
    const px = this.x[p.i] + this.tx[p.i] * tc * this.step, py = this.y[p.i] + this.ty[p.i] * tc * this.step;
    const dz = (z - this.zAt(p.i, tc) + p.d * this.bankAt(p.i, tc)) * 2;
    p.t = tc; p.score = Math.sqrt((x - px) * (x - px) + (y - py) * (y - py) + dz * dz);
    return p;
  }

  // locate a point with a hint segment: checks a window around it; falls back to a full scan when nothing fits
  locate(x, y, z, hint) {
    let best = null;
    if (hint !== undefined && hint !== null) {
      for (let k = -4; k <= 8; k++) {
        const p = this.closest(hint + k, x, y, z);
        if (!best || p.score < best.score) best = p;
      }
      if (best && best.score < this.hw[best.i] + 160) return this.finish(best);
    }
    return this.locateAll(x, y, z);
  }

  locateAll(x, y, z) {
    let best = null;
    for (let i = 0; i < this.n; i++) {
      const p = this.closest(i, x, y, z);
      if (!best || p.score < best.score) best = p;
    }
    return this.finish(best);
  }

  finish(p) {
    p.t = clamp(p.t, 0, 0.999999);
    p.s = (p.i + p.t) * this.step;
    p.hw = this.hw[p.i] + (this.hw[(p.i + 1) % this.n] - this.hw[p.i]) * p.t;
    p.bank = this.bankAt(p.i, p.t);
    p.z = this.zAt(p.i, p.t) - p.d * p.bank;      // the banked road surface under the point
    p.rail = this.rail[p.i];
    return p;
  }

  // ramp height at segment i, fraction t (0 off ramps)
  rampLift(i, t) {
    const f = this.rampOf[((i % this.n) + this.n) % this.n];
    if (!f) return 0;
    const k = ((((i - f.a) % this.n) + this.n) % this.n + t) / (((f.b - f.a + this.n) % this.n) + 1);
    return f.h * clamp(k, 0, 1);
  }
  rampAt(i) { return this.rampOf[((i % this.n) + this.n) % this.n]; }

  zAt(i, t) { const j = (i + 1) % this.n; return this.z[i] + (this.z[j] - this.z[i]) * t; }
  bankAt(i, t) { const j = (i + 1) % this.n; return this.bk[i] + (this.bk[j] - this.bk[i]) * t; }

  // a point on the centreline at progress s (any real; wraps)
  point(s) {
    s = ((s % this.len) + this.len) % this.len;
    const f = s / this.step;
    const i = Math.floor(f) % this.n, j = (i + 1) % this.n, t = f - Math.floor(f);
    return {
      x: this.x[i] + (this.x[j] - this.x[i]) * t, y: this.y[i] + (this.y[j] - this.y[i]) * t, z: this.z[i] + (this.z[j] - this.z[i]) * t,
      tx: this.tx[i], ty: this.ty[i], nx: this.nx[i], ny: this.ny[i], hw: this.hw[i] + (this.hw[j] - this.hw[i]) * t, i,
    };
  }

  // features under a point: segment i, lateral fraction (-1 left edge .. 1 right edge)
  featuresAt(i, latFrac) {
    const list = this.featAt[((i % this.n) + this.n) % this.n];
    if (!list) return null;
    let out = null;
    for (const k of list) {
      const f = this.feats[k];
      if (latFrac >= f.l0 && latFrac <= f.l1) (out || (out = [])).push(f);
    }
    return out;
  }

  // the next feature of a kind ahead of segment i within `within` samples; returns { f, dist } or null
  nextFeature(i, kind, within) {
    for (let k = 1; k <= within; k++) {
      const j = (i + k) % this.n;
      const list = this.featAt[j];
      if (!list) continue;
      for (const fi of list) if (this.feats[fi].kind === kind) return { f: this.feats[fi], dist: k * this.step };
    }
    return null;
  }

  // the bend ahead of progress s: heading change over the stretch from `from` to `to` units ahead (radians, + = left)
  turnAhead(s, from, to) {
    const a = this.point(s + from), b = this.point(s + to);
    return normRad(Math.atan2(b.ty, b.tx) - Math.atan2(a.ty, a.tx));
  }

  // grid slot k (0 = pole): 4 abreast, rows 110 units apart behind the start line, odd rows staggered
  gridSlot(k) {
    const row = Math.floor(k / 4), col = k % 4;
    const s = -(190 + row * 160 + (row % 2 ? 60 : 0));
    const p = this.point(s);
    const lat = (col - 1.5) * p.hw * 0.46;
    return { x: p.x - p.nx * lat, y: p.y - p.ny * lat, z: p.z + lat * this.bk[p.i], yaw: Math.atan2(p.ty, p.tx), s: ((s % this.len) + this.len) % this.len };
  }
}
