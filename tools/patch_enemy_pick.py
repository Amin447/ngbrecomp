#!/usr/bin/env python3
# Run after regenerating src/recomp/gen (it is not in git): the spawn functions read the spawn
# record's type (+0x50) through mymod_enemy_pick (src/my_mods.c, enemy_swap).
import os, pathlib, re
repo = pathlib.Path(os.path.expanduser("~/ngbrecomp"))
DECL = "uint16_t mymod_enemy_pick_rec(uint32_t rec);   /* src/my_mods.c */\n"
for f, fns in [("recomp_0010.c", ["sub_00153100", "sub_00153333"]), ("recomp_0024.c", ["sub_002CD040"]),
               ("recomp_0026.c", ["sub_002F2CC0"])]:
    g = repo / "src/recomp/gen" / f
    s = g.read_text()
    for fn in fns:
        i = s.index(f"void {fn}(void)\n{{"); j = s.index("\n}\n", i)
        b = re.sub(r"SET_LO16\((\w+), MEM16\((\w+) \+ 0x50\)\);",
                   r"SET_LO16(\1, mymod_enemy_pick_rec(\2));   /* my_mods.c: enemy_swap */", s[i:j])
        s = s[:i] + b + s[j:]
    if DECL not in s:
        s = s.replace('#include "recomp_funcs.h"\n', '#include "recomp_funcs.h"\n' + DECL, 1)
    g.write_text(s)

m = repo / "src/my_mods.c"
t = m.read_text()
if "enemy_swap" not in t:
    t = t.replace(" *   move_swap=0x191:0x1F2", " *   enemy_swap=0xE:0x44  every object spawned as type 0xE (Genin) spawns as 0x44 (white-clad\n"
                  " *                      ninja) instead (up to 8 lines; types as the ShowAction title's \"hit type\")\n"
                  " *   move_swap=0x191:0x1F2", 1)
    t = t.replace("static int s_nmswap;\n", "static int s_nmswap;\nstatic uint16_t s_eswap_from[8], s_eswap_to[8];\nstatic int s_neswap;\n", 1)
    t = t.replace("""    else if (!strcmp(key, "move_swap")""", """    else if (!strcmp(key, "enemy_swap") && s_neswap < 8) {
        int from, to;
        if (sscanf(val, "%i:%i", &from, &to) == 2) {
            s_eswap_from[s_neswap] = (uint16_t)from;
            s_eswap_to[s_neswap] = (uint16_t)to;
            s_neswap++;
        }
    }
    else if (!strcmp(key, "move_swap")""", 1)
    t = t.replace("/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */", r'''/* ---- Enemy swaps (enemy_swap=FROM:TO) ----
 * Objects are spawned from spawn records: +0x40 position, +0x50 u16 type (the object's +0x2774).
 * The spawn functions (sub_00153100, sub_002CD040, sub_002F2CC0; generated code edited by
 * tools/patch_enemy_pick.py) read the type through here. The new type's data must be loaded in
 * that area: swap between enemies of the same chapter. */
uint16_t mymod_enemy_pick(uint16_t type)
{
    load_options();
    for (int k = 0; k < s_neswap; k++)
        if (type == s_eswap_from[k])
            return s_eswap_to[k];
    return type;
}

/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */''', 1)
    m.write_text(t)
print("ok")

# Also the other type writers (mymod_type_write): see the scratch history; sites 1-3.
exec(open(__file__.replace('patch_enemy_pick.py', 'patch_type_write.py')).read())
