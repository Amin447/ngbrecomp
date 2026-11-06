# What the Sigma project tells us about NGB

Source: `G:\NinjaGaidenSigma` (the Ninja Gaiden Sigma 1 → UE5 project; main notes in
`PROJECT_HANDOVER.md` section 2, code notes in `code_extract\notes\`). Sigma is a remake of NGB, so
many data formats and numbers are shared. "Proven" = checked against NGB; "likely" = not checked yet.

## 1. Object type numbers = Sigma `CHAR_*` ids (proven, 2026-11-06)

`docs/char_ids.csv` (copy of Sigma `text/char_ids.csv`) lists ids 0-136 (characters) and 137+
(items; **item number = id - 137**). All 45 NGB types whose model was known match the Sigma enum.
New answers:

| NGB type | Sigma enum | Meaning |
|---|---|---|
| 0x3B | CHAR_R_RYU | Ryu for real-time cutscenes |
| 0x3D | CHAR_AYANE | Ayane (cutscene); story Ayane = 0x6F CHAR_AYA_A |
| 0x44 | CHAR_JONIN | Jonin "HIGH MASTER" (white-clad ninja) |
| 0x54 | CHAR_WHIP | Ishtaros |
| 0x59 | CHAR_ARUB | Nicchae (Alma B) |
| 0x67 | CHAR_E_RYU | Enemy Ryu |
| 0x69 | CHAR_MIMIC | Mimic |
| 0x6B | CHAR_R_NIN | Red ninja "RED SHADOW" |
| 0x53 | CHAR_GERED | Red Genin |
| 0x5D / 0x80 | CHAR_HANIN / CHAR_BLNIN | Hannya ninja / Black ninja |

Some ids are Sigma-only (e.g. 0x6F+ Ayane story, Rachel player, Sigma vehicles); NGB uses ids up to 0x6D.

## 2. Formats that most likely carry over

- **`.chr` files** (moves): section 4 rows = action + return move + category; move-select scripts
  pick moves from buttons; sub-table 9 = attack class (+8) and damage factor (+0x14); sub-table 10 =
  hit reactions; sub-table 12 = grab pairs; sub-table 14 kind 5 = post-hit lock; sub-table 0x10 =
  enemy AI scripts (ops 0x00-0x9B), which press virtual buttons (ids 5-11 AI-only) read by the same
  move scripts. Notes: `code_extract\notes\ryu_moves.csv`, `enemy_ai_input.md`, `hit_reaction_code.md`.
  Tools: `code_extract\tools\movesim.py`, `aiscript.py`, `aisim.py`, `hitreact_dump.py`.
- **Buttons:** X 12, Y 1, jump 2, guard 3, B 13, A+X 4, B+Y 14 (`notes\button_ids.md`).
- **Action tables (`.mtn`)**: command stream, arities in PROJECT_HANDOVER 2.4. `3 id frame` play motion,
  `0 n` wait to frame n (60 fps), `9 1`/`9 0` cancel window, `d 0 1`...`d 0 0` sword hit window,
  `23 kind val` if-blocks, `e hi lo` sounds. Motion id < 4000 own bank, 4000-7999 cmn.mot (hit
  reactions), 8000-9999 other character (grabs), 10000+/13000+/16000+ weapon banks.
- **Ryu's logged moves (Sigma):** X 525 → 526 → 527, Y 608, Y hold 613 → 615 → 621, idle 0, walk 141,
  run 140, jump 303, guard 378, rolls 445/467/461/455. Useful for `move_swap` - check in NGB with ShowAction.
- **Battle / stage scripts (`*.btl`, `*.sty`):** VM words `0x82000000|op`; spawn = `0x6a(a0, char_id,
  slot)` + `0x74`, position `0x75` / `0x7a`, yaw `0x7d`, create `0x97`; op `0x0A` = difficulty mask
  (bit 0 Ninja Dog ... bit 4 Master Ninja). Chapter 1 = `s_yask00` (Normal: 26 genin, 4 jonin, 18 bats,
  3 Murai). Ops: `code_extract\notes\btl_opcodes.md`, `btl_vm.md`; tools in `levels\btllib.py`.
  **This is the likely way to put titan in a chapter properly**: edit the area's battle script so the
  game itself loads the character, instead of forcing files into the load list.
- **Damage:** weapon base (katana 100) x move factor (Ryu X 0.8) x difficulty (0.8/1.0/1.1/1.2/1.5)
  x weapon level (1.0/1.5/2.0). `combat\damage_calc.py`.
- **Stats:** HP etc. come from stat scripts in `cmn/cmn_dat.cmn` (Ryu 1000 HP; genin 240/200/280/360).
- **Essence:** genin drops 50 x (kill bonus + combo multiplier).
