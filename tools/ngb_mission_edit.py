"""NGB mission editor (2026-11-08). Edits a mission script in place (same size) - see docs/mission_anatomy.md.

  python -I ngb_mission_edit.py show <mission.sty>
  python -I ngb_mission_edit.py edit <mission.sty> -o <out.sty> [--swap OLD:NEW ...] [--hp 75:90,50:60,25:30]
                                     [--repeat RULE:N] [--alive RULE:N] [--move RULE:x,y,z;x,y,z]

show : rules that spawn enemies (type, position), boss checks (health %, death), and the per-zone load list.
edit : --swap OLD:NEW   every enemy reference of type OLD becomes NEW (spawns, checks, health bars) and the load
                         list record of OLD (with its extras) is replaced by NEW with NEW's extras from
                         enemy_swap_data.csv. Several --swap allowed.
       --hp A:B,...     boss health thresholds (op 0x1c 1 A.0) A% -> B% (wave triggers).
       --repeat RULE:N  rule runs up to N times (0x02 n; 255 = forever)  - how many enemies a wave rule makes
       --alive RULE:N   spawn only while fewer than N enemies are alive (0x14 mode N)
       --move RULE:...  fixed spawn positions (0x66 x y z) of that rule, in order
The output must not be bigger than the input (the game reads missions at a fixed size); the tool refuses otherwise.
Install with afs_replace.py <Cache>/<area>_cmn.afs <m_NN...sty> <out.sty>.
"""
import argparse, csv, os, struct, sys

OP = 0x82000000
HERE = os.path.dirname(os.path.abspath(__file__))
SWAP_CSV = os.path.join(os.path.dirname(HERE), "enemy_swap_data.csv")


def is_op(w):
    return w >> 24 == 0x82 and (w & 0xFFFFFF) < 0x200


def f32(w):
    return struct.unpack("<f", struct.pack("<I", w))[0]


class Mission:
    def __init__(self, path):
        self.d = bytearray(open(path, "rb").read())
        n = struct.unpack_from("<I", self.d, 0x10)[0]
        t = struct.unpack_from("<I", self.d, 0x18)[0]
        self.secs = list(struct.unpack_from(f"<{n}I", self.d, t))
        self.s0, self.s1, self.s2 = self.secs[0], self.secs[1], self.secs[2]
        h = struct.unpack_from("<17I", self.d, self.s0)
        self.rules, p = [], self.s0 + h[6]
        while struct.unpack_from("<I", self.d, p)[0]:
            self.rules.append(self.s0 + struct.unpack_from("<I", self.d, p)[0]); p += 4

    def words(self, at):
        out, p = [], at
        while True:
            w = struct.unpack_from("<I", self.d, p)[0]; out.append((p, w)); p += 4
            if w == OP | 0x142:
                return out

    def loads(self):
        """{zone: [(pool, key), ...]} and the raw layout for rewriting."""
        L, p, hdr = self.d, self.s2, []
        while True:
            z, o = struct.unpack_from("<II", L, p); p += 8
            if z == 0xFFFF:
                break
            hdr.append((z, o))
        out = {}
        for z, o in hdr:
            q, r = self.s2 + o, []
            while struct.unpack_from("<H", L, q)[0] != 0xFF:
                r.append(struct.unpack_from("<2H", L, q)); q += 6
            out[z] = r
        return hdr, out

    def write_loads(self, lists):
        """Rewrite section 2 from {zone: [(pool, key)]} keeping the zone order; must fit the old section."""
        hdr, _ = self.loads()
        body = b""
        offs = {}
        # records start where the first zone's list started (normally right after the 0xFFFF pair)
        end_hdr = self.s2 + min(o for _, o in hdr)
        cur = end_hdr - self.s2
        for z, _ in hdr:
            offs[z] = cur
            recs = b"".join(struct.pack("<3H", pl, k, 0) for pl, k in lists[z]) + struct.pack("<3H", 0xFF, 0, 0)
            body += recs; cur += len(recs)
        size = len(self.d) - self.s2
        if (end_hdr - self.s2) + len(body) > size:
            raise SystemExit(f"load list too big: {(end_hdr - self.s2) + len(body)} > {size} bytes")
        sec = bytearray(self.d[self.s2:end_hdr])
        for i, (z, _) in enumerate(hdr):
            struct.pack_into("<II", sec, 8 * i, z, offs[z])
        sec += body
        sec += b"\0" * (size - len(sec))
        self.d[self.s2:] = sec


