"""An original phonk music bed for one episode, synthesized from scratch and seeded by the slug.

  python3 buhexplains/pipeline/phonk.py ep14-biberty        # -> .cache/music/ep14-biberty-phonk.wav

Why (owner note 2026-11-07, PLAYBOOK §6): a commercial song in every Short risks claims and blocks, and one bed on
every video reads as templated. So every episode gets its own bed, 100% synthesized here: no samples, no
recognizable melodies. Same slug -> same file.

What it is: modern drift / Brazilian phonk, built like the real thing.
- Cowbell: the 808 cowbell (two square waves 540 / 800 Hz, band-passed at 2.5-3 kHz, fast attack, 60-120 ms decay),
  played melodically by playback rate so both partials and the filter move together, with glides between notes,
  slight detune, saturation, a light bit-crush, tape wow, a plate send (20 ms pre-delay, 1.5-2.5 s, high-cut 6 kHz)
  and a dotted-1/8 ping-pong delay. The riff is a 2-bar phrygian/minor figure: a short pitch cell cycled over a
  syncopated 16th rhythm, with an octave jump, and a varied answer in bar 2.
- 808: a sine with a pitch-envelope thump, long sustain, 40-80 ms glides, saturated hard (tanh, soft clip, a touch
  of wavefolding) so its harmonics read on phone speakers; mono below 120 Hz.
- Drums: kick (click + body), clap (noise bursts at 0/10/20 ms, band-passed 1-2 kHz, into the plate), bright
  closed hats (noise + ring-modulated metal) with 1/32 and triplet rolls at phrase ends, open hat on the off-beat.
- Glue: everything but the kick ducks 4-8 dB from the kick (120 ms release), bus saturation, compressor, limiter;
  mastered to about -8.5 LUFS with true peak under -1 dBTP (render.py then sets it under the voice).
- Arrangement: 2-bar intro (low-passed riff + riser), drop, a 1-bar break (drums out, riff + 808 slide), drop again
  with a varied riff. Loop points sit on bar lines (info["loop"]: from the first drop to the end).
Per seed: style (drift 130-145 BPM, or Brazilian 115-125 with a halftime clap), key, mode, riff rhythm and cell,
808 line and progression, hat pattern and rolls, every drum and cowbell timbre, delay/reverb and the break position.
Levels and spectrum were calibrated against measurements of real phonk beds (numbers only; nothing copied).
"""
import hashlib, json, os, re, subprocess, sys
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import minimum_filter1d

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
CACHE = os.path.join(REPO, ".cache")
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODES = {"phrygian": [0, 1, 3, 5, 7, 8, 10], "aeolian": [0, 2, 3, 5, 7, 8, 10],
         "harmonic minor": [0, 2, 3, 5, 7, 8, 11], "phrygian dominant": [0, 1, 4, 5, 7, 8, 10]}
PROGS = {"phrygian": [[0, 0, 0, 0], [0, 1, 0, 1], [0, 0, 5, 6], [0, 0, 1, 0]],
         "aeolian": [[0, 0, 0, 0], [0, 0, 5, 6], [0, 5, 0, 4], [0, 0, 5, 4]],
         "harmonic minor": [[0, 0, 0, 0], [0, 0, 5, 4], [0, 5, 0, 4]],
         "phrygian dominant": [[0, 0, 0, 0], [0, 1, 0, 1], [0, 0, 1, 0]]}
# cowbell rhythms: one bar of 16ths, syncopated, 7-9 hits (real beds measure ~1.5 onsets per beat in all)
RIFF_RHYTHMS = ["x..x..x.x.x.x...", "x.x..x.x..x.x.x.", "x..x.x..x.xx.x..", "x.xx..x.x..x.x..", "x..xx.x...x.x.x.",
                "xx..x.x.x..x.x..", "x.x.x..xx.x..x..", "x..x..x.xx..x.x.", "x.xx.x..x.xx.x.."]
# kick + 808 hits (step, length in 16ths): drift = long 808s; funk = tamborzao-like 3-3-4-3-3
BASS_DRIFT = [[(0, 6), (6, 4), (10, 6)], [(0, 7), (7, 3), (10, 6)], [(0, 3), (3, 7), (10, 6)], [(0, 8), (8, 2), (10, 6)],
              [(0, 6), (6, 2), (8, 8)], [(0, 10), (10, 3), (13, 3)]]
BASS_FUNK = [[(0, 3), (3, 3), (6, 4), (10, 3), (13, 3)], [(0, 3), (3, 4), (7, 3), (10, 6)], [(0, 3), (3, 5), (8, 2), (10, 6)]]


def seed_of(slug):
    return int.from_bytes(hashlib.sha256(slug.encode()).digest()[:8], "big")


