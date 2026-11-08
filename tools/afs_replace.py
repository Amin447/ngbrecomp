"""Replace one file inside an AFS archive in place (2026-11-08).

  python -I afs_replace.py <archive.afs> <name inside> <new file>

If the new file does not fit the old slot it is appended at the end of the archive. Updates the
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
if not os.path.exists(afs + ".bak"):
    shutil.copyfile(afs, afs + ".bak")
if len(new) <= nxt - off:
    d[off:nxt] = new + b"\0" * (nxt - off - len(new))
else:                                   # too big: append at the end of the archive (2048-aligned)
    d += b"\0" * ((-len(d)) % 2048)
    off = len(d); d += new + b"\0" * ((-len(new)) % 2048)
    struct.pack_into("<I", d, 8 + 8 * idx, off)
    print(f"{name}: moved to end of archive at {off:#x}")
struct.pack_into("<I", d, 8 + 8 * idx + 4, len(new))
rec = noff + 48 * idx
if struct.unpack_from("<I", d, rec + 44)[0] == size:
    struct.pack_into("<I", d, rec + 44, len(new))
open(afs, "wb").write(d)
print(f"replaced {name}: {size} -> {len(new)} bytes")
