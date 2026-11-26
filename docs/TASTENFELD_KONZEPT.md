# CarenDMR – Bedien-Tastenfeld für Caren (Konzept, Stand 14.11.2026)

Ziel: kleines USB-Tastenfeld, mit dem Caren (blind) die wichtigsten Funktionen von CarenDMR bedient – TG wechseln, Lautstärke, Status, PTT – mit Ton- und Vibrationsquittung.

## Entschieden
- **Mikrocontroller: Raspberry Pi Pico H (RP2040)** (entschieden 26.11.2026; beide vorhandenen Boards sind Pico H, keine Pico 2 H – gleiche Pinbelegung; ersetzt den RP2040-Zero). Grund: genug GPIOs für 12 Tasten + Audio + Vibration, Erfahrung vorhanden. Micro-USB → **fest eingebautes USB-Kabel mit Zugentlastung**, Caren steckt nur am PC ein. Stiftleisten bestückt → gesteckt in zwei 1×20-Buchsenleisten (vorhanden). Onboard-LED GP25 (einfarbig) als Statusanzeige für Sehende.
- **Taster: Gateron Brown, taktil, 55 gf**, 3-Pin-Plattenmontage (2 Metallkontakte + Mittelzapfen) → rasten in gedruckter Deckplatte ein (MX-Ausschnitt 14 × 14 mm, Platte 1,5 mm, Raster 19,05 mm; per Probedruck justieren), Litze direkt angelötet, keine Platine.
- **PTT: breite Taste wie Leertaste, zwei Taster parallel** (ein GPIO), ca. 3 Tastenbreiten (~57 mm), Tasterabstand parametrisch (Start 38 mm). Doppelte Kraft in der Mitte = Schutz gegen versehentliches Senden; mit Caren testen.
- **Braille nach Standardmaßen:** Punktabstand 2,5 mm, Zellenabstand 6,0 mm, Zeilenabstand 10,0 mm, Punkthöhe 0,5 mm, Basisdurchmesser 1,5 mm – als Parameter im Modell. Zusätzlich unterschiedliche Kappenformen + Orientierungsnoppen.
- **Audio: PAM8302 (Klasse-D, mono) + Lautsprecher Zuahaly 3 W / 8 Ω** (Kapsel-Lautsprecher mit eigenem Gehäuse, ca. 70 × 30 × 15 mm laut Händler, 4 Befestigungslöcher, JST-PH2.0-Stecker, 50 cm Kabel). Eigene Kammer → nur Lochgitter vor der Membran. Quer an der Rückseite hinter den Tasten. Audio− an GND, Audio+ an PWM, SD an GPIO (stumm zwischen Tönen). Lautstärke in Firmware begrenzen (USB-Budget). PAM8302-Nachbau ok, muss Trimmpoti und SD-Pin haben.
- **Vibration: DAOKAI Vibrationsmotormodul DC 5 V** (Münzmotor auf Platine mit Treiberstufe, IN/VCC/GND, High-Pegel-Trigger, PWM-steuerbar, ca. 30 × 21–23 mm, 2 Befestigungslöcher). VCC an 5 V, IN an GPIO. Ob 3,3-V-Pegel sicher schaltet, beim ersten Test prüfen (sonst BC337 davor). Fest an die Bodenschale schrauben.
- **Anbindung: USB-CDC seriell** (nicht HID) – fokusunabhängig, keine Konflikte mit Screenreader-Kürzeln, Rückkanal für Quittungen.
- **Firmware: CircuitPython**, Pin-Belegung in eigener Datei (Board austauschbar).
- **Drucker:** Bambu Lab H2S; Gehäuse **PETG** (kein PLA), TPU-Füße, Zusatzgewicht, Lochgitter für Lautsprecher, Loch für BOOTSEL, Kabelausgang (fest eingebautes USB-Kabel) mit Zugentlastung, Einschmelzmuttern für den Deckel.

## Pin-Belegung (Pico H, gilt auch für Pico 2 H)
Verdrahtungsplan mit Stiftnummern: `hardware/keypad/README.md`.

