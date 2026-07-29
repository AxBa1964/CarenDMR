# CarenDMR 0.0.13

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
- kompatibles Parsing empfangener Stream-ID-null-Pakete ohne Lockerung der
  lokalen Sendekonstruktion,
- payloadfreie Empfangsereignisse für Rufbeginn, Sprache, Rufende und
  Signalisierung,
- verbindliche VoiceOver- und Konfigurationstrennungs-Anforderungen.
- empfangsseitige, austauschbare Software-Vocoder-Grenze,
- nativer AMBE+2-2450/1150-Decoder ohne Encode-/Sendeoberfläche,
- deterministische AMBE-zu-PCM-Referenzprüfung.
- begrenzte, rein empfangende TG91/Timeslot-2-Audioausgabe mit Jitterpuffer.
- verriegeltes, nur offline vorbereitetes privates Parrot-Testprofil für
  Ziel 9990/Timeslot 2 mit festen 10-/15-Sekunden-Grenzen.

Das frühere automatisierte TG91-Gruppenrufwerkzeug ist dauerhaft deaktiviert
und besitzt keinen Sendeloop mehr. Der neue Parrot-Executor ist ausschließlich
auf das verriegelte private Profil begrenzt.

Nicht enthalten sind Aufnahme/Persistenz, ein allgemeiner AMBE-Encoder,
Audioübertragung oder eine Laufzeit-PTT-Schnittstelle. Die bestehende
BrandMeister-Anmeldung bleibt unverändert. Die Nutzerin muss die subjektive
Sprachverständlichkeit noch praktisch bestätigen.

Die produktive Software-ID bleibt `20260728_CarenDMR`.
Die BrandMeister-Login-only-Prüfung mit `MMDVM_HS_Hat` war erfolgreich.

Die acht Payloads wurden bytegenau gegen DroidStar-Referenzcode geprüft.
Historische Live-Diagnosen ändern diese neue dauerhafte Sicherheitsregel nicht.
Der genau einmal autorisierte private Parrot-Test wurde erfolgreich
abgeschlossen: acht Pakete in 0,440 Sekunden, sechs Echo-Sprachbursts,
18 dekodierte AMBE-Codewörter, 2.880 lokale PCM-Samples, keine Dekodier- oder
DMRD-Fehler, kein Timeout und vollständige Bereinigung. Es gab keinen Retry.
Die ausgehende Fixture enthielt nur das validierte Stummmuster.

Teststatus: 122 Tests erfolgreich; nativer macOS-Build und Symbolprüfung
erfolgreich.
