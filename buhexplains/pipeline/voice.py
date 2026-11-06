"""Narration + word timings.

Placeholder engine: Kokoro (Apache 2.0, local). The final engine is Gemini TTS "Achird" (owner, 2026-11-06),
added once this repo has its own GEMINI_API_KEY. Either way the output contract is the same:
  out/<slug>/voice.wav (24 kHz mono) and out/<slug>/words.json = [{line, i, word, start, end}]
Each line is synthesized on its own, so line boundaries are exact. Inside a line, word times come from
faster-whisper word timestamps, matched back onto the script's own words (so spelling comes from the script).
"""
import difflib, json, os, re, sys
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
MODELS = os.path.join(REPO, ".cache", "models")
SR = 24000


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def synth_kokoro(lines, voice, speed):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    out = []
    for text in lines:
        audio, sr = k.create(text, voice=voice, speed=speed, lang="en-us")
        assert sr == SR, sr
        out.append(trim(np.asarray(audio, np.float32)))
    return out


def trim(a, thr=0.005, pad=0.02, lead=0.09):
    idx = np.where(np.abs(a) > thr)[0]
    if not len(idx):
        return a
    s, e = max(0, idx[0] - int(lead * SR)), min(len(a), idx[-1] + int(pad * SR))
    return a[s:e]


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def num_words(n):
    """Spell an integer the way a narrator says it (enough for view counts and years)."""
    if n < 20: return [ONES[n]]
    if n < 100: return [TENS[n // 10]] + ([ONES[n % 10]] if n % 10 else [])
    if n < 1000: return [ONES[n // 100], "hundred"] + (num_words(n % 100) if n % 100 else [])
    for big, name in ((10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        if n >= big: return num_words(n // big) + [name] + (num_words(n % big) if n % big else [])


def expand(heard):
    """Whisper writes "57" or "57 million"; the script says the words. Spread digits into word tokens."""
    out = []
    for w, s, e in heard:
        d = re.sub(r"[^0-9]", "", w)
        if d and d == re.sub(r"[^0-9a-z]", "", w.lower()) and len(d) < 10:
            parts = num_words(int(d))
            step = (e - s) / len(parts)
            out += [(p, s + k * step, s + (k + 1) * step) for k, p in enumerate(parts)]
        else:
            out.append((w, s, e))
    return out


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.6


def word_times(clip_path, tokens, model):
    a, sr = sf.read(clip_path, dtype="float32")
    a16 = np.interp(np.arange(0, len(a), sr / 16000), np.arange(len(a)), a).astype(np.float32)  # whisper wants 16 kHz
    segs, _ = model.transcribe(a16, word_timestamps=True, language="en", beam_size=5)
    heard = expand([(w.word.strip(), w.start, w.end) for s in segs for w in s.words])
    a, b = [norm(t) for t in tokens], [norm(h[0]) for h in heard]
    times, used = [None] * len(tokens), [False] * len(heard)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = (heard[blk.b + k][1], heard[blk.b + k][2]); used[blk.b + k] = True
    # second pass: soundalikes ("Caine"/"cane"), and one script word heard as two ("ThatMob"/"that mom")
    for i, t in enumerate(times):
        if t: continue
        lo = max([j for j in range(len(b)) if used[j] and any(times[k] and times[k][0] == heard[j][1] for k in range(i))] + [-1])
        hi = min([j for j in range(len(b)) if used[j] and any(times[k] and times[k][0] == heard[j][1] for k in range(i + 1, len(a)))] + [len(b)])
        for j in range(lo + 1, hi):
            if used[j]: continue
            if similar(a[i], b[j]):
                times[i] = (heard[j][1], heard[j][2]); used[j] = True; break
            if j + 1 < hi and not used[j + 1] and similar(a[i], b[j] + b[j + 1]):
                times[i] = (heard[j][1], heard[j + 1][2]); used[j] = used[j + 1] = True; break
    return times, [h[0] for h in heard]


def fill(times, tokens, dur):
    """Interpolate unmatched words by character length between their matched neighbours."""
    n = len(tokens)
    anchors = [(-1, 0.0)] + [(i, t[0]) for i, t in enumerate(times) if t] + [(n, dur)]
    out = list(times)
    for (i0, t0), (i1, t1) in zip(anchors, anchors[1:]):
        gap = list(range(i0 + 1, i1))
        if not gap:
            continue
        start = times[i0][1] if i0 >= 0 and times[i0] else t0
        lens = np.array([max(1, len(norm(tokens[g]))) for g in gap], float)
        edges = start + np.concatenate([[0], np.cumsum(lens)]) / lens.sum() * max(0.05, t1 - start)
        for g, s, e in zip(gap, edges[:-1], edges[1:]):
            out[g] = (float(s), float(e))
    return out


def main(slug):
    ep = json.load(open(os.path.join(ROOT, "episodes", slug, "episode.json")))
    v = ep["voice"]
    od = os.path.join(REPO, "out", slug)
    os.makedirs(od, exist_ok=True)
    texts = [l["text"] for l in ep["lines"]]
    clips = synth_kokoro(texts, v["voice"], v["speed"])
    from faster_whisper import WhisperModel
    model = WhisperModel("base.en", device="cpu", compute_type="int8", download_root=os.path.join(MODELS, "whisper"))
    parts, words, t, report = [], [], 0.0, []
    for li, (line, clip) in enumerate(zip(ep["lines"], clips)):
        gap = line.get("pause_before", v["gap"]) if li else 0.0
        parts.append(np.zeros(int(gap * SR), np.float32))
        t += gap
        cp = os.path.join(od, f"line{li:02d}.wav")
        sf.write(cp, clip, SR)
        tokens = line["text"].split()
        times, heard = word_times(cp, tokens, model)
        missing = [tokens[i] for i, x in enumerate(times) if x is None]
        coverage = 1 - len(missing) / len(tokens)
        report.append((li, round(coverage, 2), missing, " ".join(heard)))
        dur = len(clip) / SR
        for i, (w, (s, e)) in enumerate(zip(tokens, fill(times, tokens, dur))):
            words.append({"line": li, "i": i, "word": w, "start": round(t + s, 3), "end": round(t + min(e, dur), 3)})
        parts.append(clip)
        t += dur
    voice = np.concatenate(parts)
    sf.write(os.path.join(od, "voice.wav"), voice, SR)
    json.dump({"duration": round(t, 3), "words": words}, open(os.path.join(od, "words.json"), "w"), indent=1)
    for li, cov, miss, heard in report:
        flag = "" if cov >= 0.6 else "   <-- FAIL: line not voiced cleanly"
        print(f"line {li}: {cov:.0%} matched {miss or ''}{flag}\n   heard: {heard}")
    print(f"voice: {t:.2f} s, {len(words)} words, {len(words) / t:.2f} words/s")
    if any(cov < 0.6 for _, cov, _, _ in report):
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
