# Ninja Gaiden Black modding (ngbrecomp fork): project handover

Read this first if you are an AI agent (or a person) continuing this project. It covers the goal,
the setup, how to build and test, every mod and tool made, every finding (tested or not), what
failed and why, and what is left. **Keep it up to date**: after each piece of work, update
"Status" and "Next steps" and the date below. Exact addresses and function details are in
`docs/function_map.md`; the enemy table is `docs/enemy_types.csv`.

Last updated: 2026-11-06 (enemy table 60 rows).

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

### 5.3 Enemy types found (full table with health: `docs/enemy_types.csv`, 60 rows)
Ninjas: 0x000E Genin, 0x0044 white-clad, 0x006B chapter 5 (all genin.chr); 0x0017 yonin; 0x005D hanin;
0x0011 and 0x0016 kage. Bosses (by health): 0x0015 Murai 5000, 0x0020 kasek 13000 (4 bars, part 0x0039),
0x0022 furau 10000, 0x0029 hyudo 9800 (parts 0x002A, 0x002B), 0x002C Doku 7500. Others: 0x0019 insect
(hamu), 0x001C bat, 0x001E guuru, 0x0021/0x004E dinosaurs (garra), 0x0026/0x0060 horses, 0x0028/0x004B/
0x006C riders, 0x0055/0x006D cat, 0x000F/0x0043 unagi, 0x0012 haiki, 0x0057 dino (4600, 2 bars), 0x005F s_kag, 0x0040 mist (swarm of 16), 0x0023 masa or rei, 0x000D army, 0x0013 second SWAT type (swat.chr, kinds 0-2), 0x005E m_arm, 0x0034 tank (parts 0x0037, 0x0038), 0x0056 titan, 0x0018 gamof, 0x0010 yoku (boss 13500, 2 bars), 0x0024 Alma (aruma, 7000), 0x0045 Awakened Alma (s_aru, 12000; part 0x0046), 0x001B Rachel (rei, likely), 0x001D sohei, 0x0067 Evil Ryu (e_ryu, 7000; confirmed), 0x0025 Marbus (marub, 15000), 0x0027 Fiend Murai (s_mur, 12000), 0x002F Spirit Doku (s_dok, 7000; part 0x0033), 0x0059 Nicchae (hit type confirmed) and 0x0054 Ishtaros (very likely): these bosses' +0x26D8 is a small itm_dat2 file, not a .chr, so their model is loaded another way (name them by hit type, not by name_types.py), 0x002E s_swa, 0x005C SWAT (kinds by +0x277A), 0x0031 sumau part, 0x0047 b_grd.
Health in types_info.txt is only meaningful for characters: for items/props the health block number is not theirs and the value is noise. Boss health does not change between missions (Alma 7000, Marbus 15000, Doku 7500 in two sessions each). Names come from the game's file names; the user's descriptions turn them into in-game names.
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

## 6. Status and next steps

**Done:** builds (Linux and Windows), damage, animation, combo and enemy swaps, ShowAction research
mode with automatic logs, enemy naming tools, 60-row enemy table, docs. All pushed to `my-mods`.

**Next steps (pick with the user):**
1. Grow the enemy table: the user plays missions with ShowAction.bat; run `tools/name_types.py`
   on `recordings/typedata.txt`, read `recordings/types_info.txt`, update `docs/enemy_types.csv`
   (also copy to `G:\NinjaGaidenBlack\enemy_types.csv`) and section 5.3.
2. Enemies from other chapters: make the game load an enemy's archive in an area that lacks it
   (needed for swaps across chapters).
3. Find where a soldier's equipment / an enemy's look is set at creation (for SWAT kinds, ninja clans).
4. Combo swaps that depend on the previous move (move_swap applies everywhere today).
5. Find the cause of the occasional start-up disc error (`recordings/stderr.txt`).
