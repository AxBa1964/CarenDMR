# CarenDMR 0.0.12 – Begrenzte Live-Empfangswiedergabe

## Zweck und Sicherheitsgrenze

Der 0.0.11-Softwaredecoder speist erstmals die lokale Standard-Audioausgabe.
Der Pfad ist fest auf empfangene Gruppenrufe für TG91, Timeslot 2 begrenzt.

Das Werkzeug `tools/brandmeister_listen.py`:

- meldet sich mit der bestehenden lokalen Konfiguration an,
- öffnet die lokale Standard-Audioausgabe mit 8 kHz, mono, signed 16 bit,
- prüft den Ausgabepfad kurz mit lokal synthetisierten PCM-Samples,
- empfängt höchstens 60 Sekunden,
- dekodiert und spielt ausschließlich Ziel-Sprachrahmen,
- schließt Decoder, UDP-Kanal und Audiostream in jedem Ausführungspfad.

Es besitzt keinen DMRD-Sendeaufruf, keine Aufnahme, keine Dateiablage, keinen
Upload und keine Dashboard-/Konfigurationsänderung. Der normale
BrandMeister-Anmelde- und Abmelde-Handshake bleibt erforderlich.

## Pufferung

`DmrJitterBuffer` ordnet DMRD-Sequenznummern modulo 256. Drei 60-ms-Bursts
werden vorgepuffert. Innerhalb eines kleinen Fensters dürfen UDP-Bursts
umsortiert eintreffen. Bleibt eine Lücke nach dem Fenster bestehen, wird genau
ein 480-Sample-Stilleburst eingesetzt, damit Zeitachse und nachfolgende
Pakete stabil bleiben. Späte Duplikate werden verworfen.

`BufferedPcmOutput` hält höchstens zwei Sekunden PCM. Der PortAudio-Callback
blockiert den Netzwerkempfang nicht. Bei Unterlauf liefert er Stille; bei
Überlauf werden die ältesten vollständigen Samples verworfen, damit die
Wiedergabe nicht immer weiter hinter dem Live-Empfang zurückbleibt.

## Praktische Abnahme

Die lokale Syntheseprüfung öffnete und schloss das Standardgerät erfolgreich.
Im begrenzten Live-Test wurden sicher aggregiert beobachtet:

- 410 Datagramme,
- 407 TG91/Timeslot-2-Sprachbursts,
- 1.221 dekodierte AMBE-Codewörter,
- 195.360 zur Ausgabe übergebene PCM-Samples,
- null Dekodierfehler,
- 17 vom Decoder gemeldete korrigierte Fehler,
- null verdeckte fehlende Bursts,
- null ungültige DMRD-Pakete,
- null gesendete DMRD-Pakete.

Es wurden keine Sprachinhalte, Identitäten, Payloads oder privaten
Verbindungswerte gespeichert oder protokolliert. Die Zahlen bestätigen den
technischen Daten- und Ausgabepfad. Ob reale Sprache subjektiv verständlich
ist, bleibt eine getrennte Nutzerabnahme.
