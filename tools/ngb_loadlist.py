"""Decode a stage script's character load list (stry_dat section 2), read by sub_002EE0D0.

Section 2: u32 count, then count x {u32 id, u32 offset}; each offset (from section start) points to
6-byte records {u8 pool, u8 b1, u16 key, u8 b4, u8 b5}; key = Sigma char/item id. Per-room lists
(id = room?). Usage: python -I ngb_loadlist.py <archive> <script>
"""
import csv, os, struct, sys
G = "C:/Users/10/AppData/Local/NinjaGaidenBlack/game/"
HERE = os.path.dirname(os.path.abspath(__file__))
N = {int(r["id"]): r["enum"] for r in csv.DictReader(open(os.path.join(HERE, "..", "text", "char_ids.csv")))}
def get(arc, name):
    f = open(G + arc, "rb"); h = f.read(8); n = struct.unpack_from("<I", h, 4)[0]; tab = f.read(8 * n + 8)
    noff, nsz = struct.unpack_from("<II", tab, 8 * n); f.seek(noff); nt = f.read(nsz)
    for i in range(n):
        if nt[48 * i:48 * i + 32].split(b"\0")[0].decode() == name:
            off, sz = struct.unpack_from("<II", tab, 8 * i); f.seek(off); return f.read(sz)
def lists(d):
    t = struct.unpack_from("<I", d, 0x18)[0]
    s2 = struct.unpack_from("<I", d, t + 8)[0]
    cnt = struct.unpack_from("<I", d, s2)[0]
    out = []
    for i in range(cnt):
        idv, off = struct.unpack_from("<II", d, s2 + 4 + 8 * i)
        p = s2 + off; recs = []
        while p + 6 <= len(d):
            pool, b1, key, b4, b5 = struct.unpack_from("<BBHBB", d, p)
            if pool == 0xFF: break
            recs.append((pool, b1, key, b4, b5)); p += 6
        out.append((idv, off, recs))
    return s2, cnt, out
if __name__ == "__main__":
    d = get(sys.argv[1], sys.argv[2])
    s2, cnt, out = lists(d)
    print(sys.argv[2], "section2 at", hex(s2), "lists", cnt)
    for idv, off, recs in out:
        print(f" id {idv:#x} off {off:#x}:", " ".join(f"{p}/{N.get(k, hex(k))}[{b1:x},{b4:x},{b5:x}]" for p, b1, k, b4, b5 in recs))
