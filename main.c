#include <stdio.h>
#include <time.h>
#include <stdint.h>
#include "strumok.h"

void print_test_vector_512() {
    uint8_t key[64] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
        0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f,
        0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b, 0x2c, 0x2d, 0x2e, 0x2f,
        0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3a, 0x3b, 0x3c, 0x3d, 0x3e, 0x3f
    };
    uint8_t iv[32] = {0}; 

    strumok_ctx_t ctx;
    strumok_init(&ctx, key, 512, iv);

    printf("--- Тестові вектори Струмок-512 ---\n");
    for(int i = 0; i < 4; i++) {
        printf("Z[%d] = %016llX\n", i, (unsigned long long)strumok_next_word(&ctx));
    }
}

void test_256() {
    uint8_t key[32] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f,
        0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f
    };
    uint8_t iv[32] = {0}; 
    
    strumok_ctx_t ctx;
    strumok_init(&ctx, key, 256, iv);
    
    printf("\n--- Тест Струмок-256 ---\n");
    for(int i = 0; i < 4; i++) {
        printf("Z[%d] = %016llX\n", i, (unsigned long long)strumok_next_word(&ctx));
    }
}

void benchmark(int bits) {
    uint8_t key[64] = {0};
    uint8_t iv[32] = {0};
    strumok_ctx_t ctx;
    strumok_init(&ctx, key, bits, iv);

    const unsigned long long n = 10000000; 
    clock_t start = clock();
    for(unsigned long long i = 0; i < n; i++) {
        strumok_next_word(&ctx);
    }
    clock_t end = clock();

    double sec = (double)(end - start) / CLOCKS_PER_SEC;
    double speed = (n * 8.0) / (sec * 1024 * 1024);
    printf("Швидкість (%d-bit): %.2f MB/s\n", bits, speed);
}

int main() {
    print_test_vector_512();
    test_256();

    printf("\n--- Оцінка продуктивності ---\n");
    benchmark(256);
    benchmark(512);

    return 0;
}