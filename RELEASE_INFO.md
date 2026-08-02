# CarenDMR 0.0.21.1 – Funkgeräte-Oberfläche

Version 0.0.21.1 ordnet die Oberfläche erstmals nach dem tatsächlichen Funkbetrieb statt nach technischen Teilsystemen.

## Enthalten

- Nur noch drei Hauptbereiche: **Betrieb**, **QSO-Historie** und **Einstellungen**.
- Empfang, TG-/TS-Umschaltung und PTT befinden sich gemeinsam auf der Betriebsseite.
- Große rastende TX-Taste: erster Klick startet TX und färbt die Taste rot; zweiter Klick beendet TX und führt anschließend automatisch zum Empfang zurück.
- Feste TX-Sicherheitsabschaltung nach 60 Sekunden.
- Der Sendepfad bleibt in dieser Version aus Sicherheitsgründen weiterhin auf Parrot 9990 / TS2 verriegelt.
- Mikrofon-, Audio-, Kontakt- und Encoderverwaltung befinden sich unter Einstellungen.
- Ein bereits zugeordnetes AMBE-Plugin wird beim Programmstart automatisch geladen und geprüft. Nur bei einem Fehler erscheint eine Meldung; Empfang bleibt dann verfügbar und TX gesperrt.
- Die QSO-Historie enthält bereits eine sichtbare Spalte für den künftigen Kontaktstatus. Automatische QSO-Erkennung und Logbuchableitung folgen später.
- Die funktionierende BrandMeister-, TG-/TS- und TX→RX-Logik aus 0.0.20.2 bleibt erhalten.

## Bewusste Abgrenzung

Die Version verändert nicht den AMBE-Sendecodec und gibt noch kein freies Senden auf die aktuell gewählte Talkgroup frei. Nach der Oberflächenprüfung folgt die Härtung des Funkkerns und erst danach der reale Test mit einer befreundeten Station.
