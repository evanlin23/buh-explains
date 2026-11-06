"""Rebuild .cache/ from logged sources, so a fresh session can re-render any episode exactly.

  python buhexplains/pipeline/fetch_assets.py ep01-verity

.cache/ is never committed: the repo is public, and these files are other people's media. Everything here
comes back from a URL recorded in the repo: models, Mixkit stock, the myinstants sound kit
(assets/sfx_sources.txt), and each episode's music and name bites (episode.json, with their cut points).
Pictures are fetched on demand by render.py from episode.json. The owner's own saved sounds are committed
in assets/sfx/.
"""
import json, os, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT); C = os.path.join(REPO, ".cache")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}


def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print("  fetch", url)
    if "soundcloud.com" in url:  # public SoundCloud stream, first 90 s only
        base = os.path.splitext(path)[0]
        subprocess.run(["yt-dlp", "-q", "-x", "--audio-format", "mp3", "--download-sections", "*0-90", "-o", base + ".%(ext)s", url], check=True)
        return
    open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())


def main(slug):
    engine = json.load(open(os.path.join(ROOT, "episodes", slug, "episode.json")))["voice"].get("engine")
    for f in (("kokoro-v1.0.onnx", "voices-v1.0.bin") if engine != "gemini" else ()):
        get(f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{f}", os.path.join(C, "models", f))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    if os.environ.get("VOICE_ONLY"): render = None
    else: import render
    for f, _, _ in (render.STOCK.values() if render else []):
        vid = f.split("-")[0]; get(f"https://assets.mixkit.co/videos/{vid}/{f}", os.path.join(C, "stock", f))
    srcs = {l.split()[0]: l.split()[1] for l in open(os.path.join(ROOT, "assets", "sfx_sources.txt")) if l.strip()}
    for files in (render.KIT.values() if render else []):
        for f in files:
            if not os.path.exists(os.path.join(ROOT, "assets", "sfx", f + ".mp3")) and f in srcs:
                get(srcs[f], os.path.join(C, "sfx", f + ".mp3"))
    ep = json.load(open(os.path.join(ROOT, "episodes", slug, "episode.json")))
    m = ep.get("music")
    if m: get(m["source"].split()[0], os.path.join(C, "music", m["file"]))
    for name, cfg in ep.get("names", {}).items():
        for key, url, cut in (("bite", cfg.get("bite_src"), cfg.get("bite_cut")),
                              ("bite_full", cfg.get("bite_full_src") or cfg.get("bite_src"), cfg.get("bite_full_cut"))):
            if not url: continue
            src = os.path.join(C, "bites", (cfg.get("bite_file") if "soundcloud.com" in url else None) or os.path.basename(url)); get(url, src)
            if cfg.get(key) and cut and not os.path.exists(os.path.join(REPO, cfg[key])):
                a, b = cut
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", src, "-ac", "1", "-ar", "48000",
                                "-af", f"afade=t=in:d=0.01,afade=t=out:st={b - a - 0.08:.2f}:d=0.08", os.path.join(REPO, cfg[key])], check=True)
                print("  cut", cfg[key])
    print("assets ready for", slug)


if __name__ == "__main__":
    main(sys.argv[1])
