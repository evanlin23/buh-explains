"""HelloBuh edit: game footage -> 1080x1920 Short with the black caption band and a drawn HUD.

  python3 edit.py --video in.mp4 | --frames 'dir/f%04d.jpg' --fps 26
                  --caption "water bucket clutch 💀" [--red WORD]
                  [--timeline timeline.json] [--audio game.wav] [--hud/--no-hud]
                  --out out.mp4

Layout (measured from research/cover-frames.jpg): black band on top (~23% of the height) with a
white bold centered caption; gameplay fills the rest, center-cropped. The HUD (hotbar, hearts,
food) is drawn from the client jar's own GUI sprites at GUI scale 3, because the renderers we
use either don't draw it (prismarine-viewer) or we choose to keep it consistent. The slot
highlight and the bucket item follow the bot's timeline. Audio is loudness-normalized to about
-18 LUFS so a library song added at upload has headroom. No music is ever added here.
"""
import argparse
import io
import json
import pathlib
import subprocess
import tempfile
import urllib.request
import zipfile

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
W, H, BAND = 1080, 1920, 440
GAME_H = H - BAND
GUI = 3  # Minecraft GUI scale
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
TWEMOJI = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@15.1.0/assets/72x72/{}.png"
CLIENT_JAR = HERE / "work" / "client" / "versions" / "1.21.11.jar"
HOTBAR = ["item/diamond_sword", "item/water_bucket", "block/cobblestone", "item/bread", None, None, None, None, None]


def sprite(jar, path):
    with jar.open(f"assets/minecraft/textures/{path}.png") as f:
        im = Image.open(io.BytesIO(f.read())).convert("RGBA")
    return im.crop((0, 0, im.width, im.width)) if im.height > im.width * 2 else im  # animated strips: first frame


def big(im):
    return im.resize((im.width * GUI, im.height * GUI), Image.NEAREST)


def emoji_png(ch):
    code = "-".join(f"{ord(c):x}" for c in ch if ord(c) != 0xFE0F)
    cache = HERE / "work" / "emoji" / f"{code}.png"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(urllib.request.urlopen(TWEMOJI.format(code), timeout=30).read())
    return Image.open(cache).convert("RGBA")


