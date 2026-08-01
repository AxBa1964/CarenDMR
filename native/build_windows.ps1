[CmdletBinding()]
param(
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$NativeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Output = Join-Path $NativeDir 'carendmr_mbe.dll'

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
    ) + $sources + @('-lm', '-o', $Output)

    Write-Host "Baue nativen Empfangsdecoder mit $gcc"
    & $gcc @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Der native Windows-Decoder konnte nicht gebaut werden.'
    }
}

if (-not (Test-Path -LiteralPath $Output)) {
    throw "Die erwartete DLL fehlt: $Output"
}
if (-not (Test-Path -LiteralPath $objdump)) {
    throw "objdump.exe wurde neben dem Compiler nicht gefunden: $objdump"
}

$exports = & $objdump -p $Output | Select-String 'carendmr_mbe_' | ForEach-Object {
    if ($_.Line -match '(carendmr_mbe_[A-Za-z0-9_]+)') { $Matches[1] }
} | Sort-Object -Unique

$expected = @(
    'carendmr_mbe_decode'
    'carendmr_mbe_decoder_create'
    'carendmr_mbe_decoder_destroy'
)

if (@($exports).Count -ne 3 -or (Compare-Object $expected $exports)) {
    throw "Unerwartete DLL-Exporte: $($exports -join ', ')"
}
if ($exports | Where-Object { $_ -match 'encode' }) {
    throw 'Die reine Empfangsbibliothek darf keine Encoderfunktion exportieren.'
}

Write-Host 'Windows-Decoder erfolgreich gebaut und geprüft.'
Write-Host "DLL: $Output"