def rule_info(W):
    """repeat count, alive limits, spawns (type, where) and boss checks of one rule (word list)."""
    rep = next((W[j + 1] for j in range(len(W) - 1) if W[j] == OP | 0x02), None)
    alive = [(W[j + 1], W[j + 2]) for j in range(len(W) - 2) if W[j] == OP | 0x14]
    spawns, checks = [], []
    for j in range(len(W) - 3):
        if W[j] == OP | 0x5B and W[j + 1] == 0 and W[j + 2]:
            where = "?"
            for k in range(j + 4, min(j + 14, len(W) - 3)):
                if W[k] == OP | 0x66:
                    where = "(%.1f, %.1f, %.1f)" % tuple(f32(W[k + 1 + i]) for i in range(3)); break
                if W[k] == OP | 0x6B:
                    where = f"one of {W[k+3]} points" + (" (random)" if W[k + 1] == 2 else f" (mode {W[k+1]})"); break
                if W[k] == OP | 0x5B or W[k] == OP | 0x56:
                    break
            spawns.append(f"{W[j+2]:#x} at {where}")
        if W[j] == OP | 0x0F and W[j + 1] == 0 and W[j + 2]:
            if OP | 0x1C in W[j + 3:j + 6]:
                i = W.index(OP | 0x1C, j + 3); checks.append(f"when {W[j+2]:#x} health < {f32(W[i+2]):.0f}%")
            elif OP | 0x1A in W[j + 3:j + 6]:
                checks.append(f"{W[j+2]:#x} dead/alive check")
    return rep, alive, spawns, checks


def show(m):
    print(f"{len(m.rules)} rules, file {len(m.d)} bytes")
    for k, at in enumerate(m.rules):
        W = [w for _, w in m.words(at)]
        zones = sorted({W[j + 1] for j in range(len(W) - 1) if W[j] == OP | 5})
        rep, alive, spawns, checks = rule_info(W)
        if spawns or checks:
            bits = []
            if spawns: bits.append("spawns " + ", ".join(spawns))
            bits += checks
            if alive: bits.append("only while fewer than " + "/".join(str(n) for _, n in alive) + " alive")
            if rep is not None: bits.append(f"runs up to {rep}x" if rep != 255 else "runs forever")
            print(f"rule {k:3d} zones {zones}: " + "; ".join(bits))
    _, L = m.loads()
    names = {}
    if os.path.exists(SWAP_CSV):
        for r in csv.DictReader(open(SWAP_CSV, encoding="utf-8")):
            names[int(r["Type"], 16)] = r["Sigma name"] or r["NGB description"]
    for z, recs in L.items():
        if recs:
            print(f"zone {z} loads: " + " ".join(f"{pl}:{k:#x}" + (f"({names[k]})" if pl == 0 and k in names else "")
                                                 for pl, k in recs))


def extras_of(t):
    for r in csv.DictReader(open(SWAP_CSV, encoding="utf-8")):
        if int(r["Type"], 16) == t:
            v = r["load_chars value"]
            return [tuple(int(x, 0) for x in e.split(":")) for e in v.split(",")[1:] if e]
    raise SystemExit(f"type {t:#x} not in enemy_swap_data.csv")


