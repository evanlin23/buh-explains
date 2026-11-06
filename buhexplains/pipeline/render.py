"""Render a BuhExplains Short: real pictures, edited over the top.

  python buhexplains/pipeline/render.py ep01-verity [--preview]

Inputs: episodes/<slug>/episode.json (beats), out/<slug>/words.json + voice.wav (voice.py).
Pictures are downloaded from the URLs in episode.json into .cache/img (never committed; sources go in the
manifest). Fire/explosion footage: Mixkit free licence clips in .cache/stock. All SFX are synthesized here.
The look is measured from the original Tung Short (reference/TUNG_BREAKDOWN.md): full-bleed pictures that
never sit still, real fire over the picture, a real explosion on every name bite, live stickers, typed
labels, lightning, the whole frame shaking (captions too), loud flat master.
"""
import hashlib, io, json, math, os, random, re, subprocess, sys, urllib.request
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
CACHE = os.path.join(REPO, ".cache")
W, H, FPS, SR = 1080, 1920, 30, 48000
FONT_CAP = os.path.join(ROOT, "fonts", "schibsted-grotesk", "SchibstedGrotesk-Bold.ttf")
FONT_HEAVY = os.path.join(ROOT, "fonts", "archivo-black", "ArchivoBlack-Regular.ttf")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
RED = (226, 20, 20, 255)
STOCK = {"fire": ("12318-720.mp4", 1.0, 4.0), "fire2": ("1242-720.mp4", 1.0, 4.0), "boom": ("38818-720.mp4", 0.3, 1.2)}


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def font(path, px, _c={}):
    if (path, px) not in _c: _c[(path, px)] = ImageFont.truetype(path, px)
    return _c[(path, px)]


# ------------------------------------------------------------------ media
def fetch_image(spec):
    os.makedirs(os.path.join(CACHE, "img"), exist_ok=True)
    for u in [spec["url"]] + ([spec["fallback"]] if spec.get("fallback") else []):
        p = os.path.join(CACHE, "img", hashlib.sha1(u.encode()).hexdigest()[:16])
        if not os.path.exists(p):
            try:
                data = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read()
                Image.open(io.BytesIO(data)).load()
                open(p, "wb").write(data)
            except Exception as e:
                print("  image failed:", u, e); continue
        im = Image.open(p).convert("RGB")
        if "ytimg" in u:  # crop YouTube's letterbox bars off hqdefault
            a = np.asarray(im).mean((1, 2)); rows = np.where(a > 12)[0]
            if len(rows): im = im.crop((0, rows[0], im.width, rows[-1] + 1))
        return im, u
    raise SystemExit(f"no image for {spec}")


def stock_frames(key, size=(540, 960)):
    """Decode a stock clip once into a list of RGB arrays, centre-cropped to 9:16."""
    f, t0, dur = STOCK[key]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t0), "-t", str(dur), "-i", os.path.join(CACHE, "stock", f),
                          "-vf", f"fps={FPS},crop=ih*9/16:ih,scale={size[0]}:{size[1]}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, size[1], size[0], 3)


_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)
EDGE = np.clip(np.hypot((_XX - W / 2) / (W * 0.42), (_YY - H * 0.47) / (H * 0.30)), 0, 1)[..., None] ** 1.6  # 0 centre, 1 edges
FIRE_MASK = 0.28 + 0.72 * EDGE


def screen(base, over, amount=1.0):
    """Screen blend (how fire footage on black sits on top of a picture). Arrays are float 0..1."""
    return 1 - (1 - base) * (1 - over * amount)