def caption_png(text, red_word, path):
    """White bold caption, centered in the top band; emoji drawn from Twemoji, one word optionally red."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, BAND), fill=(0, 0, 0, 255))
    tokens = text.split(" ")
    def is_emoji(tok):
        return any(ord(c) > 0x2500 for c in tok)
    for size in range(96, 40, -2):  # largest size that fits in 90% of the width
        font = ImageFont.truetype(FONT, size)
        widths = [(size + 6) if is_emoji(t) else d.textlength(t, font=font) for t in tokens]
        space = d.textlength(" ", font=font)
        total = sum(widths) + space * (len(tokens) - 1)
        if total <= W * 0.9:
            break
    x, y = (W - total) / 2, BAND - 175
    for tok, w in zip(tokens, widths):
        if is_emoji(tok):
            e = emoji_png(tok).resize((size, size), Image.LANCZOS)
            img.alpha_composite(e, (int(x + 3), int(y + 4)))
        else:
            color = (235, 40, 40, 255) if red_word and tok.strip("?!.,").lower() == red_word.lower() else (255, 255, 255, 255)
            d.text((x, y), tok, font=font, fill=color)
        x += w + space
    img.save(path)


def hud_png(jar, slot, items, health, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bar = big(sprite(jar, "gui/sprites/hud/hotbar"))
    sel = big(sprite(jar, "gui/sprites/hud/hotbar_selection"))
    bx, by = (W - bar.width) // 2, H - bar.height - 8 * GUI
    img.alpha_composite(bar, (bx, by))
    for i, it in enumerate(items):
        if it:
            icon = big(sprite(jar, it))
            img.alpha_composite(icon, (bx + (3 + 20 * i) * GUI, by + 3 * GUI))
    img.alpha_composite(sel, (bx - GUI + 20 * GUI * slot, by - GUI))
    heart_c, heart = big(sprite(jar, "gui/sprites/hud/heart/container")), big(sprite(jar, "gui/sprites/hud/heart/full"))
    half = big(sprite(jar, "gui/sprites/hud/heart/half"))
    food_e, food = big(sprite(jar, "gui/sprites/hud/food_empty")), big(sprite(jar, "gui/sprites/hud/food_full"))
    hy = by - 10 * GUI
    for i in range(10):
        hx = bx + 8 * GUI * i
        img.alpha_composite(heart_c, (hx, hy))
        if health >= 2 * i + 2:
            img.alpha_composite(heart, (hx, hy))
        elif health >= 2 * i + 1:
            img.alpha_composite(half, (hx, hy))
        fx = bx + bar.width - 9 * GUI - 8 * GUI * i
        img.alpha_composite(food_e, (fx, hy))
        img.alpha_composite(food, (fx, hy))
    img.save(path)


def hud_states(timeline, duration):
    """[(t0, t1, slot, items, health)] from the bot timeline (ms since recording start)."""
    items = list(HOTBAR)
    slot, health = 0, 20
    states, last_t = [], 0.0
    for ev in timeline or []:
        t = ev["t"] / 1000
        new_items, new_slot, new_health = list(items), ev.get("slot", slot), ev.get("health", health)
        if ev["event"] == "placed":
            new_items[1] = "item/bucket"
        if ev["event"] == "scooped" and ev.get("ok"):
            new_items[1] = "item/water_bucket"
        if (new_items, new_slot, round(new_health)) != (items, slot, round(health)):
            states.append((last_t, t, slot, items, health))
            last_t, items, slot, health = t, new_items, new_slot, new_health
    states.append((last_t, duration + 1, slot, items, health))
    return states


def probe_duration(args):
    if args.video:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.video], capture_output=True, text=True).stdout
        return float(out)
    n = len(list(pathlib.Path(args.frames).parent.glob("*.jpg")))
    return n / args.fps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--frames")
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--out_fps", type=int, default=30)
    ap.add_argument("--caption", required=True)
    ap.add_argument("--red")
    ap.add_argument("--timeline")
    ap.add_argument("--audio")
    ap.add_argument("--hud", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--start", type=float, default=0.0, help="seconds to skip at the start of the footage")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="hb-edit-"))
    caption_png(args.caption, args.red, tmp / "caption.png")
    dur = probe_duration(args) - args.start
    inputs = (["-ss", str(args.start), "-i", args.video] if args.video else
              ["-framerate", str(args.fps), "-start_number", str(int(args.start * args.fps)), "-i", args.frames])
    inputs += ["-loop", "1", "-i", str(tmp / "caption.png")]
    graph = [f"[0:v]scale={W}:{GAME_H}:force_original_aspect_ratio=increase,crop={W}:{GAME_H},"
             f"pad={W}:{H}:0:{BAND}:black,fps={args.out_fps},format=rgba[g0]"]
    last = "g0"
    n_in = 2
    if args.hud:
        tl = json.loads(pathlib.Path(args.timeline).read_text())["timeline"] if args.timeline else []
        shift = args.start
        with zipfile.ZipFile(CLIENT_JAR) as jar:
            for k, (a, b, slot, items, health) in enumerate(hud_states(tl, dur + shift)):
                p = tmp / f"hud{k}.png"
                hud_png(jar, slot, items, health, p)
                inputs += ["-loop", "1", "-i", str(p)]
                graph.append(f"[{last}][{n_in}:v]overlay=0:0:enable='between(t,{max(0, a - shift):.3f},{b - shift:.3f})'[h{k}]")
                last, n_in = f"h{k}", n_in + 1
    graph.append(f"[{last}][1:v]overlay=0:0,format=yuv420p[v]")
    maps = ["-map", "[v]"]
    if args.audio:
        inputs += ["-ss", str(args.start), "-i", args.audio]
        graph.append(f"[{n_in}:a]loudnorm=I=-18:TP=-3:LRA=11,aresample=48000[a]")
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(graph), *maps,
           "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", args.out]
    subprocess.run(cmd, check=True)
    print("wrote", args.out, f"{dur:.2f}s")


if __name__ == "__main__":
    main()
