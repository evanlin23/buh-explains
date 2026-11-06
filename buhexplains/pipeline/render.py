"""Render a BuhExplains Short from episode.json + out/<slug>/words.json (made by voice.py).

  python buhexplains/pipeline/render.py ep01-verity [--preview]

Writes out/<slug>/<slug>.mp4 (1080x1920, 30 fps; --preview: 540x960) and prints the pacing stats that
PLAYBOOK.md section 6 gates on. Audio = narration + synthesized SFX only (the song is added at upload).
"""
import json, math, os, re, subprocess, sys
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
W, H, FPS, SR = 1080, 1920, 30, 48000
IMG_CENTER = (540, 880)
CAPTION_Y = 1270
LABEL_Y = {"top": 360, "lower": 1420}


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


# ------------------------------------------------------------------ timeline
def build(ep, words):
    by_line = {}
    for w in words:
        by_line.setdefault(w["line"], []).append(w)
    names = {norm(n) for n in ep.get("names", [])}
    tl = {k: [] for k in ("plate", "image", "sticker", "label", "flash", "stinger", "punch", "caption", "sfx")}
    for li, line in enumerate(ep["lines"]):
        ws = by_line[li]
        line_start, line_end = ws[0]["start"] - 0.04, ws[-1]["end"]

        def at(on):
            if isinstance(on, int):
                return line_start if on == 0 else ws[on]["start"]
            for w in ws:
                if w["word"] == on or norm(w["word"]) == norm(on):
                    return w["start"]
            raise SystemExit(f"line {li}: no word {on!r} in {line['text']!r}")

        for ev in line.get("events", []):
            t = max(0.0, at(ev["on"]))
            kind = ev["type"]
            if kind == "plate": tl["plate"].append((t, ev["plate"]))
            elif kind == "image":
                tl["image"].append((t, ev["art"], ev.get("enter", "scale_in")))
                tl["sfx"].append((t, {"slam": "slam", "scale_in": "whoosh", "push": "whoosh"}[ev.get("enter", "scale_in")]))
            elif kind == "sticker":
                tl["sticker"].append((t, ev["art"], tuple(ev.get("pos", IMG_CENTER)), ev.get("size", 300), ev.get("dur", 0.8)))
                tl["sfx"].append((t, "slam" if ev["art"] == "red_x" else "pop"))
            elif kind == "label": tl["label"].append((t, line_end + 0.15, ev["text"], ev.get("pos", "top")))
            elif kind == "flash": tl["flash"].append(t); tl["sfx"].append((t, "boom"))
            elif kind == "punch": tl["punch"].append(t)
        for w in ws:  # the name stinger: every time the meme's name is said
            if norm(w["word"]) in names:
                tl["stinger"].append(w["start"] - 0.06); tl["sfx"].append((w["start"] - 0.06, "fwoomp"))
        # captions: 1-2 words, break after punctuation, never wider than the frame allows
        chunk = []
        for i, w in enumerate(ws):
            chunk.append(w)
            text = " ".join(c["word"] for c in chunk)
            nxt = ws[i + 1] if i + 1 < len(ws) else None
            if (len(chunk) == 2 or re.search(r"[.,?!]$", w["word"]) or nxt is None
                    or len(text + " " + nxt["word"]) > 14):
                tl["caption"].append([chunk[0]["start"], None, re.sub(r"[.,]$", "", text)])
                chunk = []
    caps = tl["caption"]
    for a, b in zip(caps, caps[1:]):
        a[1] = min(b[0], a[0] + 1.6)
    caps[-1][1] = caps[-1][0] + 1.6
    for k in ("plate", "image"):
        tl[k].sort(key=lambda e: e[0])
    return tl


def stats(tl, dur):
    """Visible picture changes: images, plates, stickers, labels, flashes, stingers, punches (not captions)."""
    ts = sorted([e[0] for k in ("plate", "image", "sticker", "label") for e in tl[k]] + tl["flash"] + tl["stinger"] + tl["punch"])
    ts = sorted(set(round(t, 2) for t in ts))
    gaps = np.diff([0] + ts + [dur])
    return {"changes": len(ts), "per_10s": round(len(ts) / dur * 10, 1), "longest_gap_s": round(float(gaps.max()), 2),
            "gap_at_s": round(float(([0] + ts)[int(gaps.argmax())]), 2)}


