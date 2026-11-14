cmake_minimum_required(VERSION 3.12)

project(carendmr_md380_bridge LANGUAGES C CXX)

# Ab 0.2.1.89: Die Bridge wird OHNE MD380-Firmware gebaut. Der Upstream-Build
# (add_subdirectory) lädt die Firmware herunter und baut sie per xxd ein;
# deshalb übersetzen wir nur md380_vocoder.cpp aus dem Upstream-Quelltext
# und stellen die Speicherbereiche "firmware"/"sram" selbst bereit
# (native/md380_dynarmic_bridge.cpp). Die Dateien lädt CarenDMR zur Laufzeit.

if(NOT DEFINED MD380_SOURCE_DIR OR MD380_SOURCE_DIR STREQUAL "")
    message(FATAL_ERROR "MD380_SOURCE_DIR muss auf den geklonten md380_vocoder_dynarmic-Quellordner zeigen.")
endif()

if(NOT EXISTS "${MD380_SOURCE_DIR}/md380_vocoder.cpp")
    message(FATAL_ERROR "MD380_SOURCE_DIR ist ungültig: ${MD380_SOURCE_DIR}")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Gleiche dynarmic-Einstellungen wie im Upstream-CMakeLists.txt.
include(FetchContent)
set(DYNARMIC_TESTS OFF CACHE BOOL "")
set(DYNARMIC_USE_ARMV7 ON CACHE BOOL "")
FetchContent_Declare(
    dynarmic
    GIT_REPOSITORY https://github.com/yuzu-mirror/dynarmic.git
    GIT_TAG master
)
FetchContent_MakeAvailable(dynarmic)

add_library(carendmr_md380_bridge SHARED
    "${CMAKE_CURRENT_LIST_DIR}/../md380_dynarmic_bridge.cpp"
    "${MD380_SOURCE_DIR}/md380_vocoder.cpp"
)

target_include_directories(carendmr_md380_bridge PRIVATE
    "${MD380_SOURCE_DIR}"
)

target_link_libraries(carendmr_md380_bridge PRIVATE
    dynarmic
)

set_target_properties(carendmr_md380_bridge PROPERTIES
    OUTPUT_NAME "carendmr_md380_bridge"
    # MinGW setzt sonst "lib" davor (libcarendmr_md380_bridge.dll).
    PREFIX ""
)