# ------------------------------------------------------------------ timeline
def build(ep, words):
    by_line = {}
    for w in words: by_line.setdefault(w["line"], []).append(w)
    names = {norm(n) for n in ep.get("names", {})}
    tl = {k: [] for k in ("img", "sticker", "label", "flash", "lightning", "boom", "caption", "sfx", "fire")}
    for li, line in enumerate(ep["lines"]):
        ws = by_line[li]
        l0, l1 = ws[0]["start"] - 0.03, ws[-1]["end"]

        def at(on):
            if on == 0: return max(0.0, l0)
            if isinstance(on, int): return ws[on]["start"]
            for w in ws:
                if w["word"] == on or norm(w["word"]) == norm(on): return w["start"]
            raise SystemExit(f"line {li}: no word {on!r}")

        for b in line["beats"]:
            t = at(b["on"])
            if "img" in b:
                tl["img"].append(dict(t=t, key=b["img"], enter=b.get("enter", "cut"), fit=b.get("fit", "cover"),
                                      grade=b.get("grade"), zoom=b.get("zoom", 1.0)))
                if b.get("fx") == "fire": tl["fire"].append((t, l1 + 0.05))
                tl["sfx"].append((t, {"zoomblur": "whoosh", "whip": "whip", "spin": "spin", "cut": "pop"}[b.get("enter", "cut")]))
            if "sticker" in b:
                kind = b["sticker"]
                tl["sticker"].append(dict(t=t, end=t + b["dur"] if "dur" in b else l1 + 0.1, kind=kind, at=b.get("at", [540, 900]),
                                          size=b.get("size"), angle=b.get("angle", 0), text=b.get("text"), seed=len(tl["sticker"])))
                tl["sfx"].append((t, {"ellipse": "scribble", "arrow": "whipstk", "heart": "heartpop", "warning": "alarm",
                                      "interrobang": "boing", "x": "x", "number": "ding"}[kind]))
            if "label" in b:
                tl["label"].append(dict(t=t, end=l1 + 0.15, text=b["label"]))
                tl["sfx"].append((t, "typing"))
            if b.get("flash"): tl["flash"].append(t); tl["sfx"].append((t, "impact"))
            if b.get("lightning"): tl["lightning"].append(t); tl["sfx"].append((t, "zap"))
            if b.get("riser"): tl["sfx"].append((t - 1.0, "riser"))
            for extra in b.get("sfx", []): tl["sfx"].append((t, extra))
        for w in ws:  # the name: sound bite + real explosion + fire, every time
            if norm(w["word"]) in names:
                tl["boom"].append(w["start"] - 0.05); tl["sfx"].append((w["start"] - 0.05, "boom"))
                tl["fire"].append((w["start"], w["end"] + 0.25))
        # captions: 1-2 words, every word on its own onset
        chunk = []
        for i, w in enumerate(ws):
            chunk.append(w); nxt = ws[i + 1] if i + 1 < len(ws) else None
            text = " ".join(c["word"] for c in chunk)
            if len(chunk) == 2 or re.search(r"[.,?!]$", w["word"]) or nxt is None or len(text + " " + nxt["word"]) > 13:
                tl["caption"].append([chunk[0]["start"], None, re.sub(r"[.,]$", "", text)]); chunk = []
    caps = tl["caption"]
    for a, b in zip(caps, caps[1:]): a[1] = b[0]
    caps[-1][1] = caps[-1][0] + 1.5
    tl["img"].sort(key=lambda e: e["t"])
    return tl


# ------------------------------------------------------------------ stickers (alive)
def ease(x, k=1.8):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def draw_ellipse(frame, cx, cy, rx, ry, rot, progress, seed):
    """Hand-drawn double red loop. progress 0..1 draws it on."""
    rnd = random.Random(seed); layer = Image.new("RGBA", frame.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    turns = 1.85; n = int(140 * progress) + 2
    pts = []
    for i in range(n):
        a = i / 139 * turns * 2 * math.pi
        wob = 1 + 0.05 * math.sin(a * 3 + seed) + 0.03 * (i / 140)
        x, y = rx * wob * math.cos(a), ry * wob * math.sin(a)
        r = math.radians(rot)
        pts.append((cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)))
    d.line(pts, fill=(0, 0, 0, 120), width=22, joint="curve")
    d.line(pts, fill=RED, width=15, joint="curve")
    frame.alpha_composite(layer)


def arrow_img(size=360):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = size
    shaft = [(s * .38, s * .95), (s * .62, s * .95), (s * .62, s * .45), (s * .38, s * .45)]
    head = [(s * .12, s * .5), (s * .5, s * .04), (s * .88, s * .5)]
    off = 14
    for poly in (shaft, head):  # extruded dark side, then lit face: a cheap 3D look
        d.polygon([(x + off, y + off) for x, y in poly], fill=(110, 0, 0, 255))
    for poly in (shaft, head): d.polygon(poly, fill=(232, 30, 30, 255))
    d.polygon([(s * .5, s * .04), (s * .88, s * .5), (s * .62, s * .5), (s * .5, s * .2)], fill=(255, 110, 110, 255))
    d.polygon([(s * .5, s * .45), (s * .62, s * .45), (s * .62, s * .95), (s * .55, s * .95)], fill=(255, 90, 90, 255))
    return im


def heart_img(size=220):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); pts = []
    for k in range(120):
        t = k / 120 * 2 * math.pi
        x = 16 * math.sin(t) ** 3; y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((size / 2 + x * size / 36, size * .46 - y * size / 36))
    d.polygon([(x + 6, y + 8) for x, y in pts], fill=(0, 0, 0, 110)); d.polygon(pts, fill=(235, 30, 50, 255))
    d.ellipse([size * .25, size * .2, size * .4, size * .33], fill=(255, 160, 170, 255))
    return im


