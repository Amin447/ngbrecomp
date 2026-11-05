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
