# Enemy swap data (how to use enemy_swap_data.csv)

`docs/enemy_swap_data.csv` (made by `tools/ngb_swap_table.py` from every stage script in the game)
has one row per character type with everything needed to bring it into another stage.

| Column | Meaning |
|---|---|
| Type / Type (dec) | object type number (= Sigma CHAR_* id) |
| Sigma enum / Sigma name / NGB description / Model file | what it is |
| Extras (pool:key) | entries the game always loads together with it (in at least half of the stages that load it): weapons, projectiles, effects |
| **load_chars value** | ready to paste: `load_chars=<value>` in mods.txt |
| Sometimes also | extras seen only in some stages (count / lists); add them if the enemy misbehaves |
| Lists seen | how many stage load lists include it (more = more reliable) |
| Loaded in / Areas | stage scripts (s_ = story, m_ = mission, _l/_l2/_l4 = difficulty variants) and areas |
| Spawned in | stage scripts that spawn it (op 0x5b) and how often |
| Photo | render of the model (enemy_photos/) |

## Recipe (proven 2026-11-08: titan + Yonin in story chapter 1)

1. mods.txt: `load_chars=<value>` (join several enemies' values with commas) and
   `load_chars_area=yasik` (area file prefix, so other chapters are not affected).
2. Swap the spawns in the stage script (backup `.bak` made once):
   `python -I tools/ngb_sty_swap.py <Cache>/yasik_cmn.afs 0x800 <old type> <new type> 0x5b,0x0f`
   (0x800 = chapter 1 Normal block; ops 0x5b = spawn, 0x0f = count check. Never patch other ops.)
3. Big enemies (titan) get stuck on Jonin's ambush/path entrance: swap them into plain spawns
   (Genin). Human-sized enemies (Yonin) work in Jonin's spots.
4. Undo: copy `yasik_cmn.afs.bak` back and remove the load_chars lines.

Cutscene-only types (e.g. 0x3D Ayane, 0x3B R_RYU) have no load list entry and cannot fight.
Memory: several big enemies at once may still run out of character memory.

## Do not change the spawn kind (found 2026-11-08)
The 3rd argument of spawn op 0x5b (0x81-0x90 in chapter 1) is a **flag id**: it is set when that enemy dies, and door/event logic reads it with op 0xd6. Rewriting it (e.g. to 0xff) leaves doors locked forever. Keep the original kind; only swap the type.

Also swap the type in ops **0xa5**(group id, TYPE) and **0x5c**(0, TYPE): they wait until every enemy of that type in a group is dead, then open the door. If they still name the old type, those doors never open (2026-11-08). ngb_sty_swap.py ops: 0x5b,0x0f,0xa5 (patch 0x5c by hand).