def warning_img(size=420):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); g = Image.new("RGBA", im.size, (0, 0, 0, 0))
    tri = [(size / 2, size * .1), (size * .92, size * .86), (size * .08, size * .86)]
    ImageDraw.Draw(g).line(tri + [tri[0]], fill=(255, 40, 90, 255), width=26, joint="curve")
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(14))); im.alpha_composite(g.filter(ImageFilter.GaussianBlur(4))); im.alpha_composite(g)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([size * .46, size * .34, size * .54, size * .64], 10, fill=(255, 220, 0, 255))
    d.ellipse([size * .45, size * .69, size * .55, size * .78], fill=(255, 220, 0, 255))
    return im


def text_sticker(text, px, fill, stroke=10):
    f = font(FONT_HEAVY, px); w = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=f)) + 60
    im = Image.new("RGBA", (w, px + 60), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((w / 2 + 6, (px + 60) / 2 + 8), text, font=f, fill=(0, 0, 0, 150), anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    d.text((w / 2, (px + 60) / 2), text, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(15, 10, 10, 255))
    return im


def number_tile(text, px=170):
    t = text_sticker(text, px, (232, 40, 40, 255), 6); im = Image.new("RGBA", (t.width + 40, t.height + 30), (30, 30, 34, 235))
    im.alpha_composite(t, (20, 15)); return im


_STK = {}


def stk(key, fn):
    if key not in _STK: _STK[key] = fn()
    return _STK[key]


def paste(frame, im, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.02: return
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
    if rot: im = im.rotate(rot, expand=True, resample=Image.BILINEAR)
    if alpha < 1: im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def draw_sticker(frame, s, t):
    a = t - s["t"]; k = s["kind"]; x, y = s["at"]; rnd = random.Random(s["seed"])
    if k == "ellipse":
        rx, ry = (s["size"] or [560, 480])[0] / 2, (s["size"] or [560, 480])[1] / 2
        draw_ellipse(frame, x + 30 * math.cos(a * 7), y + 22 * math.sin(a * 9), rx, ry, 12 * math.sin(a * 5) + s["seed"] * 17,
                     min(1, a / 0.18), s["seed"])
    elif k == "arrow":
        ang = s["angle"]; slide = (1 - ease(a / 0.14)) * 400; bob = 28 * math.sin(a * 2 * math.pi * 2.6)
        r = math.radians(ang + 90)
        paste(frame, stk("arrow", arrow_img), x + math.cos(r) * (slide + bob), y + math.sin(r) * (slide + bob), 1.0, -ang)
    elif k == "heart":
        hop = int(a / 0.27); r2 = random.Random(s["seed"] * 100 + hop)
        hx, hy = r2.uniform(220, 860), r2.uniform(420, 1300)
        paste(frame, stk("heart", heart_img), hx, hy, (0.9 + 0.25 * math.sin(a * 30)) * ease((a % 0.27) / 0.08), r2.uniform(-25, 25))
        r3 = random.Random(s["seed"] * 77 + hop)
        paste(frame, stk("heart", heart_img), r3.uniform(220, 860), r3.uniform(420, 1300), 0.6 * ease((a % 0.27) / 0.08), r3.uniform(-25, 25))
    elif k == "warning":
        if int(a / 0.125) % 2 == 0:
            paste(frame, stk("warning", warning_img), x, y, ease(min(1, a / 0.1)) * (1 + 0.05 * math.sin(a * 40)))
    elif k == "interrobang":
        paste(frame, stk("ib", lambda: text_sticker("!?", 200, (232, 30, 30, 255))), x, y, ease(a / 0.15, 3), 15 * math.sin(a * 11))
    elif k == "x":
        paste(frame, stk("x", lambda: text_sticker("X", 520, (232, 20, 20, 255), 14)), x + rnd.uniform(-1, 1) * 8 * math.sin(a * 50), y,
              (1.6 - 0.6 * ease(a / 0.12, 2.5)), -8 + 4 * math.sin(a * 13))
    elif k == "number":
        hop = int(a / 0.3); r2 = random.Random(s["seed"] + hop)
        paste(frame, stk(("num", s["text"]), lambda: number_tile(s["text"])), x + r2.uniform(-260, 260), y + r2.uniform(-300, 200),
              ease((a % 0.3) / 0.08), r2.uniform(-12, 12))


def draw_label(frame, lab, t):
    """Pink glow label: types on letter by letter, leaves by scattering its letters."""
    a, left = t - lab["t"], lab["end"] - t
    text = lab["text"]; f = font(FONT_HEAVY, 96)
    while ImageDraw.Draw(frame).textlength(text, font=f) > 960: f = font(FONT_HEAVY, f.size - 6)
    n = min(len(text), int(a / 0.035) + 1)
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    total = d.textlength(text, font=f); x0 = 540 - total / 2; y0 = 380
    rnd = random.Random(hash(text) & 0xffff)
    for i, ch in enumerate(text[:n]):
        cx = x0 + d.textlength(text[:i], font=f); cy = y0
        if left < 0.22:
            p = 1 - left / 0.22; ang = rnd.uniform(0, 2 * math.pi)
            cx += math.cos(ang) * 500 * p * p; cy += math.sin(ang) * 500 * p * p
        d.text((cx, cy), ch, font=f, fill=(255, 70, 130, 255), stroke_width=12, stroke_fill=(255, 70, 130, 255))
    glow = layer.filter(ImageFilter.GaussianBlur(16))
    frame.alpha_composite(glow); frame.alpha_composite(glow)
    d2 = ImageDraw.Draw(frame)
    for i, ch in enumerate(text[:n]):
        cx = x0 + d.textlength(text[:i], font=f); cy = y0
        if left < 0.22:
            p = 1 - left / 0.22; rnd2 = random.Random((hash(text) & 0xffff) + i); ang = rnd2.uniform(0, 2 * math.pi)
        rnd_i = random.Random(hash(text) & 0xffff)
    # crisp white letters on top (same scatter maths, recomputed)
    rnd = random.Random(hash(text) & 0xffff)
    for i, ch in enumerate(text[:n]):
        cx = x0 + d.textlength(text[:i], font=f); cy = y0
        if left < 0.22:
            p = 1 - left / 0.22; ang = rnd.uniform(0, 2 * math.pi)
            cx += math.cos(ang) * 500 * p * p; cy += math.sin(ang) * 500 * p * p
        d2.text((cx, cy), ch, font=f, fill=(255, 255, 255, 255))


def bolt(frame, t0, t, seed):
    """Procedural lightning: a jagged bolt with glow plus a blue-white wash, flickering twice."""
    a = t - t0
    if not (0 <= a < 0.3) or (0.08 < a < 0.14): return
    rnd = random.Random(seed + int(a > 0.14))
    pts = [(rnd.uniform(200, 880), -20)]
    while pts[-1][1] < H * 0.85:
        x, y = pts[-1]; pts.append((x + rnd.uniform(-90, 90), y + rnd.uniform(60, 140)))
    layer = Image.new("RGBA", frame.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.line(pts, fill=(170, 200, 255, 255), width=26); glow = layer.filter(ImageFilter.GaussianBlur(22))
    d2 = ImageDraw.Draw(layer); d2.line(pts, fill=(255, 255, 255, 255), width=8)
    wash = Image.new("RGBA", frame.size, (200, 215, 255, int(130 * (1 - a / 0.3))))
    frame.alpha_composite(wash); frame.alpha_composite(glow); frame.alpha_composite(glow); frame.alpha_composite(layer)


# ------------------------------------------------------------------ pictures
_IMG = {}


def picture(key, spec, grade):
    ck = (key, grade)
    if ck not in _IMG:
        im, used = fetch_image(spec)
        im = ImageEnhance.Color(im).enhance(1.35); im = ImageEnhance.Contrast(im).enhance(1.12)
        if grade == "red": im = Image.blend(im, Image.new("RGB", im.size, (170, 0, 0)), 0.35)
        if grade == "dark": im = ImageEnhance.Brightness(im).enhance(0.55)
        _IMG[ck] = (im, used)
    return _IMG[ck][0]


_RGBA = {}


def picture_rgba(key, spec):
    if key not in _RGBA:
        u = spec["url"]; p = os.path.join(CACHE, "img", hashlib.sha1(u.encode()).hexdigest()[:16])
        picture(key, spec, None)
        im = Image.open(p).convert("RGBA")
        if im.getchannel("A").getextrema()[0] == 255:  # no transparency: knock out a near-white background
            a = np.asarray(im).copy(); white = (a[..., :3].min(-1) > 238); a[white, 3] = 0; im = Image.fromarray(a)
        _RGBA[key] = im
    return _RGBA[key]


def cover(im, zoom, dx, dy, focus=(0.5, 0.5)):
    """Fill 1080x1920 from any aspect, zoomed and drifted around a focus point (0..1)."""
    s = max(W / im.width, H / im.height) * zoom
    cw, ch = W / s, H / s
    fx = min(max(focus[0] * im.width, cw / 2), im.width - cw / 2); fy = min(max(focus[1] * im.height, ch / 2), im.height - ch / 2)
    cx = fx + dx * min(fx - cw / 2, im.width - cw / 2 - fx) * 0.6; cy = fy + dy * min(fy - ch / 2, im.height - ch / 2 - fy) * 0.6
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=box)


def base_frame(ev, spec, t, fire, boom_frames, booms):
    a = t - ev["t"]; im = picture(ev["key"], spec, ev["grade"]); foc = tuple(spec.get("focus", (0.5, 0.5)))
    drift = 1.06 + 0.05 * min(a / 3.0, 1)                                         # a slow push; the snaps and stickers do the moving
    dx, dy = 0.0, 0.0
    if ev["fit"] == "white":
        card = picture_rgba(ev["key"], spec); sc0 = min(W * 0.8 / card.width, H * 0.5 / card.height)
        fr = Image.new("RGBA", (W, H), (250, 250, 250, 255))
        rot = (1 - ease(a / 0.3, 1.2)) * 300 if ev["enter"] == "spin" and a < 0.3 else 3 * math.sin(a * 2.2)
        paste(fr, card, W / 2, H * 0.46, sc0 * drift * (ease(a / 0.3, 1.4) if ev["enter"] == "spin" else 1), rot)
        frame = fr.convert("RGB")
    elif ev["fit"] in ("band", "spin_in"):
        bg = Image.fromarray(fire[int(t * FPS) % len(fire)]).resize((W, H), Image.BILINEAR).convert("RGB")
        card = im.copy(); sc0 = min(W * 1.02 / card.width, H * 0.62 / card.height); card = card.resize((int(card.width * sc0), int(card.height * sc0)))
        sc = drift * (ease(a / 0.3, 1.4) if ev["enter"] == "spin" else 1)
        rot = (1 - ease(a / 0.3, 1.2)) * 300 if ev["enter"] == "spin" else 4 * math.sin(a * 2)
        fr = bg.convert("RGBA"); paste(fr, card.convert("RGBA"), W / 2, H * 0.47, sc, rot); frame = fr.convert("RGB")
    else:
        z = drift * ev["zoom"] * spec.get("zoom", 1.0)
        if ev["enter"] == "zoomblur" and a < 0.2:
            p = 1 - a / 0.2
            layers = [np.asarray(cover(im, z * (1 + 0.45 * p + 0.1 * k * p), dx, dy, foc), np.float32) for k in range(4)]
            frame = Image.fromarray((sum(layers) / 4).astype(np.uint8))
        elif ev["enter"] == "whip" and a < 0.16:
            p = 1 - a / 0.16; base = cover(im, z, dx, dy, foc); arr = np.asarray(base, np.float32)
            shifts = [int(W * p * 0.9) - k * 40 for k in range(5)]
            frame = Image.fromarray((sum(np.roll(arr, s_, axis=1) for s_ in shifts) / 5).astype(np.uint8))
        elif ev["enter"] == "spin" and a < 0.3:
            fr = cover(im, z, dx, dy, foc).convert("RGBA"); bgc = Image.new("RGBA", (W, H), (10, 10, 12, 255))
            paste(bgc, fr, W / 2, H / 2, max(0.05, ease(a / 0.3, 1.4)), (1 - ease(a / 0.3, 1.2)) * 300); frame = bgc.convert("RGB")
        else:
            frame = cover(im, z, dx, dy, foc)
    arr = np.asarray(frame, np.float32) / 255
    if fire is not None:
        fl = fire[int(t * FPS) % len(fire)].astype(np.float32) / 255
        fl = np.asarray(Image.fromarray((fl * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255
        arr = screen(arr * np.array([1.0, 0.9, 0.8]), fl * FIRE_MASK, 0.95)
    for b0 in booms:
        k = int((t - b0) * FPS)
        if 0 <= k < len(boom_frames):
            bf = np.asarray(Image.fromarray(boom_frames[k]).resize((W, H), Image.BILINEAR), np.float32) / 255
            arr = screen(arr, bf, 0.9)
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).convert("RGBA")


def caption(frame, text, a):
    f = font(FONT_CAP, 86)
    pop = 0.9 + 0.1 * ease(a / 0.07, 2)
    layer = Image.new("RGBA", (1000, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.text((500, 118), text, font=f, fill=(0, 0, 0, 200), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 200))
    sh = layer.filter(ImageFilter.GaussianBlur(6))
    top = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(top).text((500, 110), text, font=f, fill=(255, 255, 255, 255), anchor="mm", stroke_width=3, stroke_fill=(20, 20, 20, 255))
    sh.alpha_composite(top)
    paste(frame, sh, W / 2, 1000, pop)


# ------------------------------------------------------------------ the frame
class Shaker:
    """Snap shake, measured frame by frame on the original Tung (reference/TUNG_BREAKDOWN.md, shake section).
    An 8-frame cycle (0.27 s): a few frames of hard snaps to a random offset, mostly sideways, then dead still.
    Normal shots: 3 of 8 frames snap, about 13 px. Hits (name, flash, slam): 4 of 8, about 22 px.
    No rotation and no easing: Tung never rotates and never glides. Applied last, so captions shake too."""
    CYCLE = 8

    def __init__(self, hits):
        self.hits = sorted(hits); self.rng = np.random.default_rng(4); self.f = 0

    def step(self, t):
        f = self.f; self.f += 1
        hot = any(0 <= t - h < 0.45 for h in self.hits)
        on = 3 if hot else 2
        if f % self.CYCLE >= on:
            return 0.0, 0.0, 0.0                       # the hold: dead still
        amp = 17.0 if hot else 12.0
        x = self.rng.choice([-1, 1]) * amp * self.rng.uniform(0.6, 1.4)
        y = self.rng.choice([-1, 1]) * amp * self.rng.uniform(0.0, 0.6) if self.rng.random() < 0.5 else 0.0
        return float(x), float(y), 0.0


def render_frame(ep, tl, t, shaker, fire, boom_frames):
    cur = None
    for ev in tl["img"]:
        if ev["t"] <= t: cur = ev
    on_fire = any(a <= t < b for a, b in tl["fire"])
    frame = base_frame(cur, ep["images"][cur["key"]], t, fire if on_fire or cur["fit"] in ("band", "spin_in") else None,
                       boom_frames, tl["boom"]) if on_fire or cur["fit"] in ("band", "spin_in") else \
        base_frame(cur, ep["images"][cur["key"]], t, None, boom_frames, tl["boom"])
    for s in tl["sticker"]:
        if s["t"] <= t < s["end"]: draw_sticker(frame, s, t)
    for lab in tl["label"]:
        later = [o for o in tl["label"] if lab["t"] < o["t"] <= t]
        if lab["t"] <= t < lab["end"] and not later: draw_label(frame, lab, t)
    for i, lt in enumerate(tl["lightning"]): bolt(frame, lt, t, i * 31)
    for c0, c1, text in tl["caption"]:
        if c0 <= t < c1: caption(frame, text, t - c0)
    for fl in tl["flash"]:
        if 0 <= t - fl < 0.1: frame.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(255 * (1 - (t - fl) / 0.1)))))
    dx, dy, rot = shaker.step(t)
    dx, dy = int(round(dx)), int(round(dy))
    if dx == 0 and dy == 0: return frame
    # snap: shift the whole frame by whole pixels, fill the exposed strip by stretching the edge (no black bars)
    pad = Image.new("RGBA", (W, H)); pad.paste(frame.resize((int(W * 1.07), int(H * 1.07)), Image.BILINEAR).crop((38, 67, 38 + W, 67 + H)))
    out = Image.new("RGBA", (W, H)); out.paste(pad, (int(dx), int(dy)))
    if dx > 0: out.paste(pad.crop((0, 0, 1, H)).resize((int(dx) + 1, H)), (0, int(dy)))
    if dx < 0: out.paste(pad.crop((W - 1, 0, W, H)).resize((int(-dx) + 1, H)), (W + int(dx) - 1, int(dy)))
    if dy > 0: out.paste(out.crop((0, int(dy), W, int(dy) + 1)).resize((W, int(dy))), (0, 0))
    if dy < 0: out.paste(out.crop((0, H + int(dy) - 1, W, H + int(dy))).resize((W, int(-dy))), (0, H + int(dy)))
    return out


# ------------------------------------------------------------------ sound effects (all synthesized)
def _lp(x, k):
    ks = np.broadcast_to(np.asarray(k, np.float64), x.shape)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += ks[i] * (x[i] - acc); y[i] = acc
    return y


def sfx(name, var=0):
    rng = np.random.default_rng(var + 3)
    def T(d): return np.arange(int(SR * d)) / SR
    def env(t, a, d): return np.minimum(t / a, 1) * np.exp(-t / d)
    if name in ("boom", "impact"):
        t = T(0.9 if name == "boom" else 0.5); f = 75 * np.exp(-t * 6) + 30
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.002, 0.35 if name == "boom" else 0.15)
        crack = _lp(rng.standard_normal(len(t)), 0.5 if name == "impact" else 0.08) * env(t, 0.001, 0.05 if name == "impact" else 0.15)
        return np.tanh((body * 1.2 + crack * 1.5) * 1.6) * 0.9
    if name in ("whoosh", "whip", "spin"):
        d = {"whoosh": 0.35, "whip": 0.18, "spin": 0.45}[name]; t = T(d)
        n = rng.standard_normal(len(t)); hp = n - _lp(n, 0.05); x = _lp(hp, 0.25 if name != "whip" else 0.45)
        e = np.sin(np.pi * t / t[-1]) ** (2 if name != "whip" else 4)
        out = x * e * 1.4
        if name == "spin": out += np.sin(2 * np.pi * np.cumsum(300 + 900 * t / d) / SR) * e * 0.25
        return out
    if name == "pop":
        t = T(0.09); return np.sin(2 * np.pi * (700 - 3000 * t) * t) * env(t, 0.001, 0.03) * 0.7
    if name == "heartpop":
        t = T(0.35); return (np.sin(2 * np.pi * (500 + 900 * t) * t) * env(t, 0.001, 0.05) * 0.6 +
                             sum(np.sin(2 * np.pi * f * t) * env(t, 0.002, 0.18) for f in (1568, 2093)) * 0.18)
    if name == "ding":
        t = T(0.6); return sum(np.sin(2 * np.pi * f * t) * env(t, 0.002, 0.25) / (i + 1) for i, f in enumerate((1318, 2637, 3951))) * 0.45
    if name == "scribble":
        t = T(0.3); n = _lp(rng.standard_normal(len(t)), 0.35); am = 0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)
        return n * am * env(t, 0.01, 0.2) * 1.1
    if name == "alarm":
        t = T(0.5); sq = np.sign(np.sin(2 * np.pi * 880 * t)) * 0.3
        return sq * ((t % 0.25) < 0.12) * np.exp(-t * 2)
    if name == "boing":
        t = T(0.4); f = 220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 6)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(t, 0.002, 0.18) * 0.6
    if name == "zap":
        t = T(0.4); n = rng.standard_normal(len(t)); crackle = n * (rng.random(len(t)) < 0.08)
        return (crackle * 2.0 + (n - _lp(n, 0.2)) * 0.6) * env(t, 0.001, 0.15)
    if name == "riser":
        t = T(1.0); n = rng.standard_normal(len(t)); x = n - _lp(n, 0.02 + 0.3 * t)
        return (x * 0.5 + np.sin(2 * np.pi * np.cumsum(200 + 1400 * t ** 2) / SR) * 0.3) * (t / t[-1]) ** 2
    if name == "typing":
        out = np.zeros(int(SR * 0.45))
        for k in range(9):
            i = int(k * 0.045 * SR); c = rng.standard_normal(200) * np.exp(-np.arange(200) / 30)
            out[i:i + 200] += c * 0.5
        return out
    raise KeyError(name)


