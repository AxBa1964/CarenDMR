$ErrorActionPreference = "Stop"

$repo = "https://github.com/dbehnke/md380_vocoder_dynarmic.git"
$commit = "55c9a2c6d502567380c7dfaf4a2e3cc4dd6d1dd5"
$vendorRoot = Join-Path $PSScriptRoot "vendor"
$sourceDir = Join-Path $vendorRoot "md380_vocoder_dynarmic"
$buildDir = Join-Path $PSScriptRoot "md380_dynarmic_build\out"
$output = Join-Path $PSScriptRoot "carendmr_md380_bridge.dll"

$msysUsr = "C:\msys64\usr\bin"
$msysCorePerl = "C:\msys64\usr\bin\core_perl"
$msysUcrt = "C:\msys64\ucrt64\bin"
$cmake = Join-Path $msysUcrt "cmake.exe"
$ninja = Join-Path $msysUcrt "ninja.exe"
$git = Join-Path $msysUsr "git.exe"
$sh = Join-Path $msysUsr "sh.exe"
# Ab 0.2.1.89 wird die Firmware nicht mehr eingebaut; unzip, xxd und
# python3 (Firmware-Download des Upstream-Builds) werden nicht mehr gebraucht.
$required = @($cmake, $ninja, $git, $sh)
$missing = $required | Where-Object { -not (Test-Path $_) }
if ($missing.Count -gt 0) {
    Write-Host "Fehlende MSYS2-Bausteine:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  $_" }
    throw "MD380-Dynarmic kann noch nicht gebaut werden. Bitte die Fehlermeldung vollständig zurückmelden; keine Pakete auf Verdacht installieren."
}

$env:PATH = "$msysUcrt;$msysUsr;$msysCorePerl;$env:PATH"
$env:CMAKE_POLICY_VERSION_MINIMUM = "3.5"
New-Item -ItemType Directory -Force -Path $vendorRoot | Out-Null

if (-not (Test-Path (Join-Path $sourceDir ".git"))) {
    & $git clone $repo $sourceDir
    if ($LASTEXITCODE -ne 0) { throw "MD380-Dynarmic konnte nicht geklont werden." }
}

Push-Location $sourceDir
try {
    & $git fetch --all --tags
    if ($LASTEXITCODE -ne 0) { throw "MD380-Dynarmic konnte nicht aktualisiert werden." }
    & $git checkout --detach $commit
    if ($LASTEXITCODE -ne 0) { throw "Der festgelegte MD380-Dynarmic-Commit konnte nicht ausgecheckt werden." }
} finally {
    Pop-Location
}

# Der Upstream-CMake-Build wird nicht mehr verwendet (er lädt die Firmware
# herunter und baut sie ein). md380_dynarmic_build\CMakeLists.txt übersetzt
# nur md380_vocoder.cpp; die Firmware lädt CarenDMR zur Laufzeit.
if (-not (Test-Path (Join-Path $sourceDir "md380_vocoder.cpp"))) {
    throw "md380_vocoder.cpp fehlt im Upstream-Quellordner."
}

if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null
$cmakeProject = Join-Path $PSScriptRoot "md380_dynarmic_build"

& $cmake -S $cmakeProject -B $buildDir -G Ninja -DMD380_SOURCE_DIR="$sourceDir" -DCMAKE_BUILD_TYPE=Release
if ($LASTEXITCODE -ne 0) {
    throw "CMake-Konfiguration für MD380-Dynarmic fehlgeschlagen. Die konkrete Fehlermeldung darüber ist maßgeblich."
}

& $cmake --build $buildDir --config Release
if ($LASTEXITCODE -ne 0) { throw "MD380-Dynarmic-Build fehlgeschlagen." }

# Je nach Toolchain mit oder ohne "lib"-Vorsilbe.
$candidates = @(Get-ChildItem -Path $buildDir -Recurse -Filter "*carendmr_md380_bridge.dll")
if ($candidates.Count -lt 1) { throw "carendmr_md380_bridge.dll wurde nach dem Build nicht gefunden." }
Copy-Item $candidates[0].FullName $output -Force

$bridgeText = [System.Text.Encoding]::ASCII.GetString([System.IO.File]::ReadAllBytes($output))
if (-not $bridgeText.Contains("carendmr_md380_init_files")) {
    throw "Die gebaute Bridge kennt carendmr_md380_init_files nicht."
}
Write-Host "Bridge ohne eingebaute Firmware: Codec-Dateien richtet CarenDMR beim Start ein."

Write-Host "MD380-Dynarmic-Bridge erfolgreich gebaut: $output"
Write-Host "Upstream: $repo"
Write-Host "Commit: $commit"