# ------------------------------------------------------------------ DSP helpers
def _blep(t, dt):
    r = np.zeros_like(t)
    m = t < dt; x = t[m] / dt[m]; r[m] = x + x - x * x - 1
    m = t > 1 - dt; x = (t[m] - 1) / dt[m]; r[m] = x * x + x + x + 1
    return r


def saw(freq, sr, ph0=0.0):
    dt = np.asarray(freq, float) / sr
    t = (ph0 + np.cumsum(dt)) % 1.0
    return 2 * t - 1 - _blep(t, dt)


def square(freq, sr, width=0.5, ph0=0.0):
    """Band-limited (polyBLEP) pulse wave."""
    dt = np.asarray(freq, float) / sr
    t = (ph0 + np.cumsum(dt)) % 1.0; t2 = (t + 1 - width) % 1.0
    return (2 * t - 1 - _blep(t, dt)) - (2 * t2 - 1 - _blep(t2, dt))


def filt(x, kind, f, sr, order=2):
    f = np.clip(np.asarray(f, float), 10, sr / 2 * 0.95)
    return signal.sosfilt(signal.butter(order, f / (sr / 2), kind, output="sos"), x, axis=0)


def peak_eq(x, f0, gain_db, q, sr):
    """RBJ peaking EQ."""
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / sr; al = np.sin(w) / (2 * q)
    b = [1 + al * A, -2 * np.cos(w), 1 - al * A]; a = [1 + al / A, -2 * np.cos(w), 1 - al / A]
    return signal.lfilter(np.array(b) / a[0], np.array(a) / a[0], x, axis=0)


def env_exp(n, sr, tau, attack=0.001):
    t = np.arange(n) / sr; e = np.exp(-t / tau)
    a = int(attack * sr)
    if a > 0: e[:a] *= np.linspace(0, 1, a)
    return e


def place(buf, x, i, g=1.0):
    if i >= len(buf) or i + len(x) <= 0: return
    if i < 0: x = x[-i:]; i = 0
    x = x[: len(buf) - i]; buf[i:i + len(x)] += x * g


def sweep_lp(x, cut, sr, B=64):
    """One-pole low-pass with a cutoff that changes every B samples (x: (n, ch))."""
    out = np.empty_like(x); z = np.zeros((1, x.shape[1]))
    for i in range(0, len(x), B):
        a = np.exp(-2 * np.pi * cut[min(i, len(cut) - 1)] / sr)
        y, z = signal.lfilter([1 - a], [1, -a], x[i:i + B], axis=0, zi=z)
        out[i:i + B] = y
    return out


def knee(x, k=0.6):
    """Soft clip: linear below k, tanh-shaped above, never past 1."""
    a = np.abs(x)
    return np.where(a < k, x, np.sign(x) * (k + (1 - k) * np.tanh((a - k) / (1 - k))))


def lufs(x, sr):
    x = np.asarray(x, np.float32); ch = 1 if x.ndim == 1 else x.shape[1]
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(sr), "-ac", str(ch), "-i", "-",
                        "-af", "ebur128=peak=true", "-f", "null", "-"], input=x.tobytes(), capture_output=True).stderr.decode()
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return (float(i[-1]) if i else -70.0), (float(p[-1]) if p else 0.0)


def plate_ir(sr, rt60, rng, hicut=6000, predelay=0.02):
    n = int((rt60 * 1.1 + predelay) * sr); t = np.arange(n) / sr
    ir = rng.standard_normal((n, 2)) * np.exp(-6.9 * t / rt60)[:, None]
    ir = filt(filt(ir, "lowpass", hicut, sr, 2), "highpass", 300, sr, 1)
    ir[: int(predelay * sr)] = 0
    return ir / np.sqrt((ir ** 2).sum(0))


def ping_pong(x, sr, d, fb, taps=6):
    """Stereo ping-pong delay on a mono send: the echoes alternate right and left, each one darker."""
    n = len(x); out = np.zeros((n, 2)); y = filt(x, "bandpass", [400, 5000], sr)
    for k in range(1, taps + 1):
        i = int(round(k * d * sr))
        if i >= n: break
        out[i:, k % 2] += y[: n - i] * fb ** (k - 1)
        y = filt(y, "lowpass", 4500, sr, 1)
    return out


def wow(x, sr, rate, depth_ms, ph):
    """Tape wow: a slowly wandering delay (pitch moves by a few cents)."""
    n = len(x); t = np.arange(n) / sr
    pos = np.arange(n) - ((depth_ms / 1000) * (1 + np.sin(2 * np.pi * rate * t + ph)) * sr / 2 + 2)
    return np.stack([np.interp(pos, np.arange(n), x[:, c]) for c in range(x.shape[1])], 1)


