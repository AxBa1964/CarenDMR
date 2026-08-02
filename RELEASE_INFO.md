# CarenDMR 0.0.19.4.2 – TG91-Sitzungsabonnement wiederhergestellt

## Zweck

Dieses Qualitätsrelease korrigiert die Hold-to-Talk-Bedienung und entfernt überholte lokale Entwicklungsfunktionen aus der Benutzeroberfläche.

## Enthalten

- TX gedrückt halten: Aufnahme läuft
- TX loslassen: Aufnahme endet sofort, anschließend Kodierung und Versand
- flexibles TX-Sicherheitslimit von 5 bis 180 Sekunden; Standard 15 Sekunden
- fest verriegelter Privatruf an DMR-ID 9990, Timeslot 2
- bereinigte Sendeoberfläche ohne Testaufnahme-, Wiedergabe- und Loopback-Schaltflächen
- hörbarer abgestimmter Audio-Optimizer V1
- Sendehistorie und Parrot-Echo bleiben erhalten
- plattformneutraler Kern für Windows, macOS, Linux und Raspberry Pi OS

## Sicherheitsgrenze

Keine freie Zielwahl, keine Gruppenrufe und keine normalen Talkgroup-Aussendungen.


## Fehlerkorrektur 0.0.19.4.2

- TG91-Gruppenverkehr wird eingehend auf TS1 und TS2 angenommen.
- Nach einem Parrot-Test wird ein zuvor aktiver TG91-Empfang automatisch wiederhergestellt.
- Keine neue Fachfunktion.

## Technische Ursache

Der Homebrew-Login war authentifiziert, sendete aber keine DroidStar-kompatiblen RPTO-Optionen. Dadurch kamen nur Steuerdatagramme, jedoch kein abonnierter TG91-Sprachstrom an. CarenDMR sendet nun nach RPTC das Sitzungsabonnement `TS2=91`.
