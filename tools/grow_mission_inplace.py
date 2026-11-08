"""Grow m_16s_ar.sty in place over s_jigoku_l2.sty (pyrmd_cmn.afs) and fix its size in load_img.bin."""
import struct, shutil, os
G = "C:/Users/10/AppData/Local/NinjaGaidenBlack/game/"
C = "G:/NinjaGaidenBlack/RecordBuild/userdata/Cache/"
new = open("r_jig_m_16s_ar.sty", "rb").read()

d = bytearray(open(G + "pyrmd_cmn.afs.orig", "rb").read())
n = struct.unpack_from("<I", d, 4)[0]
tab = [list(struct.unpack_from("<II", d, 8 + 8 * i)) for i in range(n)]
noff = struct.unpack_from("<I", d, 8 + 8 * n)[0]
name = lambda i: d[noff + 48 * i: noff + 48 * i + 32].split(b"\0")[0].decode()
i16 = next(i for i in range(n) if name(i) == "m_16s_ar.sty")
il2 = next(i for i in range(n) if name(i) == "s_jigoku_l2.sty")
off, old = tab[i16]
end = tab[il2][0] + tab[il2][1]
assert tab[il2][0] > off and off + len(new) <= end, "does not fit"
d[off:off + len(new)] = new
struct.pack_into("<I", d, 8 + 8 * i16 + 4, len(new))
if struct.unpack_from("<I", d, noff + 48 * i16 + 44)[0] == old:
    struct.pack_into("<I", d, noff + 48 * i16 + 44, len(new))
open(C + "pyrmd_cmn.afs", "wb").write(d)
open(G + "pyrmd_cmn.afs", "wb").write(d)

li_path = G + "load_img.bin"
if not os.path.exists(li_path + ".orig"):
    shutil.copyfile(li_path, li_path + ".orig")
li = bytearray(open(li_path + ".orig", "rb").read())
k = struct.unpack_from("<I", li, 4)[0]
hits = [g for g in range(k) if struct.unpack_from("<II", li, 8 + 8 * g) == (old, 17)]
assert len(hits) == 1, hits
struct.pack_into("<I", li, 8 + 8 * hits[0], len(new))
open(li_path, "wb").write(li)
print(f"m_16s_ar {old:#x} -> {len(new):#x} at {off:#x} (over s_jigoku_l2); load_img entry {hits[0]:#x} updated")
