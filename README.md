# CarenDMR

## Version 0.2.1.9

Neu: Die eigene Modulation kann über einen geführten Parrot-Test gegen die aktive DMR-Audio-Referenz verglichen werden. Der Vergleich verwendet den lokalen AMBE-Codec-Loopback und zeigt konkrete, noch nicht automatisch angewendete Tuner-Empfehlungen.

Der DMR-Audio-Benchmark besitzt jetzt eine unterbrechungssichere Referenz-Engine mit SQLite-Datenbank und direkt zum Audio-Tuner passenden Messwerten.

# CarenDMR

## Version 0.1.9.3

Der passive Audio-Benchmark ist jetzt korrekt mit dem laufenden RX-Datenstrom verbunden.


## 0.1.9.3

- Audio-Benchmark erkennt wiederholte Voice-Aktivitätsmeldungen desselben Streams korrekt und zerlegt einen Sprechdurchgang nicht mehr in Einzelpakete.
- Aktuelle Station, laufende Sprechdauer und Analysewarteschlange werden live angezeigt.
- Fremde oder verspätete Stream-Ende-Ereignisse können den aktiven Testfall nicht mehr beenden.

CarenDMR 0.1.9.1.2 – Passiver Audio-Analyzer

Der geführte Audio-Test beobachtet die bestehende Funkstrecke, ohne RX, TX, Socket oder Audioausgabe zu steuern.

CarenDMR 0.1.8.5 – Codec-Diagnose und TX-Timing

# CarenDMR 0.1.8.0 – Talkgroup-Metadaten

CarenDMR ist ein barrierefrei bedienbarer Qt-Desktop-DMR-Client für BrandMeister.

Diese Version ergänzt das weltweite Talkgroup-Verzeichnis um abgeleitete Länder- und Sprachinformationen. Im Reiter **Talkgroups** kann nach Nummer, Name, Land und wahrscheinlicher Betriebssprache gesucht und gefiltert werden. Favoriten lassen sich im Bearbeiten-Dialog sowie über eigene kompakte Schaltflächen setzen und entfernen.

Die Sprache ist eine hilfreiche Ableitung aus MCC-Präfix und Talkgroup-Name, keine garantierte Aussage über jedes einzelne QSO.

## CarenDMR 0.1.8.2

Der geführte Audio-Test puffert zwei Sekunden Mikrofon-Vorlauf ausschließlich im RAM und zeichnet danach genau die nächste TX-Sendung an mehreren Messpunkten auf. Die Diagnose endet automatisch und erzeugt WAV-/BIN-Dateien sowie Analyseberichte unter `logs/audio_lab/`.


## Audioqualität 0.1.9.1.2
Die optionale, standardmäßig aktive DMR-Sprachaufbereitung arbeitet bewusst dezent: Hochpass gegen Rumpeln und Soft-Limiter für einzelne Spitzen, ohne Pumpen oder automatische Lautheitsanhebung.


## DMR Audio-Tuner 0.1.9.1.2

Auf der Betriebsseite lässt sich der Tuner ausklappen. Neutral ist die Referenz. Klar, DX und Warm sind sofort nutzbare Profile. Eigene Werte werden dauerhaft in `config/audio.local.json` gespeichert und gelten ab dem nächsten TX.

## DMR-Audio-Benchmark

Der Reiter **Audio-Benchmark** sammelt passiv Referenzdaten aus normalen DMR-Empfangsdurchgängen. Durchgänge ab fünf Sekunden werden getrennt nach Rufzeichen und Stream ausgewertet. Analyse und Speicherung laufen außerhalb des RX-Echtzeitpfads. Messreihen können pausiert, später fortgesetzt und nach einem Programmneustart wieder aufgenommen werden. Vollständige Sprachaufnahmen werden nicht dauerhaft gespeichert; gespeichert werden ausschließlich Kennzahlen und Metadaten.

Aktuelle Version: **0.1.9.2**
