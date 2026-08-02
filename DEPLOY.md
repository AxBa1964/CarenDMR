# Deployment CarenDMR 0.0.21.1

Dieses Dokument ist die verbindliche chronologische Anleitung für Version 0.0.21.1. Lokale Zugangsdaten, Datenbanken und externe Vocoder-Plugins dürfen nicht committed oder in das Release-ZIP aufgenommen werden.

## 1. Projektstand prüfen

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
git status
git branch --show-current
git pull --ff-only
```

## 2. Dateien unter Windows entsperren

Dieser Schritt ist nach jedem Entpacken einer neuen ZIP zwingend erforderlich, damit Windows die PowerShell-Buildskripte ausführen darf.

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

## 5. Native Bridge für den externen AMBE-Encoder bauen

```powershell
.\native\build_vocoder_bridge_windows.ps1
```

Die Bridge enthält keinen Codec. Das externe Vocoder-Plugin wird nicht mit CarenDMR ausgeliefert und muss separat und rechtmäßig bereitgestellt werden.

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

## 9. Einmalige Inbetriebnahme prüfen

1. Im Reiter **Einstellungen** kontrollieren, ob das bisher gespeicherte Mikrofon ausgewählt ist.
2. Das gespeicherte AMBE-Plugin wird automatisch geladen und geprüft.
3. Bei erfolgreicher Prüfung erscheint keine Fehlermeldung und die TX-Taste wird freigegeben.
4. Erscheint eine Encoder-Fehlermeldung, bleibt Empfang möglich. Dann unter **Einstellungen** das Plugin einmal neu zuordnen.

## 10. Funkgeräte-Oberfläche prüfen

1. Im Reiter **Betrieb** TG und TS1 oder TS2 auswählen.
2. **Verbinden und empfangen** drücken und hörbaren Empfang abwarten.
3. TG und Timeslot mehrfach mit **TG / Timeslot umschalten** wechseln.
4. Prüfen, dass die aktuelle Station und das Ereignisprotokoll aktualisiert werden.
5. Prüfen, dass es nur die Reiter **Betrieb**, **QSO-Historie** und **Einstellungen** gibt.

## 11. Rastende PTT und TX→RX-Rückkehr prüfen

Der Sendepfad ist in 0.0.21.1 weiterhin fest auf den sicheren Parrot-Privatruf 9990 / TS2 begrenzt.

1. Bei aktivem Empfang die große blaue Taste **TX AUS** einmal drücken.
2. Prüfen, dass sie rot wird und **TX EIN** anzeigt.
3. Sprechen und die Taste erneut drücken.
4. Prüfen, dass die Aussendung beendet und anschließend automatisch dieselbe Empfangs-TG-/TS-Kombination wiederhergestellt wird.
5. Prüfen, dass kein zusätzlicher Klick auf **Verbinden** nötig ist.
6. Sicherheitsprüfung: TX erneut starten und nicht manuell beenden. Nach spätestens 60 Sekunden muss CarenDMR TX selbst beenden und zum Empfang zurückkehren.

## 12. QSO-Historie prüfen

1. Mehrere Stationen empfangen.
2. Reiter **QSO-Historie** öffnen und aktualisieren.
3. Prüfen, dass Datum, Rufzeichen, Name, DMR-ID, TG/TS, Dauer und der vorbereitete Status **Nur gehört** sichtbar sind.
4. Der Status ist in dieser Version noch keine automatische QSO-Erkennung.

## 13. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Das ZIP darf insbesondere nicht enthalten: `.git`, `.venv`, Cache-Verzeichnisse, `config\*.local.json`, externe Plugins, Datenbanken, Logs, Mitschnitte oder native Binärdateien.

## 14. Git prüfen, committen und pushen

```powershell
git status
git diff --check
git diff
git add -A
git status
git diff --cached --check
git diff --cached
git commit -m "CarenDMR 0.0.21.1 Funkgeraete-Oberflaeche"
git push origin master
```
