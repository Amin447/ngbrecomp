#!/usr/bin/env python3
"""Which archive each object type's loaded files come from.

  tools/name_files.py GAME_DIR recordings/typefiles.txt

ShowAction logs, for each new object type, every pointer in the object to data starting with a
4-letter magic, with its first 32 bytes. Each is matched (first 16 bytes: magic and header) to the
start of every file in the game's .afs archives; the archives that match tell, for instance, a
Jonin (its own textures in chr_jonin.afs) from a Genin, though both use genin.chr.
"""
import struct, sys, glob, os, re, collections
game, log = sys.argv[1], sys.argv[2]
idx = collections.defaultdict(set)
for fn in sorted(glob.glob(game + "/*.afs")):
    f = open(fn, "rb"); h = f.read(8)
    if h[:3] != b"AFS": continue
    n, = struct.unpack_from("<I", h, 4)
    tab = f.read(8 * n + 8)
    noff, nsz = struct.unpack_from("<II", tab, 8 * n)
    names = []
    if noff:
        f.seek(noff); nt = f.read(nsz); names = [nt[48*i:48*i+32].split(b"\0")[0].decode("latin1") for i in range(n)]
    for i in range(n):
        off, sz = struct.unpack_from("<II", tab, 8 * i)
        if sz < 16: continue
        f.seek(off)
        idx[f.read(16)].add(f"{os.path.basename(fn)[:-4]}/{names[i] if names else i}")
types = collections.defaultdict(dict)
for l in open(log):
    m = re.match(r"type (\w+) \+(\w+) (\w+):(\w+)", l)
    if not m: continue
    b = bytes.fromhex(m.group(4))[:16]
    types[m.group(1)][b] = idx.get(b, set())
for t in sorted(types):
    arcs = collections.Counter()
    files = []
    for b, where in types[t].items():
        if not where: continue
        files.append(sorted(where)[0] + (f" (+{len(where)-1} more)" if len(where) > 1 else ""))
        if len(where) <= 3:
            for w in where: arcs[w.split("/")[0]] += 1
    print(f"type {t}: archives {dict(arcs.most_common(4))}")
    for x in files[:8]: print("    ", x)
