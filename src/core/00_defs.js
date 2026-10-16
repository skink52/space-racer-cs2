// ===================================================================================
// Space Racer - the game itself. Plain JavaScript, no engine calls, so it runs in CS2 and in Node.
// Part 0: constants, the four cars, helpers.
// ===================================================================================

const TICRATE = 64;                 // sim steps per second (one per CS2 server tick)
const DT = 1 / TICRATE;
const CAR_R = 36;                   // car collision radius (units)
const CAR_LEN = 100;                 // for drawing / grid spacing
const TEAM_NAMES = ['T', 'CT'];

// The four cars. Speeds in units/s, accel in units/s^2, turn in radians/s at mid speed, grip = how fast sideways
// speed is bled off (per second); mass only matters when cars bump.
const CARS = {
  hornet:  { key: 'hornet',  name: 'HORNET',  maxSpeed: 950,  accel: 570, brake: 1000, turn: 2.7,  grip: 12, driftGrip: 3.2, mass: 1.0, shield: 90,  charge: 100, boost: 1.30, padMult: 1.0, driftCharge: 2.0, spinCost: 18, ram: 1.0, chargeMult: 1.0, draftMult: 1.0, draftRegen: 0,
             perk: 'DRIFT CHARGE', desc: 'LIGHT AND SHARP. DRIFTING FILLS CHARGE FAST. CHEAP SPIN ATTACK.' },
  meteor:  { key: 'meteor',  name: 'METEOR',  maxSpeed: 1005, accel: 440, brake: 900,  turn: 2.35, grip: 10, driftGrip: 3.0, mass: 1.6, shield: 110, charge: 100, boost: 1.28, padMult: 1.0, driftCharge: 1.0, spinCost: 30, ram: 2.0, chargeMult: 1.0, draftMult: 1.0, draftRegen: 0,
             perk: 'RAM', desc: 'HEAVY AND FAST IN A STRAIGHT LINE. BUMPS HURT THEM, NOT YOU.' },
  comet:   { key: 'comet',   name: 'COMET',   maxSpeed: 935,  accel: 470, brake: 950,  turn: 2.4,  grip: 11, driftGrip: 3.0, mass: 1.0, shield: 100, charge: 130, boost: 1.40, padMult: 1.4, driftCharge: 1.0, spinCost: 30, ram: 1.0, chargeMult: 1.3, draftMult: 1.0, draftRegen: 0,
             perk: 'AFTERBURN', desc: 'BIGGEST CHARGE TANK, STRONGEST BOOST, PADS LAST LONGER.' },
  bastion: { key: 'bastion', name: 'BASTION', maxSpeed: 955,  accel: 490, brake: 950,  turn: 2.3,  grip: 11, driftGrip: 3.0, mass: 1.3, shield: 130, charge: 100, boost: 1.33, padMult: 1.0, driftCharge: 1.0, spinCost: 30, ram: 1.0, chargeMult: 1.0, draftMult: 2.0, draftRegen: 3,
             perk: 'SLIPSTREAM', desc: 'TOUGHEST SHIELD. DRAFTING FILLS CHARGE AND REPAIRS. TEAMMATES BEHIND YOU GAIN TOO.' },
};
const CAR_KEYS = ['hornet', 'meteor', 'comet', 'bastion'];

// rules that are not per car
const RULES = {
  boostDrain: 33,           // charge per second while boosting (100 lasts 3 s)
  padTime: 1.2,             // seconds of free boost from a boost pad
  padKick: 140,             // instant speed from a boost pad
  padSpeed: 1.42,           // top speed multiplier while a pad boost lasts
  chargeRate: 55,           // charge per second on a charge platform
  chargeShield: 8,          // shield per second on a charge platform
  draftCharge: 8,           // charge per second in a slipstream
  draftSpeed: 1.06,         // top speed multiplier in a slipstream
  driftChargeRate: 10,      // charge per second while sliding in a drift
  spinTime: 0.5, spinCooldown: 3.0, spinDamage: 20, spinKnock: 420,
  contactMax: 20,           // most shield one bump or rail hit can take
  contactSoft: 250,         // closing speed below which a bump is free
  regenDelay: 4, regenRate: 1.5,   // shield repairs slowly once nothing has hit you for this long
  startProtect: 3.0,        // seconds after the lights with no damage (the first corner is crowded)
  railRestitution: 0.3,     // bounce off the rails
  contactRestitution: 0.45,
  wreckShow: 1.5,           // seconds a wreck stays visible
  fallTime: 1.2,            // seconds falling before the reset
  fallPenalty: 15,          // shield lost for falling off
  pulseSpeed: 1500, pulseCharge: 40, pulseEnabled: true,
  startCharge: 40,
  coastDrag: 0.35,          // per second when not accelerating
  reverseMax: 220,
  wrongWayTime: 1.0,        // seconds driving backwards before the warning
  koCreditWindow: 2.0,      // seconds: the last car to hit a wreck within this gets the kill
  slickGrip: 0.3,
  gravity: 1150,            // units/s^2 in the air (jumps)
  rampKick: 60,             // extra upward speed off a ramp lip
  airControl: 0.35,         // steering left in the air
};

function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
function lerp(a, b, t) { return a + (b - a) * t; }
function normRad(a) { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; }
function deg(r) { return r * 180 / Math.PI; }
function rad(d) { return d * Math.PI / 180; }
function fmtTime(sec) {
  const m = Math.floor(sec / 60), s = sec - m * 60;
  return m + ':' + (s < 10 ? '0' : '') + s.toFixed(2);
}
function ordinal(n) {
  const s = ['TH', 'ST', 'ND', 'RD'], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

// deterministic random for tests (replaced by Math.random in CS2 if wanted)
let _seed = 12345;
function rnd() { _seed = (_seed * 1103515245 + 12345) & 0x7fffffff; return _seed / 0x7fffffff; }
function seedRandom(s) { _seed = s | 0; }
function pick(arr) { return arr[Math.floor(rnd() * arr.length)]; }
function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
