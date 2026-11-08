# How an NGB mission works (investigated 2026-11-08, for making our own mission)

## 1. Where a mission comes from
- **Script:** mission N = stage script `m_NN<area>.sty` inside the area's shared archive `<area>_cmn.afs`
  (list: docs/missions.md). The archive it sits in decides the area (map, geometry, lighting).
- **Global file table `game\load_img.bin`:** u32 version 0x10, u32 count 0xD12, then count x {u32 size, u32 category};
  category 17 = every stage script (story + missions, 326). **Mission N = global file 0xB76 + N** (consecutive).
  After the table comes an archive directory: header (u16 0x1000, 1, 0xF, 0), then 16-byte records
  {u32 first file number, u16 file count, char name[10]} for all 675 archives (`boff_cmn` 0xD52 x76, `chrch_cmn` 0xE30 x74,
  `hell_cmn` 0x11F8 x81, `yasik_cmn` 0x1CCC x63 ...). Its numbering is different from the size table's (not linked yet).
- **Hard limits (proven 2026-11-08):** the game reads a mission at its original position in the archive with the size
  from load_img.bin, and replaces a cached archive whose total size changed. So **a custom mission must be built in an
  existing mission's slot, same size or smaller** (or grow over an unneeded next file + patch load_img.bin).

## 2. What is inside a mission script (stry_dat)
- Section 0 = rules ("when <conditions> then <actions>", run while Ryu is in their zone `0x05 zone`).
  `0x01` = armed at start, `0x02 n` = may run n times, `0xd6 (rule, 1/3)` switches another rule on/off,
  `0x56 0` + `0x57 t` = action group at frame t of the rule.
- Section 2 = **load list per zone**: header (u32 zone, u32 offset) pairs up to 0xFFFF, then per zone 6-byte records
  {u16 pool, u16 key, u16 0} ending with pool 0xFF. Pool 0 = character type, pool 2 = its extras (weapons, effects),
  pool 1 = items/objects. Characters must be loaded in the zone where they fight.

## 3. Mission 00 (m_00mura, mansion, zone 33) taken apart - 40 rules
| Rules | What they do |
|---|---|
| 1-2 | Ryu at the start box (26.5, 41.4, -70.1): lock control, place Ryu at (26.3, 41.5, -68.6), give control back |
| 3 (armed at start) | setup: music/lights (0x13d/0xae/0xac), objects (0xc4), battle area (0x9b), spawn the boss Murai (type 0x15) hidden at (41.5, 41.5, -64.3), then show him |
| 4-9 | "respawn templates" per enemy type (0x0f type + 0x18/0x19): Genin 0x0e, Jonin 0x44, Yonin 0x17, Hannya 0x5d, red ninja 0x6b |
| 10 | first wave: Genin, Jonin, Yonin at fixed points, then switches on rules 11-13 |
| 11-19 | more waves when **Murai's health drops below 75 % / 50 % / 25 %** (`0x0f 0 0x15` + `0x1c 1 75.0`) |
| 20-26 | wave bookkeeping (switch rules on/off, counters) |
| 27-29 | a chest/object (type 267) at (49.6, 41.7, -64.0) with an item |
| 30 | **win condition:** Murai dead (`0x0f 0 0x15` + `0x1a 1 0`) -> slow-motion / "clear" (0x133), then rule 31 |
| 31-36 | end of mission: results screen, return to menu |
| 37-39 | standard helper rules every script has |
Load list: zone 33 loads Murai 0x15 (+4 extras), Genin 0x0e, Jonin 0x44 (+1), Yonin 0x17 (+4), Hannya 0x5d (+2),
red ninja 0x6b (+1).

## 4. Making our own mission (plan)
Edit an existing mission in place (same size): e.g. m_00mura -
1. **Enemies:** change the types in the wave rules (10-19) and the boss in rules 3/30, and swap the keys in zone 33's
   load list (same number of records keeps the size). Use enemy_swap_data.csv for each type's extras; watch memory
   (one boss + a few small enemy types is safe; Murai was replaced by bosses before).
