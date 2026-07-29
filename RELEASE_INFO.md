# CarenDMR 0.0.9

Offline-Implementierungsstand einer deterministischen, stummen DMRD-
Gruppenruf-Fixture für TG91 auf Timeslot 2 mit BrandMeister-Gerätekennung
`MMDVM_HS_Hat`.

Enthalten sind:

- striktes Parsen vollständiger 55-Byte-DMRD-Pakete,
- unveränderliche Paketmodelle,
- Serialisierung für Voice-LC-Header, Voice Sync, Sprachrahmen und
  Terminator-with-LC,
- explizite Zielprüfung auf TG91 und Timeslot 2,
- LC-, FEC-, Slot-Type- und Embedded-LC-Kodierung für genau eine Fixture,
- ein festes, upstream dokumentiertes AMBE-Stummmuster,
- GPLv3-or-later-Lizenztext und vollständige Upstream-Provenienz.

Enthalten ist außerdem ein separates, nicht wiederholbares
Einmal-Diagnosewerkzeug mit Anmeldung, fester TG91/Timeslot-2-Sequenz,
60-ms-Taktung, begrenztem Empfangsmonitor und sicherem Schließen.

Nicht enthalten sind ein allgemeiner AMBE-Encoder, Audioübertragung oder eine
Laufzeit-PTT-Schnittstelle. Die bestehende BrandMeister-Anmeldung bleibt
unverändert.

Die produktive Software-ID bleibt `20260728_CarenDMR`.
Die BrandMeister-Login-only-Prüfung mit `MMDVM_HS_Hat` war erfolgreich.

Die acht Payloads wurden bytegenau gegen DroidStar-Referenzcode geprüft.
Der kontrollierte Einmaltest wurde ohne Wiederholung erfolgreich abgeschlossen.
Teststatus: 87 Tests erfolgreich.
