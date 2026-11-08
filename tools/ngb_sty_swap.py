"""Swap an enemy type in NGB's chapter 1 stage script (stry_dat inside yasik_cmn.afs).

The script is the same VM as Sigma's .btl/.sty (opcode words 0x82000000|op). Type arguments:
  0x69 (a, TYPE, ...)  spawn (likely)      0x5b (a, TYPE, ...) / 0x0f (a, TYPE) conditions
  0xd6 (TYPE, n) / 0xac (TYPE, n) / 0xc4 (a, TYPE)  probably load / preload
Usage: python -I ngb_sty_swap.py <afs> <block offset> <from> <to> [ops] [--doors]
  Default ops: 0x5b,0x0f,0xa5,0x5c (spawns, counts, group-kill door checks).
  0x5b/0x0f with first argument 1 are door-entrance spawns (enemy bursts through a door); they are
  skipped unless --doors is given, because non-ninja enemies cannot play them and the door stays locked.
  Never change the 3rd argument of 0x5b: it is a flag id the doors read (op 0xd6).
Backup <afs>.bak is made once. Restore by copying it back.
"""
import os, shutil, struct, sys
afs, base, frm, to = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3], 0), int(sys.argv[4], 0)
ARG = {0x69: 1, 0x5b: 1, 0x0f: 1, 0xd6: 0, 0xac: 0, 0xc4: 1, 0x107: 0, 0xa5: 1, 0x22: 2, 0x5c: 1}
DOORS = '--doors' in sys.argv
sys.argv = [x for x in sys.argv if x != '--doors']
sel = sys.argv[5] if len(sys.argv) > 5 else '0x5b,0x0f,0xa5,0x5c'
if True:
    ARG = {k: v for k, v in ARG.items() if k in [int(x, 0) for x in sel.split(",")]}
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
        if (w & 0xFFFFFF) in (0x5b, 0x0f) and not DOORS and struct.unpack_from("<I", d, p + 4)[0] == 1:
            continue
        if struct.unpack_from("<I", d, q)[0] == frm:
            struct.pack_into("<I", d, q, to)
            n[hex(w & 0xFFFFFF)] = n.get(hex(w & 0xFFFFFF), 0) + 1
open(afs, "wb").write(d)
print("changed", n)
