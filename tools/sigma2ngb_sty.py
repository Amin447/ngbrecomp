"""Convert a Sigma stage script (.sty, + optional .btl) into an NGB .sty (2026-11-08).

  python -I sigma2ngb_sty.py <sigma.sty> [<sigma.btl>] -o <out.sty> [--player 0] [--load-from <ngb.sty>]

What it does (rules in docs/sigma_extra_chapters.md):
  * renumbers every op word with sty_opmap.sigma_to_ngb;
  * Sigma-only ops it cannot express are replaced by a same-size no-op pair when they have 1 argument
    (0x56 0 = NGB action-group separator ... see NOOP) and reported; others abort;
  * player type 113 (I_REI, Rachel) -> --player (default 0 = Ryu) in spawn (0x5b) / check (0x0f) ops;
  * .btl battle blocks: keep blocks whose mask includes Normal (or that have no mask), drop the mask, the
    0x06..0x07 pre-section and the 0x08 / 0x09 markers, and append them to the .sty block list
    (blocks identical to an existing .sty block are skipped);
  * header fields 15/16 set to NGB's values;
  * --load-from: take section 2 (character load list) from an NGB script of the same area.
"""
import argparse, struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sty_opmap import sigma_to_ngb

OP = 0x82000000
MAX_ENTRANCE = 2025          # highest op 0x79 id NGB uses in the 2000s range
BTL_TAG = 0x40000000          # marks "battle rule n" until it is renumbered
NORMAL_BIT = 1 << 1          # op 0x0A mask: bit 0 Ninja Dog, bit 1 Normal, ...


def sections(d):
    n = struct.unpack_from("<I", d, 0x10)[0]
    t = struct.unpack_from("<I", d, 0x18)[0]
    s = list(struct.unpack_from(f"<{n}I", d, t))
    return t, s


def block_list(d, s0):
    h = list(struct.unpack_from("<17I", d, s0))
    L, p = [], s0 + h[6]
    while struct.unpack_from("<I", d, p)[0]:
        L.append(struct.unpack_from("<I", d, p)[0]); p += 4
    return h, L


def block_words(d, s0, b, end=0x16E):
    """Words of one block, up to and including the end op 0x16E (Sigma numbering)."""
    out, p = [], s0 + b
    while True:
        w = struct.unpack_from("<I", d, p)[0]; out.append(w); p += 4
        if w == OP | end:
            return out


def is_op(w):
    return w >> 24 == 0x82 and (w & 0xFFFFFF) < 0x200


def convert_words(W, player, report):
    W = list(W)
    for i, w in enumerate(W):
        if not is_op(w):
            continue
        o = w & 0xFFFFFF
        if o in (0x6A, 0x14) and i + 2 < len(W) and W[i + 2] == 113:   # Sigma spawn 0x6a / check 0x14 (= NGB 0x5b / 0x0f)
            W[i + 2] = player
        n = sigma_to_ngb(o)
        if n is None:
            nxt = next((k for k in range(i + 1, len(W)) if is_op(W[k])), len(W))
            if nxt - i == 2:            # 1-argument Sigma-only op -> NGB "wait 0" (0x57 0): harmless, same size
                report.append(f"op {o:#x}({W[i+1]}) -> no-op")
                W[i] = OP | 0x57; W[i + 1] = 0
                continue
            raise SystemExit(f"Sigma-only op {o:#x} with {nxt - i - 1} args: no rule yet")
        W[i] = OP | n
    return W


def sigma_pre(W, report):
    """Rewrite Sigma-only ops that NGB has an equivalent for (container mode: block sizes may change).
      0x153 n            -> 0xd6 (battle rule n, 1)      start battle n
      0x154 v0..v4       -> 0xd6 (battle rule v1, 1)     start battle chosen by difficulty (v1 = Normal)
      0x157 n, s         -> 0xd6 (n, s); dropped when n = 1024 (= none)
      0x16b a, b         -> dropped (unknown, cosmetic in r_hell)"""
    idx = [i for i, w in enumerate(W) if is_op(w)] + [len(W)]
    out = list(W[:idx[0]])
    for k in range(len(idx) - 1):
        i, j = idx[k], idx[k + 1]
        o, args = W[i] & 0xFFFFFF, list(W[i + 1:j])
        if o == 0x153:
            out += [OP | 0xE5, BTL_TAG | args[0], 1]; report.append(f"0x153{tuple(args)} -> start battle {args[0]}")
        elif o == 0x154:
            out += [OP | 0xE5, BTL_TAG | args[1], 1]; report.append(f"0x154{tuple(args)} -> start battle {args[1]}")
        elif o == 0x157:
            if args[0] != 1024:
                out += [OP | 0xE5, args[0], args[1]]
        elif o == 0x16B:
            report.append(f"0x16b{tuple(args)} dropped")
        else:
            out += W[i:j]
    return out


