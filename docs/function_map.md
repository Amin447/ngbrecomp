# Function map

What each game function does, as far as we know. `tools/rec_analyze.py` reads the table rows
below (`| sub_XXXXXXXX | name | ...`) and shows the names next to its results.

How to add to it: record a short session with the recording build (F9 to start and stop, F6 to mark
a moment), run `tools/rec_analyze.py` on it, check a candidate by reading its code or poking its
values, then add a row. **Confidence**: *known* (read or tested), *likely* (strong recording
evidence), *guess*.

## Functions

| Function | Name | Confidence | Source | Notes |
|---|---|---|---|---|
| sub_001E1680 | apply hit | known | src/cheats.c | Every hit: target, attacker, segment hit; returns 1 when it kills. Hooked by my_mods.c |
| sub_00154300 | change item count | known | src/cheats.c | eax item, ebx signed change; using, throwing, pickups |
| sub_00164E50 | state checksum | known | src/cheats.c | 24 checksums over health, ninpo, inventory...; a mismatch returns to title |
| sub_0001ACD0 | pad to Ryu action | known | src/intercept.c | Turns controller input into Ryu's next action (bl) |
| sub_0003E400 | attack about to land | known | src/intercept.c | Also asks the inventory for item 0x26 (Intercept scroll) |
| sub_0001B940 | button pressed this frame | known | src/intercept.c | Button, frame window |
| sub_00023520 | UT charge counter | known | src/ut_charge.c | Counts charging frames, raises the charge level |
| sub_00029140 | UT charge marks | known | src/ut_charge.c | Sets the two charge thresholds |
| sub_00016300 | move script | known | src/ut_charge.c | Script interpreter (opcode 0x83 picks the charge attack) |
| sub_001E2EB0 | absorb essence | known | src/ut_charge.c | Essence absorbed; also raises UT charge |
| sub_0004F800 | first-person camera | known | src/camera.c | Runs while the first-person view is up |
| sub_000479B0 | third-person camera | known | src/camera.c | Stick curve, turn and tilt |
| sub_001FA210 | in-play HUD | known | src/hud.c | Each frame; health/ninpo bar and the rest |
| sub_001FA3F0 | health and ninpo bar | known | src/hud.c | |
| sub_001DBEE0 | event runner | known | src/cutscene_skip.c | Runs events and in-game cutscenes once a frame |
| sub_001DD300 | event script commands | known | src/cutscene_skip.c | Sets/clears "skippable" |
| sub_001DB520 | unlock flag test | known | src/costume_menu.c | |
| sub_001DB330 | play time | known | src/playtime.c | |
| sub_00344BE0 | movie status (mwPlyGetStat) | known | src/movie_skip.c | CRI Sofdec |
| sub_0031DA50 | title movie loop | known | src/movie_skip.c | |
| sub_00308D50 | walk render lists | known | src/render_list.c | |
| sub_00308BF0 | insert render node | known | src/render_list.c | Pool of 768 nodes |
| sub_001CA790 | reset render lists | known | src/render_list.c | |
| sub_00221210 | queue HUD and 2D layer | known | src/render_list.c | |
| sub_000FF1A0 | Ryu update (movement/physics) | likely | round 1 | Huge (4600 lines); writes Ryu's position 0x4B5710; runs only while moving in round 1 |
| sub_00107640 | caller of Ryu update | guess | round 1 | Calls sub_000FF1A0 |
| sub_000247D0 | run/locomotion step | likely | round 1 | Reads the active character at [0xDB9E9C]; called by sub_00024160 |
| sub_0002C390 | turn toward stick direction | likely | round 1 | Angle difference on 16-bit angles (0x4000 = 90 deg) at char +0x78C/+0x2D0/+0x2D4; called by sub_00025310 |
| sub_00011050 | move-script helper used while running | guess | round 1 | Called from the move script sub_00016300 |
| sub_0001B120 | move-script input test used while running | guess | round 1 | Called by sub_00016300 and the button helpers near sub_0001B940 |
| sub_003075D0 | per-object effect/attachment while moving | guess | round 1 | ~5 calls a frame while running; many callers |
| sub_000772B0 | wrapper: sub_001CA870 + sub_003075D0 | guess | round 1 | |
| sub_00193F70 | moving-only group (footsteps/ground effects?) | guess | round 1 | Calls sub_001999B0 and sub_001996E0, both running-only |
| sub_001BDD10 | Ryu-specific moving check | guess | round 1 | Reads Ryu's object 0x4B4E50 |
| sub_00193F70 | Ryu per-state update (dispatcher) | likely | rounds 1-2 | Calls the airborne (sub_001963B0) and ground/landing (sub_001999B0, sub_001996E0) updates |
| sub_001963B0 | Ryu airborne update | likely | round 2 | Runs exactly while Ryu is in the air (phi 1.00); 89 float accesses, no constant gravity in the code -- comes from data |
| sub_001999B0 | Ryu ground/landing update | likely | rounds 1-2 | Strongest on the 3 frames after landing; also while running |
| sub_00025310 | player control (stick and buttons to movement) | likely | rounds 1-2 | Calls turning sub_0002C390 and jump start sub_0002BDD0 |
| sub_0002BDD0 | start an evasive move (jump or roll) | likely | rounds 2, 4 | Just before take-off in round 2; also in 54% of roll frames in round 4; called by player control sub_00025310 |
| sub_00020F20 | move-script op used in the air | guess | round 2 | Called from the script op table at 0x00020040+; reads [0xDB9E9C] |
| sub_0003B870 | move-script op used in the air | guess | round 2 | Same op table |
| sub_001BE1D0 | landing / ground contact check | guess | round 2 | On landing; reads Ryu's object, health block and event number |
| sub_00034D60 | landing helper | guess | rounds 1-2 | Called by sub_0003E4E0 and sub_00197370 |
| sub_001CA870 | effect or sound spawn (also while running) | guess | rounds 1-2 | With sub_001CB260, on jumps and steps |
| sub_00039870 | query an object's state (by object number) | likely | round 3, action log | ax = object number (0 Ryu, others enemies), turned into the object by sub_00033B50; runs every frame. Round 3 called it set-action: wrong |
| sub_00033B50 | object by number | likely | action log | ax = object number, returns the object (Ryu's at 0x4B4E50, objects 0x2800 apart) |
| sub_00033BD0 | Ryu action helper | guess | round 3 | Called by the move script sub_00016300 and sub_0003D140 |
| sub_0003A100 | start an attack action | guess | round 3 | Only during attacks; calls sub_00039870; called by sub_0003D140 and sub_00198D70 |
| sub_000303A0 | attack input / combo buffer check | guess | round 3 | Reads 0xDB9F84; called by the button helper sub_0001B6D0 |
| sub_001A4580 | audio middleware (very frequent) | guess | round 3 | 7 lines, ~100 calls a frame during heavy attacks; called from the 0x0031F930-0x00330E70 library code |
| sub_00346800 | audio middleware | guess | round 3 | Same pattern; 0x0034xxxx is the CRI library area (see sub_00344BE0) |
| sub_0001B3C0 | move-script input test for the roll | guess | round 4 | Only while rolling; called by the move script sub_00016300; calls the button helper sub_0001B5D0 |
| sub_00032D30 | guard press handling | guess | round 4 | Right after a guard press (phi 0.32); reads 0xDB9F84; called by sub_00032A50 |
| sub_0001B5D0 | button test helper | guess | rounds 3-4 | Called by move-script tests sub_0001B3C0 and others |
| sub_0003C3D0 | look up an object's command entry | likely | action log 2, code | Takes an object (edi) and a command 0x00-0x10; returns entry [command] of the table in the object's character data (object+0x26D8 -> data, data+[data+0x18] -> section list, its 5th section), or of an override table at 0x421CF8 by object type (+0x2774). The action byte is written by its callers right after |


## Ryu's actions (0x4968B4)

From one free-play action log (act_20261105_183150.tsv): each number, how it was reached and the
buttons held. Checked live with ShowAction.bat (NGB_SHOW_ACTION=1) on 2026-11-05: no mismatches
seen for the named rows, though not every move was checked one by one. Unnamed rows remain open.

| Action | Seen | Usually after | Buttons | Guess |
|---|---|---|---|---|
| 0x00 | 39 | FF, 2A, 0B | none | neutral / back to idle |
| 0x06 | 27 | 00, 2A | none | standing idle |
| 0x08 | 1 | 06, 00 | stick (slow), or after an attack | back to free movement (after starting a walk, and after X or Y taps; Ryu's animation 82) |
| 0x09 | 1 | 08 | stick (slow) | walking (Ryu's animation 3) |
| 0x0A | 4 | 09 | none | stop walking (Ryu's animations 4, 5); then 0x00 (seen live) |
| 0x26 | 40 | 06, 2A | none | start running |
| 0x28 | 25 | 26 | none | running |
| 0x2A | 26 | 28, 26 | none | stopping from a run |
| 0x0B | 11 | 00, 28, 26 | X | light attack |
| 0x4E | 5 | FF | X | attack follow-up (combo) |
| 0x5B | 4 | 0B, 5F | Y | heavy attack |
| 0x46 | 11 | 47, 00 | LT | guard |
| 0x47 | 6 | 46, 24 | LT | guard (held / moving) |
| 0x22 | 4 | 46, 06 | LT | roll from guard |
| 0x55 | - | 00, 06 | A | standing jump take-off (Ryu's animations 34, 35); then 0x30, then 0x02 (seen live) |
| 0x30 | 4 | 61, 86, 16 | none | in the air / falling (23 records, shared by many moves) |
| 0x02 | 3 | 30 | none | landing (Ryu's 650, 651) |
| 0x56, 0x57, 0x58 | 2, 2, - | 00, 2A, 28, 26 | A | running jump take-off (all use Ryu's animation 39; confirmed by the swap test). The standing jump is 0x55 |
| 0x5F | 1 | 61 | A | second jump or air move |
| 0x61 | 3 | 56, 57 | none | in the air / falling |
| 0xFF | 15 | 00, 2A, 4E | none or X | no action (between moves) |
| 0x0E, 0x16, 0x24, 0x2D, 0x32, 0x4F, 0x67, 0x86, 0x8A | 1-5 | | | unknown (hit reactions, landings, wall moves?) |
| 0xB9 | | | X held | Ultimate Technique charge (src/ut_charge.c) |


## From action to animation

How an action number reaches an animation, from Ryu's data files (`tools/ryu_moves.py`):

1. **Ryu's character data** (`ryu.chr`, cmn.afs #141, magic `chr_dat2`) is at `*(0x4B4E50 + 0x26D8)` =
   `*0x4B7528` while playing. It has 5 sections; the 5th starts with a 17-entry command table
   (commands 0x00-0x10, the values callers pass to sub_0003C3D0).
2. **Move records**, 12 bytes: `u16 condition, u16 move, u16 0, u8 kind, u8 flags, u32 0`. *kind* is
   the action number (0x4968B4): the values match the ones seen while playing. 101 different actions,
   about 6800 records.
3. **Moves** (`ryu.mtn`, cmn.afs #22, magic `chr_dat`), section 1: 2296 entries, each `u16 3, u16
   animation id`, then a small script (timing, effects; not decoded yet).
4. **Animation ids** are decimal: below 10000, clip N of Ryu's own motions (`ryu.mtn` section 0, 1890
   slots, 1601 of 1637 such ids filled); 10000 + N, clip N of the weapon's motion file (`rm_kt.mot`,
   cmn.afs #6, for the Dragon Sword; ids empty there most likely belong to other weapons' files).

Example: action 0x0B (light attack) has 203 records; move 0x190 plays weapon clip 160 (id 10160).
Swapping a move's animation id, or a record's move, is the way to change which animation an action
plays.

**Confirmed in game (2026-11-05):** `anim_swap=39:80` in mods.txt (src/my_mods.c) changed Ryu's
running jump to play animation 80, and only the running jump. So the chain above holds: action ->
move record -> move -> animation id, and changing a move's animation id in the loaded ryu.mtn changes
what Ryu plays.

**Current move:** the u16 at Ryu's object + 0x2788 (0x4B75D8) is the move playing now; it matched the known move in 12 of 12 jumps. Attacks do not show in the action byte (it reads 0xFF or 0x08 around them), so the move number is how to tell attacks apart.

**Attack moves seen live (Dragon Sword, standing tap):** X = move 0x190 (weapon animation 400; XX = 0x191 / anim 401, XXX = 0x192 / anim 402, seen live; 0x193, 0x194 follow in the data, all action 0x0B; ryu.chr record with action 0x0B), XY = move 0x226, XYY = move 0x1F2 (seen live). Y = move 0x1CC (weapon animation 460; records with action 0xFF). The current-move field 0x4B75D8 tracks attacks, so it is the way to tell them apart.

## Memory

| Address | What | Source |
|---|---|---|
| 0x4B4E50 | Ryu's object (objects 0x2800 apart) | src/cheats.c |
| 0x4B75D8 | Ryu's current move (u16, object + 0x2788; ryu.mtn move number). +0x278A and +0x278C held the same value in every jump: related copies (previous / requested?) | jump test, move_field.txt |
| 0x4B7528 | pointer to Ryu's character data (ryu.chr, chr_dat2) = object + 0x26D8 | src/intercept.c, sub_0003C3D0 |
| 0x4B5710 | Ryu's position x y z | src/cheats.c |
| 0x58A520 | Ryu's player block (0x210 a player) | src/cheats.c |
| 0x58A564 / 0x58A566 | Ryu's max health / health | src/cheats.c |
| 0x58A56C / 0x58A56E | max ninpo / ninpo | src/cheats.c |
| 0x589570 | essence | src/cheats.c |
| 0x58A3A0 + 0x210·n | health block n (segments +0x194, sum +0x1C6) | src/cheats.c |
| 0x7F1A94 | 24 checksum "changed by the game" flags | src/cheats.c |
| 0xD219A8 | controller state, 0x78 a player (Start = bit 0x10) | src/cutscene_skip.c |
| 0xDB9C6E | current event number (0xFFFF none) | src/cutscene_skip.c |
| 0xDB9477 | watched-event flags, one byte an event | src/cutscene_skip.c |
| 0xDB9ACC | right stick mode (0 first person, 1 camera) | src/camera.c |
| 0x4968B0 | player blocks, 0xDD0 each (src/ut_charge.c) | src/ut_charge.c |
| 0x4968B4 | Ryu's current action (byte; 0xB9 the UT charge) | src/ut_charge.c, sub_00023520 |
| 0xDB9C70 | current player's object number (16-bit) | sub_00023520 |
| 0x5895E2 / E4 | UT charge level / frame count | src/ut_charge.c |
| 0xDB9E9C | pointer to the active character's control block (angles at +0x78C, +0x2D0, +0x2D4) | round 1 |
| 0x00020040 | move-script op table (consecutive entries are script commands) | round 2 |
| 0xDB9F84 | action input state (attacks, guard) | rounds 3-4 |

## Sessions

| Date | Recording | Task | Findings |
|---|---|---|---|
| 2026-11-05 | rec_20261105_170913.bin | 1: still / run / still / run (F6 between) | 101 functions only while running; Ryu update sub_000FF1A0, turning sub_0002C390. Recording ran at ~17 fps |
| 2026-11-05 | rec_20261105_171515.bin | 2: still / jump in place / still / jump | 8 jumps, 36 frames airborne each, height 2.32 (y up). Airborne sub_001963B0, take-off sub_0002BDD0, landing sub_001999B0 |
| 2026-11-05 | rec_20261105_172113.bin | 3: still / X light / still / Y heavy | Shared attack path sub_00039870 -> sub_00033B50; heavy attacks drive much more audio library work. Controller data was missing in rounds 1-3 (wrong address); fixed for round 4 |
| 2026-11-05 | rec_20261105_173623.bin | 4: still / guard / still / roll | First recording with controller data (guard = LT/Shift). Guard adds almost no functions: it is a state change, needs a memory diff. Roll shares the jump start sub_0002BDD0; roll-only sub_0001B3C0 |
| 2026-11-05 | ShowAction.bat (live title) | check the action names | No mismatches reported for the named actions |
| 2026-11-05 | swap test (anim_swap=39:80) | change one animation | Running jump played animation 80; standing jump unchanged: it uses another action/animation |
