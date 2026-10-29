"""Neon Racer music: four original electro / synthwave pieces made with synth.py (saw stacks, side-chained bass,
arpeggios, pads, an electronic kit). Same names and use as Space Racer's chiptune pieces: mus_lobby, mus_race,
mus_race2 (they take turns) and mus_results. Loops are seamless: the reverb / delay tail is wrapped onto the start."""
import numpy as np
import synth as S

NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
def m(name):
    """'A2' -> MIDI"""
    return 12 * (int(name[-1]) + 1) + NOTE[name[:-1]]
def chord(root, kind='min', octave=4):
    r = m(root + str(octave))
    return [r, r + (3 if kind == 'min' else 4), r + 7]

def loop(parts_fn, bars, bpm, tail=2.5):
    beat = 60.0 / bpm
    sec = bars * 4 * beat
    n = S.sec(sec); nt = n + S.sec(tail)
    out = parts_fn(beat, bars, nt)
    out[:S.sec(tail)] += out[n:]
    out = out[:n]
    rms = np.sqrt(np.mean(out ** 2)) + 1e-9                    # loud and dense: bring the body up, round off the peaks
    out = S.softclip(out * (S.db(-12.0) / rms), 0.65)
    out = out / (np.max(np.abs(out)) + 1e-9) * S.db(-1.5)
    f = S.sec(0.004)
    out[:f] *= np.linspace(0, 1, f)[:, None]; out[-f:] *= np.linspace(1, 0, f)[:, None]
    return out, sec

def punch_kick(times, n):
    """an extra kick layer for weight: a long sub thump (60 -> 42 Hz) and a short click, on every kick"""
    k = S.sec(0.42); t = np.arange(k) / S.SR
    f = 42 + 70 * np.exp(-t / 0.035)
    sub = S.sine(f, k) * np.exp(-t / 0.22) * np.minimum(t / 0.002, 1)
    click = S.hp(S.noise(k, np.random.default_rng(3)), 2500) * np.exp(-t / 0.004) * 0.5
    one = np.tanh(2.2 * (sub + click)) * 0.9
    buf = np.zeros(n)
    for t0 in times: S.add(buf, one, S.sec(t0))
    return buf

def four_floor(beat, bars, clap=True, ohat=True, fill_every=8, hats16=False):
    ev, kicks = [], []
    for b in range(bars):
        for q in range(4):
            t = (b * 4 + q) * beat
            ev.append((t, 'kick', 1.0)); kicks.append(t)
            if clap and q in (1, 3): ev.append((t, 'clap', 0.9)); ev.append((t, 'snare', 0.85))
            if ohat: ev.append((t + beat / 2, 'ohat', 0.5))
            if hats16:
                for s_ in (1, 3): ev.append((t + s_ * beat / 4, 'hat', 0.3))
        if fill_every and b % fill_every == fill_every - 1:
            ev.append(((b * 4 + 2) * beat, 'riser', 0.6))
        if b % 8 == 0: ev.append((b * 4 * beat, 'crash', 0.6))
    return ev, kicks

PUNCH = ((70, 1.0, 0.9), (300, -3.0, 1.0), (2500, 3.0, 0.9), (7000, 2.0, 0.8))     # master tone: weight in the lows, less box, some bite

def mix_drums(mx, kit, kicks, n, hat_db=-9):
    mx.add(punch_kick(kicks, n), -8, 0.0)
    for g, x in kit.items(): mx.add(x, {'kick': -4, 'snare': -2, 'hat': hat_db + 2, 'cym': -9}.get(g, -8), 0.0, -20 if g not in ('kick',) else -100)

