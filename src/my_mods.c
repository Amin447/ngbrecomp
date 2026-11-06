/*
 * my_mods.c -- the user's own gameplay mods.
 *
 * Damage multipliers. Every hit in the game goes through sub_001E1680 (see
 * src/cheats.c). Its target's health block is at 0x58A3A0 + 0x210 * n, where n
 * is MEM8(target + 0x27F0) (0 for Ryu):
 *   +0x184  the most each of the 8 segments can hold (0xFFFF = segment not had)
 *   +0x194  the 8 segments (damage lowers them)
 *   +0x1C6  their sum (the health the HUD shows)
 * We snapshot the segments before the game applies a hit, let the game do it,
 * then scale how much was taken.
 *
 * Settings, from mods.txt in the folder the game starts in (lines "key=value"),
 * or from environment variables of the same name in capitals with NGB_MOD_:
 *   damage_taken=0.5   Ryu takes half damage (0 = no damage)
 *   damage_dealt=2     enemies take double damage
 *   log=1              print each scaled hit to the log
 *   anim_swap=39:80    every move of Ryu's whose animation id is 39 plays 80 instead (up to 8
 *                      lines; ids as in tools/ryu_moves.py: below 10000 Ryu's own clips,
 *                      10000 + N the weapon's clip N)
 *   enemy_swap=0xE:0x44  every object spawned as type 0xE (Genin) spawns as 0x44 (white-clad
 *                      ninja) instead (up to 8 lines; types as the ShowAction title's "hit type")
 *   variant_swap=0x5C:0:1  objects of type 0x5C (SWAT) spawned as kind 0 (object +0x277A) spawn
 *                      as kind 1 (the shield soldier) instead (up to 8 lines)
 *   load_files=0xABC,... every area's file list (0xDB5804) also gets these global file numbers
 *   drop_files=0x8A,0x8B also remove these files from that list (frees memory; only when nothing
 *                      of that kind spawns any more, e.g. all Genin swapped)
 *   load_files_when=0x8A only add them to lists that already load file 0x8A (Genin's model)
 *                      (load_img.bin ids; titan: 0xABC,0xABD,0xABE,0xAC7,0xAC8,0xAC9,0xB04,0xB16)
 *   move_swap=0x191:0x1F2  every move record of Ryu's (ryu.chr) that picks move 0x191 picks 0x1F2
 *                      instead: rewires combos (up to 8 lines; numbers as the ShowAction title
 *                      shows them, 0x prefix for hex)
 */
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <direct.h>
#else
#include <sys/stat.h>
#endif

#include "xbox_memory_layout.h"
#include "my_mods.h"

static float s_taken = 1.0f, s_dealt = 1.0f;
static int s_log;
static uint16_t s_swap_from[8], s_swap_to[8];
static int s_nswap;
static uint16_t s_mswap_from[8], s_mswap_to[8];
static int s_nmswap;
static uint16_t s_eswap_from[8], s_eswap_to[8];
static int s_neswap;
static uint16_t s_load_enemy[32];
static int s_nload;
static int s_load_when = -1;
static uint16_t s_drop[16];
static int s_ndrop;   /* drop_files: file numbers removed after load_files is added */   /* load_files_when: only lists holding this file number */
static uint16_t s_vswap_type[8], s_vswap_from[8], s_vswap_to[8];
static int s_nvswap;

