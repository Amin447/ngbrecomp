/*
 * action_log.c -- logs calls to a few chosen game functions with their
 * arguments, for naming Ryu's actions by playing freely (docs/function_map.md).
 *
 * Started with NGB_REC_MODE=actions (Actions.bat). Then F9 starts and stops a
 * log and F6 drops a marker, as with the function recorder. Each log goes to
 * recordings/act_<date>_<time>.tsv in the folder the game starts in.
 *
 * Every lifted function's entry calls g_recomp_entry_hook while
 * g_recomp_capture_va is set (xboxrecomp's recomp_capture.c). Here the hook
 * only tests a bitmap of the watched addresses, so the game runs much faster
 * than with the full recording. At a watched entry the guest's registers and
 * stack hold the call's arguments: [esp] is the return address, [esp+4]... the
 * pushed arguments.
 *
 * Watched by default (NGB_ACTIONS=va,va,... replaces the list):
 *   0x00039870 set Ryu's action (ax: the action)  0x0003A100 start an attack
 *   0x0002BDD0 start a jump or roll                0x001E1680 apply a hit
 *   0x00154300 change an item count (eax item, ebx change)
 *   0x001E2EB0 absorb essence                      0x00033B50 apply an action
 *
 * Ryu's action is the byte at 0x4968B4 (the first player's block 0x4968B0 + 4; 0xB9 the
 * Ultimate Technique charge, src/ut_charge.c). The hook also compares it on every function
 * entry: a change is logged as a line with function "action", eax the old value, ecx the
 * new one, return the function entered last before the change (the writer, or the one
 * it returned to) and edx the function being entered now.
 *
 * One line a call: frame, seconds, function, return address, eax ecx edx ebx
 * esi edi, four stack arguments, Ryu's x y z, buttons (hex wButtons, then the
 * 8 analog buttons). Lines starting "#" are markers and notes.
 */
#define RECOMP_GENERATED_CODE
#include "recomp_funcs.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#include <direct.h>
#define make_dir(p) _mkdir(p)
#else
#include <sys/stat.h>
#define make_dir(p) mkdir((p), 0755)
#endif

#include "xbox_memory_layout.h"

#define ACT_VA_LIMIT 0x00E00000u
#define ACT_MAX 64
#define ACTION_BYTE 0x4968B4u

extern uint32_t g_recomp_capture_va;
extern void (*volatile g_recomp_entry_hook)(uint32_t va);
extern unsigned char ngb_rec_pad[32];     /* src/bindings.c */
extern volatile int ngb_rec_active;       /* src/func_recorder.c: the window title */

static uint8_t *s_watch;                  /* one bit an address */
static FILE *s_log;
static uint32_t s_frame;
static uint64_t s_start_us;
static int s_set_capture;
static uint32_t s_last_va;                /* the function entered last */
static uint32_t s_action;                 /* Ryu's action byte as last seen */
static volatile int s_busy;               /* the hook writing a line (several guest threads) */

static uint64_t now_us(void)
{
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return (uint64_t)ts.tv_sec * 1000000u + (uint64_t)ts.tv_nsec / 1000u;
}

int ngb_action_mode(void)
{
    static int mode = -1;
    if (mode < 0) {
        const char *m = getenv("NGB_REC_MODE");
        mode = m && !strcmp(m, "actions");
    }
    return mode;
}

static void watch_init(void)
{
    if (s_watch)
        return;
    s_watch = calloc(ACT_VA_LIMIT / 8, 1);
    if (!s_watch)
        return;
    static const uint32_t def[] = { 0x00039870, 0x0003A100, 0x0002BDD0, 0x001E1680,
                                    0x00154300, 0x001E2EB0, 0x00033B50 };
    const char *e = getenv("NGB_ACTIONS");
    if (e && *e) {
        while (*e) {
            char *end;
            unsigned long va = strtoul(e, &end, 0);
            if (end == e) break;
            if (va < ACT_VA_LIMIT) s_watch[va >> 3] |= (uint8_t)(1u << (va & 7));
            e = *end == ',' ? end + 1 : end;
        }
    } else {
        for (size_t i = 0; i < sizeof def / sizeof def[0]; i++)
            s_watch[def[i] >> 3] |= (uint8_t)(1u << (def[i] & 7));
    }
}

