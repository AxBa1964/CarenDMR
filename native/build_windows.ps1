[CmdletBinding()]
param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$NativeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DecoderOutput = Join-Path $NativeDir 'carendmr_mbe.dll'
$BridgeOutput = Join-Path $NativeDir 'carendmr_vocoder_bridge.dll'

$gccFromPath = Get-Command gcc.exe -ErrorAction SilentlyContinue
$gccCandidates = @(
    if ($gccFromPath) { $gccFromPath.Source }
    'C:\msys64\ucrt64\bin\gcc.exe'
    'C:\msys64\mingw64\bin\gcc.exe'
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique

$gcc = @($gccCandidates)[0]
if (-not $gcc) {
    throw @'
Kein geeigneter GCC-Compiler gefunden.
Installiere MSYS2 und öffne danach "MSYS2 UCRT64". Führe dort aus:
  pacman -Syu
  pacman -S --needed mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-binutils
Danach dieses Skript erneut starten.
'@
}

$compilerDir = Split-Path -Parent $gcc
$env:Path = "$compilerDir;C:\msys64\usr\bin;$env:Path"
$objdump = Join-Path $compilerDir 'objdump.exe'
$gpp = Join-Path $compilerDir 'g++.exe'

if (-not $CheckOnly) {
    $sources = @(
        (Join-Path $NativeDir 'carendmr_mbe.c')
        (Join-Path $NativeDir 'mbelib\ambe3600x2450.c')
        (Join-Path $NativeDir 'mbelib\ecc.c')
        (Join-Path $NativeDir 'mbelib\mbelib.c')
    )

    $arguments = @(
        '-std=c11', '-O2', '-Wall', '-Wextra',
        '-shared', '-D_GNU_SOURCE', '-D_DEFAULT_SOURCE', '-static-libgcc',
        ('-I' + $NativeDir),
        ('-I' + (Join-Path $NativeDir 'mbelib'))
    ) + $sources + @('-lm', '-o', $DecoderOutput)

    Write-Host "Baue nativen Empfangsdecoder mit $gcc"
    & $gcc @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Der native Windows-Decoder konnte nicht gebaut werden.'
    }

    if (-not (Test-Path -LiteralPath $gpp)) {
        throw "g++.exe wurde neben gcc.exe nicht gefunden: $gpp"
    }
    $bridgeSource = Join-Path $NativeDir 'vocoder_plugin_bridge.cpp'
    $bridgeArgs = @(
        '-shared', '-O2', '-std=c++17', '-static', '-static-libgcc', '-static-libstdc++',
        $bridgeSource, '-o', $BridgeOutput
    )
    Write-Host "Baue DroidStar-Vocoder-Bridge mit $gpp"
    & $gpp @bridgeArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'Die Windows-Vocoder-Bridge konnte nicht gebaut werden.'
    }
}

if (-not (Test-Path -LiteralPath $DecoderOutput)) {
    throw "Die erwartete Decoder-DLL fehlt: $DecoderOutput"
}
if (-not (Test-Path -LiteralPath $BridgeOutput)) {
    throw "Die erwartete Vocoder-Bridge fehlt: $BridgeOutput"
}
if (-not (Test-Path -LiteralPath $objdump)) {
    throw "objdump.exe wurde neben dem Compiler nicht gefunden: $objdump"
}

$decoderExports = & $objdump -p $DecoderOutput | Select-String 'carendmr_mbe_' | ForEach-Object {
    if ($_.Line -match '(carendmr_mbe_[A-Za-z0-9_]+)') { $Matches[1] }
} | Sort-Object -Unique
$expectedDecoder = @('carendmr_mbe_decode','carendmr_mbe_decoder_create','carendmr_mbe_decoder_destroy')
if (@($decoderExports).Count -ne 3 -or (Compare-Object $expectedDecoder $decoderExports)) {
    throw "Unerwartete Decoder-DLL-Exporte: $($decoderExports -join ', ')"
}

$bridgeExports = & $objdump -p $BridgeOutput | Select-String 'carendmr_vocoder_' | ForEach-Object {
    if ($_.Line -match '(carendmr_vocoder_[A-Za-z0-9_]+)') { $Matches[1] }
} | Sort-Object -Unique
$expectedBridge = @(
    'carendmr_vocoder_close',
    'carendmr_vocoder_decode_2450x1150',
    'carendmr_vocoder_encode_2450x1150',
    'carendmr_vocoder_last_error',
    'carendmr_vocoder_open'
)
$missing = Compare-Object $expectedBridge $bridgeExports | Where-Object SideIndicator -eq '<='
if ($missing) {
    throw "Vocoder-Bridge enthält nicht alle erwarteten Exporte: $($bridgeExports -join ', ')"
}

$dependencies = & $objdump -p $BridgeOutput | Select-String 'DLL Name'
if ($dependencies -match 'libwinpthread-1.dll|libgcc_s|libstdc\+\+') {
    throw "Die Bridge besitzt noch unerwünschte MSYS2-Laufzeitabhängigkeiten: $dependencies"
}

Write-Host 'Windows-Decoder und Vocoder-Bridge erfolgreich gebaut und geprüft.'
Write-Host "Decoder: $DecoderOutput"
Write-Host "Bridge : $BridgeOutput"
