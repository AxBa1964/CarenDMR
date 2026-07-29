# CarenDMR 0.0.9 – Offline-Stummruf-Fixture

> Historischer Stand: Die damalige TG91-Live-Diagnose ist seit 0.0.13
> dauerhaft deaktiviert. Automatisierte Sendetests dürfen nur noch das
> private, verriegelte Parrot-Profil 9990/Timeslot 2 verwenden.

## Zweck

Dieser Meilenstein schließt die Lücke zwischen der vorhandenen DMRD-
Netzwerkhülle und einer bytegenau prüfbaren DMR-Sprachrufsequenz. Er erzeugt
rein offline genau acht Pakete:

1. Voice-LC-Header,
2. Voice Sync mit AMBE-Stummdaten,
3. vier Sprachbursts mit den Fragmenten der Embedded LC,
4. ein abschließender Sprachburst,
5. Terminator-with-LC.

Damit umfasst der Sprachanteil genau sechs Bursts. Ziel und Rahmenparameter
sind fest: Gruppenruf TG91, Timeslot 2, Color Code 1.

## Kodierkette

Der Voice-LC-Header und Terminator verwenden:

- neun Byte Full Link Control,
- Reed-Solomon(12,9) mit typabhängiger CRC-Maske,
- BPTC(196,96),
- Golay(20,8,7) für den Slot Type,
- MS-sourced Data Sync.

Der Sprach-Superframe verwendet:

- ein festes, aus DroidStar übernommenes AMBE+2-Stummmuster,
- MS-sourced Audio Sync im ersten Burst,
- Embedded LC mit 5-Bit-Prüfsumme, Hamming(16,11,4) und Spaltenparität,
- LCSS/EMB-Kodierung in den Folgebursts.

## Schnittstellengrenze

`build_tg91_ts2_silent_call_fixture()` nimmt ausschließlich Quell-ID,
Repeater-ID, Stream-ID und erste Sequenznummer entgegen. Das Ergebnis enthält
unveränderliche `DmrdPacket`-Objekte.

Das Modul:

- öffnet keinen Socket,
- kennt keinen BrandMeister-Endpunkt und keine Zugangsdaten,
- besitzt keine Sendefunktion,
- besitzt keine PTT-/Keying-Funktion,
- nimmt kein Audio an,
- stellt keinen allgemeinen AMBE-Encoder bereit.

## Referenzprüfung

Ein temporärer, nicht zum Produkt gehörender C++-Generator wurde direkt gegen
die geprüften DroidStar-Komponenten gebaut. Für Dummy-IDs stimmen alle acht
33-Byte-Payloads exakt mit der Python-Ausgabe überein. Permanente Tests halten
diese Payloads als nicht-sensitive Referenzvektoren fest.

## Sicherheitsbegrenzter Einmaltest

`tools/brandmeister_one_shot.py` kapselt die ausdrücklich freigegebene
Live-Diagnose. Das Werkzeug:

- authentifiziert vor jeder weiteren Aktion,
- prüft die feste Acht-Paket-Fixture erneut,
- sendet sie genau einmal mit sieben Abständen von 60 ms,
- besitzt keine Ziel-, Wiederholungs- oder Laufzeitparameter,
- bricht bei jedem Fehler ohne Wiederholung ab,
- überwacht den Empfang höchstens 60 Sekunden,
- schließt den Netzwerkkanal in jedem Ausführungspfad.

Der kontrollierte Einmaltest wurde erfolgreich abgeschlossen und empfing
anschließend gültige Ziel-DMRD-Rahmen. Identitäten, Endpunkte, Zugangsdaten
und Nutzdaten werden weder protokolliert noch in dieser Dokumentation
festgehalten.

Eine allgemeine PTT- oder Laufzeit-Sendeschnittstelle bleibt weiterhin
außerhalb dieses Meilensteins.
