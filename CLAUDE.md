# CLAUDE.md – CarenDMR

Projektwissen für Claude Code. Der offene Stand und die nächsten Schritte stehen in
`docs/offene-punkte.md` – das ist die einzige Quelle für den Projektstand.

## Zweck

Barrierefreier DMR-Desktop-Client für BrandMeister (Homebrew/MMDVM-Protokoll),
entwickelt für die blinde Funkamateurin Caren. Screenreader- und Tastaturbedienung
sind verbindliche Abnahmebedingung (ADR-0014). Zwei Oberflächen: normales
Hauptfenster (99 % der Nutzer) und CarenDMR Easy (reduziert, für Blinde).

- Autor: Axel Baruschke, DK7EE
- Repo: github.com/AxBa1964/CarenDMR · Lizenz GPLv3
- Lokal: `C:\ABDevelop\CarenDMR` (Hauptrechner und Shack-PC)
- Projektseite mit Download: https://dk7ee.de/carendmr.html
- Plattformen: Windows 11 (Python 3.12), macOS Intel (Python 3.13)

## Arbeitsregeln (verbindlich)

- **Niemals raten** – Menüpfade, Einstellungen, Fakten erst prüfen oder klar sagen,
  dass es unbekannt ist.
- **Erst umsetzen, wenn der Nutzer „jetzt umsetzen“ schreibt.** Bis dahin Wünsche
  sammeln (in `docs/offene-punkte.md`).
- Pro umgesetztem Schritt eine neue Version (0.2.1.x) mit CHANGELOG-Eintrag,
  `RELEASE_INFO.md` und Tests.
- Befehle für den Nutzer immer in eigenem Codeblock, PowerShell, mit `cd` vorweg,
  Skripte mit `.\`:
  ```powershell
  cd C:\ABDevelop\CarenDMR
  .\start_gui.bat
  ```
- Aufwendige Bilder liefert der Nutzer selbst; Claude sagt, welches Bild gebraucht wird.
- Antworten auf Deutsch.

## Sicherheit

- Zugangsdaten nur in `*.local.json` (gitignored). Kopien von Zugangsdateien immer
  auf `.local.json` enden lassen.
- `brandmeister.local.json` (Passwort) nicht öffnen oder ausgeben; Ausgaben nur mit
  `Select-Object -ExcludeProperty password`.
- `firmware/` (MD380-Firmware) niemals einchecken. Keine DLL mit eingebauter
  Firmware ins Repo oder in Builds (Build verweigert das außer mit
  `-AllowEmbeddedFirmware`).

## Start und Tests

```text
python main.py --gui          Hauptfenster
python main.py --easy         Easy-Oberfläche
python main.py --tg-monitor   TG-Monitor (auch tg_monitor.py)
python main.py --listen       Konsolen-Empfang
```

Windows: `.\start_gui.bat`, `.\start_easy.bat` (nutzen `.venv\Scripts\python.exe`).

Tests **immer** mit `python -m pytest tests` (viele Tests sind einfache
`test_…`-Funktionen). Quelltext-Tests des Hauptfensters über
`tests/_ui_sources.py` → `main_window_source()`. Shack-PC (N100) ca. 2 Minuten.

## Architektur (siehe docs/ARCHITECTURE.md, docs/DECISIONS.md)

Oberflächen → `bootstrap.py` → Application-Services → Domain →
BrandMeister/Netzwerk/Audio/Vocoder.

- `carendmr/application/` ist Qt-frei.
- Oberflächen erzeugen keine Dienste und bedienen den Funk nur über den
  `OperatingController`.
- `build_radio_core()`, `build_desktop_services()`, `build_first_run_services()`
  in `bootstrap.py`.
- Fachlich: Vor TX wird die RX-Session geschlossen, TX meldet sich frisch an.
  RX-Grundgain 1,0, RX-AGC startet aus, TX-Zeitlimit 0–300 s.
- Papagei TG 9990 nur als Privatruf: `application/channel_rules.py`
  (`required_call_type`) stellt automatisch um.

## Programm- und Datenordner

- `carendmr/app_paths.py`: Quellcode-Start → Daten im Projektordner;
  Exe → `%LOCALAPPDATA%\CarenDMR` (bleibt bei Deinstallation erhalten);
  `CARENDMR_DATA_DIR` überschreibt.
- `project_root` in allen Diensten = Datenordner; `native_dir()` = Programmordner (DLLs).
- `prepare_data_root` kopiert `config.json`, `talkgroups.json`, `*.example.json`;
  `favorites.default.json` → `favorites.local.json`.

## BrandMeister

- Server `master2.bm262.de`, Port 62031; `package_id` muss `MMDVM_MMDVM_HS_Hat` sein
  (alte Werte werden beim Laden migriert, `LEGACY_PACKAGE_IDS`).
- Vorgaben: frequency_hz 438800000, software_id `20260728_CarenDMR`, timeout 5,0 s.
- Lokal beim Nutzer läuft der eigene UDPProvider (Windows-Dienst „UDPProvider“,
  Prozess UDPProvider.Service) auf 127.0.0.1:62030 – der normale Projektordner
  verbindet sich darüber. Testordner/Exe ohne Dienst: master2 direkt, Port 62031.

## Sprach-Codec (MD380-Emulation)

Entscheidung: wie andere Hobby-Clients (DVSwitch, DroidStar, VoxDMR) MD380-Firmware
per dynarmic emulieren; Firmware **nicht** ausliefern, sondern zur Laufzeit laden.

- Bridge `native/carendmr_md380_bridge.dll` (ohne Firmware), Export
  `carendmr_md380_init_files(fw, core)` (UTF-8-Pfade), `carendmr_md380_last_error`;
  `carendmr_md380_init()` ohne Dateien → Code 14.
- `carendmr/vocoder/md380_firmware.py`: Auspacken (XOR-Schlüssel aus md380tools),
  Prüfung per SHA-256.
  - Firmware-ZIP `https://md380.org/firmware/orig/TYT-Tytera-MD-380-FW-v232.zip`,
    Mitglied `Firmware 2.32/MD-380-D2.32(AD).bin`,
    SHA-256 `e1a1a11a84d9afd2d2ceed61be8395e32a8034785abd0be0236478f7d8609f43`
  - ausgepackt D002.032.bin: `c0351f250a834660641bca3b06be931c80cc1ed0ef808356c550b99cd0f4c632`
  - Core `https://raw.githubusercontent.com/travisgoodspeed/md380tools/master/cores/d02032-core.img`,
    SHA-256 `d40398183e9aa8db6288a62d9a0e0c233cb143ef5633680abd829cc03c719f66` (131072 Byte)
