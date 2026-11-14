#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="https://github.com/dbehnke/md380_vocoder_dynarmic.git"
COMMIT="55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5"
VENDOR_ROOT="$SCRIPT_DIR/vendor"
SOURCE_DIR="$VENDOR_ROOT/md380_vocoder_dynarmic"
CMAKE_PROJECT="$SCRIPT_DIR/md380_dynarmic_build"
BUILD_DIR="$CMAKE_PROJECT/out-macos"
OUTPUT="$SCRIPT_DIR/libcarendmr_md380_bridge.dylib"

if [ ! -f "$CMAKE_PROJECT/CMakeLists.txt" ]; then
    echo "CarenDMR-CMake-Wrapper fehlt: $CMAKE_PROJECT/CMakeLists.txt" >&2
    echo "Das Projektpaket ist unvollständig; bitte nicht auf Verdacht weitere Pakete installieren." >&2
    exit 1
fi

# Ab 0.2.1.89 ohne eingebaute Firmware: unzip, xxd und python3 entfallen.
for tool in git cmake sh; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Fehlendes Werkzeug: $tool" >&2
        exit 1
    fi
done

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
mkdir -p "$BUILD_DIR"

cmake -S "$CMAKE_PROJECT" -B "$BUILD_DIR" \
    -DMD380_SOURCE_DIR="$SOURCE_DIR" \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "$BUILD_DIR" --config Release -j"$(sysctl -n hw.ncpu)"

CANDIDATE="$(find "$BUILD_DIR" -type f -name 'libcarendmr_md380_bridge.dylib' -print -quit)"
if [ -z "$CANDIDATE" ]; then
    echo "libcarendmr_md380_bridge.dylib wurde nach dem Build nicht gefunden." >&2
    exit 1
fi

cp "$CANDIDATE" "$OUTPUT"
if ! grep -q carendmr_md380_init_files "$OUTPUT"; then
    echo "Die gebaute Bridge kennt carendmr_md380_init_files nicht." >&2
    exit 1
fi
echo "MD380-Dynarmic-Bridge erfolgreich gebaut: $OUTPUT"
echo "Upstream: $REPO"
echo "Commit: $COMMIT"
