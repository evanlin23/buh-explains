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
SR = 48000  # whole voice track at 48 kHz: a 24 kHz track cut the bites' top end (owner: "muffled")


def rs(a, sr_in):
    import librosa
    a = np.asarray(a, np.float32)
    return a if sr_in == SR else librosa.resample(a, orig_sr=sr_in, target_sr=SR, res_type="soxr_hq").astype(np.float32)


BITE_EQ = "highpass=f=110,equalizer=f=3500:t=q:w=1.2:g=4,highshelf=f=6500:g=4,aexciter=amount=1.5:drive=5:freq=5000"


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


def squeeze(a, thr=0.012, longest=0.12, keep=0.05):
    """Shorten every internal silence longer than `longest` to `keep` seconds (Tung barely pauses)."""
    hop = int(0.01 * SR); n = len(a) // hop
    loud = np.array([np.abs(a[i * hop:(i + 1) * hop]).max() > thr for i in range(n)])
    out, i = [], 0
    while i < n:
        j = i
        while j < n and loud[j] == loud[i]: j += 1
        seg = a[i * hop:j * hop]
        if not loud[i] and (j - i) * 0.01 > longest:
            k = int(keep * SR); seg = np.concatenate([seg[:k // 2], seg[-(k - k // 2):]])
        out.append(seg); i = j
    out.append(a[n * hop:])
    return np.concatenate(out)


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


def bite_audio(name, cfg, kokoro):
    """The meme's own sound bite (owner, 2026-11-06). cfg["bite"] = path to the real clip once chosen.
    Until then: a placeholder, a second voice saying the name, pitched down and crushed so it reads as "not the narrator"."""
    path = cfg.get("bite")
    if path:
        import subprocess
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(REPO, path), "-af", BITE_EQ, "-ac", "1", "-ar", str(SR),
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32).copy()
    a, _sr = kokoro.create(name + "!", voice="am_onyx", speed=1.15, lang="en-us"); a = rs(a, _sr)
    a = trim(np.asarray(a, np.float32))
    a = np.interp(np.arange(0, len(a), 0.9), np.arange(len(a)), a).astype(np.float32)  # a bit lower
    a = np.tanh(a * 4.0) * 0.8                                                            # crushed
    echo = np.zeros(len(a) + int(0.06 * SR), np.float32); echo[:len(a)] += a; echo[int(0.06 * SR):] += a * 0.35
    return echo


def main(slug):
    from kokoro_onnx import Kokoro
    from faster_whisper import WhisperModel
    ep = json.load(open(os.path.join(ROOT, "episodes", slug, "episode.json")))
    v = ep["voice"]
    names = {norm(n): (n, cfg) for n, cfg in ep.get("names", {}).items()}
    od = os.path.join(REPO, "out", slug)
    os.makedirs(od, exist_ok=True)
    k = Kokoro(os.path.join(MODELS, "kokoro-v1.0.onnx"), os.path.join(MODELS, "voices-v1.0.bin"))
    model = WhisperModel("base.en", device="cpu", compute_type="int8", download_root=os.path.join(MODELS, "whisper"))
    ref, _sr = k.create("This is a level check for the narrator.", voice=v["voice"], speed=v["speed"], lang="en-us")
    ref = rs(ref, _sr); ref_rms = np.sqrt(np.mean(ref[np.abs(ref) > 0.02] ** 2))

    def level(a):  # a bite plays as loud as the narrator (a touch hotter), never quieter
        r = np.sqrt(np.mean(a[np.abs(a) > 0.02] ** 2)) + 1e-9
        a = a * (ref_rms * 1.15 / r)
        return a / max(1.0, np.abs(a).max() / 0.98)

    bites = {key: level(bite_audio(n, cfg, k)) for key, (n, cfg) in names.items()}
    bites_full = {key: level(bite_audio(n, dict(cfg, bite=cfg.get("bite_full") or cfg.get("bite")), k)) for key, (n, cfg) in names.items()}
    parts, words, t, report = [], [], 0.0, []
    seg_n = 0
    for li, line in enumerate(ep["lines"]):
        gap = line.get("pause_before", v["gap"]) if li else 0.0
        parts.append(np.zeros(int(gap * SR), np.float32)); t += gap
        tokens = line["text"].split()
        segs, cur, grp = [], [], None
        for i, tok in enumerate(tokens):  # speech runs, split around the meme's name or a {bite group}
            if tok.startswith("{"):
                grp = []
            if grp is not None:
                grp.append(i)
                if tok.rstrip(",.?!").endswith("}"):
                    if cur: segs.append(("say", cur)); cur = []
                    segs.append(("bite", grp)); grp = None
                continue
            if norm(tok) in names:
                if cur: segs.append(("say", cur)); cur = []
                segs.append(("bite", [i]))
            else:
                cur.append(i)
        if cur: segs.append(("say", cur))
        tokens = [tok.replace("{", "").replace("}", "") for tok in tokens]
        # Speak the whole line in one breath, then swap the spoken name for the bite inside it. Synthesizing the
        # pieces separately made "Do you know" end like a finished sentence before the bite (owner: "did you know [pause] verity").
        speak, _sr = k.create(" ".join(tokens), voice=v["voice"], speed=v["speed"], lang="en-us")
        speak = squeeze(trim(rs(speak, _sr), thr=0.012, lead=0.06 if li == 0 else 0.015, pad=0.0))
        cp = os.path.join(od, f"seg{seg_n:02d}.wav"); seg_n += 1; sf.write(cp, speak, SR)
        times, heard = word_times(cp, tokens, model)
        matched = sum(1 for x in times if x); total = len(tokens); heard_all = heard
        dur = len(speak) / SR; times = fill(times, tokens, dur)
        groups = [idx for kind, idx in segs if kind == "bite"]
        pieces, cursor, shift, out_times = [], 0, 0.0, {}
        for idx in groups:
            c0 = int(max(0.0, times[idx[0]][0] - 0.02) * SR)
            nxt = idx[-1] + 1
            c1 = int((times[nxt][0] - 0.01 if nxt < len(tokens) else dur) * SR)
            for i in range(len(tokens)):
                if cursor <= int(times[i][0] * SR) < c0 and i not in idx:
                    out_times[i] = (times[i][0] + shift, times[i][1] + shift)
            pieces.append(speak[cursor:c0])
            key = next((norm(tokens[i]) for i in idx if norm(tokens[i]) in names), next(iter(names)))
            bite = (bites_full if len(idx) > 1 else bites)[key]
            bite = trim(bite, thr=0.01, lead=0.0, pad=0.0)
            t_b = (sum(len(p_) for p_ in pieces)) / SR
            span = len(bite) / SR / len(idx)
            for j, i in enumerate(idx): out_times[i] = (t_b + j * span, t_b + (j + 1) * span)
            pieces.append(bite)
            shift += len(bite) / SR - (c1 - c0) / SR
            cursor = c1
        for i in range(len(tokens)):
            if i not in out_times: out_times[i] = (times[i][0] + shift, times[i][1] + shift)
        pieces.append(speak[cursor:])
        a = np.concatenate(pieces)
        for i in range(len(tokens)):
            s_, e_ = out_times[i]
            words.append({"line": li, "i": i, "word": tokens[i], "start": round(t + s_, 3), "end": round(t + e_, 3),
                          **({"bite": True} if any(i in g for g in groups) else {})})
        parts.append(a); t += len(a) / SR
        cov = matched / total if total else 1.0
        report.append((li, round(cov, 2), " ".join(heard_all)))
    words.sort(key=lambda w: (w["line"], w["i"]))
    sf.write(os.path.join(od, "voice.wav"), np.concatenate(parts), SR)
    json.dump({"duration": round(t, 3), "words": words}, open(os.path.join(od, "words.json"), "w"), indent=1)
    for li, cov, heard in report:
        print(f"line {li}: {cov:.0%} of spoken words matched{'   <-- FAIL' if cov < 0.6 else ''}\n   heard: {heard}")
    print(f"voice: {t:.2f} s, {len(words)} words, {len(words) / t:.2f} words/s")
    if any(cov < 0.6 for _, cov, _ in report):
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
