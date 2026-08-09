#include <cstdint>
#include <cstring>
#include "md380_vocoder.h"

#ifdef _WIN32
#define CARENDMR_EXPORT extern "C" __declspec(dllexport)
#else
#define CARENDMR_EXPORT extern "C"
#endif

CARENDMR_EXPORT int carendmr_md380_init() {
    return md380_init();
}

CARENDMR_EXPORT int carendmr_md380_encode_fec(const int16_t* pcm, uint8_t* ambe) {
    if (!pcm || !ambe) return 1;
    int16_t local_pcm[160];
    std::memcpy(local_pcm, pcm, sizeof(local_pcm));
    std::memset(ambe, 0, 9);
    md380_encode_fec(ambe, local_pcm);
    return 0;
}

CARENDMR_EXPORT int carendmr_md380_decode_fec(const uint8_t* ambe, int16_t* pcm) {
    if (!pcm || !ambe) return 1;
    uint8_t local_ambe[9];
    std::memcpy(local_ambe, ambe, sizeof(local_ambe));
    md380_decode_fec(local_ambe, pcm);
    return 0;
}
