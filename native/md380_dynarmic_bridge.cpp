// CarenDMR-Hülle um md380_vocoder_dynarmic (GPLv3-or-later).
//
// Ab 0.2.1.89 ist die MD380-Firmware NICHT mehr in diese Bibliothek
// eingebaut. Der Nutzer stellt D002.032.bin und d02032-core.img bereit;
// carendmr_md380_init_files() lädt beide Dateien in die Speicherbereiche,
// die md380_vocoder.cpp als "firmware" und "sram" erwartet (dort per
// "extern unsigned char firmware[]; extern unsigned char sram[];" deklariert,
// im Upstream-Build von xxd erzeugt).

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <string>

#include "md380_vocoder.h"

#ifdef _WIN32
#include <windows.h>
#define CARENDMR_EXPORT extern "C" __declspec(dllexport)
#else
#define CARENDMR_EXPORT extern "C"
#endif

// Der Emulator liest die Firmware im Bereich 0x0800C000 .. +0x100000 und
// kopiert genau 0x20000 Byte RAM-Abbild. Beide Puffer sind deshalb fest so
// groß; nicht belegte Bytes bleiben 0.
static const std::size_t kFirmwareCapacity = 0x100000;
static const std::size_t kSramSize = 0x20000;

unsigned char firmware[kFirmwareCapacity];
unsigned int firmware_len = 0;
unsigned char sram[kSramSize];
unsigned int sram_len = 0;

namespace {

std::mutex g_lock;
bool g_files_loaded = false;
std::string g_last_error;

enum InitResult : int {
    kOk = 0,
    kFirmwareMissing = 10,
    kFirmwareTooLarge = 11,
    kCoreMissing = 12,
    kCoreWrongSize = 13,
    kNotLoaded = 14,
    kInvalidArgument = 15,
};

std::FILE* open_utf8(const char* path) {
#ifdef _WIN32
    int wide_len = MultiByteToWideChar(CP_UTF8, 0, path, -1, nullptr, 0);
    if (wide_len <= 0) return nullptr;
    std::wstring wide(static_cast<std::size_t>(wide_len), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, path, -1, &wide[0], wide_len);
    return _wfopen(wide.c_str(), L"rb");
#else
    return std::fopen(path, "rb");
#endif
}

// Liest höchstens capacity Byte; liefert die Dateigröße oder -1.
long read_file(const char* path, unsigned char* buffer, std::size_t capacity) {
    std::FILE* file = open_utf8(path);
    if (!file) return -1;
    std::memset(buffer, 0, capacity);
    std::size_t total = std::fread(buffer, 1, capacity, file);
    // Prüfen, ob die Datei größer als der Puffer ist.
    unsigned char extra = 0;
    std::size_t more = std::fread(&extra, 1, 1, file);
    std::fclose(file);
    if (more != 0) return static_cast<long>(capacity) + 1;
    return static_cast<long>(total);
}

}  // namespace

CARENDMR_EXPORT const char* carendmr_md380_last_error() {
    return g_last_error.c_str();
}

// Lädt Firmware und RAM-Abbild (UTF-8-Pfade) und startet den Emulator.
CARENDMR_EXPORT int carendmr_md380_init_files(const char* firmware_path, const char* core_path) {
    std::lock_guard<std::mutex> guard(g_lock);
    if (!firmware_path || !core_path) {
        g_last_error = "Pfad fehlt.";
        return kInvalidArgument;
    }
    if (!g_files_loaded) {
        long fw = read_file(firmware_path, firmware, kFirmwareCapacity);
        if (fw <= 0) {
            g_last_error = "Firmware-Datei nicht lesbar.";
            return kFirmwareMissing;
        }
        if (static_cast<std::size_t>(fw) > kFirmwareCapacity) {
            g_last_error = "Firmware-Datei zu groß.";
            return kFirmwareTooLarge;
        }
        long core = read_file(core_path, sram, kSramSize);
        if (core < 0) {
            g_last_error = "RAM-Abbild nicht lesbar.";
            return kCoreMissing;
        }
        if (static_cast<std::size_t>(core) != kSramSize) {
            g_last_error = "RAM-Abbild hat nicht genau 131072 Byte.";
            return kCoreWrongSize;
        }
        firmware_len = static_cast<unsigned int>(fw);
        sram_len = static_cast<unsigned int>(core);
        g_files_loaded = true;
    }
    // Wie bisher: jede Initialisierung startet den Emulator neu mit dem
    // RAM-Abbild (gemeinsamer Emulator für Senden und Empfangen).
    g_last_error.clear();
    return md380_init();
}

// Alte Einstiegsstelle: ohne vorher geladene Dateien nicht zulässig.
CARENDMR_EXPORT int carendmr_md380_init() {
    std::lock_guard<std::mutex> guard(g_lock);
    if (!g_files_loaded) {
        g_last_error = "Firmware nicht geladen; carendmr_md380_init_files verwenden.";
        return kNotLoaded;
    }
    return md380_init();
}

CARENDMR_EXPORT int carendmr_md380_encode_fec(const int16_t* pcm, uint8_t* ambe) {
    if (!pcm || !ambe || !g_files_loaded) return 1;
    int16_t local_pcm[160];
    std::memcpy(local_pcm, pcm, sizeof(local_pcm));
    std::memset(ambe, 0, 9);
    md380_encode_fec(ambe, local_pcm);
    return 0;
}

CARENDMR_EXPORT int carendmr_md380_decode_fec(const uint8_t* ambe, int16_t* pcm) {
    if (!pcm || !ambe || !g_files_loaded) return 1;
    uint8_t local_ambe[9];
    std::memcpy(local_ambe, ambe, sizeof(local_ambe));
    md380_decode_fec(local_ambe, pcm);
    return 0;
}
