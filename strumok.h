#ifndef STRUMOK_H
#define STRUMOK_H

#include <stdint.h>
#include "strumok_tables.h"

typedef struct {
    uint64_t S[16]; 
    uint64_t R[2];  
    int is_512;    
} strumok_ctx_t;

void strumok_init(strumok_ctx_t *ctx, const uint8_t *key, int key_bits, const uint8_t *iv);
uint64_t strumok_next_word(strumok_ctx_t *ctx);

#endif