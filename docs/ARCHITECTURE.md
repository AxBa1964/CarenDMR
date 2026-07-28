# CarenDMR – Technische Architektur

Stand: Version 0.0.3

## 1. Projektziel

CarenDMR ist ein eigenständiger, barrierearmer DMR-Client ausschließlich
für das BrandMeister-Netzwerk.

Das Projekt übernimmt keinen DroidStar-Code. DroidStar dient als technische
Referenz, um das verwendete DMR-Netzwerkprotokoll und die Audio-/Vocoder-
Pipeline zu verstehen.

Nicht zum Projektumfang gehören:

- D-Star
- YSF/FCS
- P25
- NXDN
- M17
- AllStar/IAX
- MMDVM-Hotspotbetrieb
- allgemeine Digitalfunk-Plattform

## 2. Erkenntnisse aus dem offiziellen DroidStar-Quellcode

DroidStar kapselt DMR in einer Klasse `DMR`, die von einer gemeinsamen
Basisklasse `Mode` erbt.

Die DMR-Klasse enthält unter anderem:

- UDP-Kommunikation
- DMR-Anmeldezustände
- Passwort-Challenge mit SHA-256
- Konfigurationsübertragung
- Heartbeat/Ping
- Disconnect
- Empfang und Versand von 55-Byte-DMRD-Paketen
- Talkgroup-, Slot- und Color-Code-Auswahl
- DMR-Rahmenbildung
- AMBE-Rahmenübergabe
- Audio-Aufnahme und Audio-Wiedergabe

## 3. BrandMeister-Verbindungsablauf

Der im DroidStar-Code erkennbare Ablauf entspricht dem MMDVM-
Masterprotokoll:

1. DNS-Auflösung des ausgewählten Masters.
2. UDP-Socket öffnen.
3. `RPTL` mit DMR-ID/ESSID senden.
4. `RPTACK` mit vier Byte Challenge empfangen.
5. Challenge und Hotspot-Passwort mit SHA-256 verarbeiten.
6. `RPTK` mit DMR-ID/ESSID und Hash senden.
7. Weiteres `RPTACK` empfangen.
8. `RPTC` mit Stations- und Programminformationen senden.
9. Optional `RPTO` mit Netzwerkoptionen senden.
10. Status auf verbunden setzen.
11. Alle fünf Sekunden `RPTPING` senden.
12. `MSTPONG` als Lebenszeichen empfangen.
13. Beim Beenden `RPTCL` senden.

Servermeldungen `MSTNAK` und `MSTCL` führen in DroidStar zu einem
Verbindungsabbruch und zeitversetztem Neuaufbau.

## 4. Empfangspfad

Ein DMR-Sprachpaket besteht im untersuchten Code aus 55 Bytes und beginnt
mit `DMRD`.

Relevante Felder:

- Byte 0–3: Kennung `DMRD`
- Byte 4: laufende Rahmennummer
- Byte 5–7: Quell-DMR-ID
- Byte 8–10: Ziel-ID bzw. Talkgroup
- Byte 11–14: Gateway-/ESSID
- Byte 15: Slot, Gruppen-/Privatruf und Rahmentyp
- Byte 16–19: Stream-ID
- Byte 20–52: DMR-Nutzdaten
- Byte 53–54: BER/RSSI-Felder

Bei Sprachrahmen werden aus den 33 Nutzdatenbytes drei AMBE-Rahmen zu je
neun Bytes extrahiert. Diese werden an den Vocoder weitergegeben. Das
dekodierte PCM-Audio wird anschließend über die Audioausgabe abgespielt.

## 5. Sendepfad

Der Sendepfad besteht aus:

1. PTT gedrückt.
2. Audioaufnahme starten.
3. PCM-Audio in AMBE umwandeln.
4. Drei AMBE-Rahmen zu einem DMR-Sprachrahmen bündeln.
5. Voice-LC-Header erzeugen.
6. Stream-ID erzeugen.
7. 55-Byte-DMRD-Paket aufbauen.
8. Pakete per UDP an den Master senden.
9. Beim Loslassen der PTT Terminator-with-LC erzeugen.
10. Audioaufnahme stoppen und in Empfang zurückkehren.

