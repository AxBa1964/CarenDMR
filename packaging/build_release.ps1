# Baut die CarenDMR-Exe (PyInstaller) und den Installer (Inno Setup).
#
# Aufruf aus dem Projektordner:
#   .\packaging\build_release.ps1
#
# Für einen privaten Testbuild mit der alten Bridge (Firmware eingebaut):
#   .\packaging\build_release.ps1 -AllowEmbeddedFirmware
# Solche Builds NICHT veröffentlichen.

param(
    [switch]$AllowEmbeddedFirmware,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtuelle Umgebung .venv nicht gefunden. Bitte zuerst einrichten (siehe INSTALL_WINDOWS.md)."
}

& $python -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller fehlt. Einmalig installieren mit: .\.venv\Scripts\python.exe -m pip install pyinstaller"
}

$version = (& $python -c "from carendmr.version import __version__; print(__version__)").Trim()
Write-Host "CarenDMR-Version: $version"

# --- Prüfung: keine Firmware im öffentlichen Build -----------------------
$bridge = Join-Path $root "native\carendmr_md380_bridge.dll"
if (-not (Test-Path $bridge)) {
    throw "native\carendmr_md380_bridge.dll fehlt. Ohne Bridge gibt es keinen Sprach-Codec."
}
$bridgeText = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($bridge))
$loadsAtRuntime = $bridgeText.Contains("carendmr_md380_init_files")
if (-not $loadsAtRuntime) {
    if ($AllowEmbeddedFirmware) {
        Write-Warning "Die Bridge enthält die MD380-Firmware. Dieser Build ist nur für private Tests und darf nicht veröffentlicht werden."
    } else {
        throw "Die Bridge enthält noch die MD380-Firmware (alte Bauart). Für einen öffentlichen Build muss zuerst die neue Bridge gebaut werden. Privater Testbuild: -AllowEmbeddedFirmware"
    }
}

# --- Laufzeit-DLLs passend zur Bridge -------------------------------------
# Die Bridge braucht libstdc++-6, libgcc_s_seh-1 und libwinpthread-1 aus
# derselben MSYS2-Installation, mit der sie gebaut wurde (objdump -p).
$runtimeNames = @("libstdc++-6.dll", "libgcc_s_seh-1.dll", "libwinpthread-1.dll")
$msysBin = "C:\msys64\ucrt64\bin"
foreach ($name in $runtimeNames) {
    $source = Join-Path $msysBin $name
    $target = Join-Path $root "native\$name"
    if (Test-Path $source) {
        Copy-Item $source $target -Force
        Write-Host "Laufzeit-DLL aus MSYS2 übernommen: $name"
    } elseif (Test-Path $target) {
        Write-Warning "MSYS2 nicht gefunden; verwende vorhandene native\$name. Sie muss zur Bridge passen."
    } else {
        throw "Laufzeit-DLL $name fehlt (weder in $msysBin noch in native\)."
    }
}

# --- Exe bauen ------------------------------------------------------------
$dist = Join-Path $root "release\dist"
$work = Join-Path $root "release\build"
& $python -m PyInstaller --noconfirm --clean --distpath $dist --workpath $work (Join-Path $root "packaging\CarenDMR.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller ist fehlgeschlagen." }

$exe = Join-Path $dist "CarenDMR\CarenDMR.exe"
if (-not (Test-Path $exe)) { throw "CarenDMR.exe wurde nicht erzeugt." }
Write-Host "Exe gebaut: $exe"

if ($SkipInstaller) { return }

# --- Installer bauen ------------------------------------------------------
$iscc = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 (ISCC.exe) wurde nicht gefunden. Bitte Inno Setup 6.3 oder neuer installieren oder mit -SkipInstaller nur die Exe bauen."
}

& $iscc "/DAppVersion=$version" "/DSourceDir=$(Join-Path $dist 'CarenDMR')" (Join-Path $root "packaging\CarenDMR.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup ist fehlgeschlagen." }

$setup = Join-Path $root "release\installer\CarenDMR-Setup-$version.exe"
Write-Host "Installer gebaut: $setup"
$hash = (Get-FileHash -Algorithm SHA256 $setup).Hash
Write-Host "SHA-256: $hash"
