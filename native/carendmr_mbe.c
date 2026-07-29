/*
 * CarenDMR receive-only adapter around DroidStar's mbelib-derived decoder.
 *
 * Adapter copyright (C) 2026 CarenDMR contributors.
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * The decoder implementation in native/mbelib retains its ISC notices.
 */
#include "carendmr_mbe.h"

#include <math.h>
#include <stdlib.h>

#include "mbelib/mbelib.h"

/* DroidStar's DMR AMBE 2450/1150 dibit-to-mbelib frame mapping. */
static const int DMR_W[36] = {
    0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
    0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 2,
    0, 2, 0, 2, 0, 2, 0, 2, 0, 2, 0, 2
};
static const int DMR_X[36] = {
    23, 10, 22, 9, 21, 8, 20, 7, 19, 6, 18, 5,
    17, 4, 16, 3, 15, 2, 14, 1, 13, 0, 12, 10,
    11, 9, 10, 8, 9, 7, 8, 6, 7, 5, 6, 4
};
static const int DMR_Y[36] = {
    0, 2, 0, 2, 0, 2, 0, 2, 0, 3, 0, 3,
    1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3,
    1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3
};
static const int DMR_Z[36] = {
    5, 3, 4, 2, 3, 1, 2, 0, 1, 13, 0, 12,
    22, 11, 21, 10, 20, 9, 19, 8, 18, 7, 17, 6,
    16, 5, 15, 4, 14, 3, 13, 2, 12, 1, 11, 0
};

struct carendmr_mbe_decoder {
    mbe_parms current;
    mbe_parms previous;
    mbe_parms enhanced;
    char data_bits[49];
};

carendmr_mbe_decoder *carendmr_mbe_decoder_create(void)
{
    carendmr_mbe_decoder *decoder = calloc(1, sizeof(*decoder));
    if (decoder != NULL) {
        mbe_initMbeParms(
            &decoder->current,
            &decoder->previous,
            &decoder->enhanced
        );
    }
    return decoder;
}

void carendmr_mbe_decoder_destroy(carendmr_mbe_decoder *decoder)
{
    free(decoder);
}

int carendmr_mbe_decode(
    carendmr_mbe_decoder *decoder,
    const uint8_t ambe[9],
    int16_t pcm[160],
    int *corrected_errors
)
{
    char frame[4][24] = {{0}};
    float audio[160];
    char error_text[64] = {0};
    int errors = 0;
    const int *w = DMR_W;
    const int *x = DMR_X;
    const int *y = DMR_Y;
    const int *z = DMR_Z;

    if (decoder == NULL || ambe == NULL || pcm == NULL) {
        return -1;
    }

    for (int byte_index = 0; byte_index < 9; ++byte_index) {
        for (int bit_index = 0; bit_index < 8; bit_index += 2) {
            frame[*y][*z] =
                (char)(1U & (ambe[byte_index] >> (7 - (bit_index + 1))));
            frame[*w][*x] =
                (char)(1U & (ambe[byte_index] >> (7 - bit_index)));
            ++w;
            ++x;
            ++y;
            ++z;
        }
    }

    mbe_processAmbe3600x2450Framef(
        audio,
        &errors,
        error_text,
        frame,
        decoder->data_bits,
        &decoder->current,
        &decoder->previous,
        &decoder->enhanced,
        3
    );

    for (int index = 0; index < 160; ++index) {
        float sample = audio[index];
        if (!isfinite(sample)) {
            sample = 0.0F;
        } else if (sample > 32760.0F) {
            sample = 32760.0F;
        } else if (sample < -32760.0F) {
            sample = -32760.0F;
        }
        pcm[index] = (int16_t)sample;
    }
    if (corrected_errors != NULL) {
        *corrected_errors = errors;
    }
    return 0;
}
