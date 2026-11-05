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
| 0x5895E2 / E4 | UT charge level / frame count | src/ut_charge.c |

## Sessions

| Date | Recording | Task | Findings |
|---|---|---|---|