def crush(x, bits, hold):
    q = 2 ** (bits - 1); y = np.round(x * q) / q
    return np.repeat(y[::hold], hold, axis=0)[: len(x)] if hold > 1 else y


# ------------------------------------------------------------------ instruments
def cowbell_sample(sr, cb):
    """One 808-style cowbell hit at native pitch: 540 / ~800 Hz squares, band-pass at 2.5-3 kHz, 60-120 ms decay."""
    n = int(0.6 * sr); f1 = 540.0
    x = square(np.full(n, f1), sr, cb["pw"]) + cb["upper"] * square(np.full(n, f1 * cb["ratio"]), sr, 0.5)
    x = filt(x, "bandpass", [cb["bp"] / 1.7, cb["bp"] * 1.4], sr, 2) + cb["body"] * filt(x, "bandpass", [450, 1100], sr, 1)
    t = np.arange(n) / sr
    e = 0.6 * np.exp(-t / 0.008) + 0.4 * np.exp(-t / cb["decay"])
    e[: int(0.001 * sr)] *= np.linspace(0, 1, int(0.001 * sr))
    x = x * e
    return x / np.abs(x).max()


def kick(sr, k, rng):
    n = int(0.4 * sr); t = np.arange(n) / sr
    f = k["f_end"] + (k["f_start"] - k["f_end"]) * np.exp(-t / k["sweep"])
    body = np.sin(2 * np.pi * np.cumsum(f) / sr) * env_exp(n, sr, k["decay"], 0.0005)
    cl = int(0.006 * sr)
    click = filt(rng.standard_normal(cl), "bandpass", [1500, 6000], sr) * np.linspace(1, 0, cl) ** 2
    blip = np.sin(2 * np.pi * k["blip"] * t[:cl]) * np.linspace(1, 0, cl)
    body[:cl] += k["click"] * (click / np.abs(click).max() + blip)
    x = np.tanh(k["drive"] * body) / np.tanh(k["drive"])
    x[-int(0.03 * sr):] *= np.linspace(1, 0, int(0.03 * sr))
    return x


def clap(sr, c, rng):
    n = int(0.4 * sr); x = np.zeros(n)
    for j, d in enumerate((0, 0.010, 0.020)):
        i = int((d + c["jit"] * j) * sr); m = n - i
        x[i:] += rng.standard_normal(m) * env_exp(m, sr, 0.0035 if j < 2 else c["tail"]) * (0.8 if j < 2 else 1.0)
    x = filt(x, "bandpass", [c["lo"], c["hi"]], sr, 2) + 0.12 * filt(x, "bandpass", [3500, 7000], sr)
    if c["snare"]:
        t = np.arange(n) / sr
        x = x / np.abs(x).max() + 0.6 * np.sin(2 * np.pi * c["snare_f"] * t * (1 + 0.25 * np.exp(-t / 0.01))) * env_exp(n, sr, 0.045)
    return x / np.abs(x).max()


def hat(sr, h, rng, open_=False, pitch=1.0):
    n = int((0.4 if open_ else 0.1) * sr)
    ring = square(np.full(n, h["r1"] * pitch), sr) * square(np.full(n, h["r2"] * pitch), sr)   # ring-mod metal
    x = (1 - h["metal"]) * rng.standard_normal(n) + h["metal"] * ring * 1.3
    x = filt(filt(x, "highpass", h["hp"] * pitch ** 0.4, sr, 4), "lowpass", h["lp"], sr, 2)
    x = x * env_exp(n, sr, h["open_decay"] if open_ else h["decay"], 0.0004)
    return x / np.abs(x).max()


# ------------------------------------------------------------------ composition
def write_riff(rng):
    """2-bar cowbell riff in scale steps (0 = root, 7 = octave): a 3-5 note cell cycled over a syncopated rhythm, with
    an octave jump; bar 2 keeps the start and swaps the tail for a short run that comes home."""
    for _ in range(500):
        rhythm = RIFF_RHYTHMS[rng.integers(len(RIFF_RHYTHMS))]
        hits = [i for i, c in enumerate(rhythm) if c == "x"]
        L = int(rng.integers(3, 6))
        cell = [0] + [int(rng.choice([0, 0, 1, 2, -1, -2, 4, 3, 7, 5, -3])) for _ in range(L - 1)]
        if 7 not in cell and rng.random() < 0.7: cell[int(rng.integers(1, L))] = 7      # the octave jump
        bar1 = [cell[i % L] for i in range(len(hits))]
        k = int(rng.integers(3, 5))
        tail = [int(np.clip(bar1[-k - 1] + d, -3, 8)) for d in np.cumsum(rng.choice([-1, -1, -2, 1, 2], k - 1))]
        bar2 = bar1[:-k] + tail + [int(rng.choice([0, 0, 1, -1]))]
        seq = bar1 + bar2
        if len(set(seq)) < 3 or max(seq) - min(seq) > 10 or bar1 == bar2: continue
        if max(seq) - min(seq) < 5: continue
        glides = [bool(abs(b - a) >= 4 or (a != b and rng.random() < 0.25)) for a, b in zip(seq[-1:] + seq[:-1], seq)]
        return {"rhythm": rhythm, "hits": hits, "cell": cell, "bars": [bar1, bar2], "glide_into": glides}
    raise RuntimeError("no riff")