static void set_option(const char *key, const char *val)
{
    if (!strcmp(key, "damage_taken")) s_taken = (float)atof(val);
    else if (!strcmp(key, "damage_dealt")) s_dealt = (float)atof(val);
    else if (!strcmp(key, "log")) s_log = atoi(val);
    else if (!strcmp(key, "anim_swap") && s_nswap < 8) {
        unsigned from, to;
        if (sscanf(val, "%u:%u", &from, &to) == 2) {
            s_swap_from[s_nswap] = (uint16_t)from;
            s_swap_to[s_nswap] = (uint16_t)to;
            s_nswap++;
        }
    }
    else if (!strcmp(key, "drop_files")) {
        const char *p = val;
        while (*p && s_ndrop < 16) {
            char *e; long v = strtol(p, &e, 0);
            if (e == p) break;
            s_drop[s_ndrop++] = (uint16_t)v;
            p = e; while (*p == ',' || *p == ' ') p++;
        }
    }
    else if (!strcmp(key, "load_files_when")) {
        int v;
        if (sscanf(val, "%i", &v) == 1) s_load_when = v;
    }
    else if (!strcmp(key, "load_files")) {   /* comma separated global file numbers */
        const char *p = val;
        while (*p && s_nload < 32) {
            char *e; long v = strtol(p, &e, 0);
            if (e == p) break;
            s_load_enemy[s_nload++] = (uint16_t)v;
            p = e; while (*p == ',' || *p == ' ') p++;
        }
    }
    else if (!strcmp(key, "enemy_swap") && s_neswap < 8) {
        int from, to;
        if (sscanf(val, "%i:%i", &from, &to) == 2) {
            s_eswap_from[s_neswap] = (uint16_t)from;
            s_eswap_to[s_neswap] = (uint16_t)to;
            s_neswap++;
        }
    }
    else if (!strcmp(key, "variant_swap") && s_nvswap < 8) {
        int ty, from, to;
        if (sscanf(val, "%i:%i:%i", &ty, &from, &to) == 3) {
            s_vswap_type[s_nvswap] = (uint16_t)ty;
            s_vswap_from[s_nvswap] = (uint16_t)from;
            s_vswap_to[s_nvswap] = (uint16_t)to;
            s_nvswap++;
        }
    }
    else if (!strcmp(key, "move_swap") && s_nmswap < 8) {
        int from, to;
        if (sscanf(val, "%i:%i", &from, &to) == 2) {
            s_mswap_from[s_nmswap] = (uint16_t)from;
            s_mswap_to[s_nmswap] = (uint16_t)to;
            s_nmswap++;
        }
    }
    else return;
    if (s_taken < 0) s_taken = 0;
    if (s_dealt < 0) s_dealt = 0;
}

static void load_options(void)
{
    static int loaded;
    if (loaded)
        return;
    loaded = 1;
    FILE *f = fopen("mods.txt", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            char *eq = strchr(line, '=');
            if (line[0] == '#' || !eq)
                continue;
            *eq = 0;
            char *val = eq + 1;
            val[strcspn(val, "\r\n")] = 0;
            char *key = line + strspn(line, " \t");
            key[strcspn(key, " \t")] = 0;
            set_option(key, val);
        }
        fclose(f);
    }
    const char *e;
    if ((e = getenv("NGB_MOD_DAMAGE_TAKEN"))) set_option("damage_taken", e);
    if ((e = getenv("NGB_MOD_DAMAGE_DEALT"))) set_option("damage_dealt", e);
    if ((e = getenv("NGB_MOD_LOG"))) set_option("log", e);
    fprintf(stderr, "[MOD] damage taken x%.2f, damage dealt x%.2f, %d animation swaps\n",
            s_taken, s_dealt, s_nswap);
}

static uint32_t health_block(uint32_t target)
{
    return MEM8(target + 0x27F0) * 0x210u + 0x58A3A0;
}

void mymod_hit_begin(struct mymod_hit *h, uint32_t target)
{
    load_options();
    h->target = target;
    h->block = health_block(target);
    h->ryu = (target == 0x4B4E50 || h->block == 0x58A3A0);
    for (int i = 0; i < 8; i++)
        h->seg[i] = MEM16(h->block + 0x194 + 2 * i);
}