def race1(beat, bars, n):
    """'Grid Runner' - 124 bpm, A minor: a driven rolling 16th saw bass pumping under a four-on-the-floor kick,
    a filtered saw arpeggio, a wide supersaw lead in the second half"""
    prog = [('A', 'min'), ('F', 'maj'), ('C', 'maj'), ('G', 'maj')]
    bass, arp, pad, lead = [], [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        pad.append((b * 4 * beat, 4 * beat, [c - 12 for c in ch], 0.7, {}))
        r1 = m(root + '1') if root in ('A', 'G') else m(root + '2') - 12
        for s_ in range(16):
            t = (b * 4 + s_ / 4) * beat
            if s_ % 4 != 0: bass.append((t, beat / 4 * 0.85, r1 + (12 if s_ % 4 == 2 else 0), 1.0 if s_ % 4 == 2 else 0.8, {}))
            arp.append((t, beat / 4 * 0.6, ch[s_ % 3] + 12 * (s_ // 8), 0.55, {}))
    mel = [('E5', 2), ('A5', 1), ('C6', 1), ('B5', 2), ('G5', 2), ('A5', 3), ('E5', 1), ('C5', 2), ('D5', 2),
           ('E5', 2), ('G5', 1), ('A5', 1), ('B5', 2), ('D6', 2), ('C6', 3), ('B5', 1), ('A5', 4)]
    t = (bars // 2) * 4 * beat
    for k in range(2):
        tt = t + k * 16 * beat
        for note, d in mel:
            if tt >= bars * 4 * beat: break
            lead.append((tt, d * beat * 0.95, m(note), 0.9, {'slide': d >= 3}))
            tt += d * beat
    drums, kicks = four_floor(beat, bars, hats16=True)
    kit = S.Drums(seed=11, style='electronic').render(drums, n)
    mx = S.Mixer(n); mx.pump = S.pump_curve(kicks, n, 0.7, 0.14)
    mx.add(S.Bass(seed=3, electronic=False, drive=4.0, sub=0.6, fc=1400).render(bass, n), -8, 0.0, -100, 0.9)
    mx.add(S.lp(S.Lead(seed=4, voices=3, detune=8, drive=1.6, delay=beat * 0.75, dmix=0.2, square=0.0, vib_depth=0.0).render(arp, n)[:, 0], 4000, 2), -9, -0.25, -18, 0.7)
    mx.add(S.Pad(seed=5, mode='strings', voices=6, detune=16).render(pad, n), -13, 0.0, -10, 0.8)
    if lead: mx.add(S.Lead(seed=6, voices=7, detune=18, drive=2.4, vib_depth=0.12, delay=beat * 0.75, dmix=0.25).render(lead, n), -3, 0.1, -12, 0.35)
    mix_drums(mx, kit, kicks, n)
    return mx.master(comp_thr=-18, ratio=4.0, drive_db=8.0, eq=PUNCH)

def race2(beat, bars, n):
    """'Neon Highway' - 128 bpm, F# minor: an octave-bouncing driven bass, stabbed saw chords, a call-and-answer lead"""
    prog = [('F#', 'min'), ('D', 'maj'), ('A', 'maj'), ('E', 'maj')]
    bass, gate, lead = [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        r1 = m(root + '1') if root in ('F#', 'E') else m(root + '2') - 12
        for e in range(8):
            t = (b * 4 + e / 2) * beat
            bass.append((t, beat / 2 * 0.75, r1 + (12 if e % 2 else 0), 1.0 if e % 2 else 0.85, {}))
            if e in (1, 3, 6): gate.append((t, beat / 2 * 0.35, ch, 0.9, {}))
    call = [('C#5', 1), ('E5', 1), ('F#5', 2), ('-', 4)]
    answer = [('A5', 1), ('G#5', 1), ('E5', 1), ('C#5', 1), ('E5', 4)]
    for b in range(4, bars, 2):
        tt = b * 4 * beat
        for note, d in (call if (b // 2) % 2 == 0 else answer):
            if note != '-': lead.append((tt, d * beat * 0.9, m(note), 0.9, {}))
            tt += d * beat
    drums, kicks = four_floor(beat, bars, ohat=True)
    kit = S.Drums(seed=12, style='electronic').render(drums, n)
    mx = S.Mixer(n); mx.pump = S.pump_curve(kicks, n, 0.7, 0.13)
    mx.add(S.Bass(seed=7, electronic=False, drive=4.5, sub=0.6, fc=1300).render(bass, n), -8, 0.0, -100, 0.9)
    mx.add(S.Lead(seed=8, voices=5, detune=14, drive=2.0, delay=beat * 0.5, dmix=0.2, vib_depth=0.0).render(gate, n), -6, 0.0, -14, 0.8)
    mx.add(S.Lead(seed=9, voices=7, detune=16, drive=2.4, vib_depth=0.1, delay=beat * 0.75, dmix=0.3).render(lead, n), -3, 0.15, -12, 0.35)
    mix_drums(mx, kit, kicks, n, -10)
    return mx.master(comp_thr=-18, ratio=4.0, drive_db=8.0, eq=PUNCH)

def lobby(beat, bars, n):
    """'After Hours' - 100 bpm, D minor: a heavy half-time groove, a dark pad and a slow saw arpeggio"""
    prog = [('D', 'min'), ('A#', 'maj'), ('F', 'maj'), ('C', 'maj')]
    bass, arp, pad = [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        pad.append((b * 4 * beat, 4 * beat, [c - 12 for c in ch], 0.8, {}))
        r1 = m(root + '2') - 12
        for e in range(8):
            bass.append(((b * 4 + e / 2) * beat, beat / 2 * 0.8, r1 + (12 if e in (3, 7) else 0), 0.95 if e % 2 == 0 else 0.7, {}))
        for s_ in range(8):
            arp.append(((b * 4 + s_ / 2) * beat, beat / 2 * 0.5, ch[(0, 1, 2, 1)[s_ % 4]] + 12, 0.5, {}))
    ev, kicks = [], []
    for b in range(bars):
        for q in range(4):
            t = (b * 4 + q) * beat
            if q == 0 or (q == 2 and b % 2): ev.append((t, 'kick', 1.0)); kicks.append(t)
            if q == 2: ev.append((t, 'snare', 0.9)); ev.append((t, 'clap', 0.7))
            ev.append((t + beat / 2, 'hat', 0.35))
    kit = S.Drums(seed=13, style='electronic').render(ev, n)
    mx = S.Mixer(n); mx.pump = S.pump_curve(kicks, n, 0.5, 0.25)
    mx.add(S.Bass(seed=14, electronic=False, drive=3.0, sub=0.6, fc=1000).render(bass, n), -8, 0.0, -100, 0.7)
    mx.add(S.Pad(seed=15, mode='strings', voices=7, detune=20).render(pad, n), -8, 0.0, -6, 0.5)
    mx.add(S.lp(S.Lead(seed=16, voices=3, detune=7, drive=1.3, delay=beat * 0.75, dmix=0.4, fb=0.5, square=0.0, vib_depth=0.0).render(arp, n)[:, 0], 3500, 2), -8, -0.2, -10, 0.4)
    mix_drums(mx, kit, kicks, n, -12)
    return mx.master(comp_thr=-18, ratio=3.5, drive_db=7.0, eq=PUNCH)

def results(beat, bars, n):
    """a short electro sting: a rising saw arpeggio into a held supersaw chord over a sub hit"""
    notes = [m(x) for x in ('A4', 'C5', 'E5', 'A5', 'C6', 'E6')]
    arp = [(k * beat / 4, beat / 4 * 0.9, p, 0.8, {}) for k, p in enumerate(notes * 2)]
    hold = [(3 * beat, 4 * beat, [m('A4'), m('C#5'), m('E5'), m('A5')], 0.9, {})]
    bass = [(3 * beat, 4 * beat, m('A1'), 1.0, {})]
    drums = [(0, 'riser', 0.7), (3 * beat, 'kick', 1.0), (3 * beat, 'crash', 0.9), (3 * beat, 'clap', 0.9)]
    kit = S.Drums(seed=17, style='electronic').render(drums, n)
    mx = S.Mixer(n)
    mx.add(S.Lead(seed=18, voices=5, detune=12, delay=beat * 0.5, dmix=0.3).render(arp, n), -6, 0.0, -10)
    mx.add(S.Lead(seed=19, voices=7, detune=18, drive=2.0, delay=beat * 0.75, dmix=0.3).render([(3 * beat, 4 * beat, p, 0.8, {}) for p in hold[0][2]], n), -6, 0.0, -8)
    mx.add(S.Bass(seed=20, drive=3.0, sub=1.0).render(bass, n), -3)
    mx.add(punch_kick([3 * beat], n), -1)
    for g, x in kit.items(): mx.add(x, -4, 0.0, -12)
    return mx.master(drive_db=4.0, eq=PUNCH)

def neon_music():
    out = {}
    for name, fn, bars, bpm in (('mus_race', race1, 16, 124), ('mus_race2', race2, 16, 128), ('mus_lobby', lobby, 8, 100)):
        out[name] = loop(fn, bars, bpm)
    x, _ = loop(results, 2, 120, tail=0.01)
    out['mus_results'] = (x, 4 * 60 / 120 * 2)
    return out

# ---------------------------------------------------------------- Depth Racer: deep, dubby, heavy
def sonar(times, n, note=m('E6')):
    """a sonar ping: a pure tone with a long watery echo"""
    k = S.sec(1.4); t = np.arange(k) / S.SR
    one = S.sine(S.midi_hz(note) * (1 - 0.02 * t), k) * np.exp(-t / 0.35) * np.minimum(t / 0.003, 1)
    buf = np.zeros(n)
    for t0 in times:
        S.add(buf, one, S.sec(t0))
        S.add(buf, one * 0.35, S.sec(t0 + 0.37)); S.add(buf, one * 0.15, S.sec(t0 + 0.74))
    return buf

def depth1(beat, bars, n):
    """'Pressure' - 112 bpm, D minor: a pounding kick, a deep rolling saw bass, dub chord stabs echoing away, sonar
    pings and a dark supersaw lead in the second half"""
    prog = [('D', 'min'), ('A#', 'maj'), ('G', 'min'), ('A', 'min')]
    bass, stab, pad, lead, pings = [], [], [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 3)
        pad.append((b * 4 * beat, 4 * beat, ch, 0.7, {}))
        r1 = m(root + '1')
        for e in range(8):
            t = (b * 4 + e / 2) * beat
            bass.append((t, beat / 2 * 0.8, r1 + (12 if e in (3, 6) else 0), 1.0 if e % 2 else 0.8, {}))
        for q in (1.5, 3.5): stab.append(((b * 4 + q) * beat, beat * 0.3, [c + 12 for c in ch], 0.8, {}))
        if b % 2 == 0: pings.append((b * 4 + 0.5) * beat)
    mel = [('D5', 3), ('F5', 1), ('E5', 2), ('C5', 2), ('D5', 3), ('A4', 1), ('C5', 4), ('D5', 3), ('F5', 1), ('G5', 2),
           ('A5', 2), ('F5', 4), ('E5', 4)]
    tt = (bars // 2) * 4 * beat
    for note, d in mel:
        if tt >= bars * 4 * beat: break
        lead.append((tt, d * beat * 0.95, m(note), 0.85, {'slide': d >= 3})); tt += d * beat
    drums, kicks = four_floor(beat, bars, hats16=False)
    kit = S.Drums(seed=21, style='electronic').render(drums, n)
    mx = S.Mixer(n, S.reverb_ir(seed=9, length=2.6)); mx.pump = S.pump_curve(kicks, n, 0.75, 0.16)
    mx.add(S.Bass(seed=22, drive=4.5, sub=0.8, fc=700).render(bass, n), -6, 0.0, -100, 0.9)
    mx.add(S.Lead(seed=23, voices=5, detune=12, drive=1.6, delay=beat * 0.75, fb=0.6, dmix=0.5, vib_depth=0.0).render(stab, n), -10, 0.0, -6, 0.6)
    mx.add(S.Pad(seed=24, mode='strings', voices=6, detune=18).render(pad, n), -12, 0.0, -4, 0.7)
    mx.add(sonar(pings, n), -10, 0.3, -4)
    if lead: mx.add(S.Lead(seed=25, voices=7, detune=16, drive=2.2, vib_depth=0.15, delay=beat * 0.75, dmix=0.3).render(lead, n), -5, -0.1, -10, 0.35)
    mix_drums(mx, kit, kicks, n, -11)
    return mx.master(comp_thr=-18, ratio=4.0, drive_db=8.0, eq=PUNCH)

def depth2(beat, bars, n):
    """'Leviathan' - 118 bpm, A minor: a huge distorted bass riff, a pulsing arpeggio deep in the water, a horn-like
    lead calling over it"""
    prog = [('A', 'min'), ('F', 'maj'), ('D', 'min'), ('E', 'min')]
    bass, arp, lead = [], [], []
    riff = [0, 0, 12, 0, 10, 0, 7, 0]
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        r1 = m(root + '1') if root in ('A', 'F', 'E') else m(root + '2') - 12
        for e in range(8):
            bass.append(((b * 4 + e / 2) * beat, beat / 2 * 0.85, r1 + riff[e], 1.0 if e % 2 == 0 else 0.85, {}))
        for s_ in range(16):
            arp.append(((b * 4 + s_ / 4) * beat, beat / 4 * 0.5, ch[(0, 2, 1, 2)[s_ % 4]] + (12 if s_ % 8 > 5 else 0), 0.5, {}))
    calls = [('E5', 2), ('A5', 2), ('G5', 1), ('E5', 3), ('-', 8), ('C6', 2), ('B5', 2), ('A5', 4), ('-', 8)]
    tt = 4 * 4 * beat
    while tt < bars * 4 * beat:
        for note, d in calls:
            if tt >= bars * 4 * beat: break
            if note != '-': lead.append((tt, d * beat * 0.95, m(note), 0.85, {'slide': True}))
            tt += d * beat
    drums, kicks = four_floor(beat, bars, ohat=True)
    kit = S.Drums(seed=26, style='electronic').render(drums, n)
    mx = S.Mixer(n, S.reverb_ir(seed=11, length=2.4)); mx.pump = S.pump_curve(kicks, n, 0.7, 0.14)
    mx.add(S.Bass(seed=27, drive=5.0, sub=0.7, fc=1100).render(bass, n), -6, 0.0, -100, 0.85)
    mx.add(S.lp(S.Lead(seed=28, voices=3, detune=8, drive=1.4, delay=beat * 0.5, dmix=0.3, vib_depth=0.0).render(arp, n)[:, 0], 1800, 2), -10, 0.2, -10, 0.7)
    mx.add(S.Lead(seed=29, voices=6, detune=14, drive=2.6, vib_depth=0.25, delay=beat * 0.75, dmix=0.35).render(lead, n), -5, -0.1, -8, 0.3)
    mix_drums(mx, kit, kicks, n, -10)
    return mx.master(comp_thr=-18, ratio=4.0, drive_db=8.0, eq=PUNCH)

def depth_lobby(beat, bars, n):
    """'Still Water' - 86 bpm, D minor: slow and heavy, a sub bass, a wide dark pad, sonar pings and a lazy kick"""
    prog = [('D', 'min'), ('A#', 'maj'), ('F', 'maj'), ('C', 'maj')]
    bass, pad, pings = [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 3)
        pad.append((b * 4 * beat, 4 * beat, ch + [ch[0] + 12], 0.85, {}))
        bass.append((b * 4 * beat, 3.5 * beat, m(root + '1') if root != 'A#' else m('A#1'), 0.9, {}))
        pings += [(b * 4 + 1) * beat, (b * 4 + 2.75) * beat]
    ev, kicks = [], []
    for b in range(bars):
        for q in range(4):
            t = (b * 4 + q) * beat
            if q in (0, 2): ev.append((t, 'kick', 0.9)); kicks.append(t)
            if q == 2: ev.append((t, 'snare', 0.7))
            ev.append((t + beat / 2, 'hat', 0.3))
    kit = S.Drums(seed=30, style='electronic').render(ev, n)
    mx = S.Mixer(n, S.reverb_ir(seed=12, length=3.2)); mx.pump = S.pump_curve(kicks, n, 0.4, 0.3)
    mx.add(S.Bass(seed=31, drive=2.0, sub=1.0, fc=500).render(bass, n), -7, 0.0, -100, 0.5)
    mx.add(S.Pad(seed=32, mode='strings', voices=7, detune=22).render(pad, n), -7, 0.0, -3, 0.4)
    mx.add(sonar(pings, n, m('A5')), -9, -0.3, -3)
    mix_drums(mx, kit, kicks, n, -13)
    return mx.master(comp_thr=-18, ratio=3.0, drive_db=6.0, eq=PUNCH)

def depth_music():
    out = {}
    for name, fn, bars, bpm in (('mus_race', depth1, 16, 112), ('mus_race2', depth2, 16, 118), ('mus_lobby', depth_lobby, 8, 86)):
        out[name] = loop(fn, bars, bpm, tail=3.0)
    x, _ = loop(results, 2, 120, tail=0.01)
    out['mus_results'] = (x, 4 * 60 / 120 * 2)
    return out