static void line_head(const char *what, uint32_t ret, uint32_t a, uint32_t c, uint32_t d)
{
    const unsigned char *p = ngb_rec_pad;
    fprintf(s_log, "%u\t%.3f\t%s\t%08X\t%08X\t%08X\t%08X\t0\t0\t0\t0\t0\t0\t0"
                   "\t%.2f\t%.2f\t%.2f\t%02X%02X\t%02X%02X%02X%02X%02X%02X%02X%02X\n",
            s_frame, (now_us() - s_start_us) / 1e6, what, ret, a, c, d,
            MEMF(0x4B5710), MEMF(0x4B5714), MEMF(0x4B5718), p[1], p[0],
            p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]);
}

static void act_hook(uint32_t va)
{
    if (!s_log)
        return;
    uint32_t now = MEM8(ACTION_BYTE);
    if (now != s_action) {
        while (__atomic_exchange_n(&s_busy, 1, __ATOMIC_ACQUIRE))
            ;
        if (now != s_action) {
            line_head("action", s_last_va, s_action, now, va);
            s_action = now;
        }
        __atomic_store_n(&s_busy, 0, __ATOMIC_RELEASE);
    }
    s_last_va = va;
    if (va >= ACT_VA_LIMIT || !(s_watch[va >> 3] & (1u << (va & 7))))
        return;
    while (__atomic_exchange_n(&s_busy, 1, __ATOMIC_ACQUIRE))
        ;
    const unsigned char *p = ngb_rec_pad;
    fprintf(s_log, "%u\t%.3f\tsub_%08X\t%08X\t%08X\t%08X\t%08X\t%08X\t%08X\t%08X"
                   "\t%08X\t%08X\t%08X\t%08X\t%.2f\t%.2f\t%.2f\t%02X%02X\t%02X%02X%02X%02X%02X%02X%02X%02X\n",
            s_frame, (now_us() - s_start_us) / 1e6, va, MEM32(esp), eax, ecx, edx, ebx, esi, edi,
            MEM32(esp + 4), MEM32(esp + 8), MEM32(esp + 12), MEM32(esp + 16),
            MEMF(0x4B5710), MEMF(0x4B5714), MEMF(0x4B5718), p[1], p[0],
            p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9]);
    __atomic_store_n(&s_busy, 0, __ATOMIC_RELEASE);
}

static void act_start(void)
{
    watch_init();
    if (!s_watch)
        return;
    make_dir("recordings");
    char path[256];
    time_t t = time(NULL);
    struct tm tmv = *localtime(&t);
    snprintf(path, sizeof path, "recordings/act_%04d%02d%02d_%02d%02d%02d.tsv", tmv.tm_year + 1900,
             tmv.tm_mon + 1, tmv.tm_mday, tmv.tm_hour, tmv.tm_min, tmv.tm_sec);
    s_log = fopen(path, "w");
    if (!s_log)
        return;
    fprintf(s_log, "frame\tseconds\tfunction\treturn\teax\tecx\tedx\tebx\tesi\tedi\targ1\targ2\targ3\targ4"
                   "\tx\ty\tz\tbuttons\tanalog\n");
    s_frame = 0;
    s_start_us = now_us();
    s_action = MEM8(ACTION_BYTE);
    g_recomp_entry_hook = act_hook;
    if (!g_recomp_capture_va) {
        g_recomp_capture_va = 1;
        s_set_capture = 1;
    }
    ngb_rec_active = 1;
}

static void act_stop(void)
{
    g_recomp_entry_hook = NULL;
    if (s_set_capture) {
        g_recomp_capture_va = 0;
        s_set_capture = 0;
    }
    while (__atomic_exchange_n(&s_busy, 1, __ATOMIC_ACQUIRE))
        ;
    if (s_log) {
        fclose(s_log);
        s_log = NULL;
    }
    __atomic_store_n(&s_busy, 0, __ATOMIC_RELEASE);
    ngb_rec_active = 0;
}

