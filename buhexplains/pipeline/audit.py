"""QA audit of finished videos against what makes a Short go viral (PLAYBOOK §1, §6, §8).
  python buhexplains/pipeline/audit.py ep01-verity ep02-last-dance ...
Measures the MP4 itself plus the episode's words.json. Prints one row per check and a list of failures."""
import json, os, re, subprocess, sys
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W, H = 135, 240   # analysis size (1/8)


def frames(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def loud(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r); p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)
    return float(i[-1]) if i else None, float(p[-1]) if p else None


def audit(slug):
    od = os.path.join(REPO, "out", slug); path = os.path.join(od, f"{slug}.mp4")
    F = frames(path); fps = 30; n = len(F); dur = n / fps
    words = json.load(open(os.path.join(od, "words.json")))["words"]
    # visual changes: big shifts in the picture (cuts, new images, flashes), from a histogram + pixel test
    diff = np.abs(np.diff(F, axis=0)).mean((1, 2))
    hist = np.array([np.histogram(f, 16, (0, 255))[0] for f in F], np.float32)
    hd = 1 - np.minimum(hist[1:], hist[:-1]).sum(1) / hist[0].sum()
    change = (hd > 0.25) | (diff > 28)
    ct = np.where(change)[0] / fps
    events = [t for i, t in enumerate(ct) if i == 0 or t - ct[i - 1] > 0.15]
    gaps = np.diff([0.0] + events + [dur])
    still = (diff < 1.5).mean() * 100
    dark = (F.mean((1, 2)) < 18)
    dark_runs = max((len(r) for r in "".join("1" if d else "0" for d in dark).split("0")), default=0) / fps
    first_move = next((i / fps for i, d in enumerate(diff) if d > 3), dur)
    first_word = words[0]["start"]
    hook_end = next((w["end"] for w in words if w["word"].endswith("?")), None)
    last_word = words[-1]["end"]; tail = dur - last_word
    I, peak = loud(path)
    vc = None
    try:
        out = subprocess.run([sys.executable, os.path.join(REPO, "buhexplains", "pipeline", "voicecheck.py"), slug], capture_output=True, text=True).stdout
        m = re.search(r"\((\d+)%\)", out); vc = int(m.group(1)) if m else None
    except Exception: pass
    rows = [
        ("length s", round(dur, 1), "20-35", 20 <= dur <= 35),
        ("first motion s", round(first_move, 2), "<= 0.2", first_move <= 0.2),
        ("first word s", round(first_word, 2), "<= 0.15", first_word <= 0.15),
        ("hook asked by s", round(hook_end, 2) if hook_end else None, "<= 3.0", bool(hook_end and hook_end <= 3.0)),
        ("visual changes /10s", round(len(events) / dur * 10, 1), ">= 6", len(events) / dur * 10 >= 6),
        ("longest hold s", round(float(gaps.max()), 2), "<= 2.5", gaps.max() <= 2.5),
        ("frozen frames %", round(still, 1), "<= 5", still <= 5),
        ("black stretch s", round(dark_runs, 2), "<= 0.15", dark_runs <= 0.15),
        ("tail after last word s", round(tail, 2), "<= 0.5", tail <= 0.5),
        ("loudness LUFS", I, "-11..-8", I is not None and -11 <= I <= -8),
        ("true peak dBFS", peak, "<= -0.5", peak is not None and peak <= -0.5),
        ("voice heard %", vc, ">= 85", vc is not None and vc >= 85),
    ]
    hold_at = round(float(([0.0] + events)[int(np.argmax(gaps))]), 2)
    return rows, hold_at


if __name__ == "__main__":
    fails = {}
    for slug in sys.argv[1:]:
        rows, hold_at = audit(slug)
        print(f"\n== {slug}")
        for name, val, target, ok in rows:
            print(f"  {'OK ' if ok else 'XX '} {name:24s} {str(val):>8s}   target {target}" + (f"   (at {hold_at}s)" if name == "longest hold s" else ""))
            if not ok: fails.setdefault(slug, []).append(name)
    print("\nFAILURES:", json.dumps(fails, indent=1) if fails else "none")
