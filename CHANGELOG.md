# Changelog

## 0.0.13 – Verriegeltes privates Parrot-Testprofil

- Dauerhafte Sicherheitsregel ergänzt: automatisierte Sendetests dürfen
  niemals eine öffentliche Gruppen-Talkgroup verwenden.
- Offline-Profil hart auf BrandMeister Parrot, Ziel 9990, Privatruf und
  Timeslot 2 verriegelt.
- Maximale zukünftige Sendezeit auf 10 Sekunden und Echo-Beobachtung auf
  exakt 15 Sekunden festgesetzt, ohne Laufzeitparameter.
- Privatrufbit und Voice-LC-FLCO bytegenau mit Referenzpayloads geprüft.
- Früheres automatisiertes TG91-Gruppenrufwerkzeug dauerhaft fail-closed
  deaktiviert und seinen Sendeloop entfernt.
- Genau einen autorisierten privaten Live-Test ausgeführt: acht Pakete in
  0,440 Sekunden, sechs Echo-Sprachbursts, keine Wiederholung und vollständige
  Bereinigung.
- Lokale gesprochene Phasenansagen und Echoausgabe über den bestehenden
  Software-Empfangspfad bestätigt; die gesendete Fixture blieb stumm.

## 0.0.12 – Begrenzte Live-Empfangswiedergabe

- Callback-gesteuerte, auf zwei Sekunden begrenzte PCM-Ausgabe für das
  Standard-Wiedergabegerät ergänzt.
- DMRD-Sequenzpuffer mit drei Bursts Vorlauf, kleiner Umsortierung und
  Stille-Verdeckung fehlender Bursts ergänzt.
- Empfangsdecoder ausschließlich für TG91/Timeslot 2 an die lokale
  Audioausgabe angebunden.
- 180-ms-Syntheseprüfung sowie begrenzten 60-s-Live-Empfang erfolgreich
  ausgeführt.
- Im Live-Test 407 Sprachbursts und 1.221 AMBE-Codewörter ohne Dekodierfehler
  verarbeitet; kein DMRD-Paket gesendet.
- Keine Aufnahme-, Persistenz-, Upload-, Dashboard- oder TX-Funktion ergänzt.

## 0.0.11 – Empfangsseitiger Software-Vocoder

- Austauschbare, zustandsbehaftete Empfangs-Vocoder-Grenze ergänzt.
- Drei AMBE+2-Codewörter evidenzgetreu aus jedem DMR-Sprachburst extrahiert.
- Minimalen nativen DroidStar/mbelib-Decoder für AMBE 2450/1150 auf macOS
  isoliert; Encoder, MD380-Firmware und Codec2 bleiben ausgeschlossen.
- Nicht-personalen Stummvektor deterministisch in 480 PCM-Samples dekodiert
  und Ergebnis, Fehleranzahl sowie ungültige Eingaben automatisiert geprüft.
- ISC-Hinweise, geprüften Upstream-Commit und getrennte Patentprüfung
  dokumentiert.
- Keine Wiedergabe, Live-Sprachbewertung, Netzwerk- oder Sendefunktion ergänzt.

## 0.0.10 – Empfangsereignisse und Accessibility-Anforderungen

- Live beobachtete DMRD-Ablehnungen strukturell und ohne Nutzdaten untersucht:
  gültige 55-Byte-Pakete mit Stream-ID null statt Transportmüll.
- Empfangsparser akzeptiert Stream-ID null als fehlende Metainformation;
  lokale Paketkonstruktion verlangt weiterhin eine von null verschiedene ID.
- Payloadfreie, unveränderliche `DmrdReceiveEvent`-Grenze für Rufbeginn,
  Sprache, Rufende und Signalisierung ergänzt.
- Vollständige VoiceOver-Bedienbarkeit und die Trennung sensibler
  Verbindungseinrichtung von der Betriebsansicht als verbindliche
  Produktanforderungen dokumentiert.
- Empfangsverifikation nach der Änderung ohne Parserablehnung abgeschlossen.
- Keine GUI, Audio-/AMBE-Dekodierung oder neue Sendefunktion ergänzt.

## 0.0.9 – Deterministische DMR-Stummruf-Fixture

- Projektlizenz bewusst als GPLv3-or-later festgelegt.
- Herkunft und Lizenzgrenze der minimal adaptierten DroidStar-DMR-Hilfen
  dokumentiert.
- Offline-Kodierung für Voice-LC-Header, einen aus sechs Bursts bestehenden
  AMBE-Stummrahmen und Terminator-with-LC ergänzt.
- Ziel unverändert fest auf Gruppenruf TG91, Timeslot 2 und Color Code 1
  begrenzt.
- Alle 33-Byte-Payloads bytegenau gegen einen unabhängigen DroidStar-C++-
  Referenzgenerator geprüft.
- Separates, fest auf eine einzige Acht-Paket-Sequenz begrenztes
  Live-Diagnosewerkzeug mit Anmeldung, 60-ms-Taktung, Empfangsmonitor und
  garantiertem Schließen ergänzt.
- Erfolgreicher kontrollierter Einmaltest ohne Wiederholung bestätigt.
- Keine allgemeine Laufzeit-Sendeschnittstelle, kein Audio und keine
  BrandMeister-Konfigurationsänderung ergänzt.

