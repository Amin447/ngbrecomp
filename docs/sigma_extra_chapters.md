# Sigma's extra chapters: can they go into NGB? (investigated 2026-11-08)

Method: every Sigma file name (`G:\NinjaGaidenSigma\text\file_names.csv`) compared with every NGB archive entry
(`plan/work/NGB-REUSE-AUDIT/black_archive_index.csv`); characters each extra script spawns read from the scripts.

## What Sigma has that NGB does not
| Content | Sigma files | Areas | Characters spawned |
|---|---|---|---|
| Rachel chapters (playable Rachel, 13 scripts) | `story/rachel/r_*.sty/.btl` | tln_a (r_tlna01/04/05), tln_b (r_tlnb01/05), chrch (r_chrc01-03), ssato (r_ssato2), boff isle (r_isle01), pyrmd (r_jigoku), hell (r_hell) | I_REI (player Rachel), BAT, BLNIN, ARUB, ARU_H, CAT, GERED, MASA, RAT, BIRD, CROW, F_UNA, KOT_B, TRUCK, S_DOK, WHIP, **M_VSW** |
| New Ryu stage "osa" | `story/s_osa00.sty/.btl`, `stage/osa_00/01/02/99`, `rtm/osa_*.rtm`, `osa_flame` items, `os_*` objects | new area (no NGB counterpart) | RYU, GENIN |
| Rachel missions | `story/m_rei00..14.sty` | various | Rachel |
| New characters | i_rei (player Rachel), i_gam, ghost, girta, s_dai, m_vap, miko, sparr, sidecar, ufo_m/r | | |

## What NGB already has
- All Rachel-chapter **areas** except osa: the stage geometry is in NGB.
- Rachel's model and hammer (`chr_rei.afs`: rei.kmd, rei.mtn, ham.kmd), but only as a cutscene/NPC: rei.chr is 1760 bytes, no move set.
- Almost every enemy the Rachel chapters spawn (only M_VSW and the player I_REI are missing).

## Blockers
1. **Model format:** NGB models are Xbox `.kmd` (+ .wva); Sigma's are `.tmc/.xmc/.g1t`. Sigma-only models (osa stage, M_VSW, i_rei variants) need a TMC->KMD converter. We can read both (Blender imports), not write KMD.
2. **Script opcodes differ:** Sigma .sty spawns with op 0x6a, NGB .sty with op 0x5b (like the AI scripts, op numbers shifted). A Sigma->NGB stage-script op map is needed before any Sigma script runs in NGB.
3. **Playable Rachel:** NGB's engine has only one player (Ryu). Sigma added a second player record (+0x1450, char 0x71 I_REI) with her own move set. Real playable Rachel = new engine code in the recomp plus her .chr/.mtn (Sigma format, needs conversion/remap).

## Verdict / cheapest paths
| Path | Effort | Result |
|---|---|---|
| A. Rachel chapters played **as Ryu**: translate r_*.sty/.btl to NGB ops, load in existing areas | medium (needs op map) | Rachel's levels/enemy layouts, Ryu as player |
| B. A + Rachel skin: Ryu's moves on Rachel's model (rei.kmd) | medium-hard (bone mapping) | looks like Rachel, plays like Ryu |
| C. Real playable Rachel | very hard (engine code + move set conversion) | like Sigma |
| D. osa stage | very hard (TMC->KMD + collision converter) | new area |

**First step for any path:** build the Sigma->NGB stage-script opcode map by lining up Sigma `s_yask00.sty` with NGB's (same chapter, same logic), the same way the AI op map was found.

## Sigma -> NGB stage-script op map (built 2026-11-08)
Tool `sty_opmap.py` (G:\NinjaGaidenSigma\levels, copy in G:\NinjaGaidenBlack and repo tools/). Found by aligning four
chapters of both games on their arguments (~44k instructions).
- NGB 0x01-0x05 = Sigma same; NGB 0x06-0x55 = Sigma +5; NGB 0x56-0x141 = Sigma +0x0F; NGB 0x142 = Sigma 0x16E.
- Sigma-only ops are mostly multi-value (per difficulty) versions of NGB ops, e.g. 0x61(a,x,...)=NGB 0x2c(a,x),
  0x160=0x83, 0x161=0x11f, 0x162/163/164=0xd1/d2/d4; flag ops 0x153-0x157 = NGB 0xd6 but with **different flag ids**
  (Sigma 1024 = NGB 896); item ids differ too (Sigma 42 = NGB 64).
