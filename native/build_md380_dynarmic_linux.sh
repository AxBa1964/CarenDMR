#!/usr/bin/env bash
# Baut die MD380-Dynarmic-Bridge für Linux (Raspberry Pi OS 64 Bit / aarch64
# und x86_64). Ergebnis: native/libcarendmr_md380_bridge.so – OHNE Firmware.
# Die Firmware lädt CarenDMR zur Laufzeit (seit 0.2.1.89).
#
# Benötigte Pakete (Raspberry Pi OS / Debian):
#   sudo apt install git cmake ninja-build g++ libboost-dev
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="https://github.com/dbehnke/md380_vocoder_dynarmic.git"
COMMIT="55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5"
VENDOR_ROOT="$SCRIPT_DIR/vendor"
SOURCE_DIR="$VENDOR_ROOT/md380_vocoder_dynarmic"
CMAKE_PROJECT="$SCRIPT_DIR/md380_dynarmic_build"
ARCH="$(uname -m)"
BUILD_DIR="$CMAKE_PROJECT/out-linux-$ARCH"
OUTPUT="$SCRIPT_DIR/libcarendmr_md380_bridge.so"

case "$ARCH" in
    aarch64|x86_64) ;;
    armv7l|armv6l)
        echo "32-Bit-System erkannt ($ARCH). Bitte Raspberry Pi OS 64 Bit verwenden." >&2
        exit 1
        ;;
    *)
        echo "Nicht unterstützte Architektur: $ARCH" >&2
        exit 1
        ;;
esac

if [ ! -f "$CMAKE_PROJECT/CMakeLists.txt" ]; then
    echo "CarenDMR-CMake-Wrapper fehlt: $CMAKE_PROJECT/CMakeLists.txt" >&2
    exit 1
fi

for tool in git cmake ninja g++; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Fehlendes Werkzeug: $tool" >&2
        echo "Installieren mit: sudo apt install git cmake ninja-build g++ libboost-dev" >&2
        exit 1
    fi
done

if [ ! -f /usr/include/boost/variant.hpp ]; then
    echo "Boost-Header fehlen (/usr/include/boost/variant.hpp)." >&2
    echo "Installieren mit: sudo apt install libboost-dev" >&2
    exit 1
fi

mkdir -p "$VENDOR_ROOT"
if [ ! -d "$SOURCE_DIR/.git" ]; then
    git clone "$REPO" "$SOURCE_DIR"
fi
git -C "$SOURCE_DIR" fetch --all --tags
git -C "$SOURCE_DIR" checkout --detach "$COMMIT"

if [ ! -f "$SOURCE_DIR/md380_vocoder.cpp" ]; then
    echo "md380_vocoder.cpp fehlt im Upstream-Quellordner." >&2
    exit 1
fi

rm -rf "$BUILD_DIR"
cmake -S "$CMAKE_PROJECT" -B "$BUILD_DIR" -G Ninja \
    -DMD380_SOURCE_DIR="$SOURCE_DIR" \
    -DCMAKE_BUILD_TYPE=Release

# Auf dem Pi mit 1 GB RAM höchstens zwei Compiler gleichzeitig (Speicher).
JOBS="${JOBS:-2}"
cmake --build "$BUILD_DIR" --config Release -j"$JOBS"

CANDIDATE="$(find "$BUILD_DIR" -type f -name 'libcarendmr_md380_bridge.so' -print -quit)"
if [ -z "$CANDIDATE" ]; then
    CANDIDATE="$(find "$BUILD_DIR" -type f -name 'carendmr_md380_bridge.so' -print -quit)"
fi
if [ -z "$CANDIDATE" ]; then
    echo "Die Bridge (.so) wurde nach dem Build nicht gefunden." >&2
    exit 1
fi

cp "$CANDIDATE" "$OUTPUT"
if ! grep -q carendmr_md380_init_files "$OUTPUT"; then
    echo "Die gebaute Bridge kennt carendmr_md380_init_files nicht." >&2
    exit 1
fi
echo "MD380-Dynarmic-Bridge erfolgreich gebaut: $OUTPUT ($ARCH)"
echo "Upstream: $REPO"
echo "Commit: $COMMIT"
