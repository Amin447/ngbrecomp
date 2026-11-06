#!/usr/bin/env python3
# Run after regenerating src/recomp/gen (not in git). sub_002E1C80 adds each enemy type an area needs
# to the game's list at 0xDB5804 (u16 types, count byte 0xDB5A02); the chr_*.afs of every listed type
# is loaded. After each add, mymod_load_enemies() (src/my_mods.c, load_enemy=TYPE) adds its types too.
import os, pathlib
g = pathlib.Path(os.path.expanduser("~/ngbrecomp")) / "src/recomp/gen/recomp_0025.c"
s = g.read_text()
DECL = "void mymod_load_enemies(void);   /* src/my_mods.c */\n"
i = s.index("void sub_002E1C80(void)\n{"); j = s.index("\n}\n", i)
old = "    MEM8(0xDB5A02) = MEM8(0xDB5A02) + 1;\n"
b = s[i:j]
if "mymod_load_enemies" not in b:
    assert b.count(old) == 1
    b = b.replace(old, old + "    mymod_load_enemies();   /* my_mods.c: load_enemy */\n")
s = s[:i] + b + s[j:]
if DECL not in s:
    s = s.replace('#include "recomp_funcs.h"\n', '#include "recomp_funcs.h"\n' + DECL, 1)
g.write_text(s); print("ok")
