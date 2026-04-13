#include "strumok.h"
#include <string.h>

static inline uint64_t a_mul(uint64_t x) {
    return ((x << 8) ^ strumok_alpha_mul[x >> 56]);
}

static inline uint64_t ainv_mul(uint64_t x) {
    return ((x >> 8) ^ strumok_alphainv_mul[x & 0xff]);
}

static inline uint64_t transform_T(uint64_t x) {
    return (strumok_T0[x & 0xff] ^ strumok_T1[(x >> 8) & 0xff] ^
            strumok_T2[(x >> 16) & 0xff] ^ strumok_T3[(x >> 24) & 0xff] ^
            strumok_T4[(x >> 32) & 0xff] ^ strumok_T5[(x >> 40) & 0xff] ^
            strumok_T6[(x >> 48) & 0xff] ^ strumok_T7[(x >> 56) & 0xff]);
}

static inline uint64_t fsm_func(uint64_t x1, uint64_t x2, uint64_t x3) {
    return (x1 + x2) ^ x3;
}

static void strumok_step(strumok_ctx_t *ctx, int init_mode) {
    uint64_t new_r2 = transform_T(ctx->R[0]);
    uint64_t new_r1 = ctx->R[1] + (ctx->S[5] ^ ctx->R[0]);
    
    uint64_t feedback = a_mul(ctx->S[0]) ^ ctx->S[2] ^ ainv_mul(ctx->S[11]) ^ ctx->S[15];
    
    if (init_mode) {
        feedback ^= fsm_func(ctx->S[15], ctx->R[0], ctx->R[1]);
    }

    for (int i = 0; i < 15; i++) ctx->S[i] = ctx->S[i+1];
    ctx->S[15] = feedback;
    ctx->R[0] = new_r1;
    ctx->R[1] = new_r2;
}

void strumok_init(strumok_ctx_t *ctx, const uint8_t *key, int key_bits, const uint8_t *iv) {
    memset(ctx, 0, sizeof(strumok_ctx_t));
    ctx->is_512 = (key_bits == 512);
    
    uint64_t K[8], IV[4];
    for (int i = 0; i < (key_bits/64); i++) {
        K[i] = 0;
        for (int j = 0; j < 8; j++) K[i] |= (uint64_t)key[i*8+j] << (56 - j*8);
    }
    for (int i = 0; i < 4; i++) {
        IV[i] = 0;
        for (int j = 0; j < 8; j++) IV[i] |= (uint64_t)iv[i*8+j] << (56 - j*8);
    }

    if (key_bits == 256) {
        ctx->S[15] = K[3] ^ IV[0]; ctx->S[14] = K[2]; ctx->S[13] = K[1] ^ IV[1]; ctx->S[12] = K[0] ^ IV[2];
        ctx->S[11] = K[3]; ctx->S[10] = K[2] ^ IV[3]; ctx->S[9] = ~K[1]; ctx->S[8] = ~K[0];
        ctx->S[7] = K[3]; ctx->S[6] = K[2]; ctx->S[5] = ~K[1]; ctx->S[4] = K[0];
        ctx->S[3] = K[3]; ctx->S[2] = ~K[2]; ctx->S[1] = K[1]; ctx->S[0] = ~K[0];
    } else {
        ctx->S[15] = K[7] ^ IV[0]; ctx->S[14] = K[6]; ctx->S[13] = K[5]; ctx->S[12] = K[4] ^ IV[1];
        ctx->S[11] = K[3]; ctx->S[10] = K[2] ^ IV[2]; ctx->S[9] = K[1]; ctx->S[8] = ~K[0];
        ctx->S[7] = K[4] ^ IV[3]; ctx->S[6] = ~K[6]; ctx->S[5] = K[5]; ctx->S[4] = ~K[7];
        ctx->S[3] = K[3]; ctx->S[2] = K[2]; ctx->S[1] = ~K[1]; ctx->S[0] = K[0];
    }

    for (int i = 0; i < 32; i++) strumok_step(ctx, 1);
    strumok_step(ctx, 0);
}

uint64_t strumok_next_word(strumok_ctx_t *ctx) {
    uint64_t z = fsm_func(ctx->S[15], ctx->R[0], ctx->R[1]) ^ ctx->S[0];
    strumok_step(ctx, 0);
    return z;
}