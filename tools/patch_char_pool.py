#!/usr/bin/env python3
# Run after regenerating src/recomp/gen (not in git). sub_00167650 sets up the memory pools once;
# char_pool_extra (src/my_mods.c) grows character pool 0 (0xDB9A04) and shrinks the general pool.
import os, pathlib
NL = chr(10)
g = pathlib.Path(os.path.expanduser("~/ngbrecomp")) / "src/recomp/gen/recomp_0011.c"
s = g.read_text()
DECL = "uint32_t mymod_char_pool_extra(void);   /* src/my_mods.c */" + NL
i = s.index("void sub_00167650(void)" + NL + "{")
j = s.index(NL + "}" + NL, i)
body = s[i:j]
if "mymod_char_pool_extra" not in body:
    body = body.replace("    eax = eax + 0x226000;" + NL, "    eax = eax + 0x226000 + mymod_char_pool_extra();" + NL, 1)
    body = body.replace("    eax = eax + 0x173E000;" + NL, "    eax = eax + 0x173E000 - mymod_char_pool_extra();" + NL, 1)
s = s[:i] + body + s[j:]
if DECL not in s:
    s = s.replace('#include "recomp_funcs.h"' + NL, '#include "recomp_funcs.h"' + NL + DECL, 1)
s = s.replace("    eax = eax + 0x173E000;" + NL, "    eax = eax + 0x173E000 - mymod_char_pool_extra();" + NL)   # pool reset at 0x0016A9C8 too
g.write_text(s); print("ok", body.count("mymod_char_pool_extra"))
