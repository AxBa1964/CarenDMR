"""Pinbelegung des CarenDMR-Tastenfelds (Raspberry Pi Pico 2 H).

Die Reihenfolge in KEY_PINS ergibt die Tastennummer (0, 1, 2 …), die an
CarenDMR gemeldet wird. Die Bedeutung der Nummern steht in
config/keypad.local.json (Vorlage: config/keypad.example.json).

Für ein anderes Board nur diese Datei anpassen.
"""
import board

KEY_PINS = (
    board.GP0,   # 0  PTT (zwei Taster parallel)
    board.GP1,   # 1  Lauter
    board.GP2,   # 2  Leiser
    board.GP3,   # 3  TG vor (Favoriten)
    board.GP4,   # 4  TG zurück (Favoriten)
    board.GP5,   # 5  Favorit 1
    board.GP6,   # 6  Favorit 2
    board.GP7,   # 7  Favorit 3
    board.GP8,   # 8  Favorit 4
    board.GP9,   # 9  Verbinden
    board.GP10,  # 10 Trennen
    board.GP11,  # 11 Beenden (lang drücken)
)

AUDIO_PWM = board.GP16      # PAM8302 A+ (A- an GND)
AUDIO_SHUTDOWN = board.GP17  # PAM8302 SD (High = an)
VIBRATION = board.GP18      # Vibrationsmodul IN (High = an)
STATUS_LED = board.LED      # GP25, Onboard-LED
