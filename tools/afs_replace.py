"""Replace one file inside an AFS archive in place (2026-11-08).

  python -I afs_replace.py <archive.afs> <name inside> <new file>

The new file must fit in the old entry's slot (up to the next entry, 2048-byte aligned). Updates the
entry size in the table and in the name table record (last u32 of the 48-byte record). Makes <archive>.bak once.
"""
import os, shutil, struct, sys

afs, name, src = sys.argv[1:4]
new = open(src, "rb").read()
d = bytearray(open(afs, "rb").read())
n = struct.unpack_from("<I", d, 4)[0]
tab = [struct.unpack_from("<II", d, 8 + 8 * i) for i in range(n)]
noff, nsz = struct.unpack_from("<II", d, 8 + 8 * n)
idx = next(i for i in range(n) if d[noff + 48 * i: noff + 48 * i + 32].split(b"\0")[0].decode() == name)
off, size = tab[idx]
nxt = min([o for o, _ in tab if o > off] + [noff])
if len(new) > nxt - off:
    raise SystemExit(f"{name}: new {len(new)} bytes does not fit slot {nxt - off}")
if not os.path.exists(afs + ".bak"):
    shutil.copyfile(afs, afs + ".bak")
d[off:nxt] = new + b"\0" * (nxt - off - len(new))
struct.pack_into("<I", d, 8 + 8 * idx + 4, len(new))
rec = noff + 48 * idx
if struct.unpack_from("<I", d, rec + 44)[0] == size:
    struct.pack_into("<I", d, rec + 44, len(new))
open(afs, "wb").write(d)
print(f"replaced {name}: {size} -> {len(new)} bytes")
