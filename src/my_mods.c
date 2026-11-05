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

static void set_option(const char *key, const char *val)
{
    if (!strcmp(key, "damage_taken")) s_taken = (float)atof(val);
    else if (!strcmp(key, "damage_dealt")) s_dealt = (float)atof(val);
    else if (!strcmp(key, "log")) s_log = atoi(val);
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
    fprintf(stderr, "[MOD] damage taken x%.2f, damage dealt x%.2f\n", s_taken, s_dealt);
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
