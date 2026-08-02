# Deployment CarenDMR 0.0.19.7

Dieses Dokument ist die verbindliche chronologische Anleitung für Version 0.0.19.7. Lokale Zugangsdaten, Datenbanken und externe Vocoder-Plugins dürfen nicht committed oder in das Release-ZIP aufgenommen werden.

## 1. Projektstand prüfen

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
git branch --show-current
git pull --ff-only
```

## 2. Dateien unter Windows entsperren

```powershell
Get-ChildItem -Recurse -File | Unblock-File
```

## 3. Virtuelle Umgebung aktivieren

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 4. Nativen Empfangsdecoder bauen

```powershell
.\native\build_windows.ps1
```

## 5. Native Bridge für DroidStar-kompatible Plugins bauen

```powershell
.\native\build_vocoder_bridge_windows.ps1
```

Die Bridge enthält keinen Codec. Das externe Vocoder-Plugin wird nicht mit CarenDMR ausgeliefert und muss vom Benutzer separat und rechtmäßig bereitgestellt werden.

## 6. Vollständige Tests ausführen

```powershell
python -m unittest discover -s tests -v
```

Erwartet werden alle Tests erfolgreich und abschließend `OK`.

## 7. Release-Konsistenz prüfen

```powershell
python tools\release_check.py
```

## 8. Anwendung starten

```powershell
python main.py --gui
```

## 9. Empfang und Audio praktisch prüfen

- Mit „Verbinden und empfangen“ verbinden.
- TG91-Empfang, aktuelle Station und QSO-Historie prüfen.
- Im Reiter „Senden – lokaler Audiotest“ Mikrofonaufnahme, Wiedergabe, AGC und Mute prüfen.

## 10. Optionales DroidStar-Plugin offline prüfen

1. Im Reiter „Senden – lokaler Audiotest“ den Bereich „Optionaler AMBE-Encoder“ öffnen.
2. „Plugin auswählen und prüfen“ wählen.
3. Eine separat bereitgestellte, zur Plattform passende DroidStar-Vocoder-Plugin-Datei auswählen.
4. Erfolgsmeldung „AMBE-Encoder bereit: 9 Byte erzeugt“ prüfen.

Die Plugin-Prüfung codiert zunächst nur einen lokalen stummen PCM-Rahmen und sendet nichts. Der anschließende Parrot-Test ist hart auf DMR-ID 9990, Privatruf und Timeslot 2 verriegelt.

## 11. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Das ZIP darf insbesondere nicht enthalten:

- `.git`, `.venv` oder Cache-Verzeichnisse,
- `config\*.local.json`,
- externe Vocoder-Plugin-Dateien,
- `data\contacts.db` oder `data\qso_history.db`,
- Audioaufnahmen, Logs oder Paketmitschnitte,
- `*.dll`, `*.so` oder `*.dylib`.

## 12. Git prüfen, committen und pushen

```powershell
git status
git diff --check
git diff
git add -A
git status
git diff --cached --check
git diff --cached
git commit -m "CarenDMR 0.0.19.7 gueltiger dynamischer TG-Gruppenruf"
git push origin master
```


## Privaten Parrot-Sprachtest prüfen

1. `python main.py --gui` starten.
2. Im Reiter **Senden** das konfigurierte Plugin erneut prüfen.
3. **5-Sekunden-Privattest an Parrot 9990 starten** wählen.
4. Bestätigen, fünf Sekunden sprechen und das Echo abwarten.
5. Prüfen, dass Ziel 9990, Ruftyp Privatruf und Timeslot 2 unveränderbar angezeigt werden.

## 8. Praktische Funktionsprüfung

```powershell
python main.py --gui
```

- Plugin erneut prüfen.
- TX-Taste drücken und zwei bis fünf Sekunden sprechen.
- TX-Taste loslassen: Die Aufnahme muss sofort enden und gesendet werden.
- Prüfen, dass das Parrot-Echo wiedergegeben und die Sendehistorie ergänzt wird.
- Prüfen, dass beim Loslassen sofort beendet und gesendet wird; das eingestellte TX-Sicherheitslimit greift nur als Notbremse.


## Prüfung Version 0.0.19.7

1. CarenDMR starten.
2. Im Reiter **Empfang** die gewünschte Talkgroup und Timeslot 1 oder 2 eintragen.
3. **Verbinden und empfangen** wählen.
4. Im Ereignisprotokoll müssen die erfolgreiche Anmeldung und der gestartete Empfang auf der gewählten Talkgroup erscheinen.
5. Für einen Wechsel zuerst **Trennen**, danach neue Talkgroup beziehungsweise neuen Timeslot eintragen und erneut verbinden.
6. In `config/brandmeister.local.json` ist kein API-Key erforderlich.
