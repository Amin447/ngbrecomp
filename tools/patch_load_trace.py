#!/usr/bin/env python3
# Run after regenerating src/recomp/gen. Logs character-load requests (NGB_SPAWN_LOG) to
# recordings/load_trace.txt via mymod_load_trace(fn, esp) in src/my_mods.c:
#   sub_00173880 (list, pool, key; al = extra)  load a character group
#   sub_002ED940 (u16 keys[4])                  pool keys -> files
#   sub_00171F30 (ecx list, esi file, size)     add one file to a list
import os, pathlib, re
NL = chr(10)
gen = pathlib.Path(os.path.expanduser("~/ngbrecomp")) / "src/recomp/gen"
DECL = "void mymod_load_trace(uint32_t fn, uint32_t sp, uint32_t r_eax, uint32_t r_ecx, uint32_t r_esi);   /* src/my_mods.c */" + NL
for fn in ("sub_00173880", "sub_002ED940", "sub_00171F30"):
    for g in sorted(gen.glob("recomp_*.c")):
        s = g.read_text()
        head = f"void {fn}(void)" + NL + "{"
        if head not in s:
            continue
        a = f"    RECOMP_ENTRY(0x{fn[4:]}u);" + NL
        i = s.index(head); k = s.index(a, i) + len(a)
        if "mymod_load_trace" not in s[k:k + 120]:
            s = s[:k] + f"    mymod_load_trace(0x{fn[4:]}u, esp, eax, ecx, esi);" + NL + s[k:]
        if DECL not in s:
            s = s.replace('#include "recomp_funcs.h"' + NL, '#include "recomp_funcs.h"' + NL + DECL, 1)
        g.write_text(s); print(fn, g.name)
        break
