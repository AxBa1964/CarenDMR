# 0.0.7.1

- RPTC-Koordinatenformat bytegenau an DroidStar angepasst.
- Regressionstest für `52.31000` und `10.470000` ergänzt.
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