void mymod_hit_end(struct mymod_hit *h)
{
    float scale = h->ryu ? s_taken : s_dealt;
    if (scale == 1.0f || health_block(h->target) != h->block)
        return;
    uint32_t b = h->block;
    int taken = 0, before_sum = 0;
    for (int i = 0; i < 8; i++) {
        uint16_t now = MEM16(b + 0x194 + 2 * i);
        if (h->seg[i] == 0xFFFF || now == 0xFFFF)
            continue;
        before_sum += h->seg[i];
        if (now < h->seg[i])
            taken += h->seg[i] - now;
    }
    if (taken <= 0)
        return;                                   /* no damage: guarded, a miss */
    int want = (int)(taken * scale + 0.5f);
    if (want == 0 && scale > 0)
        want = 1;                                 /* a scaled hit still does something */
    if (want == taken)
        return;
    uint16_t sum_before_write = MEM16(b + 0x1C6);

    if (want < taken) {                           /* give back health, to the segments that lost it */
        int back = taken - want;
        for (int i = 7; i >= 0 && back > 0; i--) {
            uint16_t now = MEM16(b + 0x194 + 2 * i);
            if (h->seg[i] == 0xFFFF || now >= h->seg[i])
                continue;
            int add = h->seg[i] - now < back ? h->seg[i] - now : back;
            MEM16(b + 0x194 + 2 * i) = (uint16_t)(now + add);
            back -= add;
        }
    } else {                                      /* take more, from the last segments with health */
        int more = want - taken;
        for (int i = 7; i >= 0 && more > 0; i--) {
            uint16_t now = MEM16(b + 0x194 + 2 * i);
            if (now == 0xFFFF || now == 0)
                continue;
            int sub = now < more ? now : more;
            MEM16(b + 0x194 + 2 * i) = (uint16_t)(now - sub);
            more -= sub;
        }
    }
    int sum = 0;
    for (int i = 0; i < 8; i++) {
        uint16_t s = MEM16(b + 0x194 + 2 * i);
        if (s != 0xFFFF)
            sum += s;
    }
    MEM16(b + 0x1C6) = (uint16_t)sum;
    /* an enemy's on-screen health bar, when it showed this enemy's health */
    if (!h->ryu && MEM8(0xD7D2B0) && MEM16(0xD7D2B2) == MEM16(h->target + 0x2774)
        && MEM16(0xD7D2B6) == sum_before_write)
        MEM16(0xD7D2B6) = (uint16_t)sum;
    SET_LO8(eax, sum == 0 ? 1 : 0);               /* sub_001E1680 returns 1 when the hit killed */
    for (uint32_t a = 0x7F1A94; a < 0x7F1A94 + 24; a++)
        MEM8(a) = 1;                              /* the game's checksums retaken (see src/cheats.c) */
    if (s_log)
        fprintf(stderr, "[MOD] %s hit: %d -> %d (health %d -> %d)\n", h->ryu ? "Ryu" : "enemy",
                taken, want, before_sum, sum);
}

/* ---- Animation swaps (anim_swap=FROM:TO) ----
 *
 * Ryu's moves are ryu.mtn (cmn.afs #22, docs/function_map.md "From action to animation"): a
 * "chr_dat" file of 0x143DA0 bytes, 3 sections; section 1 is a table of 2296 move entries, each
 * u16 3, u16 animation id, then a script. It is found in guest memory by its header, the table's
 * entries taken as offsets from the section or as addresses, whichever they are once loaded. */

#define MTN_SIZE 0x143DA0u
static uint32_t s_mtn;                    /* guest address of the loaded ryu.mtn, 0 none */

static int mtn_at(uint32_t va)
{
    return MEM32(va) == 0x5F726863u /* "chr_" */ && MEM32(va + 4) == 0x00746164u /* "dat\0" */
        && MEM32(va + 0x0C) == MTN_SIZE && MEM32(va + 0x10) == 3;
}

static uint32_t mtn_find(void)
{
    static const uint32_t ranges[][2] = { { 0x00010000u, 0x04000000u }, { 0x80000000u, 0x88000000u } };
    for (int r = 0; r < 2; r++)
        for (uint32_t va = ranges[r][0]; va < ranges[r][1] - 0x20; va += 0x10)
            if (mtn_at(va))
                return va;
    return 0;
}