- `application/codec_setup_service.py` (Download, eigene Dateien, Manifest
  `firmware/codec_manifest.json`).
- Bridge bauen: MSYS2 UCRT64 (gcc, cmake, ninja, boost),
  `native/build_md380_dynarmic_windows.ps1`; CMake setzt `PREFIX ""`.
  pacman aus PowerShell: `$env:MSYSTEM="UCRT64"; C:\msys64\usr\bin\bash.exe -lc "pacman …"`.
- Upstream-Quellen liegen in `native\vendor` (gitignored). Herkunft:
  `docs/UPSTREAM_PROVENANCE.md`.

## Ersteinrichtung und Update-Prüfung

- `ui_qt/first_run_dialogs.py`: Station (mit Verbindungstest) → Codec → Audio
  (Windows-Standardgerät vorausgewählt) → Kontakte. Favoriten vorbelegt:
  91, 9990 (privat, „Papagei“), 262, 2623. Erststart öffnet das Hauptfenster.
- Menü Programm: „Station einrichten …“, „Sprach-Codec einrichten …“,
  „Nach Updates suchen …“; Easy: Strg+Umschalt+S/C/A/U.
- Update-Prüfung **nur auf Anfrage**: `application/update_check_service.py`,
  Quelle `https://dk7ee.de/download/versionen.json`, Schlüssel `carendmr`.
  Variante A: meldet und öffnet Download/Seite im Browser, keine Selbstinstallation.

## Release

- `build_setup.bat`: Tests → `packaging/build_release.ps1` (PyInstaller-Ordner,
  MSYS2-Laufzeit-DLLs libstdc++-6/libgcc_s_seh-1/libwinpthread-1,
  `packaging/check_dependencies.py`, Inno Setup 6.3+, SHA-256) → Explorer.
- Anleitung: `docs/RELEASE_BUILD.md`. Setup ca. 165 MB (QtWebEngine ist der größte Teil).
- Veröffentlichung: `CarenDMR-Setup-<Version>.zip` unter https://dk7ee.de/download,
  danach `versionen.json` (Schlüssel `carendmr`) anpassen – erst Download hochladen,
  dann versionen.json. Webseite liegt in `C:\ABDevelop\DK7EE.web` (eigenes Projekt).
- Exe ist unsigniert → SmartScreen-Warnung.

## Git

- Commits und Pushes macht Claude selbstständig, wenn notwendig und sinnvoll
  (in Cloud-Sitzungen auf den vorgegebenen Arbeitszweig, nicht auf `main`).
- Commit-Nachrichten im Stil `0.2.1.xx: Kurzbeschreibung`.
