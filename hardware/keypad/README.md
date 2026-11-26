# CarenDMR-Tastenfeld – Firmware

Firmware für das Bedien-Tastenfeld (Raspberry Pi Pico H oder Pico 2 H, CircuitPython).
Konzept und Verdrahtung: `docs/TASTENFELD_KONZEPT.md`.

## Dateien

| Datei | Inhalt |
|---|---|
| `boot.py` | schaltet die zweite serielle USB-Schnittstelle (Daten) ein |
| `pins.py` | Pinbelegung (Tasten GP0–GP11, Audio GP16/GP17, Vibration GP18) |
| `code.py` | Tasten lesen, an CarenDMR melden, Quittungston und Vibration |

## Verdrahtung (Pico H, Stiftnummern 1–40)

Stift 1 ist neben der USB-Buchse (siehe Pinout im offiziellen Datenblatt,
Abschnitt 2.1: https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf,
interaktiv: https://pico.pinout.xyz). GND-Stifte haben eckige Lötaugen:
3, 8, 13, 18, 23, 28, 33, 38.

Jeder Taster: ein Kontakt an den GPIO-Stift, der andere an GND
(gemeinsame GND-Leitung). Kein Widerstand nötig, der Pull-up ist im Pico.

| Teil | Anschluss | Pico-Stift |
|---|---|---|
| PTT (beide Taster parallel) | GP0 | 1 |
| Lauter | GP1 | 2 |
| Leiser | GP2 | 4 |
| TG vor | GP3 | 5 |
| TG zurück | GP4 | 6 |
| Favorit 1 | GP5 | 7 |
| Favorit 2 | GP6 | 9 |
| Favorit 3 | GP7 | 10 |
| Favorit 4 | GP8 | 11 |
| Verbinden | GP9 | 12 |
| Trennen | GP10 | 14 |
| Beenden | GP11 | 15 |
| Taster, zweiter Kontakt | GND | 3, 8, 13 oder 18 |
| PAM8302 A+ | GP16 | 21 |
| PAM8302 SD | GP17 | 22 |
| PAM8302 A− und GND | GND | 23 |
| PAM8302 Vin | VBUS (5 V vom USB) | 40 |
| PAM8302 Lautsprecher +/− | Lautsprecher | – |
| Vibrationsmodul IN | GP18 | 24 |
| Vibrationsmodul GND | GND | 28 oder 38 |
| Vibrationsmodul VCC | VBUS (5 V vom USB) | 40 |

## Aufspielen

1. BOOTSEL-Taste am Pico gedrückt halten und USB einstecken. Es erscheint ein
   Laufwerk. Sein Name zeigt, welcher Chip verbaut ist:

   | Laufwerk | `INFO_UF2.TXT` | Board | CircuitPython-Seite |
   |---|---|---|---|
   | `RPI-RP2` | `Board-ID: RPI-RP2` | Pico / Pico H (RP2040) | https://circuitpython.org/board/raspberry_pi_pico/ |
   | `RP2350` | `Board-ID: RP2350` | Pico 2 / Pico 2 H (RP2350) | https://circuitpython.org/board/raspberry_pi_pico2/ |

   Passt die `.uf2` nicht zum Chip, startet der Pico nicht neu und das
   Laufwerk bleibt stehen.
2. Die passende `.uf2` herunterladen und auf das Laufwerk kopieren.
3. Der Pico startet neu, es erscheint das Laufwerk `CIRCUITPY`.
   `boot.py`, `pins.py` und `code.py` darauf kopieren.
4. USB einmal abziehen und wieder einstecken (`boot.py` wirkt nur beim Start).

Die Firmware läuft auf beiden Boards unverändert (gleiche Pinbelegung).

Danach hat der Pico zwei COM-Ports. CarenDMR Easy findet den richtigen selbst
(Handshake `HELLO`). Ist kein Tastenfeld angeschlossen, läuft Easy normal.

## Belegung in CarenDMR

Vorlage `config/keypad.example.json` nach `config/keypad.local.json` kopieren
und bei Bedarf anpassen. Ohne Datei gilt dieselbe Vorbelegung.

| Taste | Pin | Aktion |
|---|---|---|
| 0 | GP0 | PTT – halten = senden, loslassen = empfangen |
| 1 / 2 | GP1 / GP2 | Lauter / Leiser (Empfang, 10-%-Schritte) |
| 3 / 4 | GP3 / GP4 | TG vor / zurück durch die Favoriten (nur Auswahl mit Ansage) |
| 5–8 | GP5–GP8 | Favorit 1–4 (nur Auswahl mit Ansage) |
| 9 | GP9 | Verbinden |
| 10 | GP10 | Trennen |
| 11 | GP11 | CarenDMR beenden – 2 Sekunden halten |

`"port": "auto"` sucht nur Raspberry-Pi-Geräte. Bei einem anderen Board den
COM-Port fest eintragen, z. B. `"port": "COM7"`.

## Test ohne CarenDMR

Im Gerätemanager den zweiten COM-Port des Pico suchen und mit einem
Terminalprogramm öffnen (115200 Baud). Tastendrücke erscheinen als
`KEY 0 DOWN` / `KEY 0 UP`; die Eingabe `ACK` muss einen Ton erzeugen,
`VIB 500` eine Vibration.
