"""Voice QA. (1) Clipped words: words whose sound is still running at a cut (the voice track's energy at a splice or
line join is high). (2) Intelligibility: Whisper on the FINAL mix (music + effects included) against the script.
  python buhexplains/pipeline/voicecheck.py ep01-verity"""
import difflib, json, os, re, subprocess, sys
import numpy as np, soundfile as sf

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def norm(w): return re.sub(r"[^a-z0-9]", "", w.lower())


def main(slug):
    od = os.path.join(REPO, "out", slug)
    words = json.load(open(os.path.join(od, "words.json")))["words"]
    v, sr = sf.read(os.path.join(od, "voice.wav"), dtype="float32")
    env = np.sqrt(np.convolve(v ** 2, np.ones(int(0.01 * sr)) / int(0.01 * sr), "same"))
    ref = np.percentile(env[env > 0.01], 50)
    joins = json.load(open(os.path.join(od, "joins.json"))) if os.path.exists(os.path.join(od, "joins.json")) else []
    hot = [round(t, 2) for t in joins if env[min(len(env) - 1, int(t * sr))] > ref * 0.35]
    print(f"cuts/joins: {len(joins)}, cut while the voice was still sounding: {len(hot)} {hot}")
    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", device="cpu", compute_type="int8", download_root=os.path.join(REPO, ".cache", "models", "whisper"))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(od, f"{slug}.mp4"), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    segs, _ = m.transcribe(a, language="en", beam_size=5)
    heard = [norm(x) for s_ in segs for x in s_.text.split() if norm(x)]
    script = [norm(w["word"]) for w in words if not w.get("bite")]
    sm = difflib.SequenceMatcher(None, script, heard, autojunk=False)
    hit = sum(b.size for b in sm.get_matching_blocks())
    print(f"intelligibility in the final mix: {hit}/{len(script)} narrated words heard ({100 * hit / len(script):.0f}%)")
    miss = [script[i] for op, i1, i2, _, _ in sm.get_opcodes() if op in ("delete", "replace") for i in range(i1, i2)]
    print("missed:", miss)


if __name__ == "__main__":
    main(sys.argv[1])
