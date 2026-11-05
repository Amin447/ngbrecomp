#!/usr/bin/env python3
"""Summarise an action log from src/action_log.c (Actions.bat, F9).

  tools/action_summary.py LOG.tsv                Ryu's actions by number, who asked for them, buttons held
  tools/action_summary.py LOG.tsv --func sub_X   the calls of one watched function, grouped by caller

The caller is the function holding the call's return address (from the pipeline's
xboxrecomp/tools/disasm/output/functions.json); names come from docs/function_map.md and
docs/static_map.tsv, as in tools/rec_analyze.py.
"""
import argparse
import bisect
import collections
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ra", ROOT / "tools" / "rec_analyze.py")
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

ANALOG = ["A", "B", "X", "Y", "Black", "White", "LT", "RT"]
DIGITAL = ["Up", "Down", "Left", "Right", "Start", "Back", "LS", "RS"]


def owner_table():
    funcs = json.loads((ROOT / "xboxrecomp/tools/disasm/output/functions.json").read_text())
    spans = sorted((int(f["start"], 16), int(f["end"], 16)) for f in funcs)
    starts = [s for s, _ in spans]

    def owner(addr):
        i = bisect.bisect_right(starts, addr) - 1
        return spans[i][0] if i >= 0 and addr < spans[i][1] else None
    return owner


def buttons(row):
    b = int(row["buttons"], 16)
    an = bytes.fromhex(row["analog"])
    held = [n for i, n in enumerate(DIGITAL) if b >> i & 1] + [n for i, n in enumerate(ANALOG) if an[i] > 0x20]
    return "+".join(held) or "-"


def load(path):
    rows = []
    lines = pathlib.Path(path).read_text().splitlines()
    head = lines[0].split("\t")
    for line in lines[1:]:
        if line.startswith("#"):
            continue
        col = line.split("\t")
        if len(col) == len(head):
            rows.append(dict(zip(head, col)))
    return rows


def label(va, names):
    return ra.label(va, names) if va is not None else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--func", default="sub_00039870")
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--changes", action="store_true", help="Ryu's action changes and who made them")
    args = ap.parse_args()
    rows = load(args.log)
    names = ra.load_names(ROOT)
    owner = owner_table()
    counts = collections.Counter(r["function"] for r in rows)
    print(f"{len(rows)} calls logged:", ", ".join(f"{label(int(f[4:], 16), names)} x{n}"
                                                    for f, n in counts.most_common()))
    print()

    if args.changes:
        ch = [r for r in rows if r["function"] == "action"]
        print(f"{len(ch)} changes of Ryu's action byte (0x4968B4). By new action:")
        print(f"  {'action':>6} {'times':>5} {'first s':>8}  buttons (most common)          from (old)      changed in")
        by = collections.defaultdict(list)
        for r in ch:
            by[int(r["ecx"], 16)].append(r)
        for act in sorted(by):
            rs = by[act]
            btn = collections.Counter(buttons(r) for r in rs).most_common(2)
            old = collections.Counter(int(r["eax"], 16) for r in rs).most_common(3)
            who = collections.Counter(int(r["return"], 16) for r in rs).most_common(2)
            print(f"  0x{act:02X}   {len(rs):5} {float(rs[0]['seconds']):8.1f}  "
                  f"{', '.join(f'{b} x{n}' for b, n in btn):30} "
                  f"{' '.join(f'{o:02X}' for o, _ in old):15} "
                  f"{'; '.join(label(w, names) for w, _ in who)}")
        return

    sel = [r for r in rows if r["function"] == args.func]
    if args.func == "sub_00039870":
        print("Ryu's actions (ax at set-action), by number:")
        print(f"  {'action':>6} {'times':>5} {'first s':>8}  buttons held (most common)   requested by")
        by = collections.defaultdict(list)
        for r in sel:
            by[int(r["eax"], 16) & 0xFFFF].append(r)
        for act in sorted(by, key=lambda a: float(by[a][0]["seconds"])):
            rs = by[act]
            btn = collections.Counter(buttons(r) for r in rs).most_common(2)
            who = collections.Counter(owner(int(r["return"], 16)) for r in rs).most_common(2)
            print(f"  0x{act:04X} {len(rs):5} {float(rs[0]['seconds']):8.1f}  "
                  f"{', '.join(f'{b} x{n}' for b, n in btn):28} "
                  f"{'; '.join(label(w, names) for w, _ in who)}")
    else:
        print(f"Calls of {args.func} by caller:")
        by = collections.Counter(owner(int(r["return"], 16)) for r in sel)
        for w, n in by.most_common(args.top):
            print(f"  {n:5}  {label(w, names)}")


if __name__ == "__main__":
    main()
