#!/usr/bin/env python3
"""Name and tag the game's functions from what the code itself shows, without playing.

  tools/static_names.py                 writes docs/static_map.tsv and prints a summary

Sources (all produced by tools/pipeline.sh or kept in this repo):
  - docs/function_map.md                 names worked out by hand or from recordings
  - tools/d3d_symbols.txt, dsound_symbols.txt   the Direct3D / DirectSound functions
  - the CRI middleware's error messages, which carry its own function names
    ("adxt_StartSj: parameter error" names the function that prints it)
  - Xbox kernel calls (NtReadFile, ...) and the strings each function uses
  - reads of known memory (Ryu's object, health, the controller, ...)
  - the call graph: a function inside a library's address range whose calls stay
    in that library belongs to it; a function only reaching named functions of
    one area gets that area's tag.
"""
import bisect
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "xboxrecomp" / "tools"
MEMORY_TAGS = [                     # (from, to, tag) -- from docs/function_map.md's memory table
    (0x4B4E50, 0x4B7650, "ryu-object"),
    (0x4B5710, 0x4B5720, "ryu-position"),
    (0x58A3A0, 0x58A3A0 + 0x210 * 16, "health-blocks"),
    (0x589570, 0x589574, "essence"),
    (0x5895E2, 0x5895EA, "ut-charge"),
    (0x7F1A94, 0x7F1A94 + 24, "checksum-flags"),
    (0xD219A8, 0xD219A8 + 0x78 * 4, "pad"),
    (0xDB9C6E, 0xDB9C72, "event"),
    (0xDB9477, 0xDB9577, "watched-events"),
    (0xDB9E9C, 0xDB9EA0, "char-control"),
    (0xDB9F84, 0xDB9F88, "action-input"),
    (0xDB98E4, 0xDB98E8, "item-table"),
    (0xDB5E24, 0xDB5E28, "item-table"),
    (0x954698, 0x954730, "render-lists"),
]
CRI_NAME = re.compile(r"\b((?:adx[a-z]?|ahx|mw[A-Z]|wx|sfd|cri|sj|ads|xe)[A-Za-z0-9]*_?[A-Za-z0-9]+)\b")


def h(x):
    return int(x, 16) if isinstance(x, str) else x


def load():
    funcs = json.loads((OUT / "disasm/output/functions.json").read_text())
    starts = sorted(h(f["start"]) for f in funcs)
    ends = {h(f["start"]): h(f["end"]) for f in funcs}
    xrefs = json.loads((OUT / "disasm/output/xrefs.json").read_text())
    strings = json.loads((OUT / "disasm/output/strings.json").read_text())
    labels = json.loads((OUT / "disasm/output/labels.json").read_text())
    return starts, ends, xrefs, strings, labels


def owner(starts, ends, addr):
    i = bisect.bisect_right(starts, addr) - 1
    if i >= 0 and addr < ends[starts[i]]:
        return starts[i]
    return None


