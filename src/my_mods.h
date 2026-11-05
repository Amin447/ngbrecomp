/* my_mods.h -- the user's own gameplay mods (src/my_mods.c). */
#pragma once
#include <stdint.h>

/* A hit in progress: Ryu's or an enemy's health segments before the game applied it. */
struct mymod_hit {
    uint32_t target, block;
    int ryu;
    uint16_t seg[8];
};

void mymod_hit_begin(struct mymod_hit *h, uint32_t target);
void mymod_hit_end(struct mymod_hit *h);