KIT = {  # event -> myinstants files in .cache/sfx (sources in .cache/sfx/sources.txt, copied to the manifest)
    "whoosh": ["fast_whoosh_1", "whoosh", "anime_whoosh"], "whip": ["fast_whoosh_1", "whoosh"], "spin": ["whoosh"],
    "pop": ["pop"], "boom": ["explosion_2"], "impact": ["vine_boom"], "scribble": ["pop"], "whipstk": ["fast_whoosh_1"],
    "heartpop": ["sparkle_1"], "alarm": ["huh_2"], "boing": ["huh_3", "huh_1"], "x": ["error", "bonk"], "ding": ["notification_1"],
    "typing": ["notification_1"], "zap": ["lightning_2"], "riser": ["riser"], "glitch": ["glitch_1"], "wow": ["anime_wow"],
    "mcboom": ["explosion_3"], "reveal": ["bruh_sound_effect_3"],
}
GAIN = {"boom": 0.45, "whoosh": 0.5, "whip": 0.5, "spin": 0.5, "pop": 0.6, "impact": 0.9, "zap": 0.6, "riser": 0.6, "wow": 0.7,
        "alarm": 0.7, "x": 0.8, "heartpop": 0.5, "ding": 0.6, "typing": 0.5, "scribble": 0.4, "boing": 0.8, "mcboom": 0.8, "reveal": 0.9}