## 6. CarenDMR-Zielarchitektur

### 6.1 Application Core

Verwaltet ausschließlich die Zustände:

- getrennt
- verbindet
- verbunden
- empfängt
- sendet
- Fehler

Der Core kennt keine konkrete GUI.

### 6.2 BrandMeister Client

Aufgaben:

- Masteradresse auflösen
- UDP-Verbindung verwalten
- Login-Zustandsmaschine
- Heartbeats
- automatischer Neuaufbau
- DMRD-Pakete empfangen und senden
- saubere Trennung von Netzwerk und Audio

### 6.3 DMR Frame Codec

Aufgaben:

- DMRD-Pakete lesen und schreiben
- IDs, Talkgroup, Slot und Stream-ID verarbeiten
- AMBE-Nutzdaten extrahieren und einsetzen
- Header, Voice-Rahmen und Enderahmen erzeugen

Dieser Bestandteil ist nicht der Sprachvocoder. Er verarbeitet nur die
DMR-Rahmenstruktur.

### 6.4 Vocoder Adapter

Ein einheitlicher Adapter kapselt später entweder:

- einen legal verfügbaren Software-Vocoder oder
- ein unterstütztes AMBE-USB-Gerät

Der restliche CarenDMR-Code darf nicht von einem konkreten Vocoder
abhängen.

### 6.5 Audio Engine

Aufgaben:

- Mikrofon auswählen
- Lautsprecher auswählen
- PCM aufnehmen
- PCM wiedergeben
- Pegel und Fehler melden
- Echo und doppelte Wiedergabe vermeiden

### 6.6 Accessibility Layer

Aufgaben:

- alle Zustände per Sprache melden
- vollständige Tastaturbedienung
- später USB-Tastenbedienung
- PTT-Signaltöne
- Talkgroup und Anrufer ansagen
- Fehler verständlich und ohne Fachjargon ausgeben

## 7. Bewusst nicht übernommene DroidStar-Bestandteile

- Qt/QML-Oberfläche
- gemeinsame Mehrprotokoll-Basisklasse
- alle Nicht-DMR-Betriebsarten
- MMDVM-Modemsteuerung
- Hotspot- und Direct-Mode
- komplexe allgemeine Einstellungsoberfläche
- plattformspezifische Oberfläche von DroidStar

## 8. Abhängigkeiten und Risiken

### AMBE

DMR verwendet AMBE+2. Die rechtliche und technische Verfügbarkeit eines
Software-Vocoders muss vor einer Veröffentlichung gesondert geprüft
werden. Die Projektarchitektur darf deshalb keinen bestimmten inoffiziellen
Vocoder fest voraussetzen.

### Netzwerkprotokoll

Die Anmeldung ist nicht mit einer normalen Web-API vergleichbar. Sie
verwendet UDP und das MMDVM-Masterprotokoll. Verbindungszustände,
Zeitüberschreitungen und Heartbeats müssen zuverlässig behandelt werden.

### Audio-Latenz

DMR arbeitet mit zeitlich eng aufeinanderfolgenden Sprachrahmen. Aufnahme,
Vocoder und Netzwerk dürfen den Sendepfad nicht blockieren.

## 9. Nächster technischer Schritt

Version 0.0.4 soll noch keine BrandMeister-Verbindung herstellen.

Sie soll:

- verfügbare Audio-Eingänge erkennen,
- verfügbare Audio-Ausgänge erkennen,
- Standardgeräte bestimmen,
- die Auswahl in der Konfiguration speichern,
- die Ergebnisse barrierefrei in Textform ausgeben.

Damit wird zuerst die lokale Audio-Grundlage verifiziert.
