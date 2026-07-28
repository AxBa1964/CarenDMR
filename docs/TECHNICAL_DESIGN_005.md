# CarenDMR 0.0.5 – Audio und Diagnose

## Implementierter Umfang

Version 0.0.5 führt eine klar getrennte Audio-Schicht ein:

- `AudioDevice`: unveränderliches Gerätemodell
- `AudioSelection`: persistierbare Geräteidentität
- `AudioBackend`: austauschbare Hardware-Schnittstelle
- `SoundDeviceBackend`: PortAudio-Zugriff
- `AudioManager`: Erkennung, Auswahl, Rückfall und Selbsttest
- `AudioDiagnostics`: verständliche Diagnoseergebnisse

## Geräteidentität

PortAudio-Indizes werden nicht gespeichert. Sie können sich nach einem
Neustart oder dem Anstecken eines USB-Geräts ändern.

Gespeichert werden:

- Gerätename
- Host-API
- Richtung

Beim Start wird daraus das aktuell passende Gerät gesucht. Ist es nicht
vorhanden, wird zunächst das Betriebssystem-Standardgerät verwendet. Ist auch
dieses nicht eindeutig markiert, wird das erste geeignete Gerät verwendet.
Jeder Rückfall erzeugt eine verständliche Meldung.

## Lokale Konfiguration

Die tatsächliche Auswahl liegt in:

```text
config/audio.local.json
```

Diese Datei ist rechnerbezogen und darf nicht in Git oder ein normales Release
übernommen werden. `audio.example.json` dokumentiert nur das Format.

## Audio-Selbsttest

Der Selbsttest nimmt standardmäßig vier Sekunden Mono-Audio mit 48 kHz auf und
spielt die Aufnahme anschließend lokal wieder ab.

Das ist noch kein DMR-Audiopfad. Es wird damit ausschließlich geprüft:

- Mikrofon kann geöffnet werden
- Aufnahme funktioniert
- Wiedergabegerät kann geöffnet werden
- Wiedergabe funktioniert
- Betriebssystemberechtigungen sind ausreichend

## Diagnose

Diagnoseergebnisse haben drei Zustände:

- OK
- WARNING
- ERROR

Jedes Problem enthält möglichst eine konkrete nächste Handlung. Die
Audio-Diagnose ist die erste Prüfung des späteren DiagnosticsManager. Netzwerk-
und BrandMeister-Prüfungen werden erst mit den zugehörigen Releases ergänzt.

## Abhängigkeiten

`sounddevice` stellt Geräteabfrage sowie Aufnahme und Wiedergabe bereit.
`numpy` wird für die im Selbsttest aufgezeichneten Samples benötigt.

Die offizielle sounddevice-Dokumentation bestätigt, dass bei Installation über
pip unter Windows und macOS PortAudio automatisch mitgeliefert wird.

## Grenzen von 0.0.5

- kein Pegelmesser
- keine automatische Samplerate-Aushandlung
- kein dauerhaft geöffneter Audio-Stream
- keine DMR-Abtastrate
- kein Vocoder
- keine TTS-Ausgabe während der Aufnahme
- noch keine macOS-Praxiserprobung