- NGB has no .btl files; Sigma battles (.btl, ops 0x06-0x0a) must be merged into the .sty.
- Rachel chapters by Sigma-only ops: r_tlna01 0 (fully convertible), r_chrc03 1, r_jigoku 2, r_hell 3, r_isle01 27, others 100-450.
Next: flag-id + item-id maps (same alignment), then convert r_tlna01 (+ its .btl) and try it in tln_a as Ryu.

## Converting a Sigma chapter script to NGB (findings 2026-11-08)
- **File layout:** section 0 starts with a 17-field header; each field means the same in both games (only the order of the
  regions in the file differs), so a Sigma file can keep its layout. Field 6 = list of rule blocks.
  NGB sets fields 15/16 to 0xFFFFFFFF / 0x86000002 (Sigma 0 / 0).
- **Rules:** each block = "when <conditions> then <actions>": `2 n` (repeat), `5 key` (zone), `6` conditions, `56` actions, `142` end (NGB numbers).
- **Battles (.btl -> .sty):** a Sigma battle block = `0x0A mask` (difficulty variant: one block per enemy type, e.g. Genin/Jonin/Hannya)
  + `S6 ... S7` pre-section + `S8` + a normal "6 conditions 56 actions" rule + `S9`. NGB has the same rule inline in the
  .sty, without mask/markers (difficulty comes from the _l/_l2/_l4 files). Convert = keep the Normal variant, drop
  mask, pre-section and markers, append the block to the .sty block list. Proven by matching s_yask00.btl to NGB s_yask00.sty.
- **Flags:** renumbered per chapter (no global shift; `flag_map_sigma_ngb.csv` has 693 seen pairs, half uncertain).
  A converted chapter can keep its own flags; only shared/special flags (e.g. NGB 896) need mapping.
- **Sigma-only multi-value ops:** 0x61->0x2c, 0x160->0x83, 0x161->0x11f, 0x154->0xd6 (keep one value), 0x157 -> 0xd6 (flag op).
- **Rachel chapters:** player Rachel = type 113 (I_REI); as Ryu it must become Ryu's type. Text ids are Sigma's (may be missing in NGB).
  r_tlna01 = hint popups only (no fights). Smallest fight chapter: **r_chrc03** (7+4 blocks, 1 Sigma-only op, enemy type 0x2C);
  then r_jigoku (43+4), r_hell (29+7: Nicchae + Ishtaros).

## Converter + first test (2026-11-08)
- `sigma2ngb_sty.py <sigma.sty> [<sigma.btl>] -o out.sty [--player 0] [--load-from <ngb.sty>]`: renumbers ops,
  Rachel (113) -> Ryu (0), 1-arg Sigma-only ops -> no-op (`0x57 0`), merges Normal battle blocks from the .btl,
  relocates op 0x9b data (pointer,words,pointer,words into the .btl), sets NGB header fields, optional NGB load list.
- `afs_replace.py <afs> <name> <file>`: replace one file inside an AFS in place (.bak once).
- Test installed: Sigma `r_chrc03` (Rachel vs Doku, church zones 183/188) converted and put over `s_chrc03.sty` in
  `RecordBuild\userdata\Cache\chrch_cmn.afs` (backup chrch_cmn.afs.bak). NGB's own s_chrc03 (321 rules) also runs the
  rest of that church part, so doors/items outside Doku's arena may not work during this test. Undo: copy the .bak back.
- **First test crashed (2026-11-08)**: a Sigma file can NOT keep its own tables. Header regions 9-13 (and 2-3) have
  different layouts in NGB (only 4, 5, 8 = box tables match). New converter mode `--container <ngb.sty>`: take an NGB
  file of the same area (all tables NGB-format) and put in only the converted rules (+ relocated battle data).
  Test 2: r_chrc03 rules in NGB `m_06arum.sty` (the Alma mission, Monastery) - other church missions restored.
