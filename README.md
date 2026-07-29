# CarenDMR

CarenDMR ist ein bewusst einfacher, barrierearmer DMR-Client für das
BrandMeister-Netzwerk. Das Programm wird zunächst für Caren entwickelt.

## Festes Projektziel

CarenDMR soll:

- sich mit BrandMeister verbinden,
- Talkgroup 91 hörbar empfangen,
- per gedrückter PTT verständlich auf Talkgroup 91 senden,
- vollständig per Tastatur und später per externer USB-Bedieneinheit
  bedienbar sein,
- wichtige Zustände akustisch melden,
- unter Windows und später unter macOS laufen.

CarenDMR ist kein allgemeines Digitalfunk-Framework. Andere Betriebsarten
wie D-Star, YSF, P25 oder NXDN gehören ausdrücklich nicht zum Projektumfang.

## Aktueller Entwicklungsstand

CarenDMR 0.0.9 enthält:

- den bestätigten BrandMeister-Login,
- Empfang und strikte Modellierung von DMRD-Paketen,
- eine bytegenau gegen DroidStar geprüfte stumme TG91/Timeslot-2-Fixture,
- ein ausschließlich für einen einzelnen kontrollierten Einmaltest
  vorgesehenes, sicherheitsbegrenztes Diagnosewerkzeug.

Eine allgemeine PTT-Schnittstelle, Sprachkodierung und die spätere
Benutzeroberfläche sind noch nicht enthalten.

## Lizenz

CarenDMR wird unter der GNU General Public License, Version 3 oder später,
bereitgestellt. Der vollständige Lizenztext steht in `LICENSE`.

Die auf DroidStar zurückgehenden DMR-Kodierhilfen und ihre Herkunft sind in
`docs/UPSTREAM_PROVENANCE.md` dokumentiert. Bei Weitergabe müssen der
vollständige korrespondierende Quellcode, Lizenztext und Urheberhinweise
erhalten bleiben.
