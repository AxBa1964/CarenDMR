$ErrorActionPreference = "Stop"
$compiler = "C:\msys64\ucrt64\bin\g++.exe"
$env:PATH = "C:\msys64\ucrt64\bin;$env:PATH"
if (-not (Test-Path $compiler)) {
    throw "Kein MSYS2-UCRT64-g++ gefunden. Installiere mingw-w64-ucrt-x86_64-gcc."
}
$output = Join-Path $PSScriptRoot "carendmr_vocoder_bridge.dll"
$source = Join-Path $PSScriptRoot "vocoder_plugin_bridge.cpp"

# Statisch linken, damit insbesondere libwinpthread-1.dll nicht separat benötigt wird.
& $compiler -shared -O2 -std=c++17 -static -static-libgcc -static-libstdc++ `
    $source -o $output
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $output)) {
    throw "Die Windows-Vocoder-Bridge konnte nicht gebaut werden."
}

$dependencies = & "C:\msys64\ucrt64\bin\objdump.exe" -p $output |
    Select-String "DLL Name"
if ($dependencies -match "libwinpthread-1.dll|libgcc_s|libstdc\+\+") {
    throw "Die Bridge besitzt noch unerwünschte MSYS2-Laufzeitabhängigkeiten: $dependencies"
}

Write-Host "Vocoder-Bridge erfolgreich gebaut und geprüft: $output"
Write-Host "Hinweis: Das externe DroidStar-Plugin wird nicht mit CarenDMR ausgeliefert."
