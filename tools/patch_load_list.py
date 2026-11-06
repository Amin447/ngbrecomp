#!/usr/bin/env python3
# Run after regenerating src/recomp/gen (not in git). The game's file-list workers (called from a
# table; each gets a list struct: u16 file numbers at +0x404, count byte at +0x602, processed from
# the end) call mymod_list_tick(list) first (src/my_mods.c: load_files / load_files_when).
import os, pathlib
g = pathlib.Path(os.path.expanduser("~/ngbrecomp")) / "src/recomp/gen/recomp_0012.c"
s = g.read_text()
DECL = "void mymod_list_tick(uint32_t list);   /* src/my_mods.c */\n"
s = s.replace("    mymod_load_enemies();   /* my_mods.c: load_files */\n", "")   # older hook
for fn in ("sub_0016F640", "sub_0016FA40", "sub_0016FC70", "sub_0016FE40"):
    a = f"    RECOMP_ENTRY(0x{fn[4:]}u);\n"
    i = s.index(f"void {fn}(void)\n{{"); k = s.index(a, i) + len(a)
    if "mymod_list_tick" not in s[k:k+80]:
        s = s[:k] + "    mymod_list_tick(MEM32(esp + 4));   /* my_mods.c: load_files */\n" + s[k:]
if DECL not in s:
    s = s.replace('#include "recomp_funcs.h"\n', '#include "recomp_funcs.h"\n' + DECL, 1)
g.write_text(s); print("ok")
