"""Swap an enemy type in NGB's chapter 1 stage script (stry_dat inside yasik_cmn.afs).

The script is the same VM as Sigma's .btl/.sty (opcode words 0x82000000|op). Type arguments:
  0x69 (a, TYPE, ...)  spawn (likely)      0x5b (a, TYPE, ...) / 0x0f (a, TYPE) conditions
  0xd6 (TYPE, n) / 0xac (TYPE, n) / 0xc4 (a, TYPE)  probably load / preload
Usage: python -I ngb_sty_swap.py <afs> <block offset> <from> <to> [ops] [kind]
  kind: also set the third argument of swapped 0x5b spawns (the spawn kind, e.g. 0xff = default;
  Genin spots use Genin kinds like 0x81/0x3 that other types may not understand)
Backup <afs>.bak is made once. Restore by copying it back.
"""
import os, shutil, struct, sys
afs, base, frm, to = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), int(sys.argv[4], 0)
ARG = {0x69: 1, 0x5b: 1, 0x0f: 1, 0xd6: 0, 0xac: 0, 0xc4: 1, 0x107: 0, 0xa5: 1, 0x22: 2}
KIND = int(sys.argv[6], 0) if len(sys.argv) > 6 else None
if len(sys.argv) > 5:
    ARG = {k: v for k, v in ARG.items() if k in [int(x, 0) for x in sys.argv[5].split(",")]}
if not os.path.exists(afs + ".bak"):
    shutil.copyfile(afs, afs + ".bak")
d = bytearray(open(afs, "rb").read())
assert d[base:base + 8] == b"stry_dat"
a, e = struct.unpack_from("<2I", d, base + 0x20)
n = {}
for p in range(base + a, base + e - 12, 4):
    w = struct.unpack_from("<I", d, p)[0]
    if w >> 24 == 0x82 and (w & 0xFFFFFF) in ARG:
        q = p + 4 + 4 * ARG[w & 0xFFFFFF]
        if struct.unpack_from("<I", d, q)[0] == frm:
            struct.pack_into("<I", d, q, to)
            if KIND is not None and (w & 0xFFFFFF) == 0x5b and struct.unpack_from("<I", d, p + 4)[0] == 0:
                struct.pack_into("<I", d, q + 4, KIND)
            n[hex(w & 0xFFFFFF)] = n.get(hex(w & 0xFFFFFF), 0) + 1
open(afs, "wb").write(d)
print("changed", n)