def semis(scale, s):
    return scale[s % 7] + 12 * (s // 7)


def plan(slug):
    rng = np.random.default_rng(seed_of(slug)); p = {"slug": slug, "seed": seed_of(slug)}
    p["style"] = str(rng.choice(["drift", "funk"], p=[.6, .4]))
    p["bpm"] = int(rng.integers(130, 146)) if p["style"] == "drift" else int(rng.integers(115, 126))
    p["halftime"] = p["style"] == "funk"
    p["root"] = int(rng.integers(12))
    p["mode"] = str(rng.choice(list(MODES), p=[.4, .25, .2, .15]))
    p["prog"] = PROGS[p["mode"]][rng.integers(len(PROGS[p["mode"]]))]
    p["riff"] = write_riff(rng)
    p["riff_b"] = str(rng.choice(["octave", "answer", "double"]))
    if p["riff_b"] == "answer": p["riff_alt"] = write_riff(rng)
    pats = BASS_DRIFT if p["style"] == "drift" else BASS_FUNK
    p["bass"] = [list(x) for x in pats[rng.integers(len(pats))]]
    p["bass_slide"] = str(rng.choice(["octave_up", "fifth_up", "down"]))
    p["glide_ms"] = float(rng.uniform(40, 80))
    p["kick"] = {"f_start": float(rng.uniform(160, 240)), "f_end": float(rng.uniform(45, 55)), "sweep": float(rng.uniform(0.02, 0.045)),
                 "decay": float(rng.uniform(0.08, 0.14)), "drive": float(rng.uniform(1.5, 3.5)), "click": float(rng.uniform(0.25, 0.6)),
                 "blip": float(rng.uniform(900, 2500))}
    p["clap"] = {"jit": float(rng.uniform(-0.002, 0.003)), "tail": float(rng.uniform(0.07, 0.15)), "lo": float(rng.uniform(900, 1200)),
                 "hi": float(rng.uniform(1800, 2600)), "snare": bool(rng.random() < 0.35), "snare_f": float(rng.uniform(170, 230))}
    p["hat"] = {"metal": float(rng.uniform(0.25, 0.6)), "r1": float(rng.uniform(3000, 4200)), "r2": float(rng.uniform(5200, 7400)),
                "hp": float(rng.uniform(5500, 7000)), "lp": 9000.0, "decay": float(rng.uniform(0.018, 0.035)),
                "open_decay": float(rng.uniform(0.12, 0.22)), "pattern": str(rng.choice(["8ths", "16ths", "8ths+pushes"], p=[.5, .2, .3])),
                "roll": str(rng.choice(["32nds", "triplets", "ramp"])), "open_steps": [6, 14] if rng.random() < 0.5 else [2, 6, 10, 14]}
    p["cowbell"] = {"ratio": float(rng.uniform(1.46, 1.50)), "upper": float(rng.uniform(0.6, 0.9)), "pw": float(rng.uniform(0.4, 0.5)),
                    "bp": float(rng.uniform(2500, 3000)), "decay": float(rng.uniform(0.06, 0.12)), "detune": float(rng.uniform(5, 12)),
                    "drive": float(rng.uniform(1.5, 3.0)), "bits": int(rng.integers(9, 13)), "hold": int(rng.integers(1, 3)),
                    "glide_s": float(rng.uniform(0.015, 0.035)), "body": 0.6}
    p["fx"] = {"rt60": float(rng.uniform(1.5, 2.5)), "plate": float(rng.uniform(0.22, 0.35)), "delay_fb": float(rng.uniform(0.3, 0.45)),
               "delay": float(rng.uniform(0.15, 0.26)), "wow_rate": float(rng.uniform(0.4, 1.0)), "wow_ms": float(rng.uniform(0.6, 1.4)),
               "duck_db": float(rng.uniform(4, 8))}
    p["pad"] = {"kind": str(rng.choice(["saw", "choir"])), "vowel": str(rng.choice(["o", "a", "u"])), "cut": float(rng.uniform(900, 1600)),
                "voicing": [0, 2, 4] if rng.random() < 0.6 else [0, 4, 9]}
    p["drop_bars"] = int(rng.choice([6, 8]))
    p["rng_state"] = int(rng.integers(2 ** 31))
    return p


# mix levels (RMS of each stem before the bus), calibrated against measured phonk references
LEVELS = {"kick": 0.085, "808": 0.16, "clap": 0.05, "hats": 0.012, "bell": 0.08, "pad": 0.075, "fx": 0.006}


def make_bed(slug, seconds=40, sr=48000, levels=None):
    G = dict(LEVELS, **(levels or {}))
    p = plan(slug); rng = np.random.default_rng(p["rng_state"]); scale = MODES[p["mode"]]
    step = 60 / p["bpm"] / 4; bar = 16 * step
    nbars = int(np.ceil(seconds / bar)); N = int(round(nbars * bar * sr))
    sec = ["intro", "intro"] + ["A"] * p["drop_bars"] + ["break"]
    while len(sec) < nbars: sec += ["B"] * 8
    sec = sec[:nbars]
    O = 2                                                  # phrase positions count from the drop
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    idx = lambda t: int(round(t * sr))
    t_of = lambda b, s: (b * 16 + s) * step
    bass_midi = 23 + (p["root"] - 23) % 12                 # 808 tonic B0..A#1 (31-58 Hz): real beds peak at 31-40 Hz

    K = kick(sr, p["kick"], rng); C = clap(sr, p["clap"], rng)
    Hs = [hat(sr, p["hat"], rng) for _ in range(4)]; HO = hat(sr, p["hat"], rng, open_=True)
    kick_b = np.zeros(N); clap_b = np.zeros(N); hat_b = np.zeros((N, 2)); fx_b = np.zeros((N, 2))
    kicks = []

    # ---- 808: one frequency contour + envelope over the whole bed (phase continuous, so the glides are real)
    fcur = np.full(N, hz(bass_midi)); amp = np.zeros(N); prev_f = hz(bass_midi)
    for b in range(nbars):
        s_ = sec[b]
        if s_ == "intro": continue
        deg = p["prog"][(b - O) % 4]; off = scale[deg % 7]; off = off - 12 if off > 6 else off
        base = hz(bass_midi + off)
        if s_ == "break":   # drums out: one long 808 that slides up into the second drop
            notes = [(0, 8, base, False), (8, 8, base * (1.5 if p["bass_slide"] == "fifth_up" else 2.0), True)]
        else:
            notes = []
            for j, (s, ln) in enumerate(p["bass"]):
                f = base; gl = False
                if j == len(p["bass"]) - 1 and (b - O) % 2 == 1:      # the signature slide, every other bar
                    f = base * {"octave_up": 2.0, "fifth_up": 1.5, "down": 2 ** (-5 / 12)}[p["bass_slide"]]; gl = True
                notes.append((s, ln, f, gl))
        for s, ln, f, gl in notes:
            i0 = idx(t_of(b, s)); i1 = min(N, idx(t_of(b, s + ln)))
            n = i1 - i0; t = np.arange(n) / sr
            if gl:
                fcur[i0:i1] = f + (prev_f - f) * np.exp(-t / (p["glide_ms"] / 1000 / 3))
                e = np.full(n, max(0.5, amp[i0 - 1])) * np.exp(-t / 1.6)
            else:
                fcur[i0:i1] = f * (1 + 1.2 * np.exp(-t / 0.008))          # the thump: a fast pitch drop
                e = np.exp(-t / 1.4) * np.minimum(1, t / 0.002)
                if s_ != "break": kicks.append(i0)
            r = min(n, int(0.025 * sr)); e[-r:] *= np.linspace(1, 0, r)
            amp[i0:i1] = e; prev_f = f
    x = np.sin(2 * np.pi * np.cumsum(fcur) / sr) * amp
    sat = knee(1.15 * np.tanh(2.2 * x) / np.tanh(2.2))
    sat = 0.85 * sat + 0.15 * np.sin(np.pi / 2 * sat * 1.6) / np.sin(np.pi / 2 * 1.6)   # a little wavefolding
    bass_b = peak_eq(filt(filt(sat, "lowpass", 1800, sr, 2), "highpass", 25, sr, 2), 120, -4.0, 0.8, sr)   # tame the 3rd harmonic

    # ---- drums
    claps = [8] if p["halftime"] else [4, 12]
    for b in range(nbars):
        s_ = sec[b]; pos = (b - O) % 8
        if s_ in ("A", "B"):
            for i0 in [k for k in kicks if idx(t_of(b, 0)) <= k < idx(t_of(b + 1, 0))]: place(kick_b, K, i0)
            for s in claps: place(clap_b, C, idx(t_of(b, s)))
            if pos in (3, 7): place(clap_b, C, idx(t_of(b, 15)), 0.5)
            pat = p["hat"]["pattern"] if s_ == "A" else ("16ths" if p["hat"]["pattern"] != "16ths" else "8ths+pushes")
            hs = {"8ths": range(0, 16, 2), "16ths": range(16), "8ths+pushes": [0, 2, 3, 4, 6, 8, 10, 11, 12, 14]}[pat]
            roll = pos in (3, 7) or (pos % 2 == 1 and rng.random() < 0.5)
            for s in hs:
                if roll and s >= 12: continue
                v = (1.0 if s % 4 == 0 else 0.75 if s % 2 == 0 else 0.55) * rng.uniform(0.8, 1.0)
                pan = 0.2 * (1 if (s // 2) % 2 else -1)
                place(hat_b[:, 0], Hs[s % 4] * v, idx(t_of(b, s)), 1 - pan); place(hat_b[:, 1], Hs[s % 4] * v, idx(t_of(b, s)), 1 + pan)
            for s in p["hat"]["open_steps"]:
                place(hat_b[:, 0], HO * 0.5, idx(t_of(b, s)), 0.8); place(hat_b[:, 1], HO * 0.5, idx(t_of(b, s)), 1.2)
            if roll:
                t0 = t_of(b, 12); kind = p["hat"]["roll"] if pos in (3, 7) else "32nds"
                ts = {"32nds": [t0 + i * step / 2 for i in range(8)], "triplets": [t0 + i * step * 2 / 3 for i in range(6)],
                      "ramp": [t0 + i * step / 2 for i in range(4)] + [t0 + 2 * step + i * step / 4 for i in range(8)]}[kind]
                for j, t in enumerate(ts):
                    hh = hat(sr, p["hat"], rng, pitch=1 + 0.3 * j / len(ts)) * (0.4 + 0.55 * j / len(ts))
                    pan = 0.5 * np.sin(j)
                    place(hat_b[:, 0], hh, idx(t), 1 - pan); place(hat_b[:, 1], hh, idx(t), 1 + pan)
        elif s_ == "intro" and b == 1:   # second intro bar: light hats and a clap roll into the drop
            for s in range(0, 16, 2): place(hat_b[:, 0], Hs[0] * 0.4, idx(t_of(b, s))); place(hat_b[:, 1], Hs[0] * 0.4, idx(t_of(b, s)))
            for j, t in enumerate([t_of(b, 12) + i * step / 2 for i in range(8)]): place(clap_b, C, idx(t), 0.2 + 0.5 * j / 8)

    # ---- cowbell riff: the native-pitch hit read back at a rate per note (both partials and the filter move), glides
    cb = p["cowbell"]; S = cowbell_sample(sr, cb)
    root_rate = hz(60 + p["root"]) / 540.0
    while root_rate < 0.8: root_rate *= 2
    while root_rate > 1.6: root_rate /= 2
    bell = np.zeros((N, 2)); ax = np.arange(len(S))
    for b in range(nbars):
        s_ = sec[b]; ph = (b - O) % 2
        R = p["riff_alt"] if (s_ == "B" and p["riff_b"] == "answer") else p["riff"]
        hits = R["hits"]; seq = R["bars"][0] + R["bars"][1]
        for j, s in enumerate(hits):
            k = ph * len(hits) + j
            up = 7 if (s_ == "B" and p["riff_b"] == "octave" and ph == 1 and s >= 8) else 0
            rate = root_rate * 2 ** (semis(scale, seq[k] + up) / 12)
            prate = root_rate * 2 ** (semis(scale, seq[k - 1]) / 12)
            nxt = hits[j + 1] if j + 1 < len(hits) else 16
            ln = int(min((nxt - s) * step + 0.03, 0.5) * sr); tt = np.arange(ln) / sr
            r = rate + ((prate - rate) * np.exp(-tt / cb["glide_s"]) if R["glide_into"][k] else 0)
            v = (1.0 if s % 4 == 0 else 0.85) * rng.uniform(0.9, 1.0)
            for ch, dc in ((0, -cb["detune"]), (1, cb["detune"])):
                pos_ = np.cumsum(r * 2 ** (dc / 1200)); pos_ = pos_[pos_ < len(S) - 1]
                note = np.interp(pos_, ax, S); fo = min(len(note), int(0.012 * sr)); note[-fo:] *= np.linspace(1, 0, fo)
                place(bell[:, ch], note, idx(t_of(b, s)), v)
                if s_ == "B" and p["riff_b"] == "double":   # a quiet octave double after the break
                    pos2 = np.cumsum(2 * r * 2 ** (-dc / 1200)); pos2 = pos2[pos2 < len(S) - 1]
                    place(bell[:, ch], np.interp(pos2, ax, S), idx(t_of(b, s)), v * 0.3)
    bell = np.tanh(cb["drive"] * bell) / np.tanh(cb["drive"])
    bell = 0.7 * bell + 0.3 * crush(bell, cb["bits"], cb["hold"])       # light lo-fi
    bell = filt(bell, "lowpass", 9000, sr, 2)
    bell = wow(bell, sr, p["fx"]["wow_rate"], p["fx"]["wow_ms"], rng.uniform(0, 6.28))
    i_end = idx(2 * bar)   # intro: the riff low-passed, opening into the drop, over a riser
    cut = np.concatenate([np.full(idx(bar), 600.0), np.geomspace(600, 6000, i_end - idx(bar))])
    bell[:i_end] = sweep_lp(bell[:i_end], cut, sr) * 1.7
    ramp = np.linspace(0, 1, i_end) ** 2
    rz = sweep_lp(rng.standard_normal((i_end, 1)), 200 + 5000 * ramp, sr)[:, 0] * ramp
    fx_b[:i_end, 0] += rz; fx_b[:i_end, 1] += np.roll(rz, 97)
    bi = sec.index("break") if "break" in sec else None
    if bi:   # a short riser into the second drop
        i0, i1 = idx((bi + 0.5) * bar), idx((bi + 1) * bar)
        rr = np.linspace(0, 1, i1 - i0) ** 2
        rz = sweep_lp(rng.standard_normal((i1 - i0, 1)), 300 + 5000 * rr, sr)[:, 0] * rr
        fx_b[i0:i1, 0] += rz; fx_b[i0:i1, 1] += np.roll(rz, 89)

    # ---- dark pad under the riff (fills 150-600 Hz like the real beds): detuned saws, low-passed or vowel-shaped
    pd = p["pad"]; pad = np.zeros((N, 2))
    for b in range(nbars):
        deg = p["prog"][(b - O) % 4] if sec[b] != "intro" else 0
        n = idx(bar); i0 = idx(b * bar); t = np.arange(n) / sr
        v = np.zeros((n, 2))
        for c in pd["voicing"]:
            f = hz(57 + (p["root"] - 57) % 12 + semis(scale, deg + c))   # tonic A3..G#4: fills 250-600 Hz
            for ch, d in ((0, -8), (1, 8)):
                v[:, ch] += saw(np.full(n, f * 2 ** (d / 1200)), sr, 0.37 * ch + 0.11 * c) + 0.5 * saw(np.full(n, f * 2 ** (-d / 2400)), sr, 0.2 * c)
        if pd["kind"] == "choir":
            F = {"o": (450, 800), "a": (750, 1150), "u": (330, 700)}[pd["vowel"]]
            v = filt(v, "bandpass", [F[0] * .8, F[0] * 1.2], sr) + 0.6 * filt(v, "bandpass", [F[1] * .85, F[1] * 1.15], sr) + 0.35 * filt(v, "lowpass", 600, sr)
        else:
            v = filt(v, "lowpass", pd["cut"], sr, 2)
        fade = np.minimum(1, np.minimum(t / 0.05, (bar - t) / 0.05))
        pad[i0:i0 + n] += (v * fade[:, None])[: N - i0]
    pad[:idx(2 * bar)] = sweep_lp(pad[:idx(2 * bar)], np.geomspace(400, 3000, idx(2 * bar)), sr) * 1.4

    # ---- mix: sidechain pump from the kick (4-8 dB, 120 ms release) on everything but the kick
    duck = np.ones(N); depth = 1 - 10 ** (-p["fx"]["duck_db"] / 20)
    shape = np.concatenate([np.linspace(0, 1, int(0.004 * sr)), np.exp(-np.arange(int(0.45 * sr)) / sr / (0.12 / 2.3))])
    for k in kicks:
        seg = duck[k:k + len(shape)]; np.minimum(seg, 1 - depth * shape[:len(seg)], out=seg)
    rms = lambda a: np.sqrt((a ** 2).mean()) + 1e-12
    kick_m = kick_b / rms(kick_b) * G["kick"]
    bass_m = bass_b / rms(bass_b) * G["808"] * (1 - 0.5 * (1 - duck))   # half the pump on the 808: it hits with the kick
    clap_m = clap_b / rms(clap_b) * G["clap"] * duck
    hat_m = hat_b / rms(hat_b) * G["hats"] * duck[:, None]
    bell_m = bell / rms(bell) * G["bell"]
    fx_m = fx_b / rms(fx_b) * G["fx"]
    pad_m = filt(pad, "highpass", 200, sr, 2) / rms(pad) * G["pad"]
    ir = plate_ir(sr, p["fx"]["rt60"], rng)
    send = bell_m.mean(1) + clap_m * 0.7
    wet = np.stack([signal.fftconvolve(send, ir[:, c])[:N] for c in (0, 1)], 1) * p["fx"]["plate"]
    dly = ping_pong(bell_m.mean(1), sr, 3 * step, p["fx"]["delay_fb"]) * p["fx"]["delay"]   # dotted 1/8
    mix = (bell_m + wet + dly + pad_m) * duck[:, None] + hat_m + fx_m + clap_m[:, None] + (kick_m + bass_m)[:, None]
    mix = mix / np.abs(mix).max()
    mix = np.tanh(1.6 * mix) / np.tanh(1.6)                               # bus saturation
    mid = mix.mean(1); side = filt((mix[:, 0] - mix[:, 1]) / 2, "highpass", 120, sr, 4)   # mono below 120 Hz
    mix = filt(np.stack([mid + side, mid - side], 1), "highpass", 22, sr, 2)
    mix = master(mix, sr, -8.5)
    L, tp = lufs(mix, sr)
    info = {k: p[k] for k in ("slug", "seed", "style", "bpm", "halftime", "mode", "prog", "riff_b", "bass", "bass_slide", "drop_bars")}
    info.update(key=f"{NAMES[p['root']]} {p['mode']}", bar_s=round(bar, 6), bars=nbars, sections=sec,
                loop=[round(2 * bar, 4), round(nbars * bar, 4)], drop_s=round(2 * bar, 4), break_s=round(bi * bar, 4) if bi else None,
                riff={"rhythm": p["riff"]["rhythm"], "cell": p["riff"]["cell"], "bars_scale_steps": p["riff"]["bars"]},
                bass_root_midi=bass_midi, cowbell=cb, kick=p["kick"], clap=p["clap"], hat=p["hat"], fx=p["fx"],
                lufs=L, true_peak_dbtp=tp, seconds=round(N / sr, 4))
    return mix.astype(np.float32), info


def master(x, sr, target):
    """Compressor, then gain into a soft clip and a look-ahead limiter on the 4x-oversampled peak (ceiling -1.3 dB),
    iterated until the loudness is on target."""
    a = np.exp(-1 / (0.03 * sr))
    env = np.sqrt(signal.lfilter([1 - a], [1, -a], (x ** 2).mean(1)))
    thr = np.percentile(env, 60); ratio = 2.5
    x = x * np.where(env > thr, (thr / np.maximum(env, 1e-9)) ** (1 - 1 / ratio), 1.0)[:, None]
    gain = 1.0 / np.abs(x).max(); ceil = 10 ** (-1.3 / 20); la = int(0.003 * sr); dec = 64
    rel = np.exp(-dec / (0.08 * sr))
    for _ in range(8):
        y = knee(x * gain, 0.55)
        over = np.abs(signal.resample_poly(y, 4, 1, axis=0)).max(1).reshape(-1, 4).max(1)[: len(y)]
        g = minimum_filter1d(np.minimum(1, ceil / np.maximum(over, 1e-9)), 2 * la + 1)   # look-ahead hold
        gd = g[: len(g) // dec * dec].reshape(-1, dec).min(1); s = 1.0
        for i in range(len(gd)):                                            # instant attack, 80 ms release
            s = gd[i] if gd[i] < s else gd[i] + (s - gd[i]) * rel; gd[i] = s
        g2 = np.interp(np.arange(len(g)), np.arange(len(gd)) * dec + dec / 2, gd)
        g2 = np.minimum(np.convolve(g2, np.ones(la) / la, "same"), g)
        y = y * g2[:, None]
        L, tp = lufs(y, sr)
        if abs(L - target) < 0.3 and tp <= -1.0: break
        gain *= 10 ** ((target - L) / 20)
    return y


def main(slug, out=None):
    audio, info = make_bed(slug)
    out = out or os.path.join(CACHE, "music", f"{slug}-phonk.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sf.write(out, audio, 48000, subtype="PCM_24")
    print(f"wrote {out}: {info['style']} {info['key']}, {info['bpm']} BPM, loop {info['loop']}, "
          f"{info['lufs']:.1f} LUFS, true peak {info['true_peak_dbtp']:.1f} dBTP")
    return out, info


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    o, info = main(a[0], a[1] if len(a) > 1 else None)
    if "--info" in sys.argv: print(json.dumps(info, indent=1, default=str))
