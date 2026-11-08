#!/usr/bin/env python3
# Run after regenerating src/recomp/gen. sub_002EE0D0 reads the stage script's character load list
# and calls sub_00173880(list 0xDB5400, pool, key) for each entry. This adds the mods.txt
# load_chars= characters (pool 0) at its start: mymod_load_chars_n() / mymod_load_chars_key(i).
import os, pathlib
NL = chr(10)
g = pathlib.Path(os.path.expanduser("~/ngbrecomp")) / "src/recomp/gen/recomp_0026.c"
s = g.read_text()
DECL = "uint32_t mymod_load_chars_n(void); uint32_t mymod_load_chars_key(uint32_t i); uint32_t mymod_load_chars_pool(uint32_t i);   /* src/my_mods.c */" + NL
a = "    RECOMP_ENTRY(0x002EE0D0u);" + NL
i = s.index("void sub_002EE0D0(void)" + NL + "{"); k = s.index(a, i) + len(a)
CODE = ("    { uint32_t _n = mymod_load_chars_n(), _sv = eax;   /* my_mods.c: load_chars */" + NL +
        "      for (uint32_t _i = 0; _i < _n; _i++) {" + NL +
        "        PUSH32(esp, mymod_load_chars_key(_i)); PUSH32(esp, mymod_load_chars_pool(_i)); PUSH32(esp, 0xDB5400); eax = 0;" + NL +
        "        PUSH32(esp, 0x002EE0D0u); RECOMP_ABI_CALL(0x00173880u, sub_00173880); esp = esp + 0xC; }" + NL +
        "      eax = _sv; }" + NL)
if "mymod_load_chars_n" not in s[k:k + 200]:
    s = s[:k] + CODE + s[k:]
if DECL not in s:
    s = s.replace('#include "recomp_funcs.h"' + NL, '#include "recomp_funcs.h"' + NL + DECL, 1)
g.write_text(s); print("ok")
