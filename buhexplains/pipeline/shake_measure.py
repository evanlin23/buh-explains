"""Measure whole-frame shake, frame by frame: per-frame translation (sub-pixel phase correlation), scale and
rotation (log-polar phase correlation), inside shots with no cuts. Reports in 1080x1920 pixels.
  python buhexplains/pipeline/shake_measure.py VIDEO start-end [start-end ...]"""
import subprocess, sys
import numpy as np

W, H = 360, 640


def frames(path, t0, t1):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t0), "-to", str(t1), "-i", path, "-vf", f"scale={W}:{H},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


WIN = np.outer(np.hanning(H), np.hanning(W)).astype(np.float32)


def phase(a, b):
    A = np.fft.fft2((a - a.mean()) * WIN); B = np.fft.fft2((b - b.mean()) * WIN)
    R = A * np.conj(B); R /= np.abs(R) + 1e-9
    r = np.fft.fftshift(np.abs(np.fft.ifft2(R)))
    y, x = np.unravel_index(r.argmax(), r.shape)
    def sub(c, m, p):  # parabolic sub-pixel
        d = m - 2 * c + p
        return 0.0 if d == 0 else 0.5 * (m - p) / d
    dy = y - H // 2 + sub(r[y, x], r[(y - 1) % H, x], r[(y + 1) % H, x])
    dx = x - W // 2 + sub(r[y, x], r[y, (x - 1) % W], r[y, (x + 1) % W])
    return dx, dy, r.max()


def logpolar(img, n_r=256, n_t=360):
    F = np.abs(np.fft.fftshift(np.fft.fft2((img - img.mean()) * WIN)))
    cy, cx = H / 2, W / 2; maxr = min(cx, cy)
    rs = np.exp(np.linspace(0, np.log(maxr), n_r)); ts = np.linspace(0, np.pi, n_t, endpoint=False)
    yy = cy + rs[:, None] * np.sin(ts)[None, :]; xx = cx + rs[:, None] * np.cos(ts)[None, :]
    return F[np.clip(yy.astype(int), 0, H - 1), np.clip(xx.astype(int), 0, W - 1)], np.log(maxr) / (n_r - 1), 180 / n_t


def scale_rot(a, b):
    la, dr, dt = logpolar(a); lb, _, _ = logpolar(b)
    A = np.fft.fft2(la); B = np.fft.fft2(lb); R = A * np.conj(B); R /= np.abs(R) + 1e-9
    r = np.abs(np.fft.ifft2(R)); y, x = np.unravel_index(r.argmax(), r.shape)
    if y > r.shape[0] / 2: y -= r.shape[0]
    if x > r.shape[1] / 2: x -= r.shape[1]
    return float(np.exp(y * dr)), float(x * dt)


def main(path, spans):
    k = 1080 / W
    allx, ally, steps, rots, scales = [], [], [], [], []
    for sp in spans:
        t0, t1 = map(float, sp.split("-")); F = frames(path, t0, t1)
        print(f"\n== {path.split('/')[-1]} {t0}-{t1} s ({len(F)} frames)   frame: dx dy (px @1080), scale, rot(deg)")
        pos = [(0.0, 0.0)]
        for i in range(1, len(F)):
            dx, dy, c = phase(F[i], F[i - 1]); sc, rot = scale_rot(F[i], F[i - 1])
            dx, dy = dx * k, dy * k
            pos.append((pos[-1][0] + dx, pos[-1][1] + dy)); steps.append(np.hypot(dx, dy)); rots.append(rot); scales.append(sc)
            print(f"  {t0 + i / 30:6.3f}  {dx:+6.1f} {dy:+6.1f}  {sc:5.3f} {rot:+5.2f}")
        p = np.array(pos); p -= p.mean(0); allx += list(p[:, 0]); ally += list(p[:, 1])
    steps = np.array(steps); x = np.array(allx); y = np.array(ally)
    sx = np.sign(np.diff(x)); rev = (sx[1:] * sx[:-1] < 0).sum()
    total_t = len(steps) / 30
    print(f"\nSUMMARY {path.split('/')[-1]}")
    print(f"  per-frame step:   median {np.median(steps):.1f} px, p90 {np.percentile(steps, 90):.1f}, max {steps.max():.1f}")
    print(f"  position spread:  x sd {x.std():.1f} px, y sd {y.std():.1f} px (range x {np.ptp(x):.0f}, y {np.ptp(y):.0f})")
    print(f"  direction flips (x): {rev / total_t:.1f} per s  -> shake rate about {rev / total_t / 2:.1f} Hz")
    print(f"  scale per frame:  median |1-s| {np.median(np.abs(1 - np.array(scales))) * 100:.2f}%   rot median |r| {np.median(np.abs(rots)):.2f} deg")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
