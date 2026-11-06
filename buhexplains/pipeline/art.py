"""In-house art library. Everything here is drawn in code: no third-party images, textures or logos.

Each function returns an RGBA PIL image, with the subject roughly filling a square of `s` px.
Plates (full-frame backgrounds) are drawn per frame by `plate(name, t)`.
"""
import math, os, random
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts", "archivo-black", "ArchivoBlack-Regular.ttf")
YEL, INK, RED, WHITE = (255, 214, 10, 255), (18, 14, 12, 255), (226, 24, 24, 255), (255, 255, 255, 255)


def font(px):
    return ImageFont.truetype(FONT, px)


def canvas(s):
    return Image.new("RGBA", (s, s), (0, 0, 0, 0))


def outlined(img, width=10, color=(0, 0, 0, 255)):
    """A sticker look: a solid outline around the alpha shape, plus a hard drop shadow."""
    a = img.split()[3]
    grown = a.filter(ImageFilter.MaxFilter(width * 2 + 1))
    out = Image.new("RGBA", (img.width + 40, img.height + 40), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 160)); out.paste(shadow, (34, 34), grown)
    edge = Image.new("RGBA", img.size, color); out.paste(edge, (20, 20), grown)
    out.alpha_composite(img, (20, 20))
    return out


def face(d, cx, cy, r, mood="smile"):
    ew, eh = r * 0.13, r * 0.30
    for sx in (-1, 1):
        x = cx + sx * r * 0.36
        d.ellipse([x - ew, cy - r * 0.38 - eh, x + ew, cy - r * 0.38 + eh], fill=INK)
    w = r * 0.62
    if mood == "smile":
        d.arc([cx - w, cy - r * 0.55, cx + w, cy + r * 0.62], 20, 160, fill=INK, width=int(r * 0.09))
    else:  # too-wide grin
        d.chord([cx - r * 0.75, cy - r * 0.1, cx + r * 0.75, cy + r * 0.72], 0, 180, fill=INK)
        for k in range(-3, 4):
            x = cx + k * r * 0.17
            d.rectangle([x - r * 0.06, cy + r * 0.24, x + r * 0.06, cy + r * 0.36], fill=WHITE)


@lru_cache(None)
def smiley(s=820, mood="smile"):
    im = canvas(s); d = ImageDraw.Draw(im); r = s * 0.46
    d.ellipse([s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r], fill=YEL, outline=INK, width=int(s * 0.025))
    face(d, s / 2, s / 2, r, mood)
    return outlined(im)


@lru_cache(None)
def smiley_grid(s=900):
    im = canvas(s); rnd = random.Random(3)
    for row in range(4):
        for col in range(3):
            sm = smiley(260).rotate(rnd.uniform(-25, 25), expand=False)
            im.alpha_composite(sm, (col * 290 + 10, row * 220 - 40 + (col % 2) * 60))
    return im


@lru_cache(None)
def smiley_flood(s=1000):
    im = canvas(s); rnd = random.Random(7)
    for _ in range(26):
        k = rnd.randint(140, 300)
        sm = smiley(k).rotate(rnd.uniform(-40, 40), expand=True)
        im.alpha_composite(sm, (rnd.randint(-60, s - k), rnd.randint(-60, s - k)))
    return im


@lru_cache(None)
def smiley_wave(s=860):
    im = canvas(s); base = smiley(620); im.alpha_composite(base, (60, 140))
    d = ImageDraw.Draw(im)  # a little white glove waving
    d.ellipse([650, 120, 820, 290], fill=WHITE, outline=INK, width=12)
    for k in range(4):
        d.rounded_rectangle([660 + k * 38, 40 + abs(k - 1.5) * 18, 690 + k * 38, 170], 14, fill=WHITE, outline=INK, width=10)
    return im


