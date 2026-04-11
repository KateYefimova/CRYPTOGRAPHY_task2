# include <stdint.h>

#include "strumok_tables.h"


static inline uint64_t
a_mul(const uint64_t x) {
  return ( ( (x) << 8 ) ^ ( strumok_alpha_mul[x >> 56] ) );
}


static inline uint64_t
ainv_mul(const uint64_t x) {
  return ( ( (x) >> 8 ) ^ ( strumok_alphainv_mul[x & 0xff] ) );
}


static inline uint64_t
transform_T(const uint64_t x) {
  return ((strumok_T0[  x        & 0xff ]) ^
          (strumok_T1[ (x >>  8) & 0xff ]) ^
          (strumok_T2[ (x >> 16) & 0xff ]) ^
          (strumok_T3[ (x >> 24) & 0xff ]) ^
          (strumok_T4[ (x >> 32) & 0xff ]) ^
          (strumok_T5[ (x >> 40) & 0xff ]) ^
          (strumok_T6[ (x >> 48) & 0xff ]) ^
          (strumok_T7[ (x >> 56) & 0xff ]));
}

