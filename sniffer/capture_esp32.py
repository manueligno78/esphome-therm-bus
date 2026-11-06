"""Record the bus waveform from the ESP32 sampler over Wi-Fi and summarize it.

Usage:
    python capture_esp32.py idle --seconds 30
    python capture_esp32.py button_up --seconds 15 --host 192.168.1.50

Without --host the script waits for the board's UDP beacon to find it.
Output in captures/: <timestamp>_<label>.npz (bus volts + rate) and a .png.
--ratio is the divider ratio (R1+R2)/R2, 11 for 100k/10k.
"""

import argparse
import datetime
import pathlib
import socket
import struct
import time

import numpy as np

from busanalysis import save_and_report

TCP_PORT = 3333
BEACON_PORT = 3334
OUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "captures"


def find_board(timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", BEACON_PORT))
    sock.settimeout(timeout)
    try:
        while True:
            data, addr = sock.recvfrom(256)
            if data.startswith(b"therm-sniffer"):
                return addr[0]
    except socket.timeout:
        raise SystemExit(f"no beacon on UDP {BEACON_PORT} within {timeout}s "
                         "(firewall? board offline?) - try --host")
    finally:
        sock.close()


def recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("board closed the connection")
        buf += chunk
    return bytes(buf)


def capture(host, seconds):
    sock = socket.create_connection((host, TCP_PORT), timeout=5)
    if recv_exact(sock, 7) != b"THERM32":
        raise SystemExit("unexpected hello: wrong firmware?")
    (n,) = struct.unpack("<H", recv_exact(sock, 2))
    cal_mv = np.array(struct.unpack(f"<{n}H", recv_exact(sock, n * 2)), dtype=np.float32)
    cal_raw = np.minimum(np.arange(n) * 64, 4095).astype(np.float32)

    blocks, stamps = [], []
    end = time.monotonic() + seconds
    try:
        while time.monotonic() < end:
            hdr = recv_exact(sock, 8)
            if hdr[:2] != b"TS":
                raise SystemExit(f"stream out of sync: {hdr!r}")
            n, t_us = struct.unpack("<HI", hdr[2:])
            data = recv_exact(sock, n * 2)
            blocks.append(np.frombuffer(data, dtype="<u2"))
            stamps.append(t_us)
    except (ConnectionError, socket.timeout) as e:
        print(f"warning: stream ended early ({e}), keeping {len(blocks)} blocks")
    sock.close()
    if len(blocks) < 3:
        raise SystemExit("not enough data received")
    # The first block may hold samples queued before the connection.
    return cal_raw, cal_mv, blocks[1:], stamps[1:]


DMA_SAMPLES = 16 * 1024  # firmware dma_buf_count * dma_buf_len


def sample_rate(blocks, stamps):
    """Real rate from a linear fit of block timestamps vs samples received.

    Blocks are often read late (the loop stalls while Wi-Fi sends) and then
    catch up from the DMA queue, so single late blocks are not losses.
    Samples can only be lost if a stall outlasts the DMA queue: returns
    whether the worst stall came close to that.
    """
    t = np.cumsum(np.r_[0, (np.diff(np.array(stamps, dtype=np.int64)) % 2**32)])
    cum = np.cumsum([0] + [len(b) for b in blocks[1:]])
    fit = np.polyfit(cum, t, 1)
    rate = 1e6 / fit[0]
    res = t - np.polyval(fit, cum)
    worst_stall = (res.max() - res.min()) / 1e6
    return rate, worst_stall > 0.8 * DMA_SAMPLES / rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label", help="what you did during the capture, e.g. idle")
    ap.add_argument("--seconds", type=float, default=20)
    ap.add_argument("--host", help="board IP (skip beacon discovery)")
    ap.add_argument("--ratio", type=float, default=11.0)
    ap.add_argument("--find-timeout", type=float, default=15)
    args = ap.parse_args()

    host = args.host or find_board(args.find_timeout)
    print(f"board {host}, capturing {args.seconds:g}s '{args.label}'...")
    cal_raw, cal_mv, blocks, stamps = capture(host, args.seconds)
    rate, maybe_lost = sample_rate(blocks, stamps)
    if maybe_lost:
        print("warning: a Wi-Fi stall came close to the DMA queue size, samples may be lost")

    raw = np.concatenate(blocks).astype(np.float32)
    volts = np.interp(raw, cal_raw, cal_mv) / 1000 * args.ratio

    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    save_and_report(OUT_DIR / f"{stamp}_{args.label}.npz", volts, rate, args.seconds)


if __name__ == "__main__":
    main()
