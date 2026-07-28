# Technisches Design 0.0.7.2 – Paketdiagnose

## Zweck

Der Paketlogger trennt Diagnose und Protokollimplementierung. Er verändert keine Netzwerkdaten, sondern erhält unmittelbar vor dem Senden beziehungsweise nach dem Empfangen dieselben unveränderten `bytes`.

## Komponenten

- `carendmr/network/packet_log.py`: generischer `PacketLogger` und ASCII-Paketerkennung
- `carendmr/brandmeister/client.py`: zentrale TX/RX-Hooks
- `tools/brandmeister_check.py`: standardmäßig aktivierte Diagnoseoberfläche

## Ausgabeformat

Jeder Block enthält Zeitstempel, Richtung (`TX`/`RX`), Protokoll, Pakettyp, Bytezahl, Offset, Hexwerte und druckbare ASCII-Zeichen. Nicht druckbare Bytes erscheinen als Punkt.

## Sicherheitsgrenze

Das BrandMeister-Passwort ist nie Bestandteil der gesendeten Pakete. Beim RPTK wird ausschließlich der SHA-256-Digest ausgegeben. Lokale JSON-Dateien werden nicht in Release-ZIPs aufgenommen.
