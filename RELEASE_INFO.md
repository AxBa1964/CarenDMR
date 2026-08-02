# CarenDMR 0.0.19.7 – Hold-to-Talk und Sendeoberfläche

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


## Schwerpunkt 0.0.19.7

Dynamische Auswahl und Aktivierung einer Empfangs-Talkgroup über das bestehende BrandMeister-Homebrew-UDP-Protokoll. Es wird kein API-Key verwendet.