/* Once a frame (src/func_recorder.c hands over in action mode). */
void ngb_action_frame(int toggle, int marker)
{
    if (toggle) {
        if (s_log) act_stop();
        else act_start();
        return;
    }
    if (!s_log)
        return;
    if (marker) {
        while (__atomic_exchange_n(&s_busy, 1, __ATOMIC_ACQUIRE))
            ;
        fprintf(s_log, "# marker at frame %u\n", s_frame);
        __atomic_store_n(&s_busy, 0, __ATOMIC_RELEASE);
    }
    s_frame++;
    if (s_frame % 60 == 0)
        fflush(s_log);
    if (now_us() - s_start_us > 15u * 60u * 1000000u)   /* 15 minutes at most */
        act_stop();
}

/* ---- NGB_SHOW_ACTION=1: Ryu's action and the 9 before it in the window title (for checking the names in
 * docs/function_map.md). The game thread notes each change once a frame; the window
 * code (src/ingame_menu.c) shows it. ---- */

static const struct { uint8_t action; const char *name; } k_guess[] = {
    { 0x00, "neutral" }, { 0x06, "idle" }, { 0x08, "walk start" }, { 0x09, "walking" }, { 0x0A, "walk stop" }, { 0x26, "run start" }, { 0x28, "running" },
    { 0x2A, "run stop" }, { 0x0B, "light attack" }, { 0x4E, "combo" }, { 0x5B, "heavy attack" },
    { 0x46, "guard" }, { 0x47, "guard held" }, { 0x22, "roll" }, { 0x56, "running jump" },
    { 0x57, "running jump" }, { 0x58, "running jump" },
    { 0x55, "standing jump" }, { 0x30, "falling" }, { 0x02, "landing" }, { 0x5F, "air move" }, { 0x61, "in the air" }, { 0xFF, "none" },
    { 0xB9, "UT charge" },
};

#define SHOWN_N 10
static volatile uint32_t s_shown[SHOWN_N] = { 0x100, 0x100, 0x100, 0x100, 0x100,
                                              0x100, 0x100, 0x100, 0x100, 0x100 };   /* newest first; 0x100 = none yet */
static volatile uint32_t s_shown_serial;

static const char *guess_name(uint32_t a)
{
    for (size_t i = 0; i < sizeof k_guess / sizeof k_guess[0]; i++)
        if (k_guess[i].action == a)
            return k_guess[i].name;
    return "?";
}

static void mf_frame(uint32_t action, int changed);

int ngb_show_action(void)
{
    static int on = -1;
    if (on < 0)
        on = getenv("NGB_SHOW_ACTION") != NULL;
    return on;
}

/* Once a frame on the game's thread (src/func_recorder.c). */
void ngb_action_watch_frame(void)
{
    if (!ngb_show_action())
        return;
    uint32_t now = MEM8(ACTION_BYTE);
    mf_frame(now, now != s_shown[0]);
    if (now != s_shown[0]) {
        for (int i = SHOWN_N - 1; i > 0; i--)
            s_shown[i] = s_shown[i - 1];
        s_shown[0] = now;
        s_shown_serial++;
    }
}

/* The title text, and a number that changes with it (the window code updates on a change). */
uint32_t ngb_action_title(char *out, size_t n)
{
    int len = snprintf(out, n, "Ryu action 0x%02X %s", s_shown[0] & 0xFF, guess_name(s_shown[0]));
    for (int i = 1; i < SHOWN_N && len > 0 && (size_t)len < n; i++)
        if (s_shown[i] != 0x100)
            len += snprintf(out + len, n - len, " < %02X %s", s_shown[i] & 0xFF, guess_name(s_shown[i]));
    return s_shown_serial;
}

/* ---- Finding the current move (NGB_SHOW_ACTION): see docs/function_map.md. Jumps are the anchor:
 * their moves are known (standing 0x55: moves 0x22, 0x23; running 0x56-0x58: moves 0x26-0x2C). For
 * the jump's first 6 frames, every u16 in Ryu's object and player block equal to one of them, and
 * every u32 pointing at one of their entries in the loaded ryu.mtn, scores once for that jump. ---- */

#define MF_OBJ 0x4B4E50u
#define MF_OBJ_N 0x2800u
#define MF_PB 0x4968B0u
#define MF_PB_N 0xDD0u
#define MF_MTN_SIZE 0x143DA0u
static uint16_t s_mf_hits[2][2][MF_OBJ_N];   /* [region][u16 / pointer][offset] */
static uint8_t s_mf_seen[2][2][MF_OBJ_N];    /* matched during the current jump */
static int s_mf_jumps, s_mf_frames;
static uint32_t s_mf_mtn;

