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

## Memory

| Address | What | Source |
|---|---|---|
| 0x4B4E50 | Ryu's object (objects 0x2800 apart) | src/cheats.c |
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