Frei nutzbar sind GP0–GP22 und GP26–GP28 (GP23/24/25/29 sind auf dem Board
intern belegt). Alle Tasten mit internem Pull-up gegen GND.

| Funktion | Pin |
|---|---|
| PTT (2 Taster parallel) | GP0 |
| Lauter / Leiser | GP1 / GP2 |
| TG vor / TG zurück | GP3 / GP4 |
| Favorit 1–4 | GP5–GP8 |
| Verbinden | GP9 |
| Trennen | GP10 |
| Beenden (lang, 2 s) | GP11 |
| Audio PWM → PAM8302 A+ | GP16 |
| PAM8302 SD | GP17 |
| Vibrationsmodul IN | GP18 |
| Status-LED | GP25 (onboard) |
| 5 V → PAM8302 Vin, Vibrationsmodul VCC | VBUS (Pin 40) |
| GND | beliebiger GND-Pin |

## Protokoll (umgesetzt 0.2.1.93)
- Gerät → PC: `KEY n DOWN`, `KEY n UP`, `KEY n LONG`, `HELLO CARENKEY <version>`
- PC → Gerät: `ACK`, `ERR`, `VIB <ms>`, `TONE <Hz> <ms>`, `HELLO`, `LONG <ms>` (Zeit für langen Druck)
- Lokal: kurzer Vibrationsimpuls bei jedem Tastendruck; Quittung (hoch = OK, tiefer Doppelton + lange Vibration = Fehler) kommt von CarenDMR.

## CarenDMR-Erweiterung (umgesetzt in 0.2.1.93)
- Qt-freier `KeypadService` in `carendmr/application/keypad_service.py`:
  Gerätesuche (nur USB-VID 0x2E8A, Handshake `HELLO`), Reconnect alle 3 s,
  Tastennummer → Aktion, Quittungen. Aufgebaut in `build_easy_services()`.
- Easy führt die Aktionen aus; Funk nur über `OperatingController`.
- Belegung in `config/keypad.local.json`, Vorlage `config/keypad.example.json`.
- Ansagen über den bestehenden Screenreader-Weg.
- Firmware: `hardware/keypad/` (CircuitPython, `boot.py` schaltet `usb_cdc.data` ein,
  dadurch zwei COM-Ports; CarenDMR nutzt den Datenport).
- `pyserial` in `requirements.txt`.

## Tastenbelegung (entschieden 26.11.2026, umgesetzt in 0.2.1.93)
13 Taster, 12 Funktionen, Steuerung von CarenDMR Easy über USB-CDC:

| Nr. | Funktion | Verhalten | Taster | GPIO |
|---|---|---|---|---|
| 1 | PTT (große Taste wie Leertaste, zwei Taster parallel) | drücken und halten = senden, loslassen = empfangen | 2 | 1 |
| 2 | Lauter | Empfangslautstärke über das Tastenfeld, keine PC-Tastatur nötig | 1 | 1 |
| 3 | Leiser | wie Lauter | 1 | 1 |
| 4 | TG vor | durch die Favoriten blättern, nur auswählen mit Ansage | 1 | 1 |
| 5 | TG zurück | wie TG vor | 1 | 1 |
| 6–9 | TG-Favorit 1–4 | nur auswählen, mit Ansage über den Screenreader | 4 | 4 |
| 10 | Verbinden | ausgewählte TG verbinden | 1 | 1 |
| 11 | Trennen | Verbindung trennen | 1 | 1 |
| 12 | CarenDMR beenden | nur bei langem Druck (2 s); trennt vorher | 1 | 1 |
| | **Summe** | | **13** | **12** |

Bedienablauf: Favorit wählen (Ansage) → Verbinden → PTT halten zum Senden.

Entschieden am 26.11.2026 (Antworten des Nutzers):
- Große Taste = PTT (halten = senden, loslassen = empfangen).
- Beenden nur mit langem Druck (2 Sekunden).
- TG vor/zurück blättert durch die Favoriten, nur auswählen mit Ansage.
- Eigene Taste „Trennen“; Beenden trennt zusätzlich.
- Favoriten-Tasten wählen nur aus und sagen an; Verbinden per Taste, Senden per PTT.
- Lauter/Leiser über das Tastenfeld, nur Empfangslautstärke; im Betrieb keine PC-Tastatur nötig.
- Anbindung bleibt USB-CDC seriell.
- Bluetooth: gestrichen. Nur USB-CDC.

