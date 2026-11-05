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
 *   move_swap=0x191:0x1F2  every move record of Ryu's (ryu.chr) that picks move 0x191 picks 0x1F2
 *                      instead: rewires combos (up to 8 lines; numbers as the ShowAction title
 *                      shows them, 0x prefix for hex)
 */
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "xbox_memory_layout.h"
#include "my_mods.h"

static float s_taken = 1.0f, s_dealt = 1.0f;
static int s_log;
static uint16_t s_swap_from[8], s_swap_to[8];
static int s_nswap;
static uint16_t s_mswap_from[8], s_mswap_to[8];
static int s_nmswap;

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

/* Once a frame on the game's thread (src/cheats.c, ngb_frame_tick). */
void mymod_frame(void)
{
    load_options();
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
