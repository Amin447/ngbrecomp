"""List NGB missions (m_NN*.sty in *_cmn.afs) and the enemy types each spawns.

Stage-script VM words 0x82000000|op; gameplay spawn = op 0x5b(a, TYPE, ...) (confirmed in chapter 1).
Writes ngb_missions.csv: mission, script, archive, entry, enemies (type x count).
"""
import csv, glob, os, struct, collections
G = "C:/Users/10/AppData/Local/NinjaGaidenBlack/game"
HERE = os.path.dirname(os.path.abspath(__file__))
NAMES = {int(r["id"]): r["enum"][5:] for r in csv.DictReader(open(os.path.join(HERE, "..", "text", "char_ids.csv")))}

def entries(fn):
    f = open(fn, "rb"); h = f.read(8)
    if h[:3] != b"AFS": return
    n = struct.unpack_from("<I", h, 4)[0]; tab = f.read(8 * n + 8)
    noff, nsz = struct.unpack_from("<II", tab, 8 * n)
    if not noff: return
    f.seek(noff); nt = f.read(nsz)
    for i in range(n):
        off, sz = struct.unpack_from("<II", tab, 8 * i)
        yield i, nt[48 * i:48 * i + 32].split(b"\0")[0].decode("latin1"), off, sz, f

def spawns(data):
    a, e = struct.unpack_from("<2I", data, 0x20)
    W = struct.unpack_from(f"<{(e - a) // 4}I", data, a)
    c = collections.Counter()
    for i, w in enumerate(W[:-3]):
        if w == 0x8200005B and not (W[i + 2] >> 24):
            c[W[i + 2]] += 1
    return c

rows = []
for fn in sorted(glob.glob(G + "/*_cmn.afs")) + [G + "/hell_cmn.afs"]:
    for i, nm, off, sz, f in entries(fn) or []:
        if not (nm.startswith(("m_", "s_")) and nm.endswith(".sty")): continue
        f.seek(off); d = f.read(sz)
        if d[:8] != b"stry_dat": continue
        c = spawns(d)
        rows.append({"script": nm, "archive": os.path.basename(fn), "entry": i,
                     "mission": nm[2:4] if nm.startswith("m_") else "",
                     "enemies": " ".join(f"{NAMES.get(t, hex(t))}({t:#x})x{k}" for t, k in c.most_common())})
rows = list({(r["archive"], r["script"]): r for r in rows}.values())
rows.sort(key=lambda r: (r["mission"] == "", r["mission"], r["script"]))
with open(os.path.join(HERE, "ngb_missions.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["mission", "script", "archive", "entry", "enemies"]); w.writeheader(); w.writerows(rows)
for r in rows:
    if r["mission"]: print(r["mission"], r["script"], r["archive"], "|", r["enemies"])
