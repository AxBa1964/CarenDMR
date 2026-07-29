# CarenDMR 0.0.8 – DMRD-Paketdomäne

## Ziel

Version 0.0.8 bildet die Netzwerkhülle eines DMR-Sprachstroms als eigenständige,
offline testbare Domäne ab. Der vereinbarte Zielbetrieb ist ein Gruppenruf auf
Talkgroup 91 und Timeslot 2.

## Paketformat

Ein unterstütztes Paket ist genau 55 Bytes lang:

- Byte 0–3: Kennung `DMRD`
- Byte 4: Netzwerk-Sequenznummer
- Byte 5–7: Quell-DMR-ID
- Byte 8–10: Ziel-ID beziehungsweise Talkgroup
- Byte 11–14: Repeater-/Gateway-ID
- Byte 15: Timeslot, Rufart und Rahmenklasse
- Byte 16–19: Stream-ID
- Byte 20–52: bereits kodierter 33-Byte-DMR-Burst
- Byte 53: BER-Metadatum
- Byte 54: RSSI-Metadatum

Mehrbytewerte werden in Netzwerkreihenfolge (Big Endian) verarbeitet.

## Unterstützte Rahmenklassen

Die Paketdomäne unterscheidet:

- Voice-LC-Header als Data-Sync-Typ `0x01`
- Sprach-Synchronrahmen
- Sprachrahmen mit Nummer 0 bis 5
- Terminator-with-LC als Data-Sync-Typ `0x02`
- weitere empfangene Data-Sync-Typen als numerisch erhaltene Metadaten

Das unveränderliche `DmrdPacket`-Modell kann wieder bytegenau serialisiert
werden. Fehlerhafte Längen, Kennungen, IDs, reservierte Rahmenbits und
inkonsistente Rahmeneigenschaften werden früh abgewiesen.

## Sicherheits- und Verantwortungsgrenze

Dieser Meilenstein:

- öffnet keinen Netzwerkkanal,
- wird nicht vom Live-Client versendet,
- aktiviert keine Talkgroup,
- erzeugt keine Link-Control-Daten,
- kodiert kein AMBE,
- nimmt kein Audio auf.

Die Konstruktionsfunktionen erwarten einen bereits korrekt kodierten
33-Byte-DMR-Burst. Damit ist die Homebrew-Netzwerkhülle testbar, ohne
unvollständige oder unbestätigte Funkdaten zu erzeugen.

## Nächster Schritt

Vor einer kontrollierten Live-Übertragung müssen Link-Control- und
Burst-Kodierung gegen eine verlässliche Referenz spezifiziert und mit bekannten
Testvektoren bestätigt werden. Erst danach darf eine ausdrücklich freigegebene
Sendeschnittstelle die serialisierten Pakete an den BrandMeister-Client
übergeben.