@lru_cache(None)
def tall_smiley(s=1500):
    im = Image.new("RGBA", (900, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    body = (24, 22, 26, 255)
    d.rectangle([380, 420, 520, s - 40], fill=body)                      # thin torso and legs
    d.polygon([(380, 520), (120, 1050), (150, 1070), (400, 600)], fill=body)  # arms far too long
    d.polygon([(520, 520), (790, 1060), (760, 1080), (500, 600)], fill=body)
    head = smiley(440, "grin"); im.alpha_composite(head, (230, 0))
    return im.filter(ImageFilter.GaussianBlur(0.6))


@lru_cache(None)
def red_x(s=600):
    im = canvas(s); d = ImageDraw.Draw(im); w = int(s * 0.16)
    d.line([s * 0.12, s * 0.12, s * 0.88, s * 0.88], fill=RED, width=w)
    d.line([s * 0.88, s * 0.12, s * 0.12, s * 0.88], fill=RED, width=w)
    return outlined(im, 8)


@lru_cache(None)
def heart(s=300):
    im = canvas(s); d = ImageDraw.Draw(im)
    pts = []
    for k in range(200):  # the classic parametric heart curve
        t = k / 200 * 2 * math.pi
        x = 16 * math.sin(t) ** 3; y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((s / 2 + x * s / 36, s * 0.46 - y * s / 36))
    d.polygon(pts, fill=RED)
    return outlined(im, 8)


@lru_cache(None)
def interrobang(s=320):
    im = canvas(s); d = ImageDraw.Draw(im)
    d.text((s / 2, s / 2), "!?", font=font(int(s * 0.8)), fill=RED, anchor="mm", stroke_width=10, stroke_fill=INK)
    return im


@lru_cache(None)
def warning(s=300):
    im = canvas(s); d = ImageDraw.Draw(im)
    d.polygon([(s / 2, s * 0.06), (s * 0.96, s * 0.92), (s * 0.04, s * 0.92)], fill=YEL, outline=INK, width=14)
    d.text((s / 2, s * 0.62), "!", font=font(int(s * 0.55)), fill=INK, anchor="mm")
    return outlined(im, 6)


@lru_cache(None)
def circus_tent(s=860):
    im = canvas(s); d = ImageDraw.Draw(im)
    top, base, l, r = s * 0.12, s * 0.5, s * 0.08, s * 0.92
    for k in range(8):  # striped roof
        x0, x1 = l + (r - l) * k / 8, l + (r - l) * (k + 1) / 8
        d.polygon([(s / 2, top), (x0, base), (x1, base)], fill=RED if k % 2 else WHITE)
    for k in range(8):  # striped walls
        x0, x1 = s * 0.14 + s * 0.72 * k / 8, s * 0.14 + s * 0.72 * (k + 1) / 8
        d.rectangle([x0, base, x1, s * 0.9], fill=WHITE if k % 2 else RED)
    d.polygon([(s / 2, s * 0.62), (s * 0.4, s * 0.9), (s * 0.6, s * 0.9)], fill=INK)
    d.line([s / 2, top, s / 2, s * 0.02], fill=INK, width=10)
    d.polygon([(s / 2, s * 0.02), (s * 0.64, s * 0.06), (s / 2, s * 0.1)], fill=YEL)
    return outlined(im)


@lru_cache(None)
def tophat(s=860):
    """A generic shadow figure in a top hat, with a '?' for a face. Not anyone's character art."""
    im = canvas(s); d = ImageDraw.Draw(im); g = (60, 58, 70, 255)
    d.ellipse([s * 0.3, s * 0.3, s * 0.7, s * 0.66], fill=g)
    d.rectangle([s * 0.34, s * 0.04, s * 0.66, s * 0.3], fill=INK)
    d.rectangle([s * 0.22, s * 0.27, s * 0.78, s * 0.33], fill=INK)
    d.rectangle([s * 0.34, s * 0.22, s * 0.66, s * 0.26], fill=RED)
    d.polygon([(s * 0.3, s * 0.98), (s * 0.4, s * 0.64), (s * 0.6, s * 0.64), (s * 0.7, s * 0.98)], fill=g)
    d.text((s / 2, s * 0.48), "?", font=font(int(s * 0.26)), fill=WHITE, anchor="mm")
    return outlined(im)


@lru_cache(None)
def film_reel(s=800):
    im = canvas(s); d = ImageDraw.Draw(im); c, r = s / 2, s * 0.44
    d.ellipse([c - r, c - r, c + r, c + r], fill=(70, 70, 78, 255), outline=INK, width=14)
    for k in range(6):
        a = k * math.pi / 3
        x, y = c + math.cos(a) * r * 0.55, c + math.sin(a) * r * 0.55
        d.ellipse([x - r * 0.2, y - r * 0.2, x + r * 0.2, y + r * 0.2], fill=INK)
    d.ellipse([c - r * 0.12, c - r * 0.12, c + r * 0.12, c + r * 0.12], fill=(200, 200, 205, 255))
    return outlined(im)


@lru_cache(None)
def paperclip(s=800):
    im = canvas(s); d = ImageDraw.Draw(im); col, w = (190, 196, 206, 255), 34
    d.rounded_rectangle([s * 0.3, s * 0.06, s * 0.7, s * 0.94], radius=int(s * 0.2), outline=col, width=w)
    d.rounded_rectangle([s * 0.38, s * 0.2, s * 0.62, s * 0.84], radius=int(s * 0.12), outline=col, width=w)
    d.rectangle([s * 0.36, s * 0.5, s * 0.64, s * 0.96], fill=(0, 0, 0, 0))
    d.line([s * 0.38, s * 0.5, s * 0.38, s * 0.8], fill=col, width=w)
    for sx in (-1, 1):  # googly eyes
        x = s * 0.5 + sx * s * 0.07
        d.ellipse([x - 40, s * 0.3, x + 40, s * 0.4], fill=WHITE, outline=INK, width=8)
        d.ellipse([x - 14, s * 0.34, x + 14, s * 0.39], fill=INK)
    return outlined(im)


@lru_cache(None)
def grass_block(s=820):
    """An isometric voxel grass block, drawn pixel by pixel here (not Mojang's texture)."""
    n = 16; rnd = np.random.default_rng(5)
    def tex(kind):
        t = np.zeros((n, n, 3), np.uint8)
        for y in range(n):
            for x in range(n):
                v = rnd.integers(-14, 15)
                if kind == "top" or (kind == "side" and y < 3 + (x * 7 % 3)):
                    t[y, x] = np.clip([96 + v, 168 + v, 62 + v], 0, 255)
                else:
                    t[y, x] = np.clip([134 + v, 96 + v, 66 + v], 0, 255)
        return Image.fromarray(t).resize((256, 256), Image.NEAREST).convert("RGBA")
    top, side = tex("top"), tex("side")
    im = canvas(s); u = s * 0.42; cx, cy = s / 2, s * 0.3
    def warp(src, quad, shade):
        src = Image.eval(src, lambda p: int(p * shade))
        (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad  # tl, tr, br, bl
        coeffs = _persp([(0, 0), (256, 0), (256, 256), (0, 256)], quad)
        layer = src.transform((s, s), Image.PERSPECTIVE, coeffs, Image.NEAREST)
        mask = Image.new("L", (s, s), 0); ImageDraw.Draw(mask).polygon(quad, fill=255)
        im.paste(layer, (0, 0), mask)
    T = (cx, cy - u * 0.5); R = (cx + u, cy); B = (cx, cy + u * 0.5); L = (cx - u, cy)
    drop = u * 1.15
    warp(top, [T, R, B, L], 1.0)
    warp(side, [L, B, (B[0], B[1] + drop), (L[0], L[1] + drop)], 0.82)
    warp(side, [B, R, (R[0], R[1] + drop), (B[0], B[1] + drop)], 0.62)
    return outlined(im, 8)


def _persp(src, dst):
    """Coefficients mapping output (dst) points back to input (src) points, for Image.transform."""
    A, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]; b += [u, v]
    return np.linalg.solve(np.array(A, float), np.array(b, float)).tolist()


@lru_cache(None)
def smiley_on_block(s=900):
    im = canvas(s); im.alpha_composite(grass_block(700), (100, 330)); im.alpha_composite(smiley(420), (240, 40))
    return im


def card(lines, s=900, sub=None, accent=RED):
    im = canvas(s); d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, s * 0.28, s - 20, s * 0.72], radius=40, fill=WHITE, outline=INK, width=14)
    d.rectangle([20, s * 0.28, 70, s * 0.72], fill=accent)
    px = int(s * 0.1)
    while px > 20 and d.textlength(lines, font=font(px)) > s - 160:
        px -= 4
    d.text((s / 2 + 20, s * 0.47), lines, font=font(px), fill=INK, anchor="mm")
    if sub:
        d.text((s / 2 + 20, s * 0.6), sub, font=font(int(s * 0.045)), fill=(90, 90, 90, 255), anchor="mm")
    return outlined(im, 6)


