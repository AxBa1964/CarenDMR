#include <cstdint>
#include <cstring>
#include <sstream>
#include <string>

#ifdef _WIN32
#include <windows.h>
#else
#include <dlfcn.h>
#endif

class Vocoder {
public:
    virtual ~Vocoder() = default;
    virtual void decode_2400x1200(int16_t*, uint8_t*) = 0;
    virtual void decode_2450x1150(int16_t*, uint8_t*) = 0;
    virtual void decode_2450(int16_t*, uint8_t*) = 0;
    virtual void encode_2400x1200(int16_t*, uint8_t*) = 0;
    virtual void encode_2450x1150(int16_t*, uint8_t*) = 0;
    virtual void encode_2450(int16_t*, uint8_t*) = 0;
};

using create_t = Vocoder* (*)();
using destroy_t = void (*)(Vocoder*);

struct BridgeHandle {
#ifdef _WIN32
    HMODULE library = nullptr;
#else
    void* library = nullptr;
#endif
    Vocoder* vocoder = nullptr;
    destroy_t destroy = nullptr;
};

static thread_local std::string last_error;

static void set_error(const std::string& text) {
    last_error = text.empty() ? "Unbekannter Vocoderfehler." : text;
}

#ifdef _WIN32
static std::string windows_error_text(const char* prefix) {
    const DWORD code = GetLastError();
    LPSTR buffer = nullptr;
    const DWORD length = FormatMessageA(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
        nullptr,
        code,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        reinterpret_cast<LPSTR>(&buffer),
        0,
        nullptr
    );
    std::ostringstream text;
    text << prefix << " (Windows-Fehler " << code << ")";
    if (length && buffer) {
        std::string message(buffer, length);
        while (!message.empty() && (message.back() == '\r' || message.back() == '\n')) {
            message.pop_back();
        }
        text << ": " << message;
    }
    if (buffer) LocalFree(buffer);
    return text.str();
}
#endif

extern "C" {

#ifdef _WIN32
__declspec(dllexport)
#endif
void* carendmr_vocoder_open(const char* plugin_path) {
    last_error.clear();
    if (!plugin_path || !*plugin_path) {
        set_error("Es wurde kein Vocoder-Pluginpfad angegeben.");
        return nullptr;
    }

    auto* handle = new BridgeHandle();
#ifdef _WIN32
    handle->library = LoadLibraryA(plugin_path);
    if (!handle->library) {
        set_error(windows_error_text("Das DroidStar-Vocoder-Plugin konnte nicht geladen werden"));
        delete handle;
        return nullptr;
    }

    auto create = reinterpret_cast<create_t>(GetProcAddress(handle->library, "create"));
    handle->destroy = reinterpret_cast<destroy_t>(GetProcAddress(handle->library, "destroy"));
    if (!handle->destroy) {
        // Ältere DroidStar-Header enthielten den Tippfehler "destry".
        handle->destroy = reinterpret_cast<destroy_t>(GetProcAddress(handle->library, "destry"));
    }
#else
    handle->library = dlopen(plugin_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle->library) {
        set_error(dlerror());
        delete handle;
        return nullptr;
    }

    auto create = reinterpret_cast<create_t>(dlsym(handle->library, "create"));
    handle->destroy = reinterpret_cast<destroy_t>(dlsym(handle->library, "destroy"));
    if (!handle->destroy) {
        handle->destroy = reinterpret_cast<destroy_t>(dlsym(handle->library, "destry"));
    }
#endif

    if (!create || !handle->destroy) {
        std::ostringstream message;
        message << "Das Plugin stellt die benötigten DroidStar-Exporte nicht bereit. ";
        message << "create=" << (create ? "gefunden" : "fehlt") << ", ";
        message << "destroy/destry=" << (handle->destroy ? "gefunden" : "fehlt") << ".";
        set_error(message.str());
#ifdef _WIN32
        FreeLibrary(handle->library);
#else
        dlclose(handle->library);
#endif
        delete handle;
        return nullptr;
    }

    try {
        handle->vocoder = create();
    } catch (...) {
        handle->vocoder = nullptr;
    }
    if (!handle->vocoder) {
        set_error("Das Plugin wurde geladen, konnte aber kein Vocoder-Objekt erzeugen.");
#ifdef _WIN32
        FreeLibrary(handle->library);
#else
        dlclose(handle->library);
#endif
        delete handle;
        return nullptr;
    }
    return handle;
}

#ifdef _WIN32
__declspec(dllexport)
#endif
void carendmr_vocoder_close(void* opaque) {
    auto* handle = static_cast<BridgeHandle*>(opaque);
    if (!handle) return;
    if (handle->vocoder && handle->destroy) {
        try { handle->destroy(handle->vocoder); } catch (...) {}
    }
#ifdef _WIN32
    if (handle->library) FreeLibrary(handle->library);
#else
    if (handle->library) dlclose(handle->library);
#endif
    delete handle;
}

#ifdef _WIN32
__declspec(dllexport)
#endif
int carendmr_vocoder_encode_2450x1150(void* opaque, const int16_t* pcm, uint8_t* output) {
    last_error.clear();
    auto* handle = static_cast<BridgeHandle*>(opaque);
    if (!handle || !handle->vocoder || !pcm || !output) {
        set_error("Ungültiger Encoderaufruf.");
        return 1;
    }
    std::memset(output, 0, 9);
    try {
        handle->vocoder->encode_2450x1150(const_cast<int16_t*>(pcm), output);
    } catch (...) {
        set_error("Das Plugin meldete beim AMBE-Encoding einen Fehler.");
        return 2;
    }
    return 0;
}

#ifdef _WIN32
__declspec(dllexport)
#endif
const char* carendmr_vocoder_last_error() {
    return last_error.c_str();
}

}
