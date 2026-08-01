<#
.SYNOPSIS
    Erstellt eine geprüfte vollständige SmartHomeLab-Projekt-ZIP.

.DESCRIPTION
    - liest die Version aus core/version.py
    - bricht bei jedem Fehler sofort ab
    - verlangt einen sauberen Git-Arbeitsstand
    - archiviert ausschließlich Dateien des aktuellen Git-Commits
    - erzeugt zunächst eine temporäre ZIP
    - prüft ZIP, Dateianzahl und ausgeschlossene Inhalte
    - hinterlässt bei Fehlern keine unvollständige ZIP
    - erstellt SmartHomeLab_<Version>.zip standardmäßig oberhalb des Projekts

.AUSFÜHRUNG
    Im SmartHomeLab-Projektverzeichnis:

        .\tools\create_project_zip.ps1

    Optional Zielordner angeben:

        .\tools\create_project_zip.ps1 -OutputDirectory "C:\Temp"

    Optional Zielordner nach Erfolg öffnen:

        .\tools\create_project_zip.ps1 -OpenFolder
#>

[CmdletBinding()]
param(
    [string]$ProjectPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$OutputDirectory,
    [switch]$OpenFolder
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:CurrentStep = 0
$script:TotalSteps = 9
$script:TemporaryArchivePath = $null
$script:FinalArchivePath = $null
$script:FinalArchiveCreated = $false
$script:LocationPushed = $false

function Write-Separator {
    Write-Host ("=" * 68)
}

function Write-StepStart {
    param([string]$Text)

    $script:CurrentStep++
    Write-Host ("[{0}/{1}] {2} ..." -f $script:CurrentStep, $script:TotalSteps, $Text) -NoNewline
}

function Write-StepOk {
    Write-Host " OK" -ForegroundColor Green
}

function Remove-PartialArchives {
    foreach ($Path in @($script:TemporaryArchivePath)) {
        if ($Path -and (Test-Path -LiteralPath $Path)) {
            Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        }
    }

    if ($script:FinalArchiveCreated -and
        $script:FinalArchivePath -and
        (Test-Path -LiteralPath $script:FinalArchivePath)) {
        Remove-Item -LiteralPath $script:FinalArchivePath -Force -ErrorAction SilentlyContinue
    }
}

function Stop-Tool {
    param(
        [string]$Step,
        [string]$Message,
        [string[]]$Details
    )

    Write-Host " FEHLER" -ForegroundColor Red
    Write-Host ""
    Write-Host "Schritt: $Step" -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red

    if ($Details -and $Details.Count -gt 0) {
        Write-Host ""
        $Details | ForEach-Object { Write-Host "  $_" }
    }

    Remove-PartialArchives

    Write-Host ""
    Write-Separator
    Write-Host "ABBRUCH" -ForegroundColor Red
    Write-Separator
    exit 1
}

function Invoke-Git {
    param([string[]]$Arguments)

    $Output = @(& git @Arguments 2>&1)
    $ExitCode = $LASTEXITCODE

    return [pscustomobject]@{
        ExitCode = $ExitCode
        Output   = $Output
    }
}

try {
    Write-Host ""
    Write-Separator
    Write-Host " SmartHomeLab - Projekt-ZIP"
    Write-Separator
    Write-Host ""

    Write-StepStart "Projektverzeichnis prüfen"
    if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {
        Stop-Tool "Projektverzeichnis prüfen" "Das Projektverzeichnis wurde nicht gefunden." @($ProjectPath)
    }
    $ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
    Write-StepOk

    Write-StepStart "Git-Verfügbarkeit prüfen"
    $GitCommand = Get-Command git -ErrorAction SilentlyContinue
    if (-not $GitCommand) {
        Stop-Tool "Git-Verfügbarkeit prüfen" "Git wurde nicht gefunden oder ist nicht über PATH erreichbar." @()
    }
    $GitVersion = Invoke-Git @("--version")
    if ($GitVersion.ExitCode -ne 0) {
        Stop-Tool "Git-Verfügbarkeit prüfen" "Git konnte nicht ausgeführt werden." $GitVersion.Output
    }
    Write-StepOk

    Push-Location $ProjectPath
    $script:LocationPushed = $true

    Write-StepStart "Git-Repository prüfen"
    $RepoCheck = Invoke-Git @("rev-parse", "--is-inside-work-tree")
    if ($RepoCheck.ExitCode -ne 0 -or
        $RepoCheck.Output.Count -eq 0 -or
        ($RepoCheck.Output[0].ToString().Trim() -ne "true")) {
        Stop-Tool "Git-Repository prüfen" "Das Projektverzeichnis ist kein gültiges Git-Repository." $RepoCheck.Output
    }
    Write-StepOk

    Write-StepStart "Arbeitsstand prüfen"
    $GitStatus = Invoke-Git @("status", "--porcelain")
    if ($GitStatus.ExitCode -ne 0) {
        Stop-Tool "Arbeitsstand prüfen" "git status konnte nicht ausgeführt werden." $GitStatus.Output
    }
    if ($GitStatus.Output.Count -gt 0) {
        Stop-Tool `
            "Arbeitsstand prüfen" `
            "Der Git-Arbeitsstand ist nicht sauber. Bitte Änderungen zuerst committen oder zurücksetzen." `
            $GitStatus.Output
    }
    Write-StepOk

    Write-StepStart "Version und Git-Daten lesen"
    $VersionFile = Join-Path $ProjectPath "core\version.py"
    if (-not (Test-Path -LiteralPath $VersionFile -PathType Leaf)) {
        Stop-Tool "Version und Git-Daten lesen" "core\version.py wurde nicht gefunden." @($VersionFile)
    }

    $VersionText = Get-Content -LiteralPath $VersionFile -Raw
    $VersionMatch = [regex]::Match(
        $VersionText,
        '(?m)^\s*VERSION\s*=\s*["'']([^"'']+)["'']'
    )
    if (-not $VersionMatch.Success) {
        Stop-Tool "Version und Git-Daten lesen" "Die Versionsnummer konnte nicht gelesen werden." @($VersionFile)
    }

    $Version = $VersionMatch.Groups[1].Value.Trim()
    if ([string]::IsNullOrWhiteSpace($Version)) {
        Stop-Tool "Version und Git-Daten lesen" "Die Versionsnummer ist leer." @($VersionFile)
    }

    if ($Version -notmatch '^[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9]+)*$') {
        Stop-Tool "Version und Git-Daten lesen" "Die Versionsnummer hat kein zulässiges Format." @($Version)
    }

    $BranchResult = Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD")
    if ($BranchResult.ExitCode -ne 0 -or $BranchResult.Output.Count -eq 0) {
        Stop-Tool "Version und Git-Daten lesen" "Der Git-Branch konnte nicht gelesen werden." $BranchResult.Output
    }
    $Branch = $BranchResult.Output[0].ToString().Trim()

    $CommitResult = Invoke-Git @("rev-parse", "--short=8", "HEAD")
    if ($CommitResult.ExitCode -ne 0 -or $CommitResult.Output.Count -eq 0) {
        Stop-Tool "Version und Git-Daten lesen" "Der Git-Commit konnte nicht gelesen werden." $CommitResult.Output
    }
    $Commit = $CommitResult.Output[0].ToString().Trim()
    Write-StepOk

    Write-StepStart "Zielpfad vorbereiten"
    if (-not $OutputDirectory) {
        $OutputDirectory = Split-Path $ProjectPath -Parent
    }

    if (-not (Test-Path -LiteralPath $OutputDirectory)) {
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    }

    if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
        Stop-Tool "Zielpfad vorbereiten" "Der Zielordner ist ungültig." @($OutputDirectory)
    }

    $OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path
    $ArchiveName = "SmartHomeLab_$Version.zip"
    $script:FinalArchivePath = Join-Path $OutputDirectory $ArchiveName
    $script:TemporaryArchivePath = Join-Path $OutputDirectory (
        ".SmartHomeLab_{0}_{1}.tmp.zip" -f $Version, [guid]::NewGuid().ToString("N")
    )

    if (Test-Path -LiteralPath $script:TemporaryArchivePath) {
        Remove-Item -LiteralPath $script:TemporaryArchivePath -Force
    }
    Write-StepOk

    Write-StepStart "Projektdateien archivieren"
    $ArchiveResult = Invoke-Git @(
        "archive",
        "--format=zip",
        "--output=$($script:TemporaryArchivePath)",
        "HEAD"
    )
    if ($ArchiveResult.ExitCode -ne 0) {
        Stop-Tool "Projektdateien archivieren" "git archive ist fehlgeschlagen." $ArchiveResult.Output
    }
    if (-not (Test-Path -LiteralPath $script:TemporaryArchivePath -PathType Leaf)) {
        Stop-Tool "Projektdateien archivieren" "Die temporäre ZIP wurde nicht erzeugt." @()
    }
    $TemporaryInfo = Get-Item -LiteralPath $script:TemporaryArchivePath
    if ($TemporaryInfo.Length -le 0) {
        Stop-Tool "Projektdateien archivieren" "Die temporäre ZIP ist leer." @()
    }
    Write-StepOk

    Write-StepStart "ZIP-Inhalt prüfen"
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    $Zip = $null
    try {
        $Zip = [System.IO.Compression.ZipFile]::OpenRead($script:TemporaryArchivePath)
        $Entries = @($Zip.Entries)

        if ($Entries.Count -eq 0) {
            Stop-Tool "ZIP-Inhalt prüfen" "Die ZIP enthält keine Dateien." @()
        }

        $RequiredEntries = @(
            "core/version.py",
            "main.py",
            "DEPLOY.md"
        )
        $EntryNames = @($Entries | ForEach-Object { $_.FullName.Replace("\", "/") })

        $MissingRequired = @(
            $RequiredEntries | Where-Object { $_ -notin $EntryNames }
        )
        if ($MissingRequired.Count -gt 0) {
            Stop-Tool "ZIP-Inhalt prüfen" "Pflichtdateien fehlen in der ZIP." $MissingRequired
        }

        $ForbiddenPatterns = @(
            '(^|/)\.git(/|$)',
            '(^|/)__pycache__(/|$)',
            '\.pyc$',
            '\.pyo$',
            '(^|/)logs?(/|$)',
            '(^|/)data/history(/|$)',
            '(^|/)backup[^/]*/',
            '\.zip$'
        )

        $ForbiddenEntries = @()
        foreach ($EntryName in $EntryNames) {
            foreach ($Pattern in $ForbiddenPatterns) {
                if ($EntryName -match $Pattern) {
                    $ForbiddenEntries += $EntryName
                    break
                }
            }
        }

        if ($ForbiddenEntries.Count -gt 0) {
            Stop-Tool "ZIP-Inhalt prüfen" "Unzulässige Dateien wurden in der ZIP gefunden." $ForbiddenEntries
        }

        $FileCount = @($Entries | Where-Object { -not $_.FullName.EndsWith("/") }).Count
    }
    catch {
        Stop-Tool "ZIP-Inhalt prüfen" "Die ZIP konnte nicht vollständig geprüft werden." @($_.Exception.Message)
    }
    finally {
        if ($Zip) {
            $Zip.Dispose()
        }
    }
    Write-StepOk

    Write-StepStart "ZIP endgültig bereitstellen"
    if (Test-Path -LiteralPath $script:FinalArchivePath) {
        Remove-Item -LiteralPath $script:FinalArchivePath -Force
    }

    Move-Item `
        -LiteralPath $script:TemporaryArchivePath `
        -Destination $script:FinalArchivePath

    $script:TemporaryArchivePath = $null
    $script:FinalArchiveCreated = $true

    if (-not (Test-Path -LiteralPath $script:FinalArchivePath -PathType Leaf)) {
        Stop-Tool "ZIP endgültig bereitstellen" "Die endgültige ZIP wurde nicht gefunden." @()
    }
    Write-StepOk

    $ArchiveInfo = Get-Item -LiteralPath $script:FinalArchivePath
    $SizeMB = [math]::Round($ArchiveInfo.Length / 1MB, 2)

    Write-Host ""
    Write-Separator
    Write-Host "Projekt-ZIP erfolgreich erstellt." -ForegroundColor Green
    Write-Separator
    Write-Host ""
    Write-Host ("Version : {0}" -f $Version)
    Write-Host ("Branch  : {0}" -f $Branch)
    Write-Host ("Commit  : {0}" -f $Commit)
    Write-Host ("Dateien : {0}" -f $FileCount)
    Write-Host ("Größe   : {0:N2} MB" -f $SizeMB)
    Write-Host ""
    Write-Host "Erstellt:"
    Write-Host $ArchiveInfo.FullName
    Write-Host ""

    if ($OpenFolder) {
        Start-Process explorer.exe -ArgumentList "/select,`"$($ArchiveInfo.FullName)`""
    }

    exit 0
}
catch {
    if ($script:CurrentStep -eq 0) {
        $script:CurrentStep = 1
    }

    Write-Host " FEHLER" -ForegroundColor Red
    Write-Host ""
    Write-Host "Unerwarteter Fehler:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red

    Remove-PartialArchives

    Write-Host ""
    Write-Separator
    Write-Host "ABBRUCH" -ForegroundColor Red
    Write-Separator
    exit 1
}
finally {
    if ($script:LocationPushed) {
        Pop-Location
    }
}
