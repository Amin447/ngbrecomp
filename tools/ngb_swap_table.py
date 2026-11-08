"""Build enemy_swap_data.csv: everything needed to bring an enemy into another stage.

Scans the character load list (stry_dat section 2, read by sub_002EE0D0) of every stage script
(s_*.sty story stages and m_*.sty missions) in the game's *_cmn.afs archives. A list is a run of
6-byte records {u8 pool, u8 0, u16 key, u8, u8}; pool 0 = a character (key = type), and the pool
1/2 records right after it are that character's extras (weapons, projectiles, effects). Spawn
counts come from stage-script op 0x5b (a, TYPE, ...).

Output columns: see FIELDS. Run: python -I ngb_swap_table.py
"""
import collections, csv, glob, os, struct

G = "C:/Users/10/AppData/Local/NinjaGaidenBlack/game/"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IDS = {int(r["id"]): r for r in csv.DictReader(open(os.path.join(ROOT, "text", "char_ids.csv")))}
NGB = {int(r["Type"], 16): r for r in csv.DictReader(open(os.path.join(ROOT, "enemy_types.csv"), encoding="utf-8"))}
ARCHIVE_NAMES = {"yasik": "Ch1 mansion (yasik)", "ssato": "village (ssato)", "zppln": "airship (zppln)",
                 "tln_a": "Tairon A (tln_a)", "tln_b": "Tairon B (tln_b)", "suiro": "waterway (suiro)",
                 "stdim": "stadium (stdim)", "tomb": "tomb", "cave": "cave", "chrch": "church (chrch)",
                 "rail": "rail", "hori": "hori", "boff": "boff", "pyrmd": "pyramid (pyrmd)",
                 "makai": "Vigoor/makai", "hell": "hell (missions)", "tower": "tower"}


def scripts():
    for fn in sorted(glob.glob(G + "*_cmn.afs")):
        f = open(fn, "rb"); h = f.read(8)
        if h[:3] != b"AFS":
            continue
        n = struct.unpack_from("<I", h, 4)[0]; tab = f.read(8 * n + 8)
        noff, nsz = struct.unpack_from("<II", tab, 8 * n)
        if not noff:
            continue
        f.seek(noff); nt = f.read(nsz)
        for i in range(n):
            nm = nt[48 * i:48 * i + 32].split(b"\0")[0].decode("latin1")
            if not nm.endswith(".sty"):
                continue
            off, sz = struct.unpack_from("<II", tab, 8 * i)
            f.seek(off); d = f.read(sz)
            if d[:8] == b"stry_dat":
                yield os.path.basename(fn), nm, d


def load_groups(d):
    """(type, extras tuple) for every character record in section 2."""
    t = struct.unpack_from("<I", d, 0x18)[0]
    s2 = struct.unpack_from("<I", d, t + 8)[0]
    seen, out = set(), []
    for p in range(s2, len(d) - 12, 2):
        pool, b1, key = struct.unpack_from("<BBH", d, p)
        if pool != 0 or b1 != 0 or not (1 <= key <= 0x88):
            continue
        np, nb = d[p + 6], d[p + 7]
        if np > 2 or nb != 0:
            continue
        ex, r = [], p + 6
        while r + 6 <= len(d):
            a, b, k = struct.unpack_from("<BBH", d, r)
            if a != 2 or b != 0 or k > 0x300:   # stop at the first pool-1 item (stage pickups)
                break
            ex.append((a, k)); r += 6
        if (p - s2) in seen:
            continue
        seen.add(p - s2)
        out.append((key, tuple(ex)))
    return out


def spawns(d):
    a, e = struct.unpack_from("<2I", d, 0x20)
    W = struct.unpack_from(f"<{(e - a) // 4}I", d, a)
    c = collections.Counter()
    for i, w in enumerate(W[:-3]):
        if w == 0x8200005B and not (W[i + 2] >> 24) and W[i + 2] <= 0x88:
            c[W[i + 2]] += 1
    return c


extras = collections.defaultdict(collections.Counter)   # type -> Counter(extras tuple)
loaded_in = collections.defaultdict(set)
spawned_in = collections.defaultdict(collections.Counter)
for arc, nm, d in scripts():
    stage = f"{arc[:-8]}:{nm[:-4]}"
    for key, ex in load_groups(d):
        extras[key][ex] += 1
        loaded_in[key].add(stage)
    for key, k in spawns(d).items():
        spawned_in[key][stage] += k


def name(k):
    r = IDS.get(k)
    return (r["enum"], r["display"]) if r else ("", "")


def fmt(ex):
    return ",".join(f"{p}:{k:#x}" for p, k in ex)


FIELDS = ["Type", "Type (dec)", "Sigma enum", "Sigma name", "NGB description", "Model file",
          "Extras (pool:key)", "load_chars value", "Sometimes also (count/lists)", "Lists seen", "Loaded in (stage scripts)",
          "Areas", "Spawned in (op 0x5b counts)", "Photo"]
rows = []
for k in sorted(set(extras) | set(NGB)):
    if k == 0 or k > 0x88:
        continue
    en, disp = name(k)
    ng = NGB.get(k, {})
    total = sum(extras[k].values())
    if total > 1000:   # keys 1/2 match random data, not real lists
        extras[k].clear(); loaded_in[k].clear(); total = 0
    cnt = collections.Counter(e for ex, n in extras[k].items() for e in set(ex) for _ in range(n))
    order = []
    for ex, _ in extras[k].most_common():
        for e in ex:
            if e not in order: order.append(e)
    best = tuple(e for e in order if cnt[e] * 2 >= total)          # in at least half the lists
    sometimes = [f"{p}:{x:#x} ({cnt[(p, x)]}/{total})" for p, x in order if (p, x) not in best]
    others = sometimes
    stages = sorted(loaded_in[k])
    areas = sorted({s.split(":")[0] for s in stages})
    rows.append({
        "Type": f"0x{k:02X}", "Type (dec)": k, "Sigma enum": en, "Sigma name": disp,
        "NGB description": ng.get("What it is", ""), "Model file": ng.get("Model file", ""),
        "Extras (pool:key)": fmt(best),
        "load_chars value": ",".join([f"{k:#x}"] + [f"{p}:{x:#x}" for p, x in best]) if (stages or ng) else "",
        "Lists seen": total, "Sometimes also (count/lists)": ", ".join(others),
        "Loaded in (stage scripts)": " ".join(s.split(":")[1] for s in stages),
        "Areas": ", ".join(ARCHIVE_NAMES.get(a, a) for a in areas),
        "Spawned in (op 0x5b counts)": " ".join(f"{s.split(':')[1]}x{n}" for s, n in spawned_in[k].most_common(8)),
        "Photo": ng.get("Photo", ""),
    })
out = os.path.join(ROOT, "enemy_swap_data.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
    w.writeheader(); w.writerows(rows)
print(len(rows), "rows ->", out)
for r in rows:
    if r["Type"] in ("0x0E", "0x17", "0x44", "0x56", "0x6B", "0x5D"):
        print(r["Type"], r["Sigma enum"], "|", r["load_chars value"], "|", r["Sometimes also (count/lists)"][:90])