2. **Waves / difficulty:** change positions (`0x66 x y z`), health thresholds (75/50/25), counts.
3. **Win condition:** rule 30 waits for the boss type to die - point it at the new boss.
Tools to build: a small "mission editor" that reads a mission, lists its waves / boss / load list, and writes the edits
back in place (reusing sigma2ngb_sty.py's block reader and afs_replace.py).

## Mission editor + first custom mission (2026-11-08)
- `levels/ngb_mission_edit.py show|edit` (copies in G:\NinjaGaidenBlack and repo tools/): `show` lists spawning rules,
  boss health checks and per-zone loads; `edit --swap OLD:NEW` changes every reference (spawns, checks, health bars) and
  rewrites the load list with NEW's extras from enemy_swap_data.csv (drops OLD if NEW is already loaded);
  `--hp 75:90,...` changes wave thresholds. Output is always the same size (refuses if the list no longer fits).
- **Doku needs 6 extras** (`0x2c,2:0x5c,2:0xb6,2:0x106,2:0x3,2:0x10b,2:0x57`) - the earlier church line had only 2.
- **Custom mission 1 "Doku in the mansion"** in Mission 00's slot (m_00mura): `--swap 0x15:0x2c --swap 0x5d:0x6b`
  (Doku replaces Murai; Hannya waves -> red ninjas to make room in the load list). Installed in
  Cache\yasik_cmn.afs (copy before: yasik_cmn.afs.before_mission; the chapter 1 cat swap there is unchanged);
  mods.txt cat lines turned off for the test.
- **Tested 2026-11-08: WORKS - Doku fights in Mission 00** (custom mission 1).
- **Editor extended (2026-11-08):** `show` now gives each wave rule's spawn spot (fixed `0x66 x y z` or "one of N
  points", `0x6b mode offset n`, mode 2 = random), its repeat count (`0x02 n` = how many enemies the rule makes) and its
  alive limit (`0x14 mode n` = only while fewer than n alive). New edits: `--repeat RULE:N`, `--alive RULE:N`,
  `--move RULE:x,y,z;...`. In Mission 00 each wave rule makes 1 enemy, max 3 alive.
- Custom mission 1b "Doku, harder": same as 1 plus `--hp 75:90,50:60,25:30` and rules 11-19 `--repeat 4 --alive 4`.
- Tested 2026-11-09: harder Doku mission looks right to the user (bigger, earlier waves; not measured exactly). Mission scripts have no difficulty variants: edits apply on every difficulty.

## Custom mission loader: mods.txt `mission_file` (2026-11-09)
`mission_file=<N>:<archive>:<file inside>:<our file>` (up to 4), e.g.
`mission_file=0:yasik_cmn.afs:m_00mura.sty:custom/m_00_chapter1.sty`. No game file changes: a new after-read hook
(`xbox_FileReadDoneHook` in xboxrecomp/src/kernel/kernel_file.c, both read paths) lets my_mods.c patch the mission's
size in memory after `load_img.bin` (entry 0xB76+N) and the archive header are read, and copy our file over the
mission when it is read. So a custom mission can be any size. stderr shows `[MOD] mission_file: ...` lines.
Test 1: Mission 00 = unchanged chapter 1 story script s_yask00.sty (valley -> fortress -> Murai).
- **Test 1 result:** the whole chapter 1 played as Mission 00 (valley -> fortress -> Murai); it hung after Murai: the
  story's rule 338 (Murai < 16.7 %) switches on rule 339 (defeat cutscene at 12.5 % + chapter end -> chapter 2).
  Editor option `--append-from <mission> --append-rules 30-37 --redirect 338:339:30` copies Mission 00's ending
  (30 = Murai dead -> clear, 31-36 results, 37 helper) to the end of the chapter script (rules 522-529, d6 targets
  renumbered) and points rule 338 at it. custom/m_00_chapter1.sty (story-only copy kept as m_00_chapter1_story_only.sty).
