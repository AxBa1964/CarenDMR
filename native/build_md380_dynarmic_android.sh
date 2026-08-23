#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NATIVE_DIR="$ROOT_DIR/native"

ANDROID_SDK_ROOT="${ANDROID_SDK_ROOT:-$HOME/Android/Sdk}"
NDK_VERSION="${NDK_VERSION:-27.2.12479018}"
ANDROID_ABI="${ANDROID_ABI:-arm64-v8a}"
ANDROID_PLATFORM="${ANDROID_PLATFORM:-android-24}"

MD380_REPO="https://github.com/dbehnke/md380_vocoder_dynarmic.git"
MD380_COMMIT="55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5"

BOOST_VERSION="1.83.0"
BOOST_ARCHIVE="boost_1_83_0.tar.gz"
BOOST_DIRNAME="boost_1_83_0"
BOOST_URL="https://archives.boost.io/release/${BOOST_VERSION}/source/${BOOST_ARCHIVE}"

VENDOR_DIR="$NATIVE_DIR/vendor"
MD380_DIR="$VENDOR_DIR/md380_vocoder_dynarmic"
BOOST_ROOT="$VENDOR_DIR/boost"
BOOST_DIR="$BOOST_ROOT/$BOOST_DIRNAME"

BUILD_DIR="$NATIVE_DIR/md380_dynarmic_build/out-android-arm64"
TOOLCHAIN="$ANDROID_SDK_ROOT/ndk/$NDK_VERSION/build/cmake/android.toolchain.cmake"

echo "CarenDMR MD380 Android ARM64 Build"
echo "--------------------------------"
echo "SDK       : $ANDROID_SDK_ROOT"
echo "NDK       : $NDK_VERSION"
echo "ABI       : $ANDROID_ABI"
echo "Platform  : $ANDROID_PLATFORM"

if [[ ! -f "$TOOLCHAIN" ]]; then
    echo "Fehler: Android-NDK-Toolchain nicht gefunden:"
    echo "$TOOLCHAIN"
    exit 1
fi

mkdir -p "$VENDOR_DIR"

if [[ ! -d "$MD380_DIR/.git" ]]; then
    git clone "$MD380_REPO" "$MD380_DIR"
fi

git -C "$MD380_DIR" fetch --all --tags
git -C "$MD380_DIR" checkout --detach "$MD380_COMMIT"

MD380_CMAKE="$MD380_DIR/CMakeLists.txt"
BAD_LINE='target_link_libraries(md380_vocoder STATIC dynarmic)'
GOOD_LINE='target_link_libraries(md380_vocoder PRIVATE dynarmic)'

if grep -Fq "$BAD_LINE" "$MD380_CMAKE"; then
    sed -i "s/${BAD_LINE}/${GOOD_LINE}/" "$MD380_CMAKE"
elif ! grep -Fq "$GOOD_LINE" "$MD380_CMAKE"; then
    echo "Fehler: erwartete md380_vocoder-Linkzeile nicht gefunden."
    exit 1
fi

if [[ ! -f "$BOOST_DIR/boost/variant.hpp" ]]; then
    mkdir -p "$BOOST_ROOT"
    cd "$BOOST_ROOT"

    if [[ ! -f "$BOOST_ARCHIVE" ]]; then
        wget "$BOOST_URL"
    fi

    tar -xzf "$BOOST_ARCHIVE"
fi

rm -rf "$BUILD_DIR"

cmake \
    -S "$NATIVE_DIR/md380_dynarmic_build" \
    -B "$BUILD_DIR" \
    -G Ninja \
    -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN" \
    -DANDROID_ABI="$ANDROID_ABI" \
    -DANDROID_PLATFORM="$ANDROID_PLATFORM" \
    -DMD380_SOURCE_DIR="$MD380_DIR" \
    -DBoost_INCLUDE_DIR="$BOOST_DIR" \
    -DCMAKE_CXX_FLAGS="-I$BOOST_DIR" \
    -DCMAKE_BUILD_TYPE=Release

cmake --build "$BUILD_DIR"

OUTPUT="$BUILD_DIR/libcarendmr_md380_bridge.so"

if [[ ! -f "$OUTPUT" ]]; then
    echo "Fehler: Android-Bridge wurde nicht erzeugt."
    exit 1
fi

echo
echo "Erfolgreich gebaut:"
file "$OUTPUT"
echo "$OUTPUT"
