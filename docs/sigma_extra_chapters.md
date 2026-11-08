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
