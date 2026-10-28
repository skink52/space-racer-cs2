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

BRIGHT = ((180, -3.0, 1.0), (3000, 3.0, 0.8), (8000, 3.0, 0.7))   # master tone: less mud, more shine

def loop(parts_fn, bars, bpm, tail=2.5):
    beat = 60.0 / bpm
    sec = bars * 4 * beat
    n = S.sec(sec); nt = n + S.sec(tail)
    out = parts_fn(beat, bars, nt)
    out[:S.sec(tail)] += out[n:]
    out = out[:n]
    out = out / (np.max(np.abs(out)) + 1e-9) * S.db(-1.0)
    f = S.sec(0.004)
    out[:f] *= np.linspace(0, 1, f)[:, None]; out[-f:] *= np.linspace(1, 0, f)[:, None]
    return out, sec

def four_floor(beat, bars, clap=True, ohat=True, fill_every=8, hats16=False, half=False):
    ev, kicks = [], []
    for b in range(bars):
        for q in range(4):
            t = (b * 4 + q) * beat
            if not half or q in (0, 2) or True:
                ev.append((t, 'kick', 1.0)); kicks.append(t)
            if clap and q in ((2,) if half else (1, 3)): ev.append((t, 'clap', 0.85))
            if ohat: ev.append((t + beat / 2, 'ohat', 0.55))
            if hats16:
                for s in (1, 3): ev.append((t + s * beat / 4, 'hat', 0.35))
        if fill_every and b % fill_every == fill_every - 1:
            ev.append(((b * 4 + 2) * beat, 'riser', 0.6))
        if b % 8 == 0: ev.append((b * 4 * beat, 'crash', 0.6))
    return ev, kicks

