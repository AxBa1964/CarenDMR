# CarenDMR

CarenDMR ist ein bewusst einfacher, barrierearmer DMR-Client für das
BrandMeister-Netzwerk. Das Programm wird zunächst für Caren entwickelt.

CarenDMR ist nach einer blinden Person benannt. Vollständige
VoiceOver-Bedienbarkeit ist eine verbindliche Produktanforderung für jede
zukünftige Oberfläche, nicht nur eine ergänzende Funktion. Die prüfbaren
Anforderungen stehen in `docs/ACCESSIBILITY_REQUIREMENTS.md`.

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

CarenDMR 0.0.13 enthält:

- den bestätigten BrandMeister-Login,
- Empfang und strikte Modellierung von DMRD-Paketen,
- eine bytegenau gegen DroidStar geprüfte stumme TG91/Timeslot-2-Fixture,
- eine payloadfreie Empfangsereignisgrenze für spätere Statusverbraucher,
- eine austauschbare, empfangsseitige Software-Vocoder-Grenze,
- einen auf AMBE+2 2450/1150 begrenzten nativen mbelib-Decoder und
  deterministisch geprüfte PCM-Referenzvektoren,
- einen begrenzten, rein empfangenden TG91/Timeslot-2-Live-Monitor mit
  Jitterpuffer und Ausgabe auf das Standard-Wiedergabegerät,
- ein ausschließlich offline vorbereitetes, hart auf privaten BrandMeister-
  Parrot-Ruf 9990/Timeslot 2 verriegeltes Testprofil.

Eine allgemeine PTT-Schnittstelle, Sprachkodierung und die spätere
Benutzeroberfläche sind noch nicht enthalten. Die technische Live-Wiedergabe
ist bestätigt; die subjektive Sprachverständlichkeit muss die Nutzerin noch
praktisch beurteilen.

Automatisierte Sendetests auf öffentlichen Gruppen-Talkgroups sind dauerhaft
verboten. Ein späterer kontrollierter Test darf ausschließlich Parrot als
Privatruf auf 9990/Timeslot 2 verwenden, höchstens 10 Sekunden senden und
höchstens 15 Sekunden auf das Echo warten. Der getrennte Live-Executor besitzt
keine Ziel- oder Zeitparameter, keinen Retry und keinen öffentlichen Fallback.
Der einmalig autorisierte private Test wurde erfolgreich abgeschlossen; die
gesendete Fixture war stumm und das zurückkehrende Echo wurde lokal über den
Software-Empfangspfad ausgegeben.

Der lokale native Decoder wird auf macOS mit `make -C native check` gebaut.
Die erzeugte Bibliothek ist ein ignoriertes Build-Artefakt und wird nicht in
Git aufgenommen.

## Lizenz

CarenDMR wird unter der GNU General Public License, Version 3 oder später,
bereitgestellt. Der vollständige Lizenztext steht in `LICENSE`.

Die auf DroidStar zurückgehenden DMR-Kodierhilfen und ihre Herkunft sind in
`docs/UPSTREAM_PROVENANCE.md` dokumentiert. Bei Weitergabe müssen der
vollständige korrespondierende Quellcode, Lizenztext und Urheberhinweise
erhalten bleiben.