# ------------------------------------------------------------------ drawing
def ease_out_back(x, k=1.7):
    x = min(max(x, 0), 1) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def current(events, t):
    cur = None
    for e in events:
        if e[0] <= t: cur = e
        else: break
    return cur


def place(frame, img, center, scale, rot=0.0):
    if scale <= 0.01: return
    w, h = max(1, int(img.width * scale)), max(1, int(img.height * scale))
    im = img.resize((w, h), Image.BILINEAR)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BILINEAR)
    frame.alpha_composite(im, (int(center[0] - im.width / 2), int(center[1] - im.height / 2)))


def fit(img, box=(900, 1000)):
    return min(box[0] / img.width, box[1] / img.height)


def text_layer(text, px, glow=None, maxw=940):
    f = art.font(px)
    while px > 40 and ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=f) > maxw:
        px -= 4; f = art.font(px)
    pad = 60
    tw = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=f)) + pad * 2
    th = px + pad * 2
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    if glow:
        g = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((tw / 2, th / 2), text, font=f, fill=glow, anchor="mm", stroke_width=10, stroke_fill=glow)
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(14)))
        im.alpha_composite(g.filter(ImageFilter.GaussianBlur(5)))
    else:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((tw / 2 + 7, th / 2 + 8), text, font=f, fill=(0, 0, 0, 255), anchor="mm", stroke_width=9, stroke_fill=(0, 0, 0, 255))
        im.alpha_composite(sh)
    ImageDraw.Draw(im).text((tw / 2, th / 2), text, font=f, fill=(252, 253, 252, 255), anchor="mm",
                            stroke_width=0 if glow else 9, stroke_fill=(10, 10, 10, 255))
    return im


_cache = {}


def cached(key, fn):
    if key not in _cache: _cache[key] = fn()
    return _cache[key]


def frame_at(tl, t, dur):
    p = current(tl["plate"], t)
    frame = art.plate(p[1] if p else "black", t).copy()
    im = current(tl["image"], t)
    if im:
        t0, name, enter = im
        a = t - t0
        img = cached(("art", name), lambda: art.get(name))
        base = fit(img)
        if enter == "scale_in": s = base * (0.15 + 0.85 * ease_out_back(a / 0.2))
        elif enter == "slam": s = base * (1 + 0.6 * max(0, 1 - a / 0.12) ** 2)
        else: s = base * (0.92 + 0.16 * min(a / 2.5, 1))  # push: slow zoom
        for pt in tl["punch"]:
            if 0 <= t - pt < 0.25: s *= 1 + 0.14 * (1 - (t - pt) / 0.25)
        spin = 8 * math.sin(a * 2.3) if name.startswith("smiley") else 0
        place(frame, img, IMG_CENTER, s, spin)
    for t0, name, pos, size, d in tl["sticker"]:
        if t0 <= t < t0 + d:
            img = cached(("art", name, size), lambda: art.get(name, size) if name not in ("smiley_grid",) else art.get(name))
            place(frame, img, pos, 0.3 + 0.7 * ease_out_back((t - t0) / 0.14, 2.4))
    for t0, t1, text, pos in tl["label"]:
        if t0 <= t < t1 and not any(o[0] > t0 and o[0] <= t and o[3] == pos for o in tl["label"]):
            lab = cached(("label", text), lambda: text_layer(text, 104, glow=(228, 56, 104, 255)))
            place(frame, lab, (540, LABEL_Y[pos]), 0.6 + 0.4 * ease_out_back((t - t0) / 0.15, 2))
    # constant shake (the owner: "everything shakes and is intense")
    dx = 11 * (math.sin(t * 37) + 0.6 * math.sin(t * 61 + 1.3)); dy = 11 * (math.sin(t * 43 + 2) + 0.6 * math.sin(t * 71))
    rot = 0.9 * math.sin(t * 29 + 0.5)
    frame = frame.resize((int(W * 1.04), int(H * 1.04)), Image.BILINEAR).crop((21, 38, 21 + W, 38 + H))
    frame = frame.rotate(rot, resample=Image.BILINEAR, translate=(dx, dy), fillcolor=(8, 8, 10, 255))
    for st in tl["stinger"]:
        a = t - st
        if 0 <= a < 0.34:
            fb = art.fireball(); s = (0.7 + a * 5.0) * 1.6
            place(frame, fb, (540, 900), s * 0.6)
            if a > 0.2:
                frame = Image.blend(frame, frame, 1)
    for t0, t1, text in tl["caption"]:
        if t0 <= t < t1:
            cap = cached(("cap", text), lambda: text_layer(text, 112))
            pop = 0.85 + 0.15 * ease_out_back((t - t0) / 0.08, 2)
            place(frame, cap, (540, CAPTION_Y), pop)
    for fl in tl["flash"]:
        if 0 <= t - fl < 0.13:
            white = Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (t - fl) / 0.13))))
            frame.alpha_composite(white)
    return frame