MAXLEN = {"zap": 1.6, "riser": 1.2, "wow": 1.4, "heartpop": 0.9, "ding": 0.6, "alarm": 1.2, "x": 0.9, "reveal": 1.8, "mcboom": 1.6}
_KIT = {}


def kit_sound(name, var):
    files = KIT.get(name)
    if not files: return None
    f = files[var % len(files)]
    if f not in _KIT:
        p = os.path.join(CACHE, "sfx", f + ".mp3")
        if not os.path.exists(p): return None
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, np.float32).copy()
        idx = np.where(np.abs(a) > 0.02)[0]
        if len(idx): a = a[max(0, idx[0] - 50):]
        n = int(MAXLEN.get(name, 1.0) * SR)
        if len(a) > n: a = a[:n]; a[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))
        a /= max(1e-6, np.abs(a).max())
        _KIT[f] = a
    return _KIT[f]


def mix(slug, tl, dur):
    od = os.path.join(REPO, "out", slug)
    v, vsr = sf.read(os.path.join(od, "voice.wav"), dtype="float32")
    v = np.interp(np.arange(0, len(v), vsr / SR), np.arange(len(v)), v).astype(np.float32)
    n = int(dur * SR) + SR; out = np.zeros(n, np.float32); out[:len(v)] += v * 1.0
    count = {}
    for t, name in sorted(tl["sfx"]):
        count[name] = count.get(name, 0) + 1
        smp = kit_sound(name, count[name])
        s = (smp * GAIN.get(name, 0.6)) if smp is not None else sfx(name, count[name] % 3).astype(np.float32) * 0.42
        i = int(max(0.0, t) * SR); seg = s[: max(0, n - i)]
        out[i:i + len(seg)] += seg
    out = out[: int(dur * SR)]
    p = os.path.join(od, "mix.wav"); sf.write(p, out, SR)
    return p, sum(count.values())


def manifest(slug, ep):
    m = {"slug": slug, "images": {}, "stock": {k: f"https://mixkit.co (Mixkit free licence) {v[0]}" for k, v in STOCK.items()},
         "sfx": open(os.path.join(CACHE, "sfx", "sources.txt")).read().splitlines() if os.path.exists(os.path.join(CACHE, "sfx", "sources.txt")) else "synthesized", "name_bites": {n: c.get("bite") or "placeholder (synthetic)" for n, c in ep["names"].items()}}
    for k, spec in ep["images"].items():
        used = _IMG.get((k, None), _IMG.get((k, "red"), _IMG.get((k, "dark"), (None, spec["url"]))))[1]
        m["images"][k] = {"used": used, "page": spec.get("page", used), "rights": "third-party; shown under narration as commentary"}
    json.dump(m, open(os.path.join(ROOT, "episodes", slug, "manifest.json"), "w"), indent=1)


def main(slug, preview=False):
    ep = json.load(open(os.path.join(ROOT, "episodes", slug, "episode.json")))
    wj = json.load(open(os.path.join(REPO, "out", slug, "words.json")))
    tl = build(ep, wj["words"])
    dur = round(wj["duration"] + 0.25, 3)
    fire = stock_frames("fire"); boom_frames = stock_frames("boom")
    shaker = Shaker([s["t"] for s in tl["sticker"] if s["kind"] in ("x",)] + tl["flash"] + tl["boom"] +
                    [e["t"] for e in tl["img"] if e["enter"] in ("whip", "zoomblur")])
    audio, n_sfx = mix(slug, tl, dur)
    od = os.path.join(REPO, "out", slug)
    outp = os.path.join(od, f"{slug}{'-preview' if preview else ''}.mp4")
    size = (540, 960) if preview else (W, H)
    af = "acompressor=threshold=-24dB:ratio=8:attack=2:release=50:makeup=12,alimiter=limit=0.89:attack=1:release=30:level=false"  # about -9.7 LUFS, Tung is -8
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(FPS),
           "-i", "-", "-i", audio, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", outp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(dur * FPS)
    for i in range(nf):
        f = render_frame(ep, tl, i / FPS, shaker, fire, boom_frames).convert("RGB")
        if preview: f = f.resize(size, Image.BILINEAR)
        proc.stdin.write(f.tobytes())
        if i % 150 == 0: print(f"  frame {i}/{nf}", flush=True)
    proc.stdin.close(); proc.wait()
    manifest(slug, ep)
    print(f"wrote {outp}  ({dur:.2f} s, {n_sfx} sound effects, {len(tl['boom'])} name bites)")


if __name__ == "__main__":
    main(sys.argv[1], "--preview" in sys.argv)
