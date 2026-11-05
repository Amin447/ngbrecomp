import os, pathlib
repo = pathlib.Path(os.path.expanduser("~/ngbrecomp"))
DECL = "uint16_t mymod_type_write(uint16_t type, int site);   /* src/my_mods.c */\n"
edits = [("recomp_0011.c", "sub_00168EC0", "MEM16(esi + 0x2774) = LO16(ebx);", "MEM16(esi + 0x2774) = mymod_type_write(LO16(ebx), 1);"),
         ("recomp_0026.c", "sub_002F2780", "MEM16(ebp + 0x2774) = LO16(eax);", "MEM16(ebp + 0x2774) = mymod_type_write(LO16(eax), 2);"),
         ("recomp_0026.c", "sub_002F7020", "MEM16(ebx + 0x2774) = LO16(ecx);", "MEM16(ebx + 0x2774) = mymod_type_write(LO16(ecx), 3);")]
for f, fn, old, new in edits:
    g = repo / "src/recomp/gen" / f
    s = g.read_text()
    i = s.index(f"void {fn}(void)\n{{"); j = s.index("\n}\n", i); b = s[i:j]
    if new not in b:
        assert b.count(old) == 1, (fn, b.count(old))
        s = s[:i] + b.replace(old, new) + s[j:]
    if DECL not in s:
        s = s.replace('#include "recomp_funcs.h"\n', '#include "recomp_funcs.h"\n' + DECL, 1)
    g.write_text(s)

m = repo / "src/my_mods.c"
t = m.read_text()
if "mymod_type_write" not in t:
    t = t.replace("/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */", r'''/* The other places that write an object's type (+0x2774): 1 sub_00168EC0 (object reset),
 * 2 sub_002F2780 (type passed through sub_002FE290), 3 sub_002F7020 (copied from another
 * object). Logged with their number in spawns.txt ("write N"); swapped like the spawn reads. */
