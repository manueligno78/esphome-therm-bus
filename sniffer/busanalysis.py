"""Shared analysis for bus captures: levels, transitions, pulse widths, plot.

Captures are .npz files with `volts` (bus volts, float32) and `rate` (S/s).
Re-analyze a saved capture:
    python busanalysis.py ../captures/20261020-120000_idle.npz
"""

import collections
import pathlib
import sys

import numpy as np


def split_levels(v):
    """Two-cluster threshold (isodata): returns (threshold, low, high)."""
    t = float(v.mean())
    for _ in range(50):
        lo, hi = v[v < t], v[v >= t]
        if not len(lo) or not len(hi):
            break
        nt = (lo.mean() + hi.mean()) / 2
        if abs(nt - t) < 1e-4:
            break
        t = float(nt)
    return t, float(v[v < t].mean()), float(v[v >= t].mean())


def summarize(v, rate, seconds=None):
    """Print levels and pulse-width statistics; return the threshold."""
    dur = len(v) / rate
    print(f"samples: {len(v)} @ {rate:.0f} S/s = {dur:.2f} s", end="")
    print(f" (expected {seconds:g} s)" if seconds else "")
    print(f"bus volts: min={v.min():.2f} p1={np.percentile(v, 1):.2f} "
          f"median={np.median(v):.2f} p99={np.percentile(v, 99):.2f} max={v.max():.2f}")

    counts, bins = np.histogram(v, bins=np.arange(0, np.ceil(v.max()) + 1, 0.5))
    top = counts.max() or 1
    print("histogram (V: share):")
    for c, b in zip(counts, bins):
        if c:
            print(f"  {b:5.1f}-{b + 0.5:<5.1f} {c / len(v) * 100:6.2f}% "
                  f"{'#' * max(1, int(40 * c / top))}")

    t, lo, hi = split_levels(v)
    d = v >= t
    print(f"two-level split: low={lo:.2f} V high={hi:.2f} V threshold={t:.2f} V "
          f"high share={d.mean() * 100:.1f}%")

    edges = np.flatnonzero(np.diff(d.astype(np.int8))) + 1
    print(f"transitions: {len(edges)} ({len(edges) / dur:.0f}/s)")
    if len(edges) < 2:
        return t
    widths = np.diff(edges) * 1e6 / rate
    levels = d[edges[:-1]]
    for lvl, name in ((True, "HIGH"), (False, "LOW")):
        w = np.sort(widths[levels == lvl])
        if not len(w):
            continue
        common = collections.Counter(np.round(w / 10) * 10).most_common(8)
        print(f"{name}: n={len(w)} min={w[0]:.0f}us median={w[len(w) // 2]:.0f}us "
              f"max={w[-1]:.0f}us")
        print("   most common (us:count): " + ", ".join(f"{k:g}:{c}" for k, c in common))
    return t


def plot(v, rate, threshold, out_png, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t_ms = np.arange(len(v)) / rate * 1e3
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(14, 7))
    n = min(len(v), int(rate * 2))
    a1.plot(t_ms[:n], v[:n], lw=0.5)
    a1.set_title(f"{title}: first {n / rate:.1f} s")
    edges = np.flatnonzero(np.diff((v >= threshold).astype(np.int8)))
    start = max(0, (edges[0] if len(edges) else 0) - int(rate * 0.002))
    stop = min(len(v), start + int(rate * 0.03))
    a2.plot(t_ms[start:stop], v[start:stop], ".-", lw=0.7, ms=2)
    a2.axhline(threshold, color="r", lw=0.5, ls="--")
    a2.set_title("zoom: 30 ms from first transition")
    for a in (a1, a2):
        a.set_xlabel("ms")
        a.set_ylabel("bus V")
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    print(f"plot {out_png}")


def save_and_report(out_npz, volts, rate, seconds=None):
    np.savez_compressed(out_npz, volts=volts.astype(np.float32), rate=rate)
    print(f"saved {out_npz}")
    t = summarize(volts, rate, seconds)
    plot(volts, rate, t, out_npz.with_suffix(".png"), out_npz.stem)


if __name__ == "__main__":
    path = pathlib.Path(sys.argv[1])
    z = np.load(path)
    v, rate = z["volts"], float(z["rate"])
    plot(v, rate, summarize(v, rate), path.with_suffix(".png"), path.stem)
