/*
 * func_recorder.c -- records which game functions run, frame by frame, for
 * working out what they do (docs/function_map.md).
 *
 * F9 starts and stops a recording; F6 drops a marker while recording. A
 * recording also stops by itself after REC_MAX_SECONDS. Each one goes to
 * recordings/rec_<date>_<time>.bin in the folder the game starts in.
 *
 * Every lifted function starts with RECOMP_ENTRY, which calls
 * recomp_capture_entry (xboxrecomp's recomp_capture.c) while
 * g_recomp_capture_va is non-zero; that calls g_recomp_entry_hook first. While
 * recording, the hook counts calls per function in a flat table indexed by
 * address, and remembers which functions it touched this frame. Once a frame
 * (ngb_frame_tick, the game's thread) the touched ones are written and reset.
 *
 * File: "NGBREC1\0", u32 version (1), then one record a frame:
 *   u32 'FRM0', u32 frame, u64 microseconds since start, u32 flags (bit 0 a
 *   marker this frame), f32 Ryu's x y z (0x4B5710), 0x78 bytes of input: the
 *   first controller's XBOX_GAMEPAD as the game reads it (version 2: wButtons,
 *   8 analog buttons A B X Y Black White LT RT, 4 stick shorts; the rest zero),
 *   u32 n, then n x { u32 va, u32 calls }.
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

#define REC_VA_LIMIT   0x00E00000u      /* past the highest lifted function (0x00DC1918) */
#define REC_TOUCH_MAX  (1u << 17)
#define REC_MAX_SECONDS 120
#define PAD_SIZE       0x78u

extern uint32_t g_recomp_capture_va;
extern void (*volatile g_recomp_entry_hook)(uint32_t va);
extern unsigned char ngb_rec_pad[32];  /* src/bindings.c */

volatile int ngb_rec_toggle_request;     /* set by F9 (src/ingame_menu.c) */
volatile int ngb_rec_marker_request;     /* set by F6 */
volatile int ngb_rec_active;             /* read by the window title code */

static uint32_t *s_counts;               /* calls this frame, by address */
static uint32_t *s_touched;              /* addresses first called this frame */
static volatile uint32_t s_ntouched;
static volatile int s_overflow;
static FILE *s_file;
static uint32_t s_frame;
static uint64_t s_start_us;
static int s_set_capture;                /* we turned g_recomp_capture_va on */

static uint64_t now_us(void)
{
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return (uint64_t)ts.tv_sec * 1000000u + (uint64_t)ts.tv_nsec / 1000u;
}

static void rec_hook(uint32_t va)
{
    if (va >= REC_VA_LIMIT)
        return;
    if (__atomic_fetch_add(&s_counts[va], 1u, __ATOMIC_RELAXED) == 0) {
        uint32_t i = __atomic_fetch_add(&s_ntouched, 1u, __ATOMIC_RELAXED);
        if (i < REC_TOUCH_MAX)
            s_touched[i] = va;
        else
            s_overflow = 1;
    }
}

static void rec_start(void)
{
    if (!s_counts) {
        s_counts = calloc(REC_VA_LIMIT, sizeof *s_counts);
        s_touched = calloc(REC_TOUCH_MAX, sizeof *s_touched);
        if (!s_counts || !s_touched) {
            fprintf(stderr, "[REC] out of memory\n");
            return;
        }
    }
    make_dir("recordings");
    char path[256];
    time_t t = time(NULL);
    struct tm tmv = *localtime(&t);
    snprintf(path, sizeof path, "recordings/rec_%04d%02d%02d_%02d%02d%02d.bin", tmv.tm_year + 1900,
             tmv.tm_mon + 1, tmv.tm_mday, tmv.tm_hour, tmv.tm_min, tmv.tm_sec);
    s_file = fopen(path, "wb");
    if (!s_file) {
        fprintf(stderr, "[REC] cannot write %s\n", path);
        return;
    }
    static const char magic[8] = "NGBREC1";
    uint32_t version = 2;
    fwrite(magic, 1, 8, s_file);
    fwrite(&version, 4, 1, s_file);
    memset(s_counts, 0, REC_VA_LIMIT * sizeof *s_counts);
    s_ntouched = 0;
    s_overflow = 0;
    s_frame = 0;
    s_start_us = now_us();
    g_recomp_entry_hook = rec_hook;
    if (!g_recomp_capture_va) {
        g_recomp_capture_va = 1;
        s_set_capture = 1;
    }
    ngb_rec_active = 1;
    fprintf(stderr, "[REC] recording to %s\n", path);
}

