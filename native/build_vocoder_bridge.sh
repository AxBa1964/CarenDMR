#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
case "$(uname -s)" in
  Darwin) out="libcarendmr_vocoder_bridge.dylib"; g++ -dynamiclib -O2 -std=c++17 vocoder_plugin_bridge.cpp -o "$out" ;;
  *) out="libcarendmr_vocoder_bridge.so"; g++ -shared -fPIC -O2 -std=c++17 vocoder_plugin_bridge.cpp -ldl -o "$out" ;;
esac
echo "Vocoder-Bridge erfolgreich gebaut: $out"