def main():
    starts, ends, xrefs, strings, labels = load()
    name, source = {}, {}
    tags = collections.defaultdict(set)
    calls = collections.defaultdict(set)
    callers = collections.defaultdict(set)
    uses_str = collections.defaultdict(list)

    # The call graph, kernel calls and memory reads
    kernel = {h(l["address"]): l["name"].replace("xbox_", "") for l in labels if l["type"] == "kernel_import"}
    mem_lo = [m[0] for m in MEMORY_TAGS]
    for x in xrefs:
        src = owner(starts, ends, h(x["from"]))
        if src is None:
            continue
        to = h(x["to"])
        if x["type"] == "call" and to in ends:
            calls[src].add(to)
            callers[to].add(src)
        elif x["type"] == "kernel_call":
            tags[src].add("kernel:" + kernel.get(to, f"{to:#x}"))
        elif x["type"] in ("data_read", "data_imm"):
            for lo, hi, tag in MEMORY_TAGS:
                if lo <= to < hi:
                    tags[src].add(tag)

    # Strings: CRI's own function names, file names, other text
    for s in strings:
        refs = [owner(starts, ends, h(r)) for r in s.get("referenced_from") or []]
        refs = [r for r in refs if r is not None]
        text = s["string"]
        for r in refs:
            uses_str[r].append(text)
        m = re.search(r"\(([A-Za-z_][A-Za-z0-9_]*)\)\s*\.?$", text) or \
            re.match(r"^E[0-9A-Za-z]+\s*:?\s*'?([a-z][A-Za-z0-9]*_?[A-Za-z0-9]+)[;:,( ]", text) or \
            re.match(r"^([a-z]{2,5}[A-Z_][A-Za-z0-9_]+)$", text)
        if m and len(set(refs)) == 1 and CRI_NAME.match(m.group(1)):
            r = refs[0]
            if r not in name:
                name[r], source[r] = m.group(1), "cri-string"
        if re.search(r"\.(afs|sfd|adx|aix|dat|xbx|bin|ins|xbe)\b", text, re.I):
            for r in set(refs):
                tags[r].add("file")

    # Symbol files and the hand-made map
    for fname, prefix in (("d3d_symbols.txt", "D3D8LTCG__"), ("dsound_symbols.txt", "DSOUND__")):
        for line in (ROOT / "tools" / fname).read_text().splitlines():
            m = re.match(r"(\S+)\s*=\s*(0x[0-9a-fA-F]+)", line)
            if m:
                va = int(m.group(2), 16)
                name[va], source[va] = m.group(1).replace(prefix, ""), "symbols"
    fmap = ROOT / "docs" / "function_map.md"
    for line in fmap.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*sub_([0-9A-F]{8})\s*\|\s*([^|]+)\|\s*(\w+)", line)
        if m:
            va = int(m.group(1), 16)
            name[va], source[va] = m.group(2).strip(), "map:" + m.group(3)

    # Library areas: the address span of each named library, tightened to where its names sit
    def span(pred):
        vas = sorted(va for va in name if pred(va))
        if len(vas) < 3:
            return None
        lo, hi = vas[len(vas) // 20], vas[-1 - len(vas) // 20]
        return lo, hi
    areas = {
        "CRI middleware": span(lambda va: source.get(va) == "cri-string"),
        "Direct3D": span(lambda va: source.get(va) == "symbols" and "DSOUND" not in name[va]
                         and not name[va].startswith("IDirectSound")),
        "DirectSound": span(lambda va: source.get(va) == "symbols" and name[va].startswith("IDirectSound")),
    }
    area_of = {}
    for area, sp in areas.items():
        if not sp:
            continue
        for va in starts:
            if sp[0] <= va <= sp[1]:
                area_of.setdefault(va, area)

    # Propagate: a function whose named callees all share one area (and that area's tag) gets it
    for _ in range(3):
        for va in starts:
            if va in area_of:
                continue
            areas_called = {area_of.get(c) for c in calls[va]}
            areas_called.discard(None)
            if len(areas_called) == 1 and calls[va] and all(c in area_of for c in calls[va]):
                base = next(iter(areas_called)).replace(" (wrapper)", "")
                area_of[va] = base + " (wrapper)"

    for va in starts:
        for c in calls[va]:
            if c in name and source.get(c, "").startswith(("symbols", "cri")):
                tags[va].add("calls " + ("D3D" if source[c] == "symbols" and not name[c].startswith("IDirectSound")
                                         else "DSound" if name[c].startswith("IDirectSound") else "CRI"))

    # Write
    rows = []
    for va in starts:
        # Only file names: the map is kept in the repository, the game's own text is not.
        strs = [t for t in uses_str.get(va, [])
                if re.search(r"\.(afs|sfd|adx|aix|dat|xbx|bin|ins|xbe)\b", t, re.I)][:3]
        rows.append((va, ends[va] - va, name.get(va, ""), source.get(va, ""), area_of.get(va, ""),
                     ",".join(sorted(tags[va])), len(callers[va]), len(calls[va]),
                     " | ".join(repr(t)[:50] for t in strs)))
    out = ROOT / "docs" / "static_map.tsv"
    with out.open("w", encoding="utf-8") as f:
        f.write("function\tsize\tname\tname_source\tarea\ttags\tcallers\tcallees\tstrings\n")
        for va, size, n, src, area, tg, ncr, nce, strs in rows:
            f.write(f"sub_{va:08X}\t{size}\t{n}\t{src}\t{area}\t{tg}\t{ncr}\t{nce}\t{strs}\n")

    named = sum(1 for r in rows if r[2])
    in_area = sum(1 for r in rows if r[4])
    tagged = sum(1 for r in rows if r[5])
    print(f"{len(rows)} functions: {named} named, {in_area} placed in a library area, "
          f"{tagged} with tags, {sum(1 for r in rows if r[2] or r[4] or r[5])} with anything")
    print("by name source:", dict(collections.Counter(r[3].split(':')[0] for r in rows if r[3])))
    print("areas:", {a: (f"{sp[0]:#x}-{sp[1]:#x}" if sp else None) for a, sp in areas.items()})
    print("area counts:", dict(collections.Counter(r[4] for r in rows if r[4])))
    tc = collections.Counter(t for r in rows for t in r[5].split(",") if t)
    print("top tags:", tc.most_common(25))
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
