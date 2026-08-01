# Changelog

## 0.0.18.3 – Audio-Komfort

- Empfangslautstärke auf 0 bis 400 Prozent erweitert.
- Zuschaltbare langsame AGC für gleichmäßigere Sprachlautheit ergänzt.
- Soft-Limiter und DMR-Ausgangspegelanzeige ergänzt.
- DMR-Audio während der lokalen Testwiedergabe automatisch stummgeschaltet und danach wieder freigegeben.
- Mikrofonverstärkung, Ausgabelautstärke, Benutzer-Mute und AGC lokal gespeichert.
- Samplegenaue fünfsekündige Testaufnahme und verzögertes Speichern der Reglerwerte beibehalten.
- Keine PTT, kein AMBE-Encoder und keine DMRD-Sendefunktion ergänzt.

## 0.0.18 – Lokaler Audio-Sendepfad

- Eigenen, von Empfang und GUI getrennten `AudioSendService` ergänzt.
- Mikrofone in der GUI einlesen und auswählen.
- Fünfsekündige PCM-Testaufnahme mit 16 kHz, Mono und Pegelanzeige ergänzt.
- Lokale Wiedergabe der Testaufnahme und viersekündigen Loopback-Test ergänzt.
- Diagnose für Gerät, Samplerate, Kanalzahl, Sampleanzahl und Spitzenpegel ergänzt.
- Keine PTT, kein AMBE-Encoder und keine DMRD-Sendefunktion ergänzt.
- Vollständige Testreihe auf 157 Tests erweitert.

## 0.0.17 – Dauerempfang und QSO-Historie

- Periodischen BrandMeister-Heartbeat während des Live-Empfangs ergänzt; MSTPONG-Antworten werden im gemeinsamen Empfangskanal sicher verarbeitet.
- GUI-Empfang läuft ohne feste Zeitgrenze bis Trennen oder Programmende.
- Eigenen barrierefrei per Tastatur erreichbaren Reiter „QSO-Historie“ ergänzt.
- Abgeschlossene Sprechdurchgänge lokal in `data/qso_history.db` gespeichert.
- Historie zeigt Zeit, Rufzeichen, Name, Land, DMR-ID, Talkgroup/Timeslot und Dauer.
- SQLite-Verbindungen werden explizit geschlossen; lokale Historie bleibt aus Git und Release ausgeschlossen.
- Keine Sendefunktion ergänzt.

## 0.0.15 – Aktuelle Station und Live-QSO-Informationen

- Aktuellen DMR-Sprecher als UI-unabhängiges Domain-Modell ergänzt.
- Sprechbeginn, Sprecherwechsel und Sprechende aus dem vorhandenen DMRD-Empfang abgeleitet.
- DMR-ID, Talkgroup, Timeslot und laufende Sprechdauer im Hauptfenster angezeigt.
- Sprecherwechsel und beendete Sprechdurchgänge im zugänglichen Ereignisprotokoll ergänzt.
- Identische Sprecherinformationen im Konsolenempfang ausgegeben.
- Application-Service zwischen Bedienoberfläche und Empfangstechnik ergänzt; keine GUI-Abhängigkeit in Netzwerk, Decoder oder Audio.
- Keine externe Kontaktdatenbank, keine neue Sendefunktion und keine Änderung der Projektstruktur.

## 0.0.14.1 – Konsistente Betriebszustände

- BrandMeister-Verbindung, Empfang und Audio in der GUI getrennt dargestellt.
- Erfolgreiche Anmeldung und Start des TG91/TS2-Empfangs werden einmalig im Ereignisprotokoll bestätigt.
- Veralteten Eindruck „Verbindung wird hergestellt“ bei bereits laufendem Empfang beseitigt.
- Keine DMR-, Netzwerk-, Decoder- oder Sendefunktion geändert.

## 0.0.13.5 – Längerer TG91-Empfang und Windows-Buildbereinigung

- Rein empfangenden TG91-/Timeslot-2-Lauf ohne feste 60-Sekunden-Grenze ergänzt; Ende mit Strg+C.
- Option `--duration` für begrenzte Läufe zwischen 1 und 3600 Sekunden ergänzt.
- Laufende Diagnoseausgabe im 30-Sekunden-Intervall ergänzt.
- Sauberes Schließen von Netzwerk, Decoder und Audio nach Strg+C automatisiert geprüft.
- Windows-Buildskript für MSYS2-UCRT64 korrigiert: Compilererkennung, Laufzeitpfad und mathematische Konstanten.
- Keine Sendeoberfläche und keine DMRD-Aussendung ergänzt.

## 0.0.13.4 – Windows-Empfangsdecoder

- Windows-DLL-Pfad für den nativen mbelib-Empfangsdecoder ergänzt.
- Reproduzierbares PowerShell-Buildskript für MSYS2/MinGW-w64 ergänzt.
- DLL-Exporte auf exakt drei reine Empfangsfunktionen begrenzt und geprüft.
- Native DLLs aus Release-ZIPs ausgeschlossen.
- Windows-Installation, Deployment und Live-Empfang dokumentiert.
- Keine neue DMR-, Netzwerk-, Audio- oder Sendefunktion ergänzt.

## 0.0.13.3 – Reproduzierbarer TG91-Live-Empfang

- Vorhandenen rein empfangenden TG91-/Timeslot-2-Pfad über `python main.py --listen` eindeutig erreichbar gemacht.
- Laufzeit weiterhin fest auf maximal 60 Sekunden begrenzt.
- Start- und Abschlussausgabe für Authentifizierung, Audio, Sprachbursts, AMBE-Dekodierung und Ressourcenabschluss vereinheitlicht.
- Fehlerpfad bestätigt weiterhin ausdrücklich, dass kein DMRD-Paket gesendet wurde.
- Automatisierte Einstiegspunkt- und Fail-Closed-Tests ergänzt.
- Keine neue DMR-, Netzwerk-, Audio- oder Sendefunktion ergänzt.

## 0.0.13.2 – Verifizierbare Projektbasis

- Python-Paketstruktur korrigiert: sämtliche Laufzeitmodule liegen wieder unter `carendmr/`.
- Native mbelib-Buildprüfung für macOS und Linux portabel gemacht.
- Veralteten Hinweis entfernt, dass noch keine BrandMeister-Verbindung existiere.
- Startstatus an den vorhandenen BrandMeister-Login und DMR-Empfang angepasst.
- Vollständige automatisierte Testreihe und Release-ZIP-Erstellung verifiziert.
- Keine DMR-, Netzwerk-, Audio- oder Sendefunktion geändert.

## 0.0.13.1 – Project Foundation

- README als zentralen Einstieg für Ziel, Stand, Sicherheit, Installation,
  Dokumentation und Lizenz überarbeitet.
- Roadmap und Beitragsrichtlinien ergänzt.
- getrennte Installationsanleitungen für macOS, Windows und Linux ergänzt.
- Architektur auf den tatsächlichen Stand mit BrandMeister, DMRD-Empfang,
  Software-Vocoder, Jitterpuffer und verriegeltem Parrot-Test aktualisiert.
- Release-, Test-, Commit- und Pull-Request-Ablauf vereinheitlicht.
- Keine DMR-, Netzwerk-, Audio- oder Sendefunktion geändert.

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