# ------------------------------------------------------------------ sound effects (synthesized, no samples)
def sfx(name, rng=np.random.default_rng(1)):
    def env(n, a=0.004, d=0.2):
        t = np.arange(n) / SR
        return np.minimum(t / a, 1) * np.exp(-t / d)
    def lowpass(x, k):
        y = np.empty_like(x); acc = 0.0
        for i, v in enumerate(x):
            acc += k * (v - acc); y[i] = acc
        return y
    if name in ("boom", "fwoomp"):
        n = int(SR * (0.7 if name == "boom" else 0.4)); t = np.arange(n) / SR
        f = 70 * np.exp(-t * 5) + 32
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.28 if name == "boom" else 0.15)
        noise = lowpass(rng.standard_normal(n), 0.05) * env(n, 0.002, 0.12) * 3
        return (body + noise) * (0.9 if name == "boom" else 0.55)
    if name == "whoosh":
        n = int(SR * 0.28); t = np.arange(n) / SR
        x = lowpass(rng.standard_normal(n), 0.12) * np.sin(np.pi * t / t[-1]) ** 2
        return x * 0.5
    if name == "slam":
        n = int(SR * 0.3); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 95 * t) * env(n, 0.002, 0.07) + lowpass(rng.standard_normal(n), 0.3) * env(n, 0.001, 0.02)) * 0.8
    if name == "pop":
        n = int(SR * 0.08); t = np.arange(n) / SR
        return np.sin(2 * np.pi * (950 - 4000 * t) * t) * env(n, 0.001, 0.025) * 0.5
    raise KeyError(name)


def mix(slug, tl, dur):
    od = os.path.join(REPO, "out", slug)
    v, vsr = sf.read(os.path.join(od, "voice.wav"), dtype="float32")
    v = np.interp(np.arange(0, len(v), vsr / SR), np.arange(len(v)), v).astype(np.float32)
    n = int(dur * SR) + SR
    out = np.zeros(n, np.float32); out[:len(v)] += v
    bank = {}
    for t, name in tl["sfx"]:
        s = bank.setdefault(name, sfx(name).astype(np.float32))
        i = int(max(0, t) * SR); seg = s[: max(0, n - i)]
        out[i:i + len(seg)] += seg * 0.32
    out = out[: int(dur * SR)]
    p = os.path.join(od, "mix.wav"); sf.write(p, out, SR)
    return p


# ------------------------------------------------------------------ main
def main(slug, preview=False):
    ep = json.load(open(os.path.join(ROOT, "episodes", slug, "episode.json")))
    wj = json.load(open(os.path.join(REPO, "out", slug, "words.json")))
    tl = build(ep, wj["words"])
    dur = round(wj["duration"] + 0.25, 3)  # payoff is the last word, then a 0.25 s tail and the cut (loop)
    st = stats(tl, dur)
    print(json.dumps(st))
    audio = mix(slug, tl, dur)
    od = os.path.join(REPO, "out", slug)
    outp = os.path.join(od, f"{slug}{'-preview' if preview else ''}.mp4")
    size = (540, 960) if preview else (W, H)
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}",
           "-r", str(FPS), "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k",
           "-ar", "48000", "-shortest", "-movflags", "+faststart", outp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(dur * FPS)
    for i in range(nf):
        f = frame_at(tl, i / FPS, dur).convert("RGB")
        if preview: f = f.resize(size, Image.BILINEAR)
        proc.stdin.write(f.tobytes())
        if i % 150 == 0: print(f"  frame {i}/{nf}", flush=True)
    proc.stdin.close(); proc.wait()
    json.dump(st, open(os.path.join(od, "stats.json"), "w"))
    print("wrote", outp)


if __name__ == "__main__":
    main(sys.argv[1], "--preview" in sys.argv)
