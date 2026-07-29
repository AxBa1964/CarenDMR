# CarenDMR – Technische Architektur

Stand: Version 0.0.13.1

## 1. Ziel und Grenzen

CarenDMR ist ein eigenständiger, barrierefrei entwickelter DMR-Client
ausschließlich für BrandMeister. Oberfläche, Protokoll, Audio und
Accessibility bleiben getrennt, damit jeder Bereich isoliert getestet werden
kann.

Nicht zum Projektumfang gehören andere digitale Betriebsarten,
Hotspot-/Repeaterbetrieb oder ein allgemeines Mehrprotokoll-Framework.

## 2. Komponenten

```text
Bedienoberfläche (zukünftig)
        |
Accessibility Layer
        |
Application Core / Ereignisse / Status
        |
+-------------------+---------------------+
| BrandMeister      | Audio               |
| Login, UDP, DMRD  | Geräte, PCM-Ausgabe |
+-------------------+---------------------+
        |                      |
DMR Frame Model         Vocoder Adapter
                               |
                    nativer mbelib-Decoder
```

### Application Core

`carendmr/core` verwaltet Ereignisse und Zustände, ohne eine konkrete
Oberfläche zu kennen. Technische Komponenten veröffentlichen strukturierte
Informationen; Benutzertexte entstehen in der Accessibility-Schicht.

### Accessibility

`carendmr/accessibility` übersetzt Zustände in verständliche Meldungen und
kapselt lokale Sprachausgabe. Die verbindliche Definition of Done steht in
`docs/ACCESSIBILITY_REQUIREMENTS.md`.

### Netzwerk

`carendmr/network` enthält DNS-Endpunkte, UDP-Transport, Heartbeat,
Netzwerkkonfiguration und optionalen Paket-Logger. Der Transport kennt keine
DMR-Audiologik.

### BrandMeister

`carendmr/brandmeister` enthält:

- validierte lokale Konfiguration,
- `RPTL`/`RPTK`/`RPTC`-Login, Ping und sauberes Schließen,
- striktes DMRD-Paketmodell,
- payloadfreie Empfangsereignisse,
- begrenzten Live-Empfang,
- offline erzeugte DMR-Rahmen-Fixtures,
- ein getrenntes, hart verriegeltes privates Parrot-Testprofil.

Die experimentell bestätigten Kennungsregeln stehen in
`docs/BRANDMEISTER_COMPATIBILITY.md`.

### Vocoder

`carendmr/vocoder` definiert eine austauschbare, empfangsseitige Grenze:

1. drei AMBE+2-Codewörter aus einem Sprachburst extrahieren,
2. Codewörter zustandsbehaftet in PCM dekodieren,
3. Fehlerzahlen und exakt 160 Samples pro Codewort liefern,
4. keine Encode- oder Sendefunktion exponieren.

Der native Adapter lädt die lokal gebaute Bibliothek aus `native/`. Herkunft,
Lizenz und die bewusst ausgeschlossenen Komponenten sind in
`docs/UPSTREAM_PROVENANCE.md` dokumentiert.

### Audio

`carendmr/audio` trennt Geräteerkennung, lokale Auswahl, Backend und
gepufferte PCM-Ausgabe. Der Wiedergabepuffer ist begrenzt, füllt Underruns mit
Stille und blockiert den Netzwerkempfang nicht.

## 3. Datenfluss beim Empfang

```text
BrandMeister UDP
  -> Paketidentifikation
  -> striktes DMRD-Modell
  -> gefiltertes Empfangsereignis
  -> Sequenz-/Jitterpuffer
  -> drei AMBE+2-Codewörter je Sprachburst
  -> nativer Empfangsdecoder
  -> PCM-Puffer
  -> Standard-Wiedergabegerät
```

Live-Empfang ist derzeit bewusst auf TG91 und Timeslot 2 begrenzt.
Paketnutzdaten gelangen nicht in Status- oder Accessibility-Ereignisse.

## 4. BrandMeister-Verbindung

1. DNS-Auflösung und UDP-Socket
2. `RPTL` mit DMR-ID
3. `RPTACK` mit Challenge
4. SHA-256 über Challenge plus Hotspot-Passwort
5. `RPTK` und zweites `RPTACK`
6. `RPTC` mit validierten Stationsdaten
7. periodisches `RPTPING` / `MSTPONG`
8. `RPTCL` beim kontrollierten Schließen

Passwörter bleiben ausschließlich in ignorierten lokalen
Konfigurationsdateien.

## 5. Sendesicherheit

Eine allgemeine Laufzeit-Sendeschnittstelle existiert nicht.

Das einzige vorhandene Live-Testprofil ist unveränderlich auf privaten
BrandMeister-Parrot-Ruf 9990, Timeslot 2, maximal zehn Sekunden Sendezeit und
15 Sekunden Echo-Wartezeit begrenzt. Es besitzt keine Ziel-, Ruftyp-,
Timeslot- oder Dauerparameter, keinen Retry und keinen öffentlichen Fallback.

Automatisierte Sendetests auf öffentlichen Gruppen-Talkgroups sind dauerhaft
verboten.

## 6. Konfiguration und Geheimnisse

- verteilbare Beispiele: `config/*.example.json`
- lokale Werte: `config/*.local.json`
- lokale Dateien werden von Git und Release-ZIP ausgeschlossen
- Logs und UI dürfen Passwörter oder unnötige persönliche Stationsdaten nicht
  wiederholen

## 7. Abhängigkeiten und Build

Python-Laufzeit:

- `numpy` für PCM-Daten,
- `sounddevice` für lokale Audio-Ein-/Ausgabe,
- Standardbibliothek für Netzwerk, Hashing, Konfiguration und Tests.

Der native Decoder wird mit `native/Makefile` gebaut. Er exportiert nur die
kleine CarenDMR-Decoder-ABI; Encoder-Symbole sind ausgeschlossen.

## 8. Nächste Architekturgrenze

Der nächste Produktmeilenstein ist ein read-only VoiceOver-Grundfenster. Es
verbraucht ausschließlich bestehende Status- und Empfangsereignisse und führt
keine neue PTT-, Encoder- oder freie Sendefläche ein.

Die geplante Reihenfolge steht in der [Roadmap](../ROADMAP.md).