static void mtn_apply(uint32_t base)
{
    uint32_t first = MEM32(base + 0x18);
    uint32_t s1 = MEM32(base + first + 4), s2 = MEM32(base + first + 8);
    /* loaded files may hold their offsets turned into addresses */
    uint32_t sec1 = s1 < MTN_SIZE ? base + s1 : s1;
    uint32_t end = s2 < MTN_SIZE ? base + s2 : s2;
    int changed = 0;
    for (uint32_t i = 0; i < 2296 && sec1 + 4 * i < end; i++) {
        uint32_t e = MEM32(sec1 + 4 * i);
        uint32_t entry = e < MTN_SIZE ? sec1 + e : e;
        if (entry < base || entry >= base + MTN_SIZE || MEM16(entry) != 3)
            continue;
        uint16_t anim = MEM16(entry + 2);
        for (int k = 0; k < s_nswap; k++)
            if (anim == s_swap_from[k]) {
                MEM16(entry + 2) = s_swap_to[k];
                changed++;
                break;
            }
    }
    fprintf(stderr, "[MOD] ryu.mtn at %08X: %d moves' animations swapped\n", base, changed);
}

/* ---- Move swaps (move_swap=FROM:TO) ----
 *
 * The game picks Ryu's next move by choosing one of his move records in ryu.chr (sub_00034A10,
 * called from sub_000345F0, which writes the record's move to his current move at object +
 * 0x2788). Editing the loaded ryu.chr made the game report a disc error, so instead the
 * generated sub_000345F0 (src/recomp/gen/recomp_0001.c, edited by hand: redo it after a
 * regeneration) passes the move it read through here. It runs for every character that uses
 * this code, so only the moves listed change. */
uint16_t mymod_move_pick(uint16_t move)
{
    load_options();
    for (int k = 0; k < s_nmswap; k++)
        if (move == s_mswap_from[k])
            return s_mswap_to[k];
    return move;
}

/* ---- Enemy swaps (enemy_swap=FROM:TO) ----
 * Objects are spawned from spawn records: +0x40 position, +0x50 u16 type (the object's +0x2774).
 * The spawn functions (sub_00153100, sub_002CD040, sub_002F2CC0; generated code edited by
 * tools/patch_enemy_pick.py) read the type through here. The new type's data must be loaded in
 * that area: swap between enemies of the same chapter. */
/* NGB_SPAWN_LOG=1: every type read by the spawn functions goes to recordings/spawns.txt with
 * the frame number and Ryu's position (when it is read during startup, the frame is 0). */
unsigned mymod_frames;
uint16_t mymod_enemy_pick(uint16_t type)
{
    load_options();
    static int log = -1;
    if (log < 0)
        log = getenv("NGB_SPAWN_LOG") != NULL;
    if (log) {
        static FILE *f;
        if (!f) {
#ifdef _WIN32
            _mkdir("recordings");
#else
            mkdir("recordings", 0755);
#endif
            f = fopen("recordings/spawns.txt", "w");
        }
        if (f) {
            fprintf(f, "frame %6u type %04X ryu %.1f %.1f %.1f\n", mymod_frames, type,
                    MEMF(0x4B5710), MEMF(0x4B5714), MEMF(0x4B5718));
            fflush(f);
        }
    }
    /* Not at boot: the game reads some types then (a swap there gave a disc error). Only once
     * Ryu stands in a level (his position is no longer 0, 0, 0). */
    if (MEMF(0x4B5710) == 0.0f && MEMF(0x4B5714) == 0.0f && MEMF(0x4B5718) == 0.0f)
        return type;
    for (int k = 0; k < s_neswap; k++)
        if (type == s_eswap_from[k])
            return s_eswap_to[k];
    return type;
}

/* The other places that write an object's type (+0x2774): 1 sub_00168EC0 (object reset),
 * 2 sub_002F2780 (type passed through sub_002FE290), 3 sub_002F7020 (copied from another
 * object). Logged with their number in spawns.txt ("write N"); swapped like the spawn reads. */