def btl_to_sty_block(W):
    """Sigma battle block -> plain rule block, or None if not the Normal variant."""
    ops = [i for i, w in enumerate(W) if is_op(w)]
    out, i, mask = [], 0, None
    while i < len(W):
        w = W[i]
        if is_op(w) and (w & 0xFFFFFF) == 0x0A:
            mask = W[i + 1]; i += 2; continue
        if is_op(w) and (w & 0xFFFFFF) == 0x06:          # pre-section up to and incl. 0x07, then 0x08
            j = next(k for k in range(i, len(W)) if W[k] == OP | 0x07)
            i = j + 1
            if W[i] == OP | 0x08:
                i += 1
            continue
        if w in (OP | 0x08, OP | 0x09, OP | 0x07):
            i += 1; continue
        out.append(w); i += 1
    if mask is not None and not (mask & NORMAL_BIT):
        return None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sty"); ap.add_argument("btl", nargs="?")
    ap.add_argument("-o", required=True); ap.add_argument("--player", type=lambda x: int(x, 0), default=0)
    ap.add_argument("--load-from")
    ap.add_argument("--container", help="NGB .sty of the same area: keep all its tables, use the converted rules")
    ap.add_argument("--keep-container-blocks", action="store_true")
    ap.add_argument("--drop-container-spawns", action="store_true",
                    help="keep the container's rules except those that spawn enemies (0x5b 0,TYPE!=0)")
    ap.add_argument("--entrance", default="", help="op 0x79 ids Sigma-only (>2025) -> NGB id per type, e.g. 0x59:2023,0x54:2025")
    ap.add_argument("--load-only", default="", help="keep only these characters (and their extras) in the load list, e.g. 0x2f")
    ap.add_argument("--zone-map", default="", help="zone keys, e.g. 183:187,188:187")
    a = ap.parse_args()
    d = bytearray(open(a.sty, "rb").read())
    t, secs = sections(d)
    s0, s1 = secs[0], secs[1]
    h, L = block_list(d, s0)
    report = []
    # convert existing blocks in place (same size); in container mode Sigma 0x153 n (start battle n)
    # becomes 0xd6 (battle rule, 1) - one word longer, so those blocks are kept as word lists
    grown = {}
    for b in L:
        W = block_words(d, s0, b)
        if a.container:
            W = sigma_pre(W, report)
        W = convert_words(W, a.player, report)
        if len(W) != len(block_words(d, s0, b)):
            grown[b] = W
        else:
            struct.pack_into(f"<{len(W)}I", d, s0 + b, *W)
    getW = lambda b: grown.get(b) or block_words(d, s0, b, 0x142)
    existing = {tuple(getW(b)) for b in L}
    # battle blocks
    new_blocks, btl_kept, btl_dup, dummy_slots = [], [], {}, []
    sty_list = [tuple(getW(b)) for b in L]
    if a.btl:
        bd = open(a.btl, "rb").read()
        bt, bsecs = sections(bd)
        bh, bL = block_list(bd, bsecs[0])
        for j, b in enumerate(bL):
            W = btl_to_sty_block(block_words(bd, bsecs[0], b))
            if W is None:
                report.append(f"btl block {b:#x}: not Normal, skipped"); continue
            if a.container:
                W = sigma_pre(W, report)
            W = convert_words(W, a.player, report)
            if tuple(W) in existing:
                btl_dup[j] = sty_list.index(tuple(W)); continue
            btl_kept.append(j)
            new_blocks.append(W)
    if a.container:
        # NGB file of the same area supplies every table; only the converted rules are put in
        sty_blocks = [list(getW(b)) for b in L]
        cd = bytearray(open(a.container, "rb").read())
        ct, csecs = sections(cd)
        ch, cL = block_list(cd, csecs[0])
        d, t, secs, s0, s1, h = cd, ct, csecs, csecs[0], csecs[1], ch
        L = cL if (a.keep_container_blocks or a.drop_container_spawns) else []
        if a.drop_container_spawns:
            # rules are switched on BY NUMBER (op 0xd6 n,1), so keep every slot: spawn rules -> an empty rule
            def spawns(b):
                W = block_words(cd, s0, b, 0x142)
                return any(W[j] == OP | 0x5B and W[j + 1] == 0 and W[j + 2] != 0 for j in range(len(W) - 2))
            dummy_slots = [k for k, b in enumerate(L) if spawns(b)]
            report.append(f"{len(dummy_slots)} container spawn rules emptied")
        # op 0xd6 (n, state) switches rule n on (1) / off (3): renumber to the new positions
        n_new = len(sty_blocks) + len(btl_kept)
        if len(dummy_slots) >= n_new:
            # reuse the emptied rules' slot numbers (list keeps its size) and their code space
            slots = dummy_slots[:n_new]; dummy_slots = dummy_slots[n_new:]
            free = [[L[k], 4 * len(block_words(cd, s0, L[k], 0x142))] for k in slots + dummy_slots]
            report.append(f"converted rules take slots {slots}")
        else:
            slots = list(range(len(L), len(L) + n_new)); free = []
        sty_map = {k: slots[k] for k in range(len(sty_blocks))}
        btl_map = {j: slots[len(sty_blocks) + k] for k, j in enumerate(btl_kept)}
        for j, k in btl_dup.items():
            btl_map[j] = sty_map[k]
        def renum(W, own):
            for j in range(len(W) - 1):
                if W[j] == OP | 0xD6 and W[j + 1] < 0x10000:
                    W[j + 1] = own.get(W[j + 1], W[j + 1])
                elif W[j] == OP | 0xD6 and W[j + 1] & BTL_TAG:      # from Sigma 0x153 = start battle n
                    W[j + 1] = btl_map[W[j + 1] & 0xFFFF]
        for W in sty_blocks: renum(W, sty_map)
        for W in new_blocks: renum(W, sty_map)    # battle rules use the .sty's rule numbers
        new_blocks = sty_blocks + new_blocks
        if dummy_slots:
            new_blocks.append([OP | 0x02, 1, OP | 0x06, OP | 0x56, 0, OP | 0x57, 0, OP | 0x142])
            dummy_idx = len(new_blocks) - 1
        ent = dict(tuple(int(x, 0) for x in z.split(":")) for z in a.entrance.split(",") if z)
        for W in new_blocks:
            cur = None
            for j in range(len(W) - 3):
                if not is_op(W[j]):
                    continue
                if W[j + 1] == 0 and W[j + 2] == 113 and not is_op(W[j + 2]):   # any (0, Rachel, ...) char ref
                    W[j + 2] = a.player
                if W[j] == OP | 0x5B and W[j + 1] == 0:
                    cur = W[j + 2]
                if W[j] == OP | 0x79 and W[j + 1] > MAX_ENTRANCE and W[j + 1] < 2100 and cur in ent:
                    report.append(f"entrance {W[j+1]} -> {ent[cur]} for type {cur:#x}")
                    W[j + 1] = ent[cur]
        # op 0x9c id: Sigma-only ids (> 257, NGB's highest) -> the id the container itself uses most
        cw = struct.unpack_from(f"<{(csecs[1] - csecs[0]) // 4}I", cd, csecs[0])
        c9 = [cw[j + 1] for j in range(len(cw) - 1) if cw[j] == OP | 0x9C]
        if c9:
            own9c = max(set(c9), key=c9.count)
            for W in new_blocks:
                for j in range(len(W) - 1):
                    if W[j] == OP | 0x9C and W[j + 1] > 257:
                        report.append(f"0x9c id {W[j+1]} -> {own9c} (container's)"); W[j + 1] = own9c
        zm = dict(tuple(int(x, 0) for x in z.split(":")) for z in a.zone_map.split(",") if z)
        for W in new_blocks:
            for j in range(len(W) - 1):
                if W[j] == OP | 0x05 and W[j + 1] in zm:
                    W[j + 1] = zm[W[j + 1]]
        report.append(f"container {os.path.basename(a.container)}: tables kept, {len(L)} of its rules kept")
    # rebuild section 0: old bytes + new blocks + new block list
    sec0 = bytearray(d[s0:s1])
    pad = (-len(sec0)) % 16; sec0 += b"\0" * pad
    offs = list(L)
    if not a.container:
        slots, free = list(range(len(L), len(L) + len(new_blocks))), []
    def alloc(data):
        nonlocal_sec = sec0
        for f in free:
            if len(data) <= f[1]:
                at = f[0]; nonlocal_sec[at:at + len(data)] = data
                f[0] += len(data); f[1] -= len(data); return at
        at = len(nonlocal_sec); nonlocal_sec += data; nonlocal_sec += b"\0" * ((-len(nonlocal_sec)) % 16)
        return at
    targets = list(slots) + ([] if not dummy_slots else ["dummy"])
    dummy_off = None
    for W, slot in zip(new_blocks, targets):
        # op 0x9b (pointer, words, pointer, words) points into the .btl's own data: copy it and re-point
        for i, w in enumerate(W):
            if w in (OP | 0x9B, OP | 0x9C):          # 0x9c has an id first: (id, ptr, words, ptr, words)
                for k in ((1, 3) if w == OP | 0x9B else (2, 4)):
                    src, n = W[i + k], W[i + k + 1]
                    W[i + k] = alloc(bytes(bd[bsecs[0] + src: bsecs[0] + src + 4 * n]))
                report.append("op 0x9b data relocated")
        at = alloc(struct.pack(f"<{len(W)}I", *W))
        if slot == "dummy":
            dummy_off = at
        elif slot < len(offs):
            offs[slot] = at
        else:
            offs.append(at)
    for k in dummy_slots:                 # emptied container spawn rules all point at the empty rule
        offs[k] = dummy_off
    old_n = len(block_list(d, s0)[1])
    if len(offs) <= old_n:                 # reuse the old list's space (keeps the file small)
        struct.pack_into(f"<{old_n + 1}I", sec0, h[6], *offs, *([0] * (old_n + 1 - len(offs))))
    else:
        h[6] = len(sec0)
        sec0 += struct.pack(f"<{len(offs) + 1}I", *offs, 0); sec0 += b"\0" * ((-len(sec0)) % 16)
    h[15], h[16] = 0xFFFFFFFF, 0x86000002
    struct.pack_into("<17I", sec0, 0, *h)
    rest = [bytes(d[secs[k]:(secs[k + 1] if k + 1 < len(secs) else len(d))]) for k in range(1, len(secs))]
    if a.load_from:
        nd = open(a.load_from, "rb").read(); nt, ns = sections(nd)
        rest[1] = nd[ns[2]:(ns[3] if len(ns) > 3 else len(nd))]
    if a.load_only:
        # load list (section 2): 0x16-byte header, then 6-byte records {u16 pool, u16 key, u16 0} up to pool 0xFF;
        # pool-2 records belong to the pool-0 record before them
        keep = {int(x, 0) for x in a.load_only.split(",")}
        L2 = bytearray(rest[1]); recs, q = [], 0x16
        while q + 6 <= len(L2) and struct.unpack_from("<H", L2, q)[0] != 0xFF:
            recs.append(struct.unpack_from("<3H", L2, q)); q += 6
        tail = bytes(L2[q:])
        kept, drop = [], False
        for r in recs:
            if r[0] == 0:
                drop = r[1] not in keep
            if not (drop and r[0] in (0, 2)):
                kept.append(r)
        body = b"".join(struct.pack("<3H", *r) for r in kept) + tail
        rest[1] = bytes(L2[:0x16]) + body + b"\0" * (len(L2) - 0x16 - len(body))
        report.append(f"load list: {len(recs)} -> {len(kept)} records (kept chars {sorted(hex(k) for k in keep)})")
    out = bytearray(d[:s0]) + sec0
    new_secs = [s0]
    for r in rest:
        new_secs.append(len(out)); out += r; out += b"\0" * ((-len(out)) % 16)
    struct.pack_into(f"<{len(new_secs)}I", out, t, *new_secs)
    struct.pack_into("<I", out, 0x0C, len(out))
    open(a.o, "wb").write(out)
    print(f"{len(L)} sty blocks + {len(new_blocks)} battle blocks -> {a.o} ({len(out)} bytes)")
    for r in report:
        print("  ", r)


if __name__ == "__main__":
    main()
