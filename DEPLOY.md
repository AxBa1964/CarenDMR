# CarenDMR 0.0.25.2 – TTS- und Fokus-Engine V2

## Neu in dieser Version

- Windows-SAPI wird nicht mehr für jeden Satz neu gestartet, sondern bleibt als ein dauerhafter Sprachprozess geöffnet.
- Satzanfänge wie „Timeslot“ und „Rufart“ dürfen dadurch nicht mehr abgeschnitten werden.
- Fokusmeldungen sind atomare vollständige Sätze:
  - „Neue Talkgroup.“
  - „Timeslot eins.“ / „Timeslot zwei.“
  - „Rufart Gruppe.“ / „Rufart Privat.“
  - „Connect.“
- Schnelles Tabben verwirft nur noch wartende Fokusmeldungen und behält die zuletzt erreichte Position.
- Der Tab-Kreis im Betrieb ist geschlossen:
  - Neue TG → aktiver Timeslot → aktive Rufart → Connect → Neue TG.
- Hauptreiter werden über diesen Tab-Kreis nicht mehr erreicht.
- DMR-, Audio-, Verbindungs- und State-Machine-Kern sind unverändert.

## Praxisprüfung

1. Programm starten und Caren Assist aktivieren.
2. Im getrennten Zustand mehrfach langsam mit Tab durch Neue TG, Timeslot, Rufart und Connect gehen.
3. Prüfen, dass jede Meldung vollständig gesprochen wird.
4. Schnell mehrfach Tab drücken und prüfen, dass keine Wortfragmente entstehen.
5. Nach Connect erneut Tab drücken und prüfen, dass der Fokus im Betriebsbereich bleibt.
6. Parrot sowie normales TX/RX stichprobenartig prüfen.

# CarenDMR 0.0.25.1.2

## Neu in dieser Version

- Im Bereich Betrieb wird die aktuelle Talkgroup nur noch angezeigt.
- Darunter steht ein separates, beim Start leeres Eingabefeld für eine neue Talkgroup.
- Bleibt „Neue TG“ leer, wird beim Verbinden die aktuelle Talkgroup verwendet.
- Nach erfolgreichem Verbinden wird das Feld „Neue TG“ wieder geleert.
- Beim Tab auf Timeslot wird vollständig „Timeslot eins“ oder „Timeslot zwei“ gesprochen.
- Beim Tab auf Rufart wird vollständig „Rufart Gruppe“ oder „Rufart Privat“ gesprochen.
- Tab-Reihenfolge, Enter auf CONNECT und RX-Freigabe nach der vollständigen Connect-Ansage wurden nicht verändert.

## Praxisprüfung

1. Programm starten: aktuelle TG wird angezeigt, „Neue TG“ ist leer.
2. Neue TG eintippen, Tab zu Timeslot und Rufart.
3. Vollständige Ansagen prüfen.
4. Tab zu CONNECT, Enter drücken.
5. Prüfen, dass die neue TG aktiv wird und das Eingabefeld anschließend wieder leer ist.
6. Erneut trennen und bei leerem Feld verbinden: die aktuelle TG muss weiterverwendet werden.


# Neu in dieser Version – Workflow V1

- Nach Disconnect wartet Caren Assist, bis „Verbindung getrennt“ vollständig gesprochen wurde.
- Danach liegt der Fokus auf Talkgroup und der komplette bisherige Wert ist markiert.
- Die erste eingegebene Ziffer ersetzt dadurch sofort die alte Talkgroup.
- Tab-Reihenfolge im getrennten Zustand:
  - Talkgroup
  - aktiver Timeslot
  - aktive Rufart
  - CONNECT
- Bei Timeslot und Rufart ist nur die aktuell gewählte Option Bestandteil der Tab-Reihenfolge.
- Fokusansagen sind vollständig:
  - „Timeslot eins“ oder „Timeslot zwei“
  - „Rufart Gruppe“ oder „Rufart Privat“
- Beim Connect wird die lokale RX-Wiedergabe stumm gehalten, bis die vollständige Connect-Ansage beendet ist.
- Erst danach wird Empfangsaudio hörbar und der Fokus springt auf PTT.
- Nicht mehr passende TTS-Meldungen werden bei Zustandswechseln verworfen.
- DMR-, AMBE-, Netzwerk- und Live-TX-Pfad wurden nicht verändert.

## Neu in dieser Version

- Talkgroup wird beim Erhalt des Fokus vollständig markiert; die erste eingegebene Ziffer ersetzt den bisherigen Wert.
- Beim Tab auf die aktive Timeslot-Auswahl spricht Caren Assist vollständig „Timeslot eins“ oder „Timeslot zwei“.
- Beim Tab auf die aktive Rufart spricht Caren Assist vollständig „Rufart Gruppe“ oder „Rufart Privat“.
- Der fokussierte CONNECT-Button kann mit Enter oder der Enter-Taste des Ziffernblocks ausgelöst werden.
- Keine weiteren Änderungen an Workflow, DMR-, Audio- oder Netzwerkpfad.

### Gezielter Praxistest

1. Programm starten: Talkgroup muss vollständig markiert sein.
2. Neue Talkgroup eintippen: alter Wert muss sofort ersetzt werden.
3. Tab: vollständige Timeslot-Ansage prüfen.
4. Tab: vollständige Rufart-Ansage prüfen.
5. Tab auf CONNECT und Enter drücken: Verbindung muss starten.


## Praxisprüfung

1. Programm starten und verbinden.
2. F5 drücken und auf die vollständige Meldung „Verbindung getrennt“ achten.
3. Direkt eine neue TG eintippen. Der alte Wert muss ohne Backspace vollständig ersetzt werden.
4. Tab drücken. Fokus und Ansage müssen auf dem aktuell aktiven Timeslot liegen.
5. Timeslot mit 1/2 oder Pfeiltaste ändern. Die vollständige Ansage muss hörbar sein.
6. Tab drücken. Fokus und Ansage müssen auf der aktuell aktiven Rufart liegen.
7. Rufart mit G/P oder Pfeiltaste ändern. Die vollständige Ansage muss hörbar sein.
8. Tab drücken. Fokus muss auf CONNECT liegen.
9. Enter drücken. Die komplette Connect-Ansage muss zuerst beendet werden.
10. Erst danach darf Audio der gewählten TG hörbar werden.
11. Fokus muss anschließend auf PTT liegen; Space-TX prüfen.

## Installation und Prüfung

Dieses Dokument ist die verbindliche chronologische Anleitung für Version 0.0.25.1.2. Lokale Zugangsdaten, Datenbanken und externe Vocoder-Plugins dürfen nicht committed oder in das Release-ZIP aufgenommen werden.

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
3. Im getrennten Zustand TG, Timeslot und Rufart ändern, anschließend erneut mit **CONNECT** verbinden.
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
git commit -m "CarenDMR 0.0.24.6.4 Stabilitätsfix Fokus PTT Verbindung"
git push origin master
```


## Messlauf für TX/RX-Umschaltung

1. CarenDMR starten und normal verbinden.
2. Einen kurzen Sendedurchgang von etwa drei Sekunden durchführen.
3. Warten, bis links wieder **VERBUNDEN** angezeigt wird.
4. CarenDMR beenden.
5. Die Datei `logs\tx_rx_timing.log` bereitstellen.

Die Datei enthält keine Audioaufnahme und kein Passwort. Sie enthält Zeitmarken, Ziel-ID, Timeslot, Rufart und den konfigurierten BrandMeister-Server.