uint16_t mymod_type_write(uint16_t type, int site)
{
    load_options();
    static int log = -1;
    if (log < 0)
        log = getenv("NGB_SPAWN_LOG") != NULL;
    int ingame = !(MEMF(0x4B5710) == 0.0f && MEMF(0x4B5714) == 0.0f && MEMF(0x4B5718) == 0.0f);
    uint16_t out = type;
    if (ingame)
        for (int k = 0; k < s_neswap; k++)
            if (type == s_eswap_from[k]) {
                out = s_eswap_to[k];
                break;
            }
    if (log && type) {
        FILE *f = fopen("recordings/spawns.txt", "a");
        if (f) {
            fprintf(f, "frame %6u write %d type %04X -> %04X\n", mymod_frames, site, type, out);
            fclose(f);
        }
    }
    return out;
}

/* ---- Kind swaps (variant_swap=TYPE:FROM:TO) ----
 * sub_002F2CC0 copies a spawn record's kind (+0x52) to object +0x277A, then its partner (+0x5B) to
 * +0x2791; it has already written the type (+0x2774). For SWAT soldiers the partner is 0x81 + the
 * kind, so it is moved by the same amount when it matches. */
uint32_t mymod_variant(uint32_t obj, int field, uint32_t value)
{
    load_options();
    if (!s_nvswap || (MEMF(0x4B5710) == 0.0f && MEMF(0x4B5714) == 0.0f && MEMF(0x4B5718) == 0.0f))
        return value;
    uint16_t type = MEM16(obj + 0x2774);
    for (int k = 0; k < s_nvswap; k++) {
        if (type != s_vswap_type[k])
            continue;
        if (field == 0 && value == s_vswap_from[k])
            return s_vswap_to[k];
        if (field == 1 && value == 0x81u + s_vswap_from[k] && MEM16(obj + 0x277A) == s_vswap_to[k])
            return 0x81u + s_vswap_to[k];
    }
    return value;
}

/* Kind swaps for objects spawned elsewhere: the first frame an object slot holds a new object
 * (its character data pointer changed), its kind is swapped there too. */
static void variant_frame(void)
{
    static uint32_t seen[48];
    if (!s_nvswap)
        return;
    int ingame = !(MEMF(0x4B5710) == 0.0f && MEMF(0x4B5714) == 0.0f && MEMF(0x4B5718) == 0.0f);
    for (int i = 1; i < 48; i++) {
        uint32_t o = 0x4B4E50u + 0x2800u * i, cd = MEM32(o + 0x26D8);
        if (cd == seen[i])
            continue;
        seen[i] = cd;
        if (!cd || !ingame)
            continue;
        uint16_t type = MEM16(o + 0x2774), kind = MEM16(o + 0x277A);
        for (int k = 0; k < s_nvswap; k++)
            if (type == s_vswap_type[k] && kind == s_vswap_from[k]) {
                MEM16(o + 0x277A) = s_vswap_to[k];
                if (MEM8(o + 0x2791) == 0x81u + s_vswap_from[k])
                    MEM8(o + 0x2791) = (uint8_t)(0x81u + s_vswap_to[k]);
                break;
            }
    }
}

/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */
extern ptrdiff_t g_xbox_mem_offset;
static void needed_dump(const char *why);
void mymod_load_enemies(void);
void mymod_frame(void)
{
    mymod_frames++;
    needed_dump("frame");
    load_options();
    variant_frame();
    if (!s_nswap)
        return;
    static unsigned tick;
    if (s_mtn && mtn_at(s_mtn))
        return;                           /* still there and already changed */
    s_mtn = 0;
    if (++tick % 120)                     /* look for it every two seconds or so */
        return;
    uint32_t va = mtn_find();
    if (va) {
        mtn_apply(va);
        s_mtn = va;
    }
}