def race1(beat, bars, n):
    """'Grid Runner' - 124 bpm, A minor: rolling 16th bass, a pulse arpeggio, a soaring detuned lead in the second half"""
    prog = [('A', 'min'), ('F', 'maj'), ('C', 'maj'), ('G', 'maj')]
    bass, arp, pad, lead = [], [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        pad.append((b * 4 * beat, 4 * beat, ch, 0.7, {}))
        r2 = m(root + '2')
        for s in range(16):
            t = (b * 4 + s / 4) * beat
            if s % 4 != 0: bass.append((t, beat / 4 * 0.8, r2 + (12 if s % 4 == 2 else 0), 0.9, {}))
            arp.append((t, beat / 4 * 0.7, ch[s % 3] + 12 * (s // 8), 0.6, {}))
    mel = [('E5', 2), ('A5', 1), ('C6', 1), ('B5', 2), ('G5', 2), ('A5', 3), ('E5', 1), ('C5', 2), ('D5', 2),
           ('E5', 2), ('G5', 1), ('A5', 1), ('B5', 2), ('D6', 2), ('C6', 3), ('B5', 1), ('A5', 4)]
    t = (bars // 2) * 4 * beat
    for k in range(2):
        tt = t + k * 16 * beat
        for note, d in mel:
            if tt >= bars * 4 * beat: break
            lead.append((tt, d * beat * 0.95, m(note), 0.85, {'slide': d >= 3}))
            tt += d * beat
    drums, kicks = four_floor(beat, bars, hats16=True)
    kit = S.Drums(seed=11, style='electronic').render(drums, n)
    mx = S.Mixer(n); mx.pump = S.pump_curve(kicks, n, 0.55, 0.12)
    mx.add(S.Bass(seed=3, electronic=True, drive=2.0).render(bass, n), -7, 0.0, -100, 0.85)
    mx.add(S.Lead(seed=4, voices=2, detune=6, drive=1.4, delay=beat * 0.75, dmix=0.25, square=0.7, vib_depth=0.0).render(arp, n), -6, 0.0, -20, 0.6)
    mx.add(S.Pad(seed=5, mode='strings', voices=6, detune=18).render(pad, n), -9, 0.0, -10, 0.7)
    if lead: mx.add(S.Lead(seed=6, voices=5, detune=14, drive=2.0, delay=beat * 0.75, dmix=0.3).render(lead, n), -3, 0.0, -12, 0.3)
    for g, x in kit.items(): mx.add(x, {'kick': -3, 'snare': -5, 'hat': -7, 'cym': -9}.get(g, -8), 0.0, -18 if g != 'kick' else -100)
    return mx.master(comp_thr=-12, ratio=3.5, eq=BRIGHT)

def race2(beat, bars, n):
    """'Neon Highway' - 128 bpm, F# minor: an octave-bouncing bass, gated chords, a call-and-answer lead"""
    prog = [('F#', 'min'), ('D', 'maj'), ('A', 'maj'), ('E', 'maj')]
    bass, gate, lead = [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        r1 = m(root + '1') if root in ('F#', 'E') else m(root + '2') - 12
        for e in range(8):
            t = (b * 4 + e / 2) * beat
            bass.append((t, beat / 2 * 0.7, r1 + (12 if e % 2 else 0), 0.9, {}))
            if e % 2 == 1 or e == 0: gate.append((t, beat / 2 * 0.5, ch, 0.7 if e else 0.9, {}))
    call = [('C#5', 1), ('E5', 1), ('F#5', 2), ('-', 4)]
    answer = [('A5', 1), ('G#5', 1), ('E5', 1), ('C#5', 1), ('E5', 4)]
    for b in range(4, bars, 2):
        tt = b * 4 * beat
        for note, d in (call if (b // 2) % 2 == 0 else answer):
            if note != '-': lead.append((tt, d * beat * 0.9, m(note), 0.8, {}))
            tt += d * beat
    drums, kicks = four_floor(beat, bars, ohat=True)
    kit = S.Drums(seed=12, style='electronic').render(drums, n)
    mx = S.Mixer(n); mx.pump = S.pump_curve(kicks, n, 0.6, 0.11)
    mx.add(S.Bass(seed=7, electronic=True, drive=2.6, sub=0.8).render(bass, n), -7, 0.0, -100, 0.9)
    mx.add(S.Pad(seed=8, mode='strings', voices=5, detune=12).render(gate, n), -5, 0.0, -14, 0.8)
    mx.add(S.Lead(seed=9, voices=4, detune=10, drive=1.8, delay=beat * 0.75, dmix=0.35, square=0.3).render(lead, n), -3, 0.15, -12, 0.3)
    for g, x in kit.items(): mx.add(x, {'kick': -3, 'snare': -4, 'hat': -7, 'cym': -9}.get(g, -8), 0.0, -18 if g != 'kick' else -100)
    return mx.master(comp_thr=-12, ratio=3.5, eq=BRIGHT)

def lobby(beat, bars, n):
    """'After Hours' - 96 bpm, D minor: a slow synthwave groove, warm pads and a sparkling arpeggio"""
    prog = [('D', 'min'), ('A#', 'maj'), ('F', 'maj'), ('C', 'maj')]
    bass, arp, pad = [], [], []
    for b in range(bars):
        root, kind = prog[b % 4]
        ch = chord(root, kind, 4)
        pad.append((b * 4 * beat, 4 * beat, ch + [ch[0] + 12], 0.8, {}))
        r2 = m(root + '2')
        for e in range(8):
            bass.append(((b * 4 + e / 2) * beat, beat / 2 * 0.9, r2, 0.8 if e % 2 else 0.95, {}))
        for s in range(8):
            arp.append(((b * 4 + s / 2) * beat, beat / 2 * 0.6, ch[(0, 1, 2, 1)[s % 4]] + 12, 0.5, {}))
    ev, kicks = [], []
    for b in range(bars):
        for q in range(4):
            t = (b * 4 + q) * beat
            if q in (0, 2): ev.append((t, 'kick', 0.9)); kicks.append(t)
            if q == 2: ev.append((t, 'snare', 0.7))
            ev.append((t + beat / 2, 'hat', 0.4))
    kit = S.Drums(seed=13, style='electronic').render(ev, n)
    mx = S.Mixer(n); mx.pump = S.pump_curve(kicks, n, 0.3, 0.2)
    mx.add(S.Bass(seed=14, electronic=True, drive=1.5).render(bass, n), -5, 0.0, -100, 0.5)
    mx.add(S.Pad(seed=15, mode='strings', voices=7, detune=20).render(pad, n), -9, 0.0, -6, 0.4)
    mx.add(S.Lead(seed=16, voices=2, detune=5, drive=1.2, delay=beat * 0.75, dmix=0.45, fb=0.5, square=0.8, vib_depth=0.0).render(arp, n), -12, 0.0, -10, 0.3)
    for g, x in kit.items(): mx.add(x, {'kick': -3, 'snare': -7, 'hat': -14, 'cym': -12}.get(g, -8), 0.0, -14 if g != 'kick' else -100)
    return mx.master(comp_thr=-14, ratio=2.5)

def results(beat, bars, n):
    """a short electro fanfare: a rising arpeggio into a held chord"""
    notes = [m(x) for x in ('A4', 'C5', 'E5', 'A5', 'C6', 'E6')]
    arp = [(k * beat / 4, beat / 4 * 0.9, p, 0.8, {}) for k, p in enumerate(notes * 2)]
    hold = [(3 * beat, 4 * beat, [m('A4'), m('C#5'), m('E5'), m('A5')], 0.9, {})]
    bass = [(3 * beat, 4 * beat, m('A1'), 1.0, {})]
    drums = [(0, 'riser', 0.7), (3 * beat, 'kick', 1.0), (3 * beat, 'crash', 0.9)]
    kit = S.Drums(seed=17, style='electronic').render(drums, n)
    mx = S.Mixer(n)
    mx.add(S.Lead(seed=18, voices=3, detune=8, delay=beat * 0.5, dmix=0.3, square=0.5).render(arp, n), -6, 0.0, -10)
    mx.add(S.Pad(seed=19, mode='strings', voices=7, detune=16).render(hold, n), -5, 0.0, -6)
    mx.add(S.Bass(seed=20, electronic=True).render(bass, n), -5)
    for g, x in kit.items(): mx.add(x, -4, 0.0, -12)
    return mx.master()

def neon_music():
    out = {}
    for name, fn, bars, bpm in (('mus_race', race1, 16, 124), ('mus_race2', race2, 16, 128), ('mus_lobby', lobby, 8, 96)):
        out[name] = loop(fn, bars, bpm)
    x, _ = loop(results, 2, 120, tail=0.01)
    out['mus_results'] = (x, 4 * 60 / 120 * 2)
    return out
