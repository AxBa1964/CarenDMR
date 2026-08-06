CarenDMR 0.1.9.1.3 – Passiver Audio-Analyzer

Der geführte Audio-Test beobachtet die bestehende Funkstrecke, ohne RX, TX, Socket oder Audioausgabe zu steuern.

CarenDMR 0.1.8.5 – Codec-Diagnose und TX-Timing

# CarenDMR 0.1.8.0 – Talkgroup-Metadaten

CarenDMR ist ein barrierefrei bedienbarer Qt-Desktop-DMR-Client für BrandMeister.

Diese Version ergänzt das weltweite Talkgroup-Verzeichnis um abgeleitete Länder- und Sprachinformationen. Im Reiter **Talkgroups** kann nach Nummer, Name, Land und wahrscheinlicher Betriebssprache gesucht und gefiltert werden. Favoriten lassen sich im Bearbeiten-Dialog sowie über eigene kompakte Schaltflächen setzen und entfernen.

Die Sprache ist eine hilfreiche Ableitung aus MCC-Präfix und Talkgroup-Name, keine garantierte Aussage über jedes einzelne QSO.

## CarenDMR 0.1.8.2

Der geführte Audio-Test puffert zwei Sekunden Mikrofon-Vorlauf ausschließlich im RAM und zeichnet danach genau die nächste TX-Sendung an mehreren Messpunkten auf. Die Diagnose endet automatisch und erzeugt WAV-/BIN-Dateien sowie Analyseberichte unter `logs/audio_lab/`.


## Audioqualität 0.1.9.1.3
Die optionale, standardmäßig aktive DMR-Sprachaufbereitung arbeitet bewusst dezent: Hochpass gegen Rumpeln und Soft-Limiter für einzelne Spitzen, ohne Pumpen oder automatische Lautheitsanhebung.


## DMR Audio-Tuner 0.1.9.1.3

Auf der Betriebsseite lässt sich der Tuner ausklappen. Neutral ist die Referenz. Klar, DX und Warm sind sofort nutzbare Profile. Eigene Werte werden dauerhaft in `config/audio.local.json` gespeichert und gelten ab dem nächsten TX.