/* Spawn functions call this with the spawn record (generated code, tools/patch_enemy_pick.py).
 * With NGB_SPAWN_LOG it writes recordings/spawn_records.txt: the record's guest address and its
 * first 0x60 bytes, to find which loaded file the records come from (see all_loads.txt bufs). */
uint16_t mymod_enemy_pick_rec(uint32_t rec)
{
    if (getenv("NGB_SPAWN_LOG")) {
        static FILE *f;
        if (!f) f = fopen("recordings/spawn_records.txt", "w");
        if (f) {
            fprintf(f, "rec %08X type %04X :", rec, MEM16(rec + 0x50));
            for (uint32_t q = 0; q < 0x60; q += 4) fprintf(f, " %08X", MEM32(rec + q));
            fprintf(f, " | stack");
            for (uint32_t q = 0; q < 0x2000; q += 4) {
                uint32_t v = MEM32(esp + q);
                if (v >= 0x11000 && v < 0x329000) fprintf(f, " %X@%X", v, q);
            }
            fputc(10, f); fflush(f);
        }
    }
    return mymod_enemy_pick(MEM16(rec + 0x50));
}

/* load_enemy=TYPE: make every area also load TYPE's chr_*.afs, so enemy_swap can use enemies from
 * other chapters. Called (tools/patch_load_enemy.py) each time the game's area setup
 * (sub_002E1C80) adds a type to its needed-types list (u16 at 0xDB5804, count byte 0xDB5A02);
 * the loader (sub_0016CC60 etc.) then loads a file for every listed type. */

/* Debug (NGB_SPAWN_LOG): recordings/needed.txt, the game's needed-types list when it changes. */
static void needed_dump(const char *why)
{
    static FILE *f; static uint32_t last;
    if (!getenv("NGB_SPAWN_LOG")) return;
    {   /* also recordings/chr_slots.txt: the loaded chr table at 0xDB33E0 (0x20 bytes a slot) */
        static FILE *sf; static uint32_t sl;
        uint32_t hh = 0;
        for (uint32_t q = 0; q < 64 * 0x20; q += 4) hh = hh * 33 + MEM32(0xDB33E0 + q);
        if (hh != sl) {
            sl = hh;
            if (!sf) sf = fopen("recordings/chr_slots.txt", "w");
            if (sf) {
                fprintf(sf, "== frame %u\n", mymod_frames);
                for (uint32_t s = 0; s < 64; s++) {
                    uint32_t a = 0xDB33E0 + s * 0x20, nz = 0;
                    for (uint32_t q = 0; q < 0x20; q += 4) nz |= MEM32(a + q);
                    if (!nz) continue;
                    fprintf(sf, "%2u", s);
                    for (uint32_t q = 0; q < 0x20; q += 4) fprintf(sf, " %08X", MEM32(a + q));
                    uint32_t d = MEM32(a);
                    if (d >= 0x10000 && d < 0x8000000) fprintf(sf, "  [%.8s]", (const char *)(intptr_t)(g_xbox_mem_offset + (ptrdiff_t)d));
                    fputc(10, sf);
                }
                fflush(sf);
            }
        }
    }
    unsigned n = MEM8(0xDB5A02);
    uint32_t h = n * 7 + MEM8(0xDA4FC2);
    for (unsigned i = 0; i < MEM8(0xDA4FC2); i++) h = h * 31 + MEM16(0xDA4DC4 + i * 2);
    for (unsigned i = 0; i < n; i++) h = h * 31 + MEM16(0xDB5804 + i * 2);
    if (h == last && why[0] == 'f') return;
    last = h;
    if (!f) f = fopen("recordings/needed.txt", "w");
    if (!f) return;
    fprintf(f, "frame %u %s A(DA4DC4) n %u:", mymod_frames, why, MEM8(0xDA4FC2));
    for (unsigned i = 0; i < MEM8(0xDA4FC2); i++) fprintf(f, " %04X", MEM16(0xDA4DC4 + i * 2));
    fprintf(f, "\n   B n %u:", n);
    for (unsigned i = 0; i < n; i++) fprintf(f, " %04X", MEM16(0xDB5804 + i * 2));
    fputc(10, f); fflush(f);
}

