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
