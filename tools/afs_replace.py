"""Replace one file inside an AFS archive in place (2026-11-08).

  python -I afs_replace.py <archive.afs> <name inside> <new file>

The total archive size never changes (else the game copies the original archive back into the cache).
A file that does not fit its slot can take over the slot of an unneeded file: --borrow <that file>. Updates the
entry size in the table and in the name table record (last u32 of the 48-byte record). Makes <archive>.bak once.
"""
import os, shutil, struct, sys

borrow = None
if "--borrow" in sys.argv:          # --borrow <other file>: store the new file in THAT file's slot (it is lost)
    k = sys.argv.index("--borrow"); borrow = sys.argv[k + 1]; del sys.argv[k:k + 2]
afs, name, src = sys.argv[1:4]
new = open(src, "rb").read()
d = bytearray(open(afs, "rb").read())
n = struct.unpack_from("<I", d, 4)[0]
tab = [struct.unpack_from("<II", d, 8 + 8 * i) for i in range(n)]
noff, nsz = struct.unpack_from("<II", d, 8 + 8 * n)
idx = next(i for i in range(n) if d[noff + 48 * i: noff + 48 * i + 32].split(b"\0")[0].decode() == name)
off, size = tab[idx]
if borrow:
    bidx = next(i for i in range(n) if d[noff + 48 * i: noff + 48 * i + 32].split(b"\0")[0].decode() == borrow)
    off = tab[bidx][0]
    struct.pack_into("<I", d, 8 + 8 * idx, off)
    print(f"{name}: now stored in {borrow}'s slot at {off:#x} ({borrow} is overwritten)")
nxt = min([o for o, _ in tab if o > off] + [noff])
if not os.path.exists(afs + ".bak"):
    shutil.copyfile(afs, afs + ".bak")
if len(new) <= nxt - off:
    d[off:nxt] = new + b"\0" * (nxt - off - len(new))
else:   # the archive's total size must not change (else the game copies the original back into the cache)
    raise SystemExit(f"{name}: {len(new)} bytes does not fit its slot ({nxt - off}); use --borrow <unneeded file>")
struct.pack_into("<I", d, 8 + 8 * idx + 4, len(new))
rec = noff + 48 * idx
if struct.unpack_from("<I", d, rec + 44)[0] == size:
    struct.pack_into("<I", d, rec + 44, len(new))
open(afs, "wb").write(d)
print(f"replaced {name}: {size} -> {len(new)} bytes")