## 0.0.8.1 – BrandMeister-Gerätekennung

- Produktive Package-ID von der projektspezifischen Kennung auf
  `MMDVM_HS_Hat` umgestellt.
- Software-ID `20260728_CarenDMR` unverändert beibehalten.
- Beispielkonfiguration, lokale Laufzeitkonfiguration, Tests und
  Kompatibilitätsdokumentation angeglichen.
- Login-only-Prüfung mit `MMDVM_HS_Hat` erfolgreich gegen BrandMeister
  bestätigt.
- DMRD-Paketdomäne aus 0.0.8 bleibt unverändert und weiterhin ohne
  Netzwerksendeschnittstelle.

## 0.0.8 – DMRD-Paketdomäne

- Unveränderliches Modell für vollständige 55-Byte-DMRD-Pakete ergänzt.
- Strikte Empfangsprüfung für Kennung, Länge, IDs, Timeslot, Ruftyp,
  Rahmenklasse, Stream-ID und 33-Byte-DMR-Nutzdaten implementiert.
- Sprach-LC-Header, Sprach-Synchronrahmen, Sprachrahmen 0 bis 5 und
  Terminator-with-LC als getrennte Konstruktionsprimitive ergänzt.
- Zielbetrieb auf Gruppenruf TG91, Timeslot 2, als explizite und getestete
  Konstante festgelegt.
- Netzwerkversand, Talkgroup-Aktivierung, LC-Kodierung, AMBE und Audio bleiben
  bewusst außerhalb dieses Meilensteins.

## 0.0.7.6 – Eigene BrandMeister-Kennung

- Produktive Software-ID auf `20260728_CarenDMR` gesetzt.
- Produktive Package-ID auf `MMDVM_CarenDMR_PC` gesetzt.
- Beschreibung auf `CarenDMR Digital Voice Client` gesetzt.
- Konfigurationsprüfung für die experimentell bestätigten BrandMeister-Formate ergänzt.
- Vollständige Testmatrix in `docs/BRANDMEISTER_COMPATIBILITY.md` dokumentiert.
- Diagnoseparameter aus 0.0.7.5 bleiben erhalten.

## 0.0.7.5 – Freie RPTC-Kennungen testen

- `brandmeister_check.py` um `--software-value` und `--package-value` erweitert.
- Beliebige Software- und Package-IDs können einzeln gegen das akzeptierte Referenzprofil getestet werden.
- Gegenseitig widersprüchliche Parameter werden mit einer verständlichen Fehlermeldung abgewiesen.
- Zusätzliche Regressionstests für frei gewählte Kennungen ergänzt.

## 0.0.7.4 – BrandMeister-RPTC-Diagnose

- `tools/brandmeister_check.py` um ein reproduzierbares DroidStar-Referenzprofil erweitert.
- Einzeltests für Software-ID, Package-ID, Beschreibung und URL ergänzt.
- Aktives RPTC-Profil wird vor dem Login vollständig angezeigt.
- Lokales Standardprofil bleibt ohne Parameter unverändert.
- 62 automatisierte Tests erfolgreich.

# 0.0.7.1

- RPTC-Koordinatenformat bytegenau an DroidStar angepasst.
- Regressionstest für das nicht-personale Koordinatenformat ergänzt.
- Lokale Konfigurationsdateien werden nicht im Update-Paket ausgeliefert.

# Änderungsverlauf

## 0.0.7 – BrandMeister-Login

- DroidStar-kompatiblen DMR-Master-Handshake implementiert
- `RPTL`, `RPTK`, `RPTC`, `RPTPING` und `RPTCL` implementiert
- SHA-256-Authentifizierung aus vier Byte Challenge plus Hotspot-Passwort
  implementiert
- `RPTACK`, `MSTNAK` und `MSTPONG` ausgewertet
- explizite Login-Zustände ergänzt
- lokales, von Git auszuschließendes BrandMeister-Konfigurationsformat ergänzt
- einmaliges Diagnosewerkzeug `tools/brandmeister_check.py` ergänzt
- Protokoll- und Clienttests ergänzt
- noch keine DMRD- oder Sprachdatenübertragung

## 0.0.6 – Netzwerkgrundlage

- UDP-Transport, DNS-Auflösung, Netzwerkdiagnose und Heartbeat-Grundlage

## 0.0.5.1 – Audio-Startfehler

- direkter Skriptstart korrigiert

## 0.0.5 – Audio

- Gerätescan, Speicherung und Selbsttest

## 0.0.4 – Core

- EventBus, StatusManager und Accessibility-Grundlage

## 0.0.3 – DroidStar-Analyse

- Architektur- und Protokollanalyse

## 0.0.2 – Release-Werkzeug

- Release-Erzeugung

## 0.0.1 – Projektgrundgerüst

- Projektstart

## 0.0.7.3 – BrandMeister-Referenztest

- Neuer Referenztest mit den exakt aus dem funktionierenden DroidStar-Mitschnitt ermittelten RPTC-Metadaten.
- Der Test verändert `config/brandmeister.local.json` nicht und übernimmt daraus nur Zugangsdaten und Rufzeichen.
- Referenzprofil mit nicht-personalen Testwerten für Beschreibung, URL,
  Software-/Package-ID und Koordinaten ergänzt.
