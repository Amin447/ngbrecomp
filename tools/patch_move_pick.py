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

m = repo / "src/my_mods.c"
t = m.read_text()
a = t.index("/* ---- Move swaps (move_swap=FROM:TO) ----"); b = t.index("/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */")
t = t[:a] + r'''/* ---- Move swaps (move_swap=FROM:TO) ----
 *
 * The game picks Ryu's next move by choosing one of his move records in ryu.chr (sub_00034A10,
 * called from sub_000345F0, which writes the record's move to his current move at object +
 * 0x2788). Editing the loaded ryu.chr made the game report a disc error, so instead the
 * generated sub_000345F0 (src/recomp/gen/recomp_0001.c, edited by hand: redo it after a
 * regeneration) passes the move it read through here. It runs for every character that uses
 * this code, so only the moves listed change. */
uint16_t mymod_move_pick(uint16_t move)
{
    load_options();
    for (int k = 0; k < s_nmswap; k++)
        if (move == s_mswap_from[k])
            return s_mswap_to[k];
    return move;
}

''' + t[b:]
t = t.replace("    load_options();\n    chr_frame();\n", "    load_options();\n", 1)
m.write_text(t)
h = repo / "src/my_mods.h"
ht = h.read_text()
if "mymod_move_pick" not in ht:
    ht = ht.replace("void mymod_frame(void);", "void mymod_frame(void);\nuint16_t mymod_move_pick(uint16_t move);", 1)
    h.write_text(ht)
print("ok")
