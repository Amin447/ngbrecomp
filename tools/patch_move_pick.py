#!/usr/bin/env python3
# Run after regenerating src/recomp/gen (it is not in git): routes sub_000345F0's move through mymod_move_pick.
"""Move swaps in code: sub_000345F0 reads the picked record's move through mymod_move_pick().
Drops the ryu.chr memory patch (the game reported a disc error after it)."""
import os, pathlib, re, subprocess
repo = pathlib.Path(os.path.expanduser("~/ngbrecomp"))
g = repo / "src/recomp/gen/recomp_0001.c"
s = g.read_text()
i = s.index("void sub_000345F0(void)\n{"); j = s.index("\n}\n", i)
body = s[i:j]
old = "loc_00034620: ;\n    SET_LO16(eax, MEM16(eax + 2));"
if "mymod_move_pick" not in body:
    assert body.count(old) == 1
    body = body.replace(old, "loc_00034620: ;\n    SET_LO16(eax, mymod_move_pick(MEM16(eax + 2)));   /* my_mods.c: move_swap */")
    s = s[:i] + body + s[j:]
    s = s.replace('#include "recomp_funcs.h"\n', '#include "recomp_funcs.h"\nuint16_t mymod_move_pick(uint16_t move);   /* src/my_mods.c */\n', 1)
    assert "uint16_t mymod_move_pick" in s
    g.write_text(s)
print("ok")
# (its my_mods.c/.h part is already in src/my_mods.c and src/my_mods.h)