static void rec_stop(void)
{
    g_recomp_entry_hook = NULL;
    if (s_set_capture) {
        g_recomp_capture_va = 0;
        s_set_capture = 0;
    }
    if (s_file) {
        fclose(s_file);
        s_file = NULL;
    }
    ngb_rec_active = 0;
    fprintf(stderr, "[REC] stopped after %u frames\n", s_frame);
}

static void rec_write_frame(int marker)
{
    uint32_t n = s_ntouched < REC_TOUCH_MAX ? s_ntouched : REC_TOUCH_MAX;
    uint32_t head[2] = { 0x304D5246u /* 'FRM0' */, s_frame++ };
    uint64_t us = now_us() - s_start_us;
    uint32_t flags = marker ? 1u : 0u;
    float pos[3] = { MEMF(0x4B5710), MEMF(0x4B5714), MEMF(0x4B5718) };
    fwrite(head, 4, 2, s_file);
    fwrite(&us, 8, 1, s_file);
    fwrite(&flags, 4, 1, s_file);
    fwrite(pos, 4, 3, s_file);
    unsigned char pad[PAD_SIZE] = { 0 };
    memcpy(pad, ngb_rec_pad, sizeof ngb_rec_pad);
    fwrite(pad, 1, PAD_SIZE, s_file);

    if (s_overflow) {                     /* too many to have listed: take them all from the table */
        uint32_t count = 0;
        long at = ftell(s_file);
        fwrite(&count, 4, 1, s_file);
        for (uint32_t va = 0; va < REC_VA_LIMIT; va++) {
            uint32_t c = __atomic_exchange_n(&s_counts[va], 0u, __ATOMIC_RELAXED);
            if (c) {
                uint32_t pair[2] = { va, c };
                fwrite(pair, 4, 2, s_file);
                count++;
            }
        }
        long end = ftell(s_file);
        fseek(s_file, at, SEEK_SET);
        fwrite(&count, 4, 1, s_file);
        fseek(s_file, end, SEEK_SET);
        s_overflow = 0;
        __atomic_store_n(&s_ntouched, 0u, __ATOMIC_RELAXED);
        return;
    }
    fwrite(&n, 4, 1, s_file);
    for (uint32_t i = 0; i < n; i++) {
        uint32_t va = s_touched[i];
        uint32_t pair[2] = { va, __atomic_exchange_n(&s_counts[va], 0u, __ATOMIC_RELAXED) };
        fwrite(pair, 4, 2, s_file);
    }
    __atomic_store_n(&s_ntouched, 0u, __ATOMIC_RELAXED);
}

/* Once a frame, on the game's thread (src/cheats.c, ngb_frame_tick). */
void ngb_rec_frame(void)
{
    { extern void ngb_action_watch_frame(void); ngb_action_watch_frame(); }   /* src/action_log.c: NGB_SHOW_ACTION */
    static int autostart_checked;            /* NGB_REC_AUTOSTART=1: debugging, record from the first frame */
    if (!autostart_checked) {
        autostart_checked = 1;
        if (getenv("NGB_REC_AUTOSTART"))
            ngb_rec_toggle_request = 1;
    }
    {   /* NGB_REC_MODE=actions: F9 and F6 drive the action log instead (src/action_log.c) */
        extern int ngb_action_mode(void);
        extern void ngb_action_frame(int toggle, int marker);
        if (ngb_action_mode()) {
            int toggle = ngb_rec_toggle_request, marker = ngb_rec_marker_request;
            ngb_rec_toggle_request = ngb_rec_marker_request = 0;
            ngb_action_frame(toggle, marker);
            return;
        }
    }
    if (ngb_rec_toggle_request) {
        ngb_rec_toggle_request = 0;
        if (s_file) rec_stop();
        else rec_start();
        return;
    }
    if (!s_file)
        return;
    int marker = ngb_rec_marker_request;
    if (marker) {
        ngb_rec_marker_request = 0;
        fprintf(stderr, "[REC] marker at frame %u\n", s_frame);
    }
    rec_write_frame(marker);
    if (s_frame % 60 == 0)
        fflush(s_file);                       /* a crash or a closed window loses a second at most */
    if (now_us() - s_start_us > (uint64_t)REC_MAX_SECONDS * 1000000u)
        rec_stop();
}