static void load_files_in(uint32_t L)
{
    unsigned n = MEM8(L + 0x602), i;
    if (!s_nload || n == 0) return;
    if (s_load_when >= 0) {   /* only a list that already loads this file (e.g. 0x156 Jonin) */
        for (i = 0; i < n; i++)
            if (MEM16(L + 0x404 + i * 2) == (uint16_t)s_load_when) break;
        if (i == n) return;
    }
    else if (s_ndrop) {   /* no load_files_when: only lists holding one of drop_files */
        int hit = 0;
        for (i = 0; i < n && !hit; i++)
            for (int k = 0; k < s_ndrop; k++)
                if (MEM16(L + 0x404 + i * 2) == s_drop[k]) { hit = 1; break; }
        if (!hit) return;
    }
    int d = 0;   /* next drop_files entry whose place a loaded file takes (no shifting) */
    for (int k = 0; k < s_nload; k++) {
        n = MEM8(L + 0x602);
        for (i = 0; i < n; i++)
            if (MEM16(L + 0x404 + i * 2) == s_load_enemy[k]) break;
        if (i < n) continue;               /* already listed */
        unsigned at = n;
        for (; d < s_ndrop && at == n; d++)
            for (i = 0; i < n; i++)
                if (MEM16(L + 0x404 + i * 2) == s_drop[d]) { at = i; break; }
        if (at == n) {
            if (n >= 0xFF) return;
            MEM8(L + 0x602) = (uint8_t)(n + 1);
        }
        MEM16(L + 0x404 + at * 2) = s_load_enemy[k];
        MEM32(L + at * 4) = 0;
    }
}

/* Two file lists share one layout (u32[255] at +0, u16 file numbers at +0x404, count byte at
 * +0x602): 0xDB5400 (marks loaded slots, sub_0016CC60...) and 0xDA49C0. */
void mymod_load_enemies(void)
{
    load_options();
    /* list B (0xDB5400) is per area: adding there did not load the files and broke areas */
    load_files_in(0xDA49C0);
}

/* Called by the file-list workers (tools/patch_load_list.py) with the list they process. Logs each
 * new list (recordings/lists.txt, NGB_SPAWN_LOG) and adds load_files when load_files_when is in it. */
void mymod_list_tick(uint32_t L)
{
    load_options();
    if (getenv("NGB_SPAWN_LOG")) {
        static FILE *f; static uint32_t last;
        unsigned n = MEM8(L + 0x602);
        uint32_t h = L * 7 + n;
        for (unsigned i = 0; i < n; i++) h = h * 31 + MEM16(L + 0x404 + i * 2);
        if (h != last) {
            last = h;
            if (!f) f = fopen("recordings/lists.txt", "w");
            if (f) {
                fprintf(f, "frame %u list %08X n %u:", mymod_frames, L, n);
                for (unsigned i = 0; i < n; i++) fprintf(f, " %04X", MEM16(L + 0x404 + i * 2));
                fputc(10, f); fflush(f);
            }
        }
    }
    /* Add once per filling of a list: the workers cross off loaded files from the end (0xFFFF,
     * then count - 1), so re-checking would add them again forever (the game hung loading). */
    static uint32_t done[64];   /* lists already given load_files (exact addresses) */
    unsigned k, n = MEM8(L + 0x602);
    for (k = 0; k < 64 && done[k] != L; k++) ;
    if (n == 0) { if (k < 64) done[k] = 0; return; }
    if (k < 64 || L < 0x1000 || L >= 0x4000000) return;
    unsigned before = n;
    load_files_in(L);
    if (MEM8(L + 0x602) != before || MEM16(L + 0x404) != 0xFFFF) {
        for (k = 0; k < 64 && done[k]; k++) ;
        if (k < 64) done[k] = L;
    }
}
