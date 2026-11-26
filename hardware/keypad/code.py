"""CarenDMR-Tastenfeld – Firmware (CircuitPython, Raspberry Pi Pico 2 H).

Protokoll über usb_cdc.data (eine Zeile pro Meldung, ASCII, "\n"):

Gerät → PC:  HELLO CARENKEY <version>
             KEY <n> DOWN | KEY <n> UP | KEY <n> LONG
PC → Gerät:  HELLO              → Antwort HELLO CARENKEY <version>
             ACK                → kurzer hoher Ton
             ERR                → tiefer Doppelton + lange Vibration
             VIB <ms>           → Vibration
             TONE <Hz> <ms>     → Ton
             LONG <ms>          → Zeit für langen Druck (Vorgabe 2000)

Jeder Tastendruck gibt sofort einen kurzen Vibrationsimpuls.
"""
import time

import digitalio
import keypad
import pwmio
import usb_cdc

import pins

VERSION = "1.0"
LOCAL_PULSE_MS = 40
MAX_DUTY = 2 ** 14  # Lautstärke begrenzen (USB-Strombudget); 2**15 = 50 %

serial = usb_cdc.data

keys = keypad.Keys(pins.KEY_PINS, value_when_pressed=False, pull=True)

led = digitalio.DigitalInOut(pins.STATUS_LED)
led.direction = digitalio.Direction.OUTPUT

vibration = digitalio.DigitalInOut(pins.VIBRATION)
vibration.direction = digitalio.Direction.OUTPUT
vibration.value = False

amp_on = digitalio.DigitalInOut(pins.AUDIO_SHUTDOWN)
amp_on.direction = digitalio.Direction.OUTPUT
amp_on.value = False

speaker = pwmio.PWMOut(pins.AUDIO_PWM, frequency=1000, duty_cycle=0, variable_frequency=True)

long_press_ms = 2000
pressed_at = {}      # Taste → Zeitpunkt (ms) des Drückens
long_sent = set()    # Tasten, für die LONG schon gemeldet wurde
vibration_off_at = 0
buffer = b""


def now_ms():
    return time.monotonic_ns() // 1_000_000


def send(line):
    if serial is not None and serial.connected:
        try:
            serial.write((line + "\n").encode("ascii"))
        except OSError:
            pass


def vibrate(ms):
    global vibration_off_at
    vibration.value = True
    vibration_off_at = max(vibration_off_at, now_ms() + max(0, ms))


def tone(frequency, ms):
    if frequency <= 0 or ms <= 0:
        return
    amp_on.value = True
    speaker.frequency = int(frequency)
    speaker.duty_cycle = MAX_DUTY
    time.sleep(ms / 1000)
    speaker.duty_cycle = 0
    amp_on.value = False


def handle_command(line):
    global long_press_ms
    parts = line.strip().upper().split()
    if not parts:
        return
    command = parts[0]
    try:
        if command == "HELLO":
            send("HELLO CARENKEY " + VERSION)
        elif command == "ACK":
            tone(1500, 80)
        elif command == "ERR":
            vibrate(400)
            tone(400, 120)
            time.sleep(0.08)
            tone(400, 120)
        elif command == "VIB" and len(parts) == 2:
            vibrate(min(2000, int(parts[1])))
        elif command == "TONE" and len(parts) == 3:
            tone(min(4000, int(parts[1])), min(1000, int(parts[2])))
        elif command == "LONG" and len(parts) == 2:
            long_press_ms = max(500, min(10000, int(parts[1])))
    except ValueError:
        pass


def read_commands():
    global buffer
    if serial is None or not serial.in_waiting:
        return
    buffer += serial.read(serial.in_waiting)
    while b"\n" in buffer:
        raw, buffer = buffer.split(b"\n", 1)
        handle_command(raw.decode("ascii", "replace"))
    if len(buffer) > 128:
        buffer = b""


send("HELLO CARENKEY " + VERSION)
led.value = True

while True:
    event = keys.events.get()
    while event:
        number = event.key_number
        if event.pressed:
            pressed_at[number] = now_ms()
            long_sent.discard(number)
            send("KEY %d DOWN" % number)
            vibrate(LOCAL_PULSE_MS)
        else:
            pressed_at.pop(number, None)
            long_sent.discard(number)
            send("KEY %d UP" % number)
        event = keys.events.get()

    current = now_ms()
    for number, since in pressed_at.items():
        if number not in long_sent and current - since >= long_press_ms:
            long_sent.add(number)
            send("KEY %d LONG" % number)
            vibrate(150)

    if vibration.value and current >= vibration_off_at:
        vibration.value = False

    read_commands()
    # LED blinkt kurz, solange CarenDMR nicht verbunden ist.
    led.value = serial is not None and serial.connected or (current // 500) % 2 == 0
    time.sleep(0.005)
