#!/usr/bin/env python3
"""Analyse a function recording from src/func_recorder.c (F9 in the game).

  tools/rec_analyze.py REC.bin                      summary, segments split at F6 markers
  tools/rec_analyze.py REC.bin --compare 0 1        functions in segment 1 but not (or rarely) in 0
  tools/rec_analyze.py REC.bin --compare 0,2 1,3    segments 1 and 3 against 0 and 2
  tools/rec_analyze.py REC.bin --buttons            functions that follow each pad bit
  tools/rec_analyze.py REC.bin --moving             functions that follow Ryu moving
  tools/rec_analyze.py REC.bin --range 10-20        segments by seconds instead (repeatable)

Known names come from docs/function_map.md (lines starting "| sub_XXXXXXXX |" or "0xXXXXXXXX").
"""
import argparse
import math
import pathlib
import re
import struct
import sys

PAD_SIZE = 0x78
VERSION = 1
DIGITAL = ["dpad up", "dpad down", "dpad left", "dpad right", "start", "back",
           "left stick click", "right stick click"]
ANALOG = ["A (jump)", "B (projectile)", "X (attack)", "Y (heavy attack)", "Black", "White",
          "LT (guard)", "RT (center camera)"]


def load(path):
    data = pathlib.Path(path).read_bytes()
    if data[:7] != b"NGBREC1":
        sys.exit(f"{path}: not a recording")
    global VERSION
    (VERSION,) = struct.unpack_from("<I", data, 8)
    off = 12
    frames = []
    while off + 32 + PAD_SIZE + 4 <= len(data):
        magic, frame, us, flags = struct.unpack_from("<IIQI", data, off)
        if magic != 0x304D5246:
            break
        off += 20
        pos = struct.unpack_from("<3f", data, off)
        off += 12
        pad = data[off:off + PAD_SIZE]
        off += PAD_SIZE
        (n,) = struct.unpack_from("<I", data, off)
        off += 4
        if off + 8 * n > len(data):
            break                          # a frame cut off when the game was closed
        calls = dict(struct.iter_unpack("<II", data[off:off + 8 * n]))
        off += 8 * n
        frames.append({"frame": frame, "t": us / 1e6, "marker": flags & 1, "pos": pos,
                       "pad": pad, "calls": calls})
    return frames


def load_names(root):
    names = {}
    static = root / "docs" / "static_map.tsv"      # tools/static_names.py: names, areas and tags
    if static.exists():
        for line in static.read_text(encoding="utf-8").splitlines()[1:]:
            col = line.split("\t")
            if len(col) < 6:
                continue
            label = col[2] or (col[4] and f"[{col[4]}]") or (col[5] and f"[{col[5][:40]}]")
            if label:
                names[int(col[0][4:], 16)] = label
    p = root / "docs" / "function_map.md"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*(?:sub_|0x)([0-9A-Fa-f]{8})\s*\|\s*([^|]+)\|", line)
            if m:
                names[int(m.group(1), 16)] = m.group(2).strip()
    return names


def segments_from_markers(frames):
    cuts = [0] + [i for i, f in enumerate(frames) if f["marker"]] + [len(frames)]
    cuts = sorted(set(cuts))
    return [(a, b) for a, b in zip(cuts, cuts[1:]) if b > a]


def segments_from_ranges(frames, ranges):
    segs = []
    for r in ranges:
        lo, hi = (float(x) for x in r.split("-"))
        idx = [i for i, f in enumerate(frames) if lo <= f["t"] < hi]
        if idx:
            segs.append((idx[0], idx[-1] + 1))
    return segs


def presence(frames, seg):
    """Per function: fraction of the segment's frames it ran in, and calls per frame."""
    a, b = seg
    n = b - a
    seen, calls = {}, {}
    for f in frames[a:b]:
        for va, c in f["calls"].items():
            seen[va] = seen.get(va, 0) + 1
            calls[va] = calls.get(va, 0) + c
    return {va: (seen[va] / n, calls[va] / n) for va in seen}


def label(va, names):
    return f"sub_{va:08X}" + (f"  ({names[va]})" if va in names else "")


def cmd_summary(frames, segs, names):
    dur = frames[-1]["t"] - frames[0]["t"] if len(frames) > 1 else 0
    allf = set()
    for f in frames:
        allf.update(f["calls"])
    print(f"{len(frames)} frames, {dur:.1f} s ({len(frames) / dur if dur else 0:.1f} fps), "
          f"{sum(f['marker'] for f in frames)} markers, {len(allf)} distinct functions")
    for i, (a, b) in enumerate(segs):
        fa, fb = frames[a], frames[b - 1]
        moved = math.dist(fa["pos"], fb["pos"])
        p = presence(frames, (a, b))
        print(f"  segment {i}: frames {a}-{b - 1}, {fa['t']:.1f}-{fb['t']:.1f} s, "
              f"{len(p)} functions, Ryu moved {moved:.1f}")