static uint32_t mf_find_mtn(void)
{
    static const uint32_t ranges[][2] = { { 0x00010000u, 0x04000000u }, { 0x80000000u, 0x88000000u } };
    for (int r = 0; r < 2; r++)
        for (uint32_t va = ranges[r][0]; va < ranges[r][1] - 0x20; va += 0x10)
            if (MEM32(va) == 0x5F726863u && MEM32(va + 4) == 0x00746164u && MEM32(va + 0x0C) == MF_MTN_SIZE
                && MEM32(va + 0x10) == 3)
                return va;
    return 0;
}

static uint32_t mf_entry(uint32_t move)          /* the move's entry in the loaded ryu.mtn, 0 unknown */
{
    if (!s_mf_mtn)
        return 0;
    uint32_t base = s_mf_mtn, first = MEM32(base + 0x18);
    uint32_t s1 = MEM32(base + first + 4);
    uint32_t sec1 = s1 < MF_MTN_SIZE ? base + s1 : s1;
    uint32_t e = MEM32(sec1 + 4 * move);
    return e < MF_MTN_SIZE ? sec1 + e : e;
}

static void mf_scan(const uint16_t *moves, int n)
{
    uint32_t ent[8] = { 0 };
    for (int i = 0; i < n; i++)
        ent[i] = mf_entry(moves[i]);
    for (int r = 0; r < 2; r++) {
        uint32_t base = r ? MF_PB : MF_OBJ, len = r ? MF_PB_N : MF_OBJ_N;
        for (uint32_t o = 0; o + 4 <= len; o += 2) {
            uint16_t h = MEM16(base + o);
            uint32_t w = MEM32(base + o);
            for (int i = 0; i < n; i++) {
                if (h == moves[i])
                    s_mf_seen[r][0][o] = 1;
                if (ent[i] && w == ent[i])
                    s_mf_seen[r][1][o] = 1;
            }
        }
    }
}

static void mf_report(void)
{
    FILE *f = fopen("recordings/move_field.txt", "w");
    if (!f)
        return;
    fprintf(f, "Jumps seen: %d (ryu.mtn at %08X)\nPlaces matching the jump's move, by jumps matched:\n",
            s_mf_jumps, s_mf_mtn);
    for (int want = s_mf_jumps; want >= 1 && want >= s_mf_jumps - 2; want--)
        for (int r = 0; r < 2; r++)
            for (int k = 0; k < 2; k++)
                for (uint32_t o = 0; o < (r ? MF_PB_N : MF_OBJ_N); o += 2)
                    if (s_mf_hits[r][k][o] == want)
                        fprintf(f, "  %2d/%d  %s +0x%04X (%08X)  %s, now %08X\n", want, s_mf_jumps,
                                r ? "player block" : "Ryu object", o, (r ? MF_PB : MF_OBJ) + o,
                                k ? "pointer to the move entry" : "u16 move number", MEM32((r ? MF_PB : MF_OBJ) + o));
    fclose(f);
}

/* Once a frame (from ngb_action_watch_frame) with the action now and whether it just changed. */
static void mf_frame(uint32_t action, int changed)
{
    static unsigned tick;
    if (!s_mf_mtn && ++tick % 120 == 0)
        s_mf_mtn = mf_find_mtn();
    static const uint16_t stand[] = { 0x22, 0x23 };
    static const uint16_t run[] = { 0x26, 0x27, 0x28, 0x29, 0x2A, 0x2B, 0x2C };
    int is_stand = action == 0x55, is_run = action >= 0x56 && action <= 0x58;
    if (changed && (is_stand || is_run) && !s_mf_frames) {
        memset(s_mf_seen, 0, sizeof s_mf_seen);
        s_mf_frames = 6;
    }
    if (!s_mf_frames)
        return;
    if (is_stand) mf_scan(stand, 2);
    else if (is_run) mf_scan(run, 7);
    if (--s_mf_frames == 0) {
        s_mf_jumps++;
        for (int r = 0; r < 2; r++)
            for (int k = 0; k < 2; k++)
                for (uint32_t o = 0; o < MF_OBJ_N; o++)
                    s_mf_hits[r][k][o] += s_mf_seen[r][k][o];
        make_dir("recordings");
        mf_report();
    }
}
