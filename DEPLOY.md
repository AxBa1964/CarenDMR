# Deployment CarenDMR 0.0.23.9

**0.0.23.9:** Reine Audio-Diagnose mit WAV-Ausgabe vor und nach der 16-kHz-zu-8-kHz-Aufbereitung; Funkverhalten unverändert.

Dieses Dokument ist die verbindliche chronologische Anleitung für Version 0.0.23.9. Lokale Zugangsdaten, Datenbanken und externe Vocoder-Plugins dürfen nicht committed oder in das Release-ZIP aufgenommen werden.

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
2. **CONNECT** drücken und hörbaren Empfang abwarten.
3. TG und Timeslot mehrfach mit **TG wechseln** wechseln.
4. Prüfen, dass die aktuelle Station und das Ereignisprotokoll aktualisiert werden.
5. Prüfen, dass es nur die Reiter **Betrieb**, **QSO-Historie** und **Einstellungen** gibt.

## 11. Beschleunigten PTT-Start und TX→RX-Rückkehr prüfen

Die TX-Taste sendet auf das aktuell eingestellte Ziel, den gewählten Timeslot und die gewählte Rufart. Nur 9990 / TS2 / Privat wird als Parrot-Test mit Echo ausgewertet.

1. Bei aktivem Empfang die große blaue Taste **TX AUS** einmal drücken.
2. Prüfen, dass sie rot wird und **TX EIN** anzeigt.
3. Direkt nach dem Rotwerden mit einem deutlich gesprochenen Testsatz beginnen, zum Beispiel „Eins zwei drei, hier ist DO1DPL“.
4. Die Taste erneut drücken und beim Parrot-Echo prüfen, dass „Eins“ vollständig hörbar ist.
5. Prüfen, dass die Aussendung beendet und anschließend automatisch dieselbe Empfangs-TG-/TS-Kombination wiederhergestellt wird.
6. Prüfen, dass kein zusätzlicher Klick auf **Verbinden** nötig ist.
7. Sicherheitsprüfung: TX erneut starten und nicht manuell beenden. Nach spätestens 60 Sekunden muss CarenDMR TX selbst beenden und zum Empfang zurückkehren.

## 12. QSO-Historie prüfen

1. Mehrere Stationen empfangen.
2. Reiter **QSO-Historie** öffnen und aktualisieren.
3. Prüfen, dass Datum, Rufzeichen, Name, DMR-ID, TG/TS, Dauer und der vorbereitete Status **Nur gehört** sichtbar sind.
4. Der Status ist in dieser Version noch keine automatische QSO-Erkennung.


## 13. Einstellungen prüfen

1. Reiter **Einstellungen** öffnen.
2. Links nacheinander **Audio**, **Netzwerk**, **Daten**, **Bedienung**, **Diagnose** und **Erweiterungen** auswählen.
3. Unter **Audio** prüfen, dass Mikrofon, Wiedergabe und AMBE-Codec in getrennten kompakten Karten erscheinen.
4. Unter **Netzwerk** prüfen, dass Server, Rufzeichen, DMR-ID und Port angezeigt werden; das Passwort darf nicht sichtbar sein.
5. Unter **Daten** die Anzeige der RadioID-Kontaktdaten sowie den Aktualisieren-Button prüfen.
6. Im Suchfeld `Mikrofon`, `Datenbank` und `Diagnose` eingeben und jeweils mit Enter bestätigen. Die passende Kategorie muss geöffnet werden.
7. Prüfen, dass der Diagnosemodus im Normalbetrieb ausgeschaltet ist.

## 14. Diagnosemodus prüfen

1. Anwendung normal starten und empfangen. In PowerShell dürfen keine fortlaufenden `[DIAG]`-Meldungen erscheinen.
2. Unter **Einstellungen → Diagnose** den Diagnosemodus aktivieren.
3. Empfang starten und prüfen, dass die ausführlichen Diagnosemeldungen erscheinen.
4. Diagnosemodus wieder ausschalten. Die Einstellung wird in `config\diagnostics.local.json` lokal gespeichert und nicht in das Release übernommen.

## 15. Release-ZIP erzeugen

```powershell
python tools\create_release_zip.py
```

Das ZIP darf insbesondere nicht enthalten: `.git`, `.venv`, Cache-Verzeichnisse, `config\*.local.json`, externe Plugins, Datenbanken, Logs, Mitschnitte oder native Binärdateien.

## 16. Git prüfen, committen und pushen

```powershell
git status
git diff --check
git diff
git add -A
git status
git diff --cached --check
git diff --cached
git commit -m "CarenDMR 0.0.23.9 TX Sprachqualitaet verbessert"
git push origin master
```


## Messlauf für TX/RX-Umschaltung

1. CarenDMR starten und normal verbinden.
2. Einen kurzen Sendedurchgang von etwa drei Sekunden durchführen.
3. Warten, bis links wieder **VERBUNDEN** angezeigt wird.
4. CarenDMR beenden.
5. Die Datei `logs\tx_rx_timing.log` bereitstellen.

Die Datei enthält keine Audioaufnahme und kein Passwort. Sie enthält Zeitmarken, Ziel-ID, Timeslot, Rufart und den konfigurierten BrandMeister-Server.