Festgelegt bei der Umsetzung (0.2.1.93, bei Bedarf ändern):
- Während einer Verbindung wechseln Favoriten-Tasten nicht, Ansage
  „Zum Wechseln der Talkgroup erst trennen.“
- Lauter/Leiser in 10-%-Schritten (wie Strg+Plus/Minus).
- Fällt das Tastenfeld bei gedrückter PTT weg, endet das Senden.

Idee (noch nicht entschieden): Sendepegel automatisieren, damit Caren ihn nie
einstellen muss. Heute gibt es dafür nur die Sprachaufbereitung
(`StreamingTxSpeechProcessor` in `carendmr/audio/optimizer.py`: Hochpass,
Kompressor, weicher Limiter, ausdrücklich **keine** automatische
Lautheitsnormalisierung). Eine TX-AGC wäre neu und müsste mit Papagei 9990 und
dem AMBE-Loopback geprüft werden.

## Gehäuse und Deckplatte (Entwurf 1, 26.11.2026)
Zeichnung: `hardware/keypad/gehaeuse.png` (bzw. `.svg`). Kurzfassung:
- Deckplatte 140 × 145 × 1,5, Gehäuse außen 145 × 150 × 32 (Wand 2,5, Boden 2,5,
  innen 28), PETG; Deckplatte auf Absatz, 4 × M3 in Einschmelzmuttern.
- Anordnung (Caren sitzt vorne): hinten Favorit 1–4, rechts abgesetzt Beenden;
  Mitte TG zurück/vor | Leiser/Lauter; Verbinden links, Trennen rechts;
  vorne breite PTT (Kappe 57,15, Taster 38 auseinander). Raster 19,05,
  Gruppenabstand 28,58, Reihenabstand 23,81.
- Tastbare Kappen (Vorschlag): Favoriten mit Braille-Ziffer 1–4, TG ◀ ▶,
  Leiser Steg, Lauter Kreuz, Verbinden Noppe, Trennen ✕, Beenden als Mulde;
  Orientierungsnoppe vorne Mitte.
- Innen: Lautsprecher hinten rechts unter Lochgitter, Pico H hinten links
  (USB nach hinten, Kabelausgang Ø6 mit Kabelbinder-Steg), PAM8302 daneben,
  Vibrationsmodul am Boden unter der PTT, zwei Gewichtstaschen vorne, 4 TPU-Füße.
- Offen: BOOTSEL über abgeschraubte Deckplatte statt Loch? Modulmaße nachmessen;
  Probedruck Ausschnitt 14,0 ± 0,1; Anordnung mit Caren testen.

## Offen
- Belegung mit Caren ausprobieren
- Deckplatte und Gehäuse (PETG) für 12 Einzeltasten + breite PTT-Taste konstruieren
- Nachmessen: Lautsprecher und Vibrationsmodul (Außenmaß, Lochabstand, Schraubengröße)

## Material (vollständig vorhanden, Stand 26.11.2026)
- Lautsprecher Zuahaly 3 W / 8 Ω: vorhanden
- PAM8302-Modul (mit Trimmpoti + SD-Pin): vorhanden
- Vibrationsmodul DAOKAI 5 V: vorhanden
- Pico H (RP2040): vorhanden (2 Stück, beide Pico H)
- Gateron Brown: vorhanden (30 Stück)
- USB-**Daten**kabel Micro-USB → PC-Seite, fest eingebaut, mit Zugentlastung: vorhanden
- Buchsenleisten RM 2,54 (2 × 1×20) für den Pico: vorhanden
- Schrauben M2/M2,5, M3 + Einschmelzmuttern für Deckel: vorhanden (Größe für Lautsprecher/Vibration beim Nachmessen festlegen)
- Filament (PETG, TPU) und Kleinteile: vorhanden
