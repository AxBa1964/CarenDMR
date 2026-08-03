# CarenDMR UX Guide

## Grundsatz

Alle vorhandenen Funkfunktionen bleiben während des Redesigns nutzbar. Die Oberfläche löst ausschließlich Befehle der Anwendungsschicht aus und implementiert keine DMR-Protokolllogik.

## Betrieb

- CONNECT verbindet, DISCONNECT trennt.
- TG, Timeslot und Rufart werden gemeinsam über **TG wechseln** übernommen.
- TX ist ein rastender Toggle: blau AUS, rot EIN.
- Nach TX wird der vorherige Empfang automatisch wiederhergestellt.
- Nach 60 Sekunden beendet die Sicherheitsabschaltung TX.
- Stumm unterdrückt nur die lokale Ausgabe; Empfang und Historie laufen weiter.

## Rückmeldungen

- Keine Bestätigungsdialoge für normale Aktionen.
- Ereignisse werden mit Zeitstempel protokolliert.
- Fehler, die eine Benutzereingabe erfordern, dürfen als Dialog erscheinen.
- Diagnosemeldungen sind standardmäßig aus.
