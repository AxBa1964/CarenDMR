# Release bauen und veröffentlichen (Windows)

Stand: 0.2.1.88. Diese Anleitung beschreibt den Weg vom Quellcode zur
Installationsdatei `CarenDMR-Setup-<Version>.exe`.

## Grundsatz: keine Firmware im öffentlichen Download

CarenDMR nutzt für Sprache den AMBE+2-Codec aus der Firmware des Funkgeräts
MD380 (Emulation über dynarmic). Diese Firmware wird **nicht** mitgeliefert.
Der Nutzer stellt `D002.032.bin` und `d02032-core.img` selbst bereit; CarenDMR
fragt beim ersten Start danach („Sprach-Codec einrichten“) und legt sie unter
`%LOCALAPPDATA%\CarenDMR\firmware\` ab.

Dafür braucht es eine Bridge, die die Firmware zur Laufzeit lädt (Export
`carendmr_md380_init_files`). `packaging\build_release.ps1` bricht ab, solange
`native\carendmr_md380_bridge.dll` noch die alte Bauart mit eingebauter
Firmware ist. Ein privater Testbuild ist mit `-AllowEmbeddedFirmware` möglich;
er darf nicht veröffentlicht werden.

Das ist eine technische Festlegung, keine Rechtsberatung. Zu Patenten auf
AMBE+2 (DVSI) siehe `docs/UPSTREAM_PROVENANCE.md`.

## Einmalige Vorbereitung

1. PyInstaller in die virtuelle Umgebung installieren:

   ```powershell
   cd C:\ABDevelop\CarenDMR
   .\.venv\Scripts\python.exe -m pip install pyinstaller
   ```

2. Inno Setup 6.3 oder neuer installieren (https://jrsoftware.org/isinfo.php).
   Das Skript sucht `ISCC.exe` in den üblichen Installationsordnern von
   Inno Setup 6.

3. Die Bridge ohne eingebaute Firmware bauen (MSYS2 UCRT64 mit den Paketen
   `mingw-w64-ucrt-x86_64-gcc`, `-cmake`, `-ninja`, `-boost`). Das
   Release-Skript kopiert danach die passenden Laufzeit-DLLs aus
   `C:\msys64\ucrt64\bin` nach `native\`:

   ```powershell
   cd C:\ABDevelop\CarenDMR
   powershell -ExecutionPolicy Bypass -File .\native\build_md380_dynarmic_windows.ps1
   ```

4. Optional ein Programmsymbol als `packaging\CarenDMR.ico` ablegen.

## Bauen

Am einfachsten per Doppelklick auf `build_setup.bat` im Projektordner
(Tests, Exe, Installer, danach öffnet sich der Ordner mit dem Setup).
Gleichwertig von Hand:

```powershell
cd C:\ABDevelop\CarenDMR
.\.venv\Scripts\python.exe -m pytest tests -q
.\packaging\build_release.ps1
```

Ergebnis:

- `release\dist\CarenDMR\CarenDMR.exe` – lauffähiger Programmordner
- `release\installer\CarenDMR-Setup-<Version>.exe` – Installer
- Das Skript gibt die SHA-256-Prüfsumme des Installers aus.

Nur die Exe ohne Installer: `.\packaging\build_release.ps1 -SkipInstaller`

## Was der Installer anlegt

- Programm unter `%LOCALAPPDATA%\Programs\CarenDMR` (ohne Adminrechte) bzw.
  `C:\Program Files\CarenDMR` (für alle Benutzer)
- Startmenü: „CarenDMR“ (`--gui`), „CarenDMR Easy“ (`--easy`),
  „CarenDMR TG-Monitor“ (`--tg-monitor`), Deinstallation
- optional eine Desktop-Verknüpfung für CarenDMR Easy

Nutzerdaten (Einstellungen, Logbuch, Mitschnitte, Codec-Dateien) liegen in
`%LOCALAPPDATA%\CarenDMR` und bleiben bei Deinstallation und Update erhalten.

## Vor der Veröffentlichung prüfen

1. Installer auf einem Rechner ohne Python und ohne MSYS2 installieren.
2. Erster Start: Dialog „Station einrichten“ erscheint, danach
   „Sprach-Codec einrichten“. Beide mit Screenreader (NVDA) bedienen.
3. Verbinden, Empfang, Parrot TG 9990, PTT, TG-Wechsel, Trennen – mit
   `--gui` und `--easy`.
4. TG-Monitor aus dem Startmenü und aus dem Hauptfenster starten.
5. Deinstallieren; `%LOCALAPPDATA%\CarenDMR` ist noch vorhanden.

## Veröffentlichen

- **GitHub Releases:** Tag `v<Version>` setzen, Installer und SHA-256 als
  Release-Datei anhängen. Der Quellcode-Hinweis der GPLv3 ist durch das
  öffentliche Repository erfüllt; im Release auf den Tag verlinken.
- **afu-software.de:** dieselbe Installationsdatei mit derselben
  SHA-256-Prüfsumme und einem Link auf das GitHub-Release anbieten.

- **Update-Hinweis:** Erst nach dem Hochladen des Setups in der zentralen
  `versionen.json` (Hauptkopie im Ordner `_AFUVersionen`) beim Schlüssel
  `carendmr` `version`, `datum`, `neu` und `download` (direkter Link zur
  Setup-Datei) eintragen und die Datei nach
  `https://dk7ee.de/download/versionen.json` hochladen. CarenDMR liest nur
  diese Adresse, und nur auf Knopfdruck.

Die Exe ist nicht signiert. Windows SmartScreen zeigt deshalb beim ersten
Start des Installers eine Warnung. Darauf in der Release-Beschreibung
hinweisen.
