"""Find and cut a meme's sound bite from a source video or audio file.

  python buhexplains/pipeline/bite.py SOURCE --word Verity            # list every line that says the word
  python buhexplains/pipeline/bite.py SOURCE --cut 612.40-613.55 --name verity   # cut it to .cache/bites/verity.wav

The bite file stays out of git (third-party audio). Point episode.json -> names -> <Name> -> bite at it.
"""
import argparse, os, re, subprocess
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(src, sr=16000):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def find(src, word):
    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", device="cpu", compute_type="int8", download_root=os.path.join(REPO, ".cache", "models", "whisper"))
    segs, _ = m.transcribe(load(src), word_timestamps=True, language="en", beam_size=5)
    key = re.sub(r"[^a-z]", "", word.lower())
    for s in segs:
        hits = [w for w in s.words if key in re.sub(r"[^a-z]", "", w.word.lower())]
        if hits:
            h = hits[0]
            print(f"{s.start:8.2f}-{s.end:7.2f}  word at {h.start:.2f}-{h.end:.2f}  | {s.text.strip()}")


def cut(src, span, name):
    a, b = map(float, span.split("-"))
    out = os.path.join(REPO, ".cache", "bites", f"{name}.wav"); os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(a), "-to", str(b), "-i", src, "-ac", "1", "-ar", "24000",
                    "-af", "afade=t=in:d=0.01,areverse,afade=t=in:d=0.04,areverse", out], check=True)
    print("wrote", out, f"({b - a:.2f} s) -> set episode.json names.<Name>.bite = \".cache/bites/{name}.wav\"")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("--word"); ap.add_argument("--cut"); ap.add_argument("--name", default="bite")
    a = ap.parse_args()
    if a.cut: cut(a.src, a.cut, a.name)
    else: find(a.src, a.word or "Verity")
