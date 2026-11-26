# CarenDMR – Bedien-Tastenfeld für Caren (Konzept, Stand 14.11.2026)

Ziel: kleines USB-Tastenfeld, mit dem Caren (blind) die wichtigsten Funktionen von CarenDMR bedient – TG wechseln, Lautstärke, Status, PTT – mit Ton- und Vibrationsquittung.

## Entschieden
- **Mikrocontroller: Waveshare RP2040-Zero** (USB-C, steckt beidseitig – wichtig für Blinde; RGB-LED GP16 als Statusanzeige für Sehende). Pico 2 H nur als Steckbrett-Testaufbau. Gesteckt in **zwei 1×9-Buchsenleisten (RM 2,54)** an den beiden Längsseiten; untere Reihe (GP9–GP13) wird nicht genutzt.
- **Taster: Gateron Brown, taktil, 55 gf**, 3-Pin-Plattenmontage (2 Metallkontakte + Mittelzapfen) → rasten in gedruckter Deckplatte ein (MX-Ausschnitt 14 × 14 mm, Platte 1,5 mm, Raster 19,05 mm; per Probedruck justieren), Litze direkt angelötet, keine Platine.
- **PTT: breite Taste wie Leertaste, zwei Taster parallel** (ein GPIO), ca. 3 Tastenbreiten (~57 mm), Tasterabstand parametrisch (Start 38 mm). Doppelte Kraft in der Mitte = Schutz gegen versehentliches Senden; mit Caren testen.
- **Braille nach Standardmaßen:** Punktabstand 2,5 mm, Zellenabstand 6,0 mm, Zeilenabstand 10,0 mm, Punkthöhe 0,5 mm, Basisdurchmesser 1,5 mm – als Parameter im Modell. Zusätzlich unterschiedliche Kappenformen + Orientierungsnoppen.
- **Audio: PAM8302 (Klasse-D, mono) + Lautsprecher Zuahaly 3 W / 8 Ω** (Kapsel-Lautsprecher mit eigenem Gehäuse, ca. 70 × 30 × 15 mm laut Händler, 4 Befestigungslöcher, JST-PH2.0-Stecker, 50 cm Kabel). Eigene Kammer → nur Lochgitter vor der Membran. Quer an der Rückseite hinter den Tasten. Audio− an GND, Audio+ an PWM, SD an GPIO (stumm zwischen Tönen). Lautstärke in Firmware begrenzen (USB-Budget). PAM8302-Nachbau ok, muss Trimmpoti und SD-Pin haben.
- **Vibration: DAOKAI Vibrationsmotormodul DC 5 V** (Münzmotor auf Platine mit Treiberstufe, IN/VCC/GND, High-Pegel-Trigger, PWM-steuerbar, ca. 30 × 21–23 mm, 2 Befestigungslöcher). VCC an 5 V, IN an GPIO. Ob 3,3-V-Pegel sicher schaltet, beim ersten Test prüfen (sonst BC337 davor). Fest an die Bodenschale schrauben.
- **Anbindung: USB-CDC seriell** (nicht HID) – fokusunabhängig, keine Konflikte mit Screenreader-Kürzeln, Rückkanal für Quittungen.
- **Firmware: CircuitPython**, Pin-Belegung in eigener Datei (Board austauschbar).
- **Drucker:** Bambu Lab H2S; Gehäuse PETG/PLA, TPU-Füße, Zusatzgewicht, Lochgitter für Lautsprecher, Loch für BOOT, USB-C-Ausgang mit Zugentlastung, Einschmelzmuttern für den Deckel.

## Pin-Belegung (RP2040-Zero, nur Längsseiten)
| Funktion | Pin |
|---|---|
| Funktionstasten 1–6 | GP0–GP5 (Pull-up, gegen GND) |
| PTT (2 Taster parallel) | GP6 |
| Audio PWM → PAM8302 A+ | GP7 |
| PAM8302 SD | GP8 |
| Vibrationsmodul IN | GP26 |
| RGB-LED | GP16 (onboard) |
| 5 V → PAM8302 Vin, Vibrationsmodul VCC | 5V-Pin |

## Protokoll (Entwurf)
- Gerät → PC: `KEY n DOWN`, `KEY n UP`, `KEY n LONG`, `HELLO CARENKEY <version>`
- PC → Gerät: `ACK`, `ERR`, `VIB <ms>`, `TONE <Hz> <ms>`, `HELLO`
- Lokal: kurzer Vibrationsimpuls bei jedem Tastendruck; Quittung (hoch = OK, tiefer Doppelton + lange Vibration = Fehler) kommt von CarenDMR.

## CarenDMR-Erweiterung (gesammelt, Umsetzung erst nach „jetzt umsetzen“)
- Qt-freier `KeypadService` in der Application-Schicht; Geräteerkennung, Reconnect; Befehle nur über `OperatingController`.
- Belegung in `config/keypad.local.json` (+ `.example.json`).
- Ansagen über bestehenden Screenreader-Weg.
- Prüfen, ob `pyserial` in requirements ist.

## Offen
- 5 oder 6 Funktionstasten + PTT; Belegung kurz/lang mit Caren abstimmen
- Nach Lieferung nachmessen: Lautsprecher und Vibrationsmodul (Außenmaß, Lochabstand, Schraubengröße)

## Bestellliste
- Lautsprecher Zuahaly 3 W / 8 Ω
- PAM8302-Modul (mit Trimmpoti + SD-Pin)
- Vibrationsmodul DAOKAI 5 V
- Buchsenleisten RM 2,54 (2 × 1×9)
- USB-C-**Daten**kabel
- Schrauben M2/M2,5 (nach Nachmessen), M3 + Einschmelzmuttern für Deckel
- optional: JST-PH2.0-Buchse, TPU-Filament oder Gummifüße, Gewicht
