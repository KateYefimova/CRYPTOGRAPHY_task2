/*
 * TABLES FOR STREAM CIPHER STRUMOK
 *
 * Filename: strumok_tables.h
 *
 * Synopsis:
 *  Defines multiplication with alpha and alpha^-1 as well as the S-box
 */

#ifndef STRUMOK_TABLES
# define STRUMOK_TABLES

# include <stdint.h>

extern const uint64_t strumok_T0[256];
extern const uint64_t strumok_T1[256];
extern const uint64_t strumok_T2[256];
extern const uint64_t strumok_T3[256];
extern const uint64_t strumok_T4[256];
extern const uint64_t strumok_T5[256];
extern const uint64_t strumok_T6[256];
extern const uint64_t strumok_T7[256];

extern const uint64_t strumok_alpha_mul[256];
extern const uint64_t strumok_alphainv_mul[256];

#endif /* STRUMOK_TABLES */