@lru_cache(None)
def song_card(s=900):
    im = card("IT'S ME, IT'S VERITY", s, "the song, July 2026")
    d = ImageDraw.Draw(im)
    d.text((s * 0.5, s * 0.18), "♫", font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 200) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") else font(160), fill=YEL, anchor="mm", stroke_width=10, stroke_fill=INK)
    return im


@lru_cache(None)
def name_card(s=900):
    return card("THATMOB", s, "the YouTuber who made Verity")


ART = {f.__name__: f for f in [smiley, smiley_grid, smiley_flood, smiley_wave, tall_smiley, red_x, heart, interrobang,
                                warning, circus_tent, tophat, film_reel, paperclip, grass_block, smiley_on_block,
                                song_card, name_card]}


def get(name, size=None):
    f = ART[name]
    return f(size) if size else f()


# ---------------------------------------------------------------- plates (full-frame backgrounds)
_rng = np.random.default_rng(11)
_NOISE = _rng.random((64, 270)).astype(np.float32)


def _fire_rgb(heat):
    r = np.clip(heat * 3.0, 0, 1); g = np.clip(heat * 3.0 - 1.0, 0, 1); b = np.clip(heat * 3.0 - 2.2, 0, 1)
    return np.stack([r * 255, g * 230, b * 160], -1)


@lru_cache(64)
def _fire_frame(k):
    """Two flame bands (top and bottom) on dark red, the BuhExplains fire plate. 1/4 res, upscaled."""
    w, h = 270, 480
    x = np.arange(w)[None, :]; y = np.arange(h)[:, None].astype(np.float32)
    t = k / 12.0
    flick = (np.sin(x * 0.21 + t * 9) + np.sin(x * 0.067 - t * 6.3) + np.sin(x * 0.43 + t * 13)) / 3
    rows = _NOISE[(np.arange(h)[:, None] + k * 3) % 64, x % 270]
    reach = 120 + 34 * flick
    bot = np.clip(1 - (h - y) / reach, 0, 1) ** 1.4 * (0.75 + 0.5 * rows)
    top = np.clip(1 - y / (reach * 0.8), 0, 1) ** 1.6 * (0.7 + 0.5 * rows)
    heat = np.clip(np.maximum(bot, top), 0, 1)
    rgb = _fire_rgb(heat)
    base = np.array([60, 6, 4], np.float32)
    rgb = np.maximum(rgb, base)
    img = Image.fromarray(rgb.astype(np.uint8)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3))
    return img.convert("RGBA")


@lru_cache(8)
def _speedlines(k):
    im = Image.new("RGBA", (W, H), (245, 245, 245, 255)); d = ImageDraw.Draw(im); rnd = random.Random(k)
    for _ in range(140):
        a = rnd.uniform(0, 2 * math.pi); r0 = rnd.uniform(380, 620); w = rnd.uniform(0.004, 0.02)
        cx, cy = W / 2, H / 2
        d.polygon([(cx + math.cos(a - w) * 2000, cy + math.sin(a - w) * 2000), (cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                   (cx + math.cos(a + w) * 2000, cy + math.sin(a + w) * 2000)], fill=(20, 20, 20, 255))
    return im


@lru_cache(1)
def _vignette():
    y, x = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
    r = np.hypot((x - W / 8) / (W / 8), (y - H / 8) / (H / 8))
    v = np.clip(1 - r * 0.75, 0, 1)
    rgb = np.stack([110 * v + 20, 8 * v, 10 * v], -1).astype(np.uint8)
    return Image.fromarray(rgb).resize((W, H), Image.BILINEAR).convert("RGBA")


def plate(name, t):
    if name == "fire": return _fire_frame(int(t * 24) % 48)
    if name == "speedlines": return _speedlines(int(t * 12) % 4)
    if name == "vignette": return _vignette()
    if name == "white": return Image.new("RGBA", (W, H), WHITE)
    return Image.new("RGBA", (W, H), (8, 8, 10, 255))


@lru_cache(1)
def fireball():
    s = 1400; y, x = np.mgrid[0:s // 4, 0:s // 4].astype(np.float32)
    c = s / 8; r = np.hypot(x - c, y - c) / c
    ang = np.arctan2(y - c, x - c)
    edge = 0.78 + 0.16 * np.sin(ang * 9) + 0.08 * np.sin(ang * 23 + 1)
    heat = np.clip(1.15 - r / edge, 0, 1)
    rgb = _fire_rgb(heat * 1.1)
    a = (np.clip(heat * 4, 0, 1) * 255)
    img = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA").resize((s, s), Image.BILINEAR)
    return img.filter(ImageFilter.GaussianBlur(4))