def edit_rules(m, repeat, alive, move):
    """repeat {rule: n}, alive {rule: n}, move {rule: [(x,y,z), ...]} (one position per spawn in that rule, in order)."""
    for k, at in enumerate(m.rules):
        Wp = m.words(at); W = [w for _, w in Wp]
        if k in repeat:
            j = next((j for j in range(len(W)) if W[j] == OP | 0x02), None)
            if j is None: raise SystemExit(f"rule {k} has no repeat count (op 0x02)")
            struct.pack_into("<I", m.d, Wp[j + 1][0], repeat[k]); print(f"rule {k}: runs up to {repeat[k]}x")
        if k in alive:
            js = [j for j in range(len(W)) if W[j] == OP | 0x14]
            if not js: raise SystemExit(f"rule {k} has no alive limit (op 0x14)")
            for j in js: struct.pack_into("<I", m.d, Wp[j + 2][0], alive[k])
            print(f"rule {k}: only while fewer than {alive[k]} alive")
        if k in move:
            spots = [j for j in range(len(W) - 3) if W[j] == OP | 0x66]
            for (x, y, z), j in zip(move[k], spots):
                struct.pack_into("<3f", m.d, Wp[j + 1][0], x, y, z)
            print(f"rule {k}: {min(len(spots), len(move[k]))} position(s) moved")


def edit(m, swaps, hp):
    n_ref = 0
    for at in m.rules:
        Wp = m.words(at)
        W = [w for _, w in Wp]
        for j in range(len(W) - 2):
            if not is_op(W[j]):
                continue
            if W[j + 1] == 0 and W[j + 2] in swaps:                          # (0, TYPE, ...) references
                struct.pack_into("<I", m.d, Wp[j + 2][0], swaps[W[j + 2]]); n_ref += 1
            if W[j] in (OP | 0x119, OP | 0x11B) and W[j + 1] in swaps:     # health bar ops (TYPE, ...)
                struct.pack_into("<I", m.d, Wp[j + 1][0], swaps[W[j + 1]]); n_ref += 1
            if W[j] == OP | 0x1C and W[j + 1] == 1:                          # health threshold
                v = round(f32(W[j + 2]))
                if v in hp:
                    struct.pack_into("<f", m.d, Wp[j + 2][0], float(hp[v]))
    hdr, L = m.loads()
    for z, recs in L.items():
        out, i = [], 0
        while i < len(recs):
            pl, k = recs[i]
            if pl == 0 and k in swaps:
                i += 1
                while i < len(recs) and recs[i][0] == 2:      # drop OLD's extras
                    i += 1
                new = swaps[k]
                if (0, new) not in recs and (0, new) not in out:   # NEW already loaded here: just drop OLD
                    out.append((0, new)); out += extras_of(new)
                continue
            out.append(recs[i]); i += 1
        L[z] = out
    m.write_loads(L)
    print(f"{n_ref} enemy references changed; load list rewritten")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["show", "edit"]); ap.add_argument("sty")
    ap.add_argument("-o"); ap.add_argument("--swap", action="append", default=[])
    ap.add_argument("--hp", default="")
    ap.add_argument("--repeat", action="append", default=[], help="RULE:N  rule runs up to N times (255 = forever)")
    ap.add_argument("--alive", action="append", default=[], help="RULE:N  spawn only while fewer than N alive")
    ap.add_argument("--move", action="append", default=[], help="RULE:x,y,z[;x,y,z...]  fixed spawn positions")
    a = ap.parse_args()
    m = Mission(a.sty)
    if a.cmd == "show":
        show(m); return
    size = len(m.d)
    swaps = dict(tuple(int(x, 0) for x in s.split(":")) for s in a.swap)
    hp = dict(tuple(int(x) for x in s.split(":")) for s in a.hp.split(",") if s)
    edit(m, swaps, hp)
    pairs = lambda L: {int(r.split(":")[0]): int(r.split(":")[1], 0) for r in L}
    move = {int(r.split(":")[0]): [tuple(float(v) for v in p.split(",")) for p in r.split(":")[1].split(";")] for r in a.move}
    edit_rules(m, pairs(a.repeat), pairs(a.alive), move)
    assert len(m.d) == size
    open(a.o, "wb").write(m.d)
    print(f"-> {a.o} ({len(m.d)} bytes, same as input)")


if __name__ == "__main__":
    main()
