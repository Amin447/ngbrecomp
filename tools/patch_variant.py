#!/usr/bin/env python3
# Run after regenerating src/recomp/gen (it is not in git): sub_002F2CC0 copies a spawn record's
# kind (+0x52 -> object +0x277A) and its partner (+0x5B -> +0x2791) through mymod_variant
# (src/my_mods.c, variant_swap).
import os, pathlib
repo = pathlib.Path(os.path.expanduser("~/ngbrecomp"))
DECL = "uint32_t mymod_variant(uint32_t obj, int field, uint32_t value);   /* src/my_mods.c */\n"
g = repo / "src/recomp/gen/recomp_0026.c"
s = g.read_text()
i = s.index("void sub_002F2CC0(void)\n{"); j = s.index("\n}\n", i); b = s[i:j]
for old, new in [("MEM16(edx + 0x277A) = LO16(ecx);", "MEM16(edx + 0x277A) = (uint16_t)mymod_variant(edx, 0, LO16(ecx));   /* my_mods.c: variant_swap */"),
                 ("MEM8(edx + 0x2791) = LO8(ecx);", "MEM8(edx + 0x2791) = (uint8_t)mymod_variant(edx, 1, LO8(ecx));   /* my_mods.c: variant_swap */")]:
    if new not in b:
        assert b.count(old) == 1, old
        b = b.replace(old, new)
s = s[:i] + b + s[j:]
if DECL not in s:
    s = s.replace('#include "recomp_funcs.h"\n', '#include "recomp_funcs.h"\n' + DECL, 1)
g.write_text(s)

m = repo / "src/my_mods.c"; t = m.read_text()
if "variant_swap" not in t:
    t = t.replace(" *   move_swap=0x191:0x1F2", " *   variant_swap=0x5C:0:1  objects of type 0x5C (SWAT) spawned as kind 0 (object +0x277A) spawn\n"
                  " *                      as kind 1 (the shield soldier) instead (up to 8 lines)\n"
                  " *   move_swap=0x191:0x1F2", 1)
    t = t.replace("static int s_neswap;\n", "static int s_neswap;\nstatic uint16_t s_vswap_type[8], s_vswap_from[8], s_vswap_to[8];\nstatic int s_nvswap;\n", 1)
    t = t.replace("""    else if (!strcmp(key, "move_swap")""", """    else if (!strcmp(key, "variant_swap") && s_nvswap < 8) {
        int ty, from, to;
        if (sscanf(val, "%i:%i:%i", &ty, &from, &to) == 3) {
            s_vswap_type[s_nvswap] = (uint16_t)ty;
            s_vswap_from[s_nvswap] = (uint16_t)from;
            s_vswap_to[s_nvswap] = (uint16_t)to;
            s_nvswap++;
        }
    }
    else if (!strcmp(key, "move_swap")""", 1)
    t = t.replace("/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */", r'''/* ---- Kind swaps (variant_swap=TYPE:FROM:TO) ----
 * sub_002F2CC0 copies a spawn record's kind (+0x52) to object +0x277A, then its partner (+0x5B) to
 * +0x2791; it has already written the type (+0x2774). For SWAT soldiers the partner is 0x81 + the
 * kind, so it is moved by the same amount when it matches. */
uint32_t mymod_variant(uint32_t obj, int field, uint32_t value)
{
    load_options();
    if (!s_nvswap || (MEMF(0x4B5710) == 0.0f && MEMF(0x4B5714) == 0.0f && MEMF(0x4B5718) == 0.0f))
        return value;
    uint16_t type = MEM16(obj + 0x2774);
    for (int k = 0; k < s_nvswap; k++) {
        if (type != s_vswap_type[k])
            continue;
        if (field == 0 && value == s_vswap_from[k])
            return s_vswap_to[k];
        if (field == 1 && value == 0x81u + s_vswap_from[k] && MEM16(obj + 0x277A) == s_vswap_to[k])
            return 0x81u + s_vswap_to[k];
    }
    return value;
}

/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */''', 1)
    m.write_text(t)
print("ok")