- **Test 2 result:** loaded, but no enemies and Start (pause) froze: all mission rules were removed, and Rachel's
  rules use zones 183/188 while the Alma mission's arena is zone **187** (same room, same trigger box).
  New options: `--drop-container-spawns` (keep the mission's rules, drop only its enemy spawns), `--zone-map 183:187,188:187`;
  converted rules' flags are moved above the container's highest flag; the rule list is rewritten in place when it fits.
  Test 3 command: `sigma2ngb_sty.py r_chrc03.sty r_chrc03.btl -o out --container m_06arum.sty --drop-container-spawns --zone-map 183:187,188:187`.
- **Test 3 result: no Doku.** Logs: Doku was loaded, Ryu was in zone 187 (object +0x2786 = current zone in NGB).
  Cause: **op 0xd6 (n, s) is not a flag op: it switches rule n of the block list on (s=1) / off (s=3)** (a rule
  disables itself with `0xd6 <own index> 3`). Earlier "spawn kind = flag id" finding: the kind byte is read by the same
  op, so treat it as a rule/slot number. Sigma `0x153 n` = start battle rule n (from the .btl list).
  Converter now: renumbers 0xd6 targets to the rules' new positions, turns 0x153 n into `0xd6 <battle rule> 1`,
  keeps the container's emptied spawn rules in their slots (pointing at an empty rule) so its own numbering stays valid.
  `afs_replace.py` appends a file at the end of the archive when it no longer fits its slot.
- **Test 4 result: the original mission ran** (Alma appeared). The game finds files through its own built-in file
  table, so a file moved to the end of the archive is ignored: **a replaced file must fit its original slot**.
  Converter: with `--drop-container-spawns`, the converted rules now take over the emptied spawn rules' slot numbers
  and code space, so the rule list and file size stay the same (r_chrc03 in m_06arum: 113232 bytes, slots 178-252).
- **Test 5 (2026-11-08): WORKS - Doku appears** in the Alma mission from Sigma's converted Rachel chapter r_chrc03.
  First Sigma stage script running in NGB. Recipe:
  1. `sigma2ngb_sty.py <r_x.sty> <r_x.btl> -o out.sty --container <NGB script of the same area> --drop-container-spawns --zone-map <sigma zone>:<ngb zone>`
     (find the NGB zone by matching trigger boxes; Ryu's current zone = object +0x2786).
  2. Load the new enemies with mods.txt `load_chars=` / `load_chars_area=`.
  3. `afs_replace.py <Cache>/<area>_cmn.afs <script> out.sty` - the file must fit its original slot.
  Next: Sigma-only multi-value ops (0x157, 0x154, 0x61/0x160/0x161) for the bigger chapters (r_jigoku, r_hell).
- **r_hell (2026-11-08):** Sigma-only ops now converted: `0x153 n` / `0x154 v0..v4` (start battle; v1 = Normal) ->
  `0xd6 battle 1`; `0x157 n,s` = rule switch like 0xd6 (n=1024 = none, dropped); `0x16b` dropped. Battle-file rules use
  the .sty's rule numbers. r_hell (zone 213, Nicchae 0x59 + Ishtaros 0x54) put into NGB Mission `m_72arub.sty`
  (Nicchae mission, hell area, same zone 213); mods.txt loads Ishtaros in `hell` (Nicchae is already loaded there).
- **r_hell test 1:** bosses spawned (life bars, positions next to Ryu) but stayed invisible; loud scratching noise.
  Found: bosses are spawned hidden (`0x78 0`) and shown later (`0x78 1`); the Sigma rule also used
  (a) `0x70(0,113,0)` = target Rachel -> now any `(0, 113, ...)` char reference becomes the player;
  (b) entrance id `0x79 2026` - NGB only has 2001-2025 -> `--entrance 0x59:2023,0x54:2025` (NGB's own values);
  (c) `0x9c(id, ptr, n, ptr, n)` pointing into the .btl -> relocated like 0x9b; its id 307 is Sigma-only (NGB max 257,
  probably the battle music/sound - the noise) -> replaced by the container's own id (229).
- **r_hell test 2: WORKS - Nicchae and Ishtaros both fight** (Sigma Rachel chapter r_hell in the Nicchae mission).
  Ishtaros had no hand: mods.txt missed her 3rd extra; correct line `load_chars=0x54,2:0x132,2:0x13d,2:0x13e`
  (always copy the whole "load_chars value" column of enemy_swap_data.csv).
- Ishtaros's hand is a **separate character, type 0x5B CHAR_WHIPW "WHIP HAND"**, created by Ishtaros herself (no
  script spawns it). NGB's m_74whip loads it right after her. Correct line: `load_chars=0x54,2:0x132,2:0x13d,2:0x13e,0x5b`.
  Lesson: some bosses need companion characters; check the boss's own NGB mission load list (section 2) for
  pool-0 entries right after it. (enemy_swap_data.csv's extras for 0x5B are wrong - it picked up the next records.)
- **Confirmed 2026-11-08:** with 0x5B loaded, Ishtaros has her hand. r_hell fully works.
