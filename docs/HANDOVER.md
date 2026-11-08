# Ninja Gaiden Black modding (ngbrecomp fork): project handover

Read this first if you are an AI agent (or a person) continuing this project. It covers the goal,
the setup, how to build and test, every mod and tool made, every finding (tested or not), what
failed and why, and what is left. **Keep it up to date**: after each piece of work, update
"Status" and "Next steps" and the date below. Exact addresses and function details are in
`docs/function_map.md`; the enemy table is `docs/enemy_types.csv`.

Last updated: 2026-11-06 (enemy table 64 rows).

---------------------------------------------------------------------------------------------------

## 1. The project

**Goal:** more control over **Ninja Gaiden Black** (original Xbox, 2005) than the ngbrecomp port
gives: change damage, combos, animations, enemies, and understand the game's code. The user chose
"option 1": fork ngbrecomp and mod it in C (not a UE5 remake; that is a separate older project in
`G:\NinjaGaidenSigma\`, see its `PROJECT_HANDOVER.md`).

**ngbrecomp** (upstream `github.com/gamboozino/ngbrecomp`) is a *static recompilation*: the Xbox
game's x86 code was turned into C (`src/recomp/gen/`, about 11,559 functions named `sub_XXXXXXXX`,
89 MB) and runs natively with a kernel / D3D / audio layer (`xboxrecomp/`). The user's own Xbox
game files are needed at run time; they are not in the repo.

**About the user:** works in English (not their first language); wants short, plain explanations
and quick results. They play and report what they see (move numbers from the title, what enemies
did). They found long manual rounds too slow: prefer automatic logging and offline analysis.
They run `sudo` commands themselves. Never enter passwords or credentials. Commit email:
amin.saeedi447@gmail.com. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---------------------------------------------------------------------------------------------------

## 2. Setup, build and test

| What | Where |
|---|---|
| Repo (WSL Ubuntu, user `amin`) | `~/ngbrecomp`, branch **`my-mods`** |
| Remotes | `origin` = github.com/Amin447/ngbrecomp (the user's fork), `upstream` = gamboozino/ngbrecomp |
| Game files (from the user's disc) | `C:\Users\10\AppData\Local\NinjaGaidenBlack\game\` (default.xbe, *.afs, load_img.bin) |
| Normal play build | `G:\NinjaGaidenBlack\WindowsBuild\` (its `mods.txt` has the damage mod) |
| Test build (all research tools) | `G:\NinjaGaidenBlack\RecordBuild\` |
| Extracted files | `G:\NinjaGaidenBlack\Extracted\first_slice\` (ryu.chr, ryu.mtn, ...) |
| Logs from play | `G:\NinjaGaidenBlack\RecordBuild\recordings\` |
| Enemy table (CSV) | `G:\NinjaGaidenBlack\enemy_types.csv` and `docs/enemy_types.csv` |

**Build (Windows exe, cross-compiled in WSL):**
```
cd ~/ngbrecomp && packaging/windows/build.sh
cp build/windows-release/NinjaGaidenBlack/NinjaGaidenBlack.exe /mnt/g/NinjaGaidenBlack/RecordBuild/
```
- Quick compile check with errors shown: `ninja -C build/windows-release/build ninja_gaiden_black`.
- Copying fails with "Permission denied" while the game is open: ask the user to close it.
- Linux build: `ninja -C build/linux` (runs on the CPU in WSL, too slow to play; use Windows).
- Build fixes made: `xboxrecomp/src/nv2a_vk/CMakeLists.txt` adds `SPIRV-Tools-static` (Ubuntu
  glslang link bug); `packaging/windows/build.sh` makes the arcade-target grep optional (`|| true`).

**Launchers in RecordBuild:**
- `ShowAction.bat`: the main research launcher. Sets `NGB_SHOW_ACTION=1` and `NGB_SPAWN_LOG=1`,
  `NGB_GAME_DIR=%LOCALAPPDATA%\NinjaGaidenBlack\game`, writes the game's stderr to
  `recordings\stderr.txt`. Play in a window to read the title bar.
- `Record.bat` (F9 function recording), `Actions.bat` (`NGB_REC_MODE=actions`): older tools.

**Practical tips (learned the hard way):**
- From Windows, run WSL commands as script files: write `x.sh` in the scratchpad, strip `\r`
  (`tr -d '\r'`), then `wsl bash /mnt/c/.../x.sh`. Inline `wsl bash -c "..."` mangles `$`,
  quotes and parentheses.
- The Bash tool's heredocs turn `\\n` into `\n`: when a Python patch must match C text containing
  `'\n'`, use `chr(92)` or anchor on other lines.
- Do not name a scratch script `nt.py` (it shadows Python's `nt` module); run Python with `-I`.
- `src/recomp/gen/` is **not in git**. Hand edits there are redone by `tools/patch_*.py`
  (see section 4); run them all after any regeneration.
- **Mission Mode** is unlocked by the port itself: main menu > RECOMP SETTINGS > Cheats > Unlocks >
  Missions (every mission offered, the save untouched). Missions are the fastest way to meet many
  enemy kinds.
- The game sometimes shows "There's a problem with the disc you're using" at start-up and then
  starts fine on the next try with the same settings (seen twice with no mod code run). Cause
  unknown; `recordings\stderr.txt` is captured to find out. Editing a loaded game file in memory
  (ryu.chr) also caused this screen, so don't patch loaded files.

---------------------------------------------------------------------------------------------------

## 3. Mods (in `src/my_mods.c`, set in `mods.txt` next to the exe, or env `NGB_MOD_*`)

All take effect at game start (restart after editing `mods.txt`). Numbers may be hex (`0x...`).

| Option | What it does | Status |
|---|---|---|
| `damage_taken=X` / `damage_dealt=X` | Scale damage to Ryu / to enemies (hit function `sub_001E1680`, hooked in `src/cheats.c`) | Works |
| `log=1` | Print each scaled hit | Works |
| `anim_swap=FROM:TO` | Every move of Ryu's playing animation FROM plays TO (patches the loaded ryu.mtn move table; ids: <10000 Ryu's own clip, 10000+N weapon clip N) | Works: `39:80` changed only the running jump; `10400:10550` made X play the XY swing |
| `move_swap=FROM:TO` | When the game picks Ryu's next move FROM, it gets TO (rewires combos) | Works: `0x191:0x1F2` made X X end in the XYY finisher |
| `enemy_swap=FROM:TO` | Objects spawning as type FROM spawn as TO | Works between enemies loaded in the same area: Genin (0xE) to white-clad ninja (0x44) and to bat (0x1C) tested |
| `variant_swap=TYPE:FROM:TO` | Change an object's kind (+0x277A) at spawn and on its first frame | Changes the number only: SWAT kind and look did **not** change (see 5.4) |

All swaps wait until Ryu stands in a level (his position is not 0,0,0), because the game reads some
types during boot.

---------------------------------------------------------------------------------------------------

## 4. Research tools

**In the game (`src/action_log.c`, on with `NGB_SHOW_ACTION=1`, i.e. ShowAction.bat):**
- Window title: `move XXX anim ryu:N|weapon:N | action 0xNN name < last 10 actions | hit type TTTT v ...`
  (Ryu's current move and its animation, his action byte, the type and spawn fields of the last
  thing he hit). Built on the game thread; the window thread only reads copies (reading guest
  memory there crashed the game).
- Object slots: up to 128 looked at (the first 48 only until 2026-11-06, which could miss bosses); a slot counts when its +0x26D8 leads to a chr_/itm_ file.
- `recordings/objects.txt`: snapshot of all object slots when they change (type, health block,
  position, variant fields).
- `recordings/spawns.txt` (`NGB_SPAWN_LOG=1`): every type read by the spawn code, with frame.
- `recordings/typedata.txt`: first 128 bytes of each new type's data (+0x26D8), to name it.
- `recordings/typefiles.txt`: every pointer in a new type's object to a loaded file.
- `recordings/types_info.txt`: per type: most seen at once, highest health and segments, behavior
  group, data file, kinds. Rewritten every 10 s.
- `recordings/move_writer.txt` (only with `NGB_MOVE_TRACE=1`): functions entered just before Ryu's
  move changed. It hooks **every function call** and slows the game a lot; off by default.
- `recordings/move_field.txt`: the finder that located the current-move field (jump anchored).
- Older: F9 function recording (`src/func_recorder.c`, recordings/rec_*.bin), action logger
  (recordings/act_*.tsv), entry hook `g_recomp_entry_hook` (added in
  `xboxrecomp/src/kernel/recomp_capture.c`), `xbox_FileReadBuffer` (added in
  `xboxrecomp/src/kernel/kernel_file.c`, the buffer of the read the file-read hook sees).

**Offline (`tools/`):**
- `name_types.py GAME_DIR typedata.txt`: names each type by matching its data header (magic,
  size, sections) to every file in the .afs archives. Exact for characters (.chr sizes differ).
- `name_files.py GAME_DIR typefiles.txt`: archive of each loaded file (found that objects point
  at only 2 files; see 5.3).
- `ryu_moves.py RYU_CHR RYU_MTN [--action N | --move N]`: Ryu's move records and animations.
- `rec_analyze.py`, `action_summary.py`, `static_names.py` (docs/static_map.tsv: names, areas
  and tags for 3,339 of the 11,559 functions).
- `patch_move_pick.py`, `patch_enemy_pick.py`, `patch_type_write.py`, `patch_variant.py`: redo
  the hand edits in `src/recomp/gen/` after a regeneration.

---------------------------------------------------------------------------------------------------

## 5. Findings

### 5.1 Ryu
- Action byte `0x4968B4` (player block 0x4968B0). Named live: 00 neutral, 06 idle, 08 recover /
  walk start, 09 walking, 0A walk stop, 26/28/2A run start/running/run stop, 55 standing jump,
  56-58 running jump, 30 falling, 02 landing, 46/47 guard, 22 roll, 0B X-string attacks,
  5B XYY finisher, FF other attacks, B9 Ultimate Technique charge.
- **Current move** u16 at object + 0x2788 = `0x4B75D8` (Ryu's object 0x4B4E50). Confirmed on jumps
  and attacks. X 0x190, XX 0x191, XXX 0x192 (then 0x193, 0x194 in data), Y 0x1CC, XY 0x226,
  XYX 0x227, XYY 0x1F2.
- Move to animation: ryu.mtn (cmn.afs #22) section 1 holds 2,296 move entries `u16 3, u16 anim id`.
  X = weapon clip 400, XX 401, XXX 402, XY 550, XYY 498.
- **How the next move is chosen:** `sub_00034A10` picks one of Ryu's move records in ryu.chr
  (cmn.afs #141; 12-byte records `u16 condition, u16 move, u16 0, u8 action, u8 flags, u32 0`)
  from the command at object + 0x277C; `sub_000345F0` writes the record's move to + 0x2788 and
  starts it. move_swap hooks that read.

### 5.2 Objects and enemies
- Objects are 0x2800 bytes apart from `0x4B4E50` (slot 0 = Ryu). Fields: + 0x8C0 position,
  + 0x26D0 its motions file (.mtn, "chr_dat"), + 0x26D8 its .chr ("chr_dat2") or item/prop file
  ("itm_dat2"), **+ 0x2774 type**, + 0x277A kind, + 0x277C command (changes while acting),
  + 0x2788 current move, + 0x2791 kind partner, + 0x27F0 health block number.
- Health blocks `0x58A3A0 + 0x210 * n`: + 0x184 segment maxima, + 0x194 segments, + 0x1C6 sum.
- **Spawning:** spawn records hold + 0x40 position, + 0x50 u16 type, + 0x52.. more fields copied
  to the object (+0x52 to +0x277A, +0x54 to +0x277C, +0x56 +0x2782, +0x58 +0x2786, +0x5A +0x278E,
  +0x5B +0x2791, +0x5C +0x2794). Spawn functions: `sub_00153100`, `sub_002CD040`, `sub_002F2CC0`.
  Other type writers: `sub_00168EC0` (reset), `sub_002F2780` (via `sub_002FE290`), `sub_002F7020`
  (copies from another object). The spawn lists were **not** found in the .afs files as plain
  records (probably packed or script-built).
- Each enemy kind has its own archive `chr_<name>.afs` (about 60: army, bat, genin, jonin,
  yonin, hanin, kage, garra, hamu, horse, rider, swat, murai, s_mur, doku, ...); `load_img.bin`
  lists the archives alphabetically. chr_jonin.afs has **no .chr**: Jonin reuse genin.chr.
- The table at `0x423600` (index = type) gives a behavior group, valid only for types below
  about 0x5C.
- Weapons and props are objects too, with types of their own (SWAT: 0x135 knife, 0x137 gun,
  0x139 grenade, 0x13B shield; 0x0003 Ryu's hand; types above 0xFF exist).

### 5.3 Enemy types found (full table with health: `docs/enemy_types.csv`, 64 rows)
Ninjas: 0x000E Genin, 0x0044 white-clad, 0x006B chapter 5 (all genin.chr); 0x0017 yonin; 0x005D hanin;
0x0011 and 0x0016 kage. Bosses (by health): 0x0015 Murai 5000, 0x0020 kasek 13000 (4 bars, part 0x0039),
0x0022 furau 10000, 0x0029 hyudo 9800 (parts 0x002A, 0x002B), 0x002C Doku 7500. Others: 0x0019 insect
(hamu), 0x001C bat, 0x001E guuru, 0x0021/0x004E dinosaurs (garra), 0x0026/0x0060 horses, 0x0028/0x004B/
0x006C riders, 0x0055/0x006D cat, 0x000F/0x0043 unagi, 0x0012 haiki, 0x0057 dino (4600, 2 bars), 0x005F s_kag, 0x0040 mist (swarm of 16), 0x0023 masa (byte compare), 0x003A crow, 0x004D ario, 0x0069 fish or mimic (swarm), 0x003B unidentified tiny part, 0x000D army, 0x0013 second SWAT type (swat.chr, kinds 0-2), 0x005E m_arm, 0x0034 tank (parts 0x0037, 0x0038), 0x0056 titan, 0x0018 gamof, 0x0010 yoku (boss 13500, 2 bars), 0x0024 Alma (aruma, 7000), 0x0045 Awakened Alma (s_aru, 12000; part 0x0046), 0x001B Rachel (rei, likely), 0x001D sohei, 0x0067 Evil Ryu (e_ryu, 7000; confirmed), 0x0025 Marbus (marub, 15000), 0x0027 Fiend Murai (s_mur, 12000), 0x002F Spirit Doku (s_dok, 7000; part 0x0033), 0x0059 Nicchae (hit type confirmed) and 0x0054 Ishtaros (very likely): these bosses' +0x26D8 is a small itm_dat2 file, not a .chr, so their model is loaded another way (name them by hit type, not by name_types.py), 0x002E s_swa, 0x005C SWAT (kinds by +0x277A), 0x0031 sumau part, 0x0047 b_grd.
Health in types_info.txt is only meaningful for characters: for items/props the health block number is not theirs and the value is noise. Caution: the first data dump of a type is sometimes an itm file although the type is a character (an object slot's type can outlive the object, or the slot is reused); types_info.txt and the user's hit types are more reliable. Boss health does not change between missions (Alma 7000, Marbus 15000, Doku 7500 in two sessions each). Names come from the game's file names; the user's descriptions turn them into in-game names.
Types sharing a .chr point at the very same loaded files, so the clan / look (e.g. Jonin
textures) is set elsewhere: not yet found. Red ninjas seen in a mission: type still unknown.
Fixed 2026-11-06: typedata.txt skipped types the old address namer had named; every new type is
dumped now. Types missing from it can be named by size (header + 0x0C) against the archives.

### 5.4 Tested and did not work (don't repeat)
- Editing the loaded ryu.chr in memory: disc error screen. Hook the code instead.
- SWAT kind (+0x277A with +0x2791) changed at spawn or first frame: number changes, soldier the same.
- Swapping SWAT weapon object types (knife/gun to shield): types changed, looks the same.
  Equipment and behavior are decided when the soldier and its weapons are created, from data not
  found yet.
- Naming types from the file-read buffer address: wrong (the game copies data elsewhere).
- Searching the executable for a type to archive table: none found (types are not a simple index).

---------------------------------------------------------------------------------------------------

### 5.5 How an area picks its enemies (research, 2026-11-06)

- Cross-chapter enemy_swap fails because the game only spawns types whose chr_*.afs is loaded,
  and each area loads a fixed set (chapter 1 / yasik: ayane, crow, genin, jonin, bat, murai, rat).
- Archive reads run on the game's loader thread (thread entry sub_00333070 -> sub_003399F0 ->
  sub_00339940 worker table at 0x45F320); the stack never shows who asked, so call-chain logging is
  a dead end. Archive names are not in the XBE.
- recordings/all_loads.txt (ShowAction build) logs every file read. Normal vs another difficulty in
  chapter 1 differ in one block: yasik_cmn.afs entry at 0x800 (Normal) vs 0x6A4800 (other
  difficulty), about 0x33000 bytes, magic "stry_dat" (story data). Header: +0x0C size, +0x10 count 3,
  section offsets at +0x20 (0x30 / 0x32070 / 0x328F0 on Normal). Section 1 is a script (records
  like 02 00 00 86 <id> <args...>), section 2 is position/float data. Enemy spawns and chr loads are
  most likely script commands; Genin also loads a different chr_genin entry on the other difficulty.
- Ayane is most likely type 0x3D (named from the archive read; 0x3B has the same size and hp and
  may be a variant). Not yet confirmed by a hit.
- Spawn records are built in memory at run time (e.g. 0x0137DF50), not copied from a file.
  NGB_SPAWN_LOG now also writes recordings/spawn_records.txt (record address, 0x60 bytes, call
  chain); spawn reads go through mymod_enemy_pick_rec(rec) (tools/patch_enemy_pick.py).
- Genin spawn chain: sub_002DF750 > sub_002E3AD0 > sub_002E4630 > sub_002E4790 (event/area manager)
  > sub_002E58D0 > sub_002F7580 > sub_002CD040 (spawn). sub_002F7580 copies the type (+0x2774),
  kind partner (+0x2791), position (+0x8C0) etc. from an existing object (edi) into the record:
  Genin here are cloned from a parent/generator object, so the type originates earlier.
- Next idea: instead of decoding the script, find the function that queues a chr_*.afs load on the
  game thread and call it for titan at area start (load_enemy option).
- **Breakthrough (2026-11-06):** each area builds a list of *global file numbers* to load at
  0xDB5804 (u16, count byte 0xDB5A02; 0xDB5400 is a parallel u32 array, set to 0). The numbers are
  entries of load_img.bin (header: +4 count 0xD12; then 8-byte entries {size, category}); the loaded
  file table at 0xDB33E0 (0x20 bytes a slot: +0 start, +4 end, +8 size, +0x14 u16 file number).
  A chr_*.afs entry's number is found by matching its size with load_img.bin entries.
  Genin: 0x8A 0x8B 0x2C4 0x343 0x388 0x4F5 0x4FF 0x844 0x849 0x8C1 (ryu.chr entry 0 is 0x5E).
  Titan: 0xABC 0xABD 0xABE 0xAC7? 0xAC8 0xAC9 0xB04? 0xB16 (? = guessed between same-size files).
- New options: `load_files=` (add file numbers to the area list, mymod_load_enemies, every frame),
  `load_files_when=` (only lists that hold that number), `drop_files=` (remove numbers).
  Test: load_files=titan + enemy_swap=0xE:0x56 -> **titans appeared in chapter 1, then the game
  crashed** when the next area list (28 files + titan) loaded: likely out of memory. Now testing with
  load_files_when=0x8A and drop_files=0x8A,0x8B (remove Genin's model files).
- sub_002E1C80 (patched by tools/patch_load_enemy.py) also appends to that list but did not run in
  chapter 1; recordings/needed.txt and chr_slots.txt log the list and the table (NGB_SPAWN_LOG).
- **File-list workers (2026-11-06):** sub_0016F640/FA40/FC70/FE40 (called from a table) each take
  a list struct (u32[255] +0, u16 file numbers +0x404, count byte +0x602) and work through it from
  the end (entry set to 0xFFFF, then count - 1). After filling, the game sorts the list and removes
  files already loaded (count drops, e.g. 99 -> 74; normal). tools/patch_load_list.py hooks them with
  mymod_list_tick(list): logs every list to recordings/lists.txt and adds load_files once per filling
  (re-adding as entries were crossed off hung the game). In chapter 1 titan's files then loaded but
  the area hung at 48 files: most likely out of memory.
- A titan mission's list confirmed titan's files: 0ABC 0ABD 0001 0ABE 0B16 0AC7 0AC8 0AC9 0B04.
  Lists are grouped per character. Jonin's group in chapter 1: 0156 051A 0325. Genin's: 0388 008A
  0003 008B 0844 04F5 02C4 0849 04FF 0343 08C1.
- Testing now: Genin and Jonin both swapped to titan, and titan's 8 files take the places of their
  8 biggest own files (drop_files, replaced in place, so the list does not grow).
- Earlier plan: decode the stry_dat script commands (find the command whose argument is type 0x0E or
  genin's archive number), then patch it when the block is read to request titan (chr_titan).

## 6. Status and next steps

**Done:** builds (Linux and Windows), damage, animation, combo and enemy swaps, ShowAction research
mode with automatic logs, enemy naming tools, 64-row enemy table, docs. All pushed to `my-mods`.

**Next steps (pick with the user):**
1. Grow the enemy table: the user plays missions with ShowAction.bat; run `tools/name_types.py`
   on `recordings/typedata.txt`, read `recordings/types_info.txt`, update `docs/enemy_types.csv`
   (also copy to `G:\NinjaGaidenBlack\enemy_types.csv`) and section 5.3.
2. Enemies from other chapters: make the game load an enemy's archive in an area that lacks it
   (needed for swaps across chapters).
3. Find where a soldier's equipment / an enemy's look is set at creation (for SWAT kinds, ninja clans).
4. Combo swaps that depend on the previous move (move_swap applies everywhere today).
5. Find the cause of the occasional start-up disc error (`recordings/stderr.txt`).

### char_pool_extra (2026-11-06)
Grows character pool 0 by N bytes taken from the general pool so titan fits in chapter 1. Re-run tools/patch_char_pool.py after regenerating gen. Result: pending user test.
Result 2026-11-06: hang on area load. Cross-chapter titan shelved.

Photos: G:/NinjaGaidenSigma/make_enemy_photos.py adds a Photo column (Blender renders from UE_Export) and builds enemy_types.xlsx with pictures. No model yet: 003B, 0054 Ishtaros, 0059 Nicchae, 0067 Evil Ryu.

### Sigma data (2026-11-06)
Type numbers = Sigma CHAR_* ids (docs/char_ids.csv). Ishtaros 0x54, Nicchae 0x59, red ninja 0x6B, Ayane 0x3D. See docs/sigma_knowledge.md.

### Stage script swap (2026-11-07)
yasik_cmn.afs (userdata/Cache, Normal block at 0x800) stry_dat = Sigma btl/sty VM (0x82000000|op). Spawn = op 0x69(1, TYPE, 0, x, y, z...); 20 Genin spawns in chapter 1. tools/ngb_sty_swap.py swaps a type in all type-taking ops (backup .bak). Test Genin->titan: Genin gone from gameplay (still in cutscenes), titan not spawned: the script does not load files (0xd6 = flags), the area data does. So the script controls spawns, but titan still needs its files loaded (memory problem, see above).
Update 2026-11-07: op 0x69 = cutscene placement; **op 0x5b(0, TYPE, ...) = gameplay spawn** (Jonin 4, Genin 59; 0x0f(0, TYPE) = count/check). Jonin->Ayane 0x3D via 0x5b: Jonin gone, nothing spawned (0x3D = cutscene-only Ayane, no fighter). Do not patch 0xd6 (flag ids). Use: ngb_sty_swap.py afs 0x800 FROM TO 0x5b,0x0f. Original restored.
Confirmed 2026-11-07: Jonin->Genin via 0x5b/0x0f works (Genin spawn at Jonin spots). Jonin->Murai 0x15 spawned nothing: the new type must be loaded in that area (Murai files only load in his areas). Rule: script swaps work for types the area already loads.
Area map (2026-11-07): ShowAction build writes recordings/area_chars.txt (area archive, room 0xDB9AC2, chr archives in the loaded-file table) on every change. tools/ngb_join.py names file numbers from chr_loads + chr_slots. File numbers name files inside archives (genin.afs: 8A genin.kmd, 8B genin.mtn, 388 genin.chr, 844 genin.wva; 2C4/4F5/849 ninjatou, 343/4FF/8C1 syuri_02); load_img sizes are unpacked sizes.

### Chapter 1 areas: loaded enemies (area_chars.txt, 2026-11-07, Normal, partial run)
| Area archive (order played) | Enemies loaded |
|---|---|
| yasik_05 (start) | genin |
| yasik_03 | genin, jonin |
| yasik_02 | genin, jonin, bat, crow |
| yasik_01 | genin |
| yasik_00 | genin, crow, rat |
Not reached: Murai's areas (Murai/Ayane load only there). A script swap works only to a type loaded in the
same area (e.g. Jonin->Genin anywhere, Genin->Jonin only in yasik_03/02, ->bat in yasik_02).
Room field 0xDB9AC2 read 0 here (wrong address); the area archive read is the reliable marker.
The start of the log also shows a one-time read of every stage archive header (menu scan), ignore it.

### Missions (2026-11-07)
Missions = m_NN*.sty stage scripts in *_cmn.afs (82 found). Table: docs/missions.md (tools/ngb_missions.py). g_*.grp are geometry, not load lists. Open: where a mission chooses its chr loads.
Mission/area character loading (2026-11-07, in progress): on every room change sub_002E2340 (sets room 0xDB9AC2, [0xD52CE0] = stage script) calls sub_002ED290(ctx=[0xDB9350]); it reads a record stream at script section 0 + ctx+0x20 and fills character load keys 0xD52D00 (u16 value, u8 pool, u8 extra) and 0xD69F80 (6-byte), then sub_002ED940 turns keys into files via the stage-data (key, file) table and queues them. Cutscene (rtm) loads use a separate table in the XBE: sub_001DBAE0(n) reads list n at 0x430158 (6-byte records: kind 0 file / 1 character (type, variant) / 2 item / 6,7 file numbers / 8 end). Script command 0x22 = boxes, not loads. ShowAction build logs recordings/load_keys.txt.
Test 2026-11-07: load_keys.txt stayed empty in every room (0xD52D00 / 0xD69F80 layout or timing wrong; ctx+0x20 read 0). area_chars in Mission 00 (room 128, yasik_03): ryu genin jonin yonin bat crow, loaded one by one after the area file. Next: log calls of sub_00173880 (list, pool, key, extra) directly instead of guessing the key tables.

### How an area chooses which characters load (solved 2026-11-08)
load_trace.txt (tools/patch_load_trace.py) showed it: sub_002EE0D0 reads the stage script's load
list (stry_dat header +0x18 -> offset table, entry +8 = section 2) and calls sub_00173880(list
0xDB5400, pool, key) per record (6 bytes: u8 pool, u16 key at +2, u8 extra at +4; a difficulty bit
from 0xD532F2 is tested). key = character/item id (Sigma char_ids numbering), pool 0 = characters,
1/2 = items/objects. sub_002ED940 then turns keys into files through the stage data table.
Chapter 1 story (s_yask00) loads 0/E 0/44 0/1C 0/3A (+rat 4); Mission 00 (m_00mura, same area)
adds 0/6B red ninja and 0/17 Yonin (+ 5D Hannya), which is why the mission can spawn them.
Cutscenes use a separate list in the XBE (sub_001DBAE0, table 0x430158).
New option load_chars=0x17,... (+ load_chars_area=yasik): sub_002EE0D0 also requests these
(tools/patch_load_chars.py). Test pending: load_chars=0x17 + script swap Genin->Yonin.
tools/ngb_loadlist.py is a first decoder of section 2 (record layout still partly off).
RESULT 2026-11-08: load_chars=0x17 (load_chars_area=yasik) + script swap Genin->Yonin (ngb_sty_swap.py 0x800 0xE 0x17 0x5b,0x0f) -> **Yonin appear in story chapter 1**. Cross-chapter enemies work this way: add to the load list + swap the spawn type in the script.
Titan test 2026-11-08: load_chars=0x56,2:0x149,2:0x131,2:0x10B loads all 9 titan files (same as titan stages; extras = pool-2 entries that follow titan in every titan stage load list). Jonin->titan: titans spawn but stand still. Jonin spawns use path/ambush follow-up ops (op6d + op76 waypoints); titan likely lacks that entrance. Next test: Genin->titan (plain spawns).
RESULT 2026-11-08: Genin->titan (plain spawns) + Jonin->Yonin with load_chars=0x56,2:0x149,2:0x131,2:0x10B,0x17,2:0x2B,2:0x2C,2:0x2D,2:0x2E (load_chars_area=yasik): **titans and Yonin both fight in story chapter 1**. Rule: load the type plus the pool-2 extras that follow it in its own stage load list; swap spawns with ngb_sty_swap.py (ops 0x5b,0x0f). Big enemies (titan) do not handle the Jonin path/ambush entrance; use plain spawns (Genin) for them.

Swap data for all enemies: docs/enemy_swap_data.csv + docs/enemy_swap.md (tools/ngb_swap_table.py), 2026-11-08.
Test 2026-11-08: Jonin->cat (0x55) cats only walk (path/ambush spawns again); Genin->Murai (0x15,2:0x82) Murai fight but the game hangs on entering another area (likely character memory: boss model loaded in every yasik area). Rule: ambush (Jonin) spots only for ninja-type enemies; bosses in many areas may not fit.
Test 2026-11-08: Genin->cat (plain spots): cats still passive and wave doors stay locked. Cat stages spawn cats as 0x5b(0, 0x55, 0xff); Genin spots use Genin kinds (0x81, 0x3). ngb_sty_swap.py now takes a 6th arg = kind for swapped 0x5b spawns with first arg 0 (testing 0xff). load_chars=0x55,2:0x10b,2:0x57.
Test 2026-11-08: Genin->cat with kind 0xff + extras 2:0x10b,2:0x57: cats still wander, wave doors stay locked. Not spawn kind, not load. Cat probably needs stage-specific AI input (AI scripts in cat.chr use area/route sensors) - open. Titan/Yonin/Murai fight in ch1; cat does not.
Cat AI (2026-11-08): Sigma tools (code_extract/tools/aiscript.py) do not decode NGB .chr AI correctly (op set differs; too few ops). Sigma cat.chr AI (03230, same enemy) decoded -> G:/NinjaGaidenBlack/enemy_swap/ai/cat_sigma.ai.txt. Main script: default mode var0=2/var2=1 = wander/approach (script 1: aim/route to Ryu, attack only when mode2838 self==1 / target==2, likely the battle group engagement state); special branches for its home battle groups 401/407 (areas). Hypothesis: in chapter 1 the Genin groups never set the cat engaged, so it wanders; titan/Yonin AI do not wait for it. Next: live log of the cat AI vars / mode (Sigma +0x2838 ~ NGB +0x279C if the +0x9C shift of type +0x2810/+0x2774 holds).
ai_snap test 2026-11-08 (Genin->cat, 4 cats + Jonin): object +0x277C/+0x277E/+0x2780 = current move (3 copies), +0x2784.. = action. Cats only use moves 0x06-0x23 (walk/turn/idle), never attacks (Jonin 0x105/0x109 etc). Sigma-style AI vars (u16 x13) are not inside the 0x2800 object: NGB keeps the AI/controller block elsewhere (pointer not found yet). Spawn kinds from Genin spots stay in +0x2791 (0x80-0x82). Cat swap still open; next would be finding the NGB AI runner/controller.

### Enemy AI decoded (2026-11-08)
NGB .chr AI scripts (section 4 sub-table 0x10) = Sigma's bytecode with shifted op numbers:
NGB op <= 0x30 same; 0x31-0x91 = Sigma +1; 0x92-0x96 (NOT/AND/OR/ELSE/END) = Sigma +4.
tools/ngb_ai.py converts and runs Sigma's aiscript.py (needs G:/NinjaGaidenSigma/code_extract/tools).
Decoded: G:/NinjaGaidenBlack/enemy_swap/ai/<name>.ngb_ai.txt (cat, genin, titan, yonin).
Cat: script 0 "IF NOT in_area(self) -> var2 = 3" sends it to script 7 = walk back to its group's
spot (op 0x4E = point INSIDE an area; aiscript's name outside_area reads backwards). In chapter 1's
Genin groups the cat is never inside a group area, so it only wanders. Test patch: cat.chr script 0
byte (pattern 92 4d 01 0d 02 03 00, the 03) -> 01 in userdata/Cache/chr_cat.afs (backup .bak).
Cat patch 1 (out-of-area rule) alone: still wandering. Cat attacks only when within 5 m AND (var0==5 or var2 in 4/6); its own AI never sets var0=5/15 (only var0==15 -> var2=4), so the battle group script must order it. Patch 2: script 0 "var== 0, 15" (NGB bytes 59 00 0f 00 0d 02 04 00) -> "var== 0, 2" so the default state allows attacks. Testing.
RESULT 2026-11-08: **cats attack in chapter 1** (Genin->cat, kind 0xff, load_chars=0x55,2:0x10b,2:0x57) with two 1-byte AI patches in userdata/Cache/chr_cat.afs cat.chr script 0: (1) 92 4d 01 0d 02 03 00 -> ...02 01 00 (out-of-area no longer sends it home), (2) 59 00 0f 00 0d 02 04 00 -> 59 00 02 00 ... (default state allows attacks; normally the battle group orders var0=15). General rule: enemies that wait for group orders need such AI patches outside their home stages; check with tools/ngb_ai.py.

## Do not change the spawn kind (found 2026-11-08)
The 3rd argument of spawn op 0x5b (0x81-0x90 in chapter 1) is a **flag id**: it is set when that enemy dies, and door/event logic reads it with op 0xd6. Rewriting it (e.g. to 0xff) leaves doors locked forever. Keep the original kind; only swap the type.

Also swap the type in ops **0xa5**(group id, TYPE) and **0x5c**(0, TYPE): they wait until every enemy of that type in a group is dead, then open the door. If they still name the old type, those doors never open (2026-11-08). ngb_sty_swap.py ops: 0x5b,0x0f,0xa5 (patch 0x5c by hand).

The 3rd argument of spawn op 0x5b (0x81-0x90 in chapter 1) is a **flag id**: it is set when that enemy dies, and door/event logic reads it with op 0xd6. Rewriting it (e.g. to 0xff) leaves doors locked forever. Keep the original kind; only swap the type.

Also swap the type in ops **0xa5**(group id, TYPE) and **0x5c**(0, TYPE): they wait until every enemy of that type in a group is dead, then open the door. If they still name the old type, those doors never open (2026-11-08). ngb_sty_swap.py ops: 0x5b,0x0f,0xa5 (patch 0x5c by hand).

## Locked doors after a swap: solved (2026-11-08, tested: door opens)
Spawns `0x5b(1, TYPE, area)` and their `0x0f(1, TYPE)` checks are **door-entrance spawns** (enemy bursts in through a door). A non-ninja enemy (cat) cannot do that entrance, the event never ends and the door stays locked. Keep those as the original type. `ngb_sty_swap.py` now skips them by default (`--doors` to force), swaps ops 0x5b,0x0f,0xa5,0x5c by default, and no longer changes the spawn kind.
Working chapter 1: `python -I ngb_sty_swap.py <Cache>/yasik_cmn.afs 0x800 0xe 0x55` (cats in Genin spots, Genin still burst through doors).

## Sigma extra chapters (2026-11-08)
See docs/sigma_extra_chapters.md: Rachel chapters use NGB areas; blockers = script op numbering, playable Rachel, KMD model format. Next: Sigma->NGB stage-script op map.

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

## Several areas at once + r_jigoku (2026-11-08)
- **mods.txt `load_chars` per area:** up to 8 `load_chars=` lines (64 entries), each followed by its own
  `load_chars_area=`; every area gets only its own line's extras (my_mods.c, exe built 22:10). Current lines:
  yasik (cats), chrch (Doku), hell (Ishtaros + hand 0x5B), pyrmd (Doku's spirit 0x2F + companions 0x32, 0x33).
- **Why the moved file was ignored (test 4):** if a cached archive's total size differs from the original, the game
  copies the original back into the cache. So an archive must keep its size. `afs_replace.py --borrow <file>` puts a
  bigger file into the slot of a file that is not needed (the append fallback was removed).
- **r_jigoku** (Rachel vs Doku's spirit, pyramid zone 106) converted into BOTH pyramid missions `m_16s_ar` and
  `m_59prmd` (their arenas match Rachel's coordinates). They borrow the slots of `s_jigoku_l2.sty` / `s_jigoku_l4.sty`,
  so **the story pyramid on Hard / Master Ninja is broken until pyrmd_cmn.afs.bak is restored**.
  Doku's spirit needs companions (from m_17s_dk's load list): `load_chars=0x2f,2:0xb8,2:0x3,0x32,2:0x89,0x33,1:0xb8`.
- **r_jigoku test 1: black screen.** all_loads.txt: the game read m_16s_ar at its ORIGINAL offset (0x819800) with
  the NEW length - file positions come from the archive in the installed game folder
  (`%LOCALAPPDATA%\NinjaGaidenBlack\game`), data/sizes from the cache copy. So `--borrow` (a moved file) needs the
  installed copy to have the same header: the edited archive was copied there too, original kept as
  `pyrmd_cmn.afs.orig` (restore both: game\pyrmd_cmn.afs.orig -> pyrmd_cmn.afs, Cache\pyrmd_cmn.afs.bak -> pyrmd_cmn.afs).
- **r_jigoku test 2: crash.** The game still read the mission at its ORIGINAL position with its ORIGINAL size:
  **mission scripts (category 17) are listed in `game\load_img.bin` (size, category) and read from their original
  place.** So a mission file can never move; it can only grow IN PLACE over the next file, with its size also patched
  in load_img.bin. `levels/grow_mission_inplace.py` does this for m_16s_ar (grows over s_jigoku_l2.sty, patches
  load_img entry 0xB86 0x4A50 -> 0x68C0). m_59prmd is back to original (its next neighbour is the name table).
  Restore: game\load_img.bin.orig, game\pyrmd_cmn.afs.orig, Cache\pyrmd_cmn.afs.bak.
  (r_hell / r_chrc03 worked because their files kept the original position and size.)
- **r_jigoku test 3 (m_16s_ar): crash while loading characters** (Super Alma, Arioch, shadows, cats from the mission's
  own list + Doku's spirit set = too much memory). New converter option `--load-only <types>`: removes every other
  character (and its pool-2 extras) from the container's load list. Test 4: `--load-only 0x2f` (list emptied;
  mods.txt adds Doku's spirit and companions).
- **r_jigoku test 4: still crashes - parked.** Load list trimming works (only Doku's spirit 0x2F + companions 0x32,
  0x33 load from our lists), but: Super Alma (`s_aru`) still loads through another path (LOADCHR from 0x002EDF18,
  not the stage load list), and Doku's spirit pulls files from its home area boff (e.g. `bf_door3.sob` from
  boff_cmn.afs) right before the crash. In NGB, Doku's spirit seems tied to its final-stage arena (boff); Sigma
  rebuilt that fight for the pyramid. Object ids 151/192 are the same in both games (not the cause).
  Options: test it in a boff mission instead (Doku's spirit's home), or move on to the Tairon chapters.
  Current state: pyrmd changes still installed (restore game\pyrmd_cmn.afs.orig, game\load_img.bin.orig,
  Cache\pyrmd_cmn.afs.bak to undo).

## Tairon: r_tlna04 (2026-11-08)
- Load lists (section 2) are **per zone**: header of (u32 zone, u32 offset) pairs up to 0xFFFF, then one record list
  per zone ({u16 pool, u16 key, u16 0} up to pool 0xFF). `--load-only` only handles single-zone lists (guarded).
- New converter options: `--replace-zone-rules` (the container's zone-keyed rules = story stage logic also give their
  slots/space to the converted rules; global rules = mission mechanics stay), `--drop-battles N`.
  Item-drop ops 0x61/0x160/0x161 (item ids differ between games) and 0x16a/0x16c are dropped for now.
- r_tlna04 (Rachel in Tairon: Super SWAT wave + Nicchae, zone 77) -> NGB Mission `m_54tlna.sty` (the Super SWAT
  mission; it already loads Super SWAT in zone 77). Battle 0 (a Doku's-spirit 0x2F appearance) left out.
  Same size, replaced in place. mods.txt adds Nicchae for `tln_a`.
- r_tlna04 test 1: the user opened m_70tlna (unchanged; regular SWAT + Genin) and it hung while loading. Like m_59prmd,
  an unchanged big mission hangs once mods.txt adds a boss (Nicchae) to its area: **extra load_chars in big story-stage
  missions run out of memory**. Nicchae line for tln_a commented out; test m_54tlna (Super SWAT + dinosaurs) without it.
- r_tlna04 test 2: the user opened m_70tlna, then m_39tlna (menu names do not show which file is which). So r_tlna04 is
  now in **all 8 Tairon city missions** (`levels/install_r_tlna04_all.py`); new converter option `--type-map 0x2e:X`
  swaps Rachel's Super SWAT wave for an enemy the mission already loads in zone 77 (no extra loading = no memory hang):
  m_39/m_54 Super SWAT, m_27/m_53/m_70 Genin (0xe), m_33/m_43 soldiers (0xd), m_78 Enemy Ryu (0x67). All same size,
  in place. Undo: Cache\tln_a_cmn.afs.bak.
- r_tlna04 test 3: no enemies, Ryu could not move (m_70tlna, zone 75). Rachel's start-up rules (no zone key) lock control
  (0x10c) and teleport her to Sigma point 465 (`0x76 0 465`); NGB's container has no such point, so Ryu stayed in zone 75
  locked, and control is only given back by the battle rule in zone 77. New option `--no-start-lock` drops 0x10c and
  0x76 from start-up rules; all 8 Tairon missions rebuilt with it. The battle starts when Ryu walks into zone 77
  (Rachel's battle area around x 45..75, z -65..-90).

## Sigma extra chapters: REVERTED (2026-11-08)
All game-file changes undone (cache archives, game\load_img.bin, game\pyrmd_cmn.afs, mods.txt lines). Findings and tools kept: see the summary at the top of docs/sigma_extra_chapters.md. The per-area load_chars feature in my_mods.c is kept (general).

## Missions: how they work (2026-11-08)
See docs/mission_anatomy.md: mission N = global file 0xB76+N (load_img.bin cat 17), script in <area>_cmn.afs decides the area, per-zone load lists, Mission 00 rules taken apart, plan for a custom mission (edit in place).

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
