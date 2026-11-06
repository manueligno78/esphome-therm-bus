"""Decode a bus capture (.npz from capture_*.py) as async serial frames.

Usage:
    python decode_uart.py ../captures/20261020-140123_idle.npz
    python decode_uart.py FILE --baud 4800 --bits 8 --parity none --list

The bus idles high; a burst separated by more than --gap-ms of idle is one
frame. Each frame is tagged by how low the bus goes while it is sent: two
transmitters with different pull-down strength show up as two low levels.
"""

import argparse
import collections
import pathlib

import numpy as np

from busanalysis import split_levels


def find_frames(d, rate, gap_ms):
    """Yield (start, end) sample indexes of bursts separated by idle-high gaps."""
    lows = np.flatnonzero(~d)
    if not len(lows):
        return
    gap = int(gap_ms * rate / 1000)
    breaks = np.flatnonzero(np.diff(lows) > gap)
    starts = np.r_[lows[0], lows[breaks + 1]]
    ends = np.r_[lows[breaks], lows[-1]]
    yield from zip(starts, ends + 1)


def decode_bytes(d, rate, start, end, baud, bits, parity):
    """Classic UART sampling at bit centers; returns (bytes, framing_errors)."""
    spb = rate / baud
    out, errors = [], 0
    i = start
    while i < end:
        # Next falling edge = start bit.
        while i < end and d[i]:
            i += 1
        if i >= end:
            break
        center = lambda k: int(i + (k + 0.5) * spb)
        n_bits = bits + (parity != "none")
        if center(n_bits + 1) >= len(d):
            break
        if d[center(0)]:  # glitch, not a real start bit
            i += 1
            continue
        val = sum(int(d[center(1 + b)]) << b for b in range(bits))
        if parity != "none":
            p = int(d[center(1 + bits)])
            ones = bin(val).count("1") + p
            if (parity == "even") != (ones % 2 == 0):
                errors += 1
        if not d[center(n_bits + 1)]:
            errors += 1
        out.append(val)
        # Resume half a bit into the stop bit, ready for the next falling edge.
        i = center(n_bits + 1)
    return out, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=pathlib.Path)
    ap.add_argument("--baud", type=float, default=4800)
    ap.add_argument("--bits", type=int, default=8)
    ap.add_argument("--parity", choices=["none", "even", "odd"], default="none")
    ap.add_argument("--gap-ms", type=float, default=5)
    ap.add_argument("--list", action="store_true", help="print every frame")
    ap.add_argument("--changes", action="store_true",
                    help="print frames whose content changed vs the previous one of the same kind")
    args = ap.parse_args()

    z = np.load(args.file)
    v, rate = z["volts"], float(z["rate"])
    t, _, _ = split_levels(v)
    d = v >= t

    frames = []
    for s, e in find_frames(d, rate, args.gap_ms):
        low = float(np.median(v[s:e][~d[s:e]]))
        data, err = decode_bytes(d, rate, s, e, args.baud, args.bits, args.parity)
        frames.append((s / rate * 1000, (e - s) / rate * 1000, low, data, err))

    lows = np.array([f[2] for f in frames])
    split = (lows.min() + lows.max()) / 2 if len(lows) else 0
    tag = lambda low: "A" if low < split else "B"
    total_err = sum(f[4] for f in frames)
    total_bytes = sum(len(f[3]) for f in frames)
    print(f"{len(frames)} frames, {total_bytes} bytes, framing/parity errors: {total_err}")
    for name in "AB":
        sel = [f for f in frames if tag(f[2]) == name]
        if sel:
            print(f"source {name}: {len(sel)} frames, bus low ~{np.median([f[2] for f in sel]):.2f} V, "
                  f"length {min(len(f[3]) for f in sel)}-{max(len(f[3]) for f in sel)} bytes")

    if args.list:
        for t_ms, dur, low, data, err in frames:
            print(f"{t_ms:9.1f} ms {tag(low)} {dur:5.1f}ms err={err} " + " ".join(f"{b:02X}" for b in data))

    if args.changes:
        # Frames of one kind share source + first 3 bytes; show when one differs
        # from the previous frame of its kind, with the changed bytes marked.
        print("\nchanges over time:")
        last = {}
        for t_ms, _, low, data, _ in frames:
            key = (tag(low), tuple(data[:3]))
            prev = last.get(key)
            if prev is not None and len(prev) == len(data) and prev != data:
                marks = " ".join(f"{b:02X}" if p == b else f"[{b:02X}]" for p, b in zip(prev, data))
                print(f"{t_ms / 1000:8.2f} s {key[0]} {marks}")
            last[key] = data

    print("\ndistinct frames (count, source, bytes):")
    counts = collections.Counter((tag(f[2]), tuple(f[3])) for f in frames)
    for (src, data), n in counts.most_common(30):
        print(f"{n:5d} {src} [{len(data):2d}] " + " ".join(f"{b:02X}" for b in data))


if __name__ == "__main__":
    main()
