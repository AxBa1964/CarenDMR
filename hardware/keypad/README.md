# CarenDMR-Tastenfeld – Firmware

Firmware für das Bedien-Tastenfeld (Raspberry Pi Pico H oder Pico 2 H, CircuitPython).
Konzept und Verdrahtung: `docs/TASTENFELD_KONZEPT.md`.

## Dateien

| Datei | Inhalt |
|---|---|
| `boot.py` | schaltet die zweite serielle USB-Schnittstelle (Daten) ein |
| `pins.py` | Pinbelegung (Tasten GP0–GP11, Audio GP16/GP17, Vibration GP18) |
| `code.py` | Tasten lesen, an CarenDMR melden, Quittungston und Vibration |

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