def cmd_compare(frames, segs, base_ids, test_ids, names, top):
    def merged(ids):
        idx = []
        for i in ids:
            a, b = segs[i]
            idx.extend(range(a, b))
        n = len(idx)
        seen, calls = {}, {}
        for i in idx:
            for va, c in frames[i]["calls"].items():
                seen[va] = seen.get(va, 0) + 1
                calls[va] = calls.get(va, 0) + c
        return {va: (seen[va] / n, calls[va] / n) for va in seen}

    base, test = merged(base_ids), merged(test_ids)
    rows = []
    for va, (frac, cpf) in test.items():
        bfrac, bcpf = base.get(va, (0.0, 0.0))
        rows.append((frac - bfrac, frac, bfrac, cpf, bcpf, va))
    rows.sort(reverse=True)
    print(f"Functions more present in {test_ids} than in {base_ids} (frames ran in, calls a frame):")
    print(f"  {'gain':>6} {'test':>6} {'base':>6} {'calls':>8} {'base':>8}  function")
    for gain, frac, bfrac, cpf, bcpf, va in rows[:top]:
        if gain <= 0.05:
            break
        print(f"  {gain:6.2f} {frac:6.2f} {bfrac:6.2f} {cpf:8.1f} {bcpf:8.1f}  {label(va, names)}")
    only = [r for r in rows if r[2] == 0]
    print(f"\n{len(only)} functions ran in {test_ids} and never in {base_ids}.")
    gone = sorted(((bfrac, va) for va, (bfrac, _) in base.items() if va not in test), reverse=True)
    if gone:
        print(f"{len(gone)} ran in {base_ids} and never in {test_ids}; most present:")
        for bfrac, va in gone[:min(top, 15)]:
            print(f"  {bfrac:6.2f}  {label(va, names)}")


def phi(xs, ys):
    n = len(xs)
    a = sum(1 for x, y in zip(xs, ys) if x and y)
    b = sum(1 for x, y in zip(xs, ys) if x and not y)
    c = sum(1 for x, y in zip(xs, ys) if not x and y)
    d = n - a - b - c
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (a * d - b * c) / den if den else 0.0


def follow(frames, signal, names, top, title):
    if sum(signal) in (0, len(signal)):
        print(f"{title}: no change in this recording")
        return
    funcs = set()
    for f in frames:
        funcs.update(f["calls"])
    scored = []
    for va in funcs:
        ran = [va in f["calls"] for f in frames]
        if sum(ran) in (0, len(ran)):
            continue
        scored.append((phi(signal, ran), va))
    scored.sort(reverse=True)
    print(f"{title} (on in {sum(signal)}/{len(signal)} frames):")
    for r, va in scored[:top]:
        if r < 0.3:
            break
        print(f"  {r:5.2f}  {label(va, names)}")


def cmd_buttons(frames, names, top):
    if VERSION < 2:
        print("This recording has no controller data (recorded before version 2).")
        return
    for bit, name in enumerate(DIGITAL):
        sig = [(struct.unpack_from("<H", f["pad"], 0)[0] >> bit) & 1 for f in frames]
        if 3 <= sum(sig) <= len(sig) - 3:
            follow(frames, sig, names, top, f"{name} held")
            print()
    for i, name in enumerate(ANALOG):
        held = [int(f["pad"][2 + i] > 0x20) for f in frames]
        press = [0] + [int(b and not a) for a, b in zip(held, held[1:])]
        near = [int(any(press[max(0, k - 1):k + 6])) for k in range(len(press))]
        if sum(press) >= 2:
            follow(frames, near, names, top, f"{name}: the frames just after a press ({sum(press)} presses)")
            print()
        if 3 <= sum(held) <= len(held) - 3:
            follow(frames, held, names, top, f"{name} held")
            print()


def cmd_moving(frames, names, top):
    sig = [0] + [int(math.dist(a["pos"], b["pos"]) > 0.01) for a, b in zip(frames, frames[1:])]
    follow(frames, sig, names, top, "Ryu moving")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rec")
    ap.add_argument("--compare", nargs=2, metavar=("BASE", "TEST"))
    ap.add_argument("--buttons", action="store_true")
    ap.add_argument("--moving", action="store_true")
    ap.add_argument("--range", action="append", default=[])
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()

    frames = load(args.rec)
    if not frames:
        sys.exit("no frames")
    names = load_names(pathlib.Path(__file__).resolve().parent.parent)
    segs = segments_from_ranges(frames, args.range) if args.range else segments_from_markers(frames)
    cmd_summary(frames, segs, names)
    print()
    if args.compare:
        ids = [[int(x) for x in s.split(",")] for s in args.compare]
        cmd_compare(frames, segs, ids[0], ids[1], names, args.top)
    if args.buttons:
        cmd_buttons(frames, names, args.top)
    if args.moving:
        cmd_moving(frames, names, args.top)


if __name__ == "__main__":
    main()
