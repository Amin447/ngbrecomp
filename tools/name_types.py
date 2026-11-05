#!/usr/bin/env python3
"""Name object types from a ShowAction session.

  tools/name_types.py GAME_DIR recordings/typedata.txt

ShowAction (NGB_SHOW_ACTION) writes recordings/typedata.txt: for each object type (+0x2774)
seen, the first bytes of its data (+0x26D8), which is the loaded .chr (enemies, "chr_dat2")
or .itm/.sob (items, props, "itm_dat2") file. Its header (magic, size at +0x0C, section count
at +0x10) is matched against every file in the game's .afs archives. Enemy files have sizes of
their own, so they match exactly; several items can share a size (all are listed).
"""
import struct, sys, glob, os, re, collections
game, dump = sys.argv[1], sys.argv[2]
idx = collections.defaultdict(list)   # (first 8 bytes, size, nsec, rest words) -> names
for fn in sorted(glob.glob(game + "/chr_*.afs") + glob.glob(game + "/*.afs")):
    f = open(fn, "rb"); h = f.read(8)
    if h[:3] != b"AFS": continue
    n, = struct.unpack_from("<I", h, 4)
    tab = f.read(8 * n + 8)
    noff, nsz = struct.unpack_from("<II", tab, 8 * n)
    names = []
    if noff:
        f.seek(noff); nt = f.read(nsz)
        names = [nt[48*i:48*i+32].split(b"\0")[0].decode("latin1") for i in range(n)]
    for i in range(n):
        off, sz = struct.unpack_from("<II", tab, 8 * i)
        if sz < 0x20: continue
        f.seek(off); hd = f.read(0x20)
        if hd[4:8] != b"dat2" and hd[4:8] != b"dat\0": continue
        key = (hd[:8], struct.unpack_from("<I", hd, 0x0C)[0], struct.unpack_from("<I", hd, 0x10)[0])
        idx[key].append(f"{os.path.basename(fn)}#{i} {names[i] if names else ''}")
seen = set()
for l in open(dump):
    m = re.match(r"type (\w+) data (\w+):(\w+)", l)
    if not m: continue
    t, b = m.group(1), bytes.fromhex(m.group(3))
    if t in seen: continue
    seen.add(t)
    if b[4:7] != b"dat":
        print(f"type {t}: not a chr file ({b[:8].hex()})"); continue
    key = (b[:8], struct.unpack_from("<I", b, 0x0C)[0], struct.unpack_from("<I", b, 0x10)[0])
    print(f"type {t}: {b[:8].rstrip(bytes(1)).decode('latin1')} size {key[1]:#x} -> {idx.get(key, ['no match'])}")
