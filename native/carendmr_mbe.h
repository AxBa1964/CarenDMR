/*
 * CarenDMR receive-only AMBE+2 decoder boundary.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef CARENDMR_MBE_H
#define CARENDMR_MBE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32)
#define CARENDMR_MBE_API __declspec(dllexport)
#else
#define CARENDMR_MBE_API __attribute__((visibility("default")))
#endif

typedef struct carendmr_mbe_decoder carendmr_mbe_decoder;

CARENDMR_MBE_API carendmr_mbe_decoder *carendmr_mbe_decoder_create(void);
CARENDMR_MBE_API void carendmr_mbe_decoder_destroy(
    carendmr_mbe_decoder *decoder
);

/*
 * Decode one DMR AMBE+2 2450/1150 codeword.
 *
 * `ambe` must address exactly 9 bytes and `pcm` exactly 160 signed,
 * native-endian 16-bit samples. Returns 0 on success, -1 for a null argument.
 * The decoder is stateful and must be used in call order.
 */
CARENDMR_MBE_API int carendmr_mbe_decode(
    carendmr_mbe_decoder *decoder,
    const uint8_t ambe[9],
    int16_t pcm[160],
    int *corrected_errors
);

#ifdef __cplusplus
}
#endif

#endif
