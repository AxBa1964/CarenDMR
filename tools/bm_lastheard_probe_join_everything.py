from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

try:
    import socketio
except ImportError:
    print("FEHLER: python-socketio ist nicht installiert.", file=sys.stderr)
    print("Mit aktivierter venv ausführen:", file=sys.stderr)
    print("  python -m pip install \"python-socketio[client]\"", file=sys.stderr)
    raise SystemExit(2)


URL = "https://api.brandmeister.network"
SOCKETIO_PATH = "/lh/socket.io"


def stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def show(prefix: str, value=None) -> None:
    if value is None:
        print(f"{stamp()} {prefix}", flush=True)
        return
    try:
        rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    except Exception:
        rendered = repr(value)
    print(f"{stamp()} {prefix} {rendered}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unabhängiger BrandMeister-Last-Heard-Probe"
    )
    parser.add_argument(
        "--seconds",
        type=int,
        default=60,
        help="Testdauer in Sekunden (Standard: 60)",
    )
    args = parser.parse_args()

    seconds = max(5, min(3600, int(args.seconds)))

    print()
    print("BrandMeister Last-Heard Probe")
    print("=" * 60)
    print(f"URL            : {URL}")
    print(f"Socket.IO-Pfad : {SOCKETIO_PATH}")
    print(f"Testdauer      : {seconds} s")
    print()
    print("Während des Tests bitte auf einer bekannten aktiven TG (z. B. 91)")
    print("Verkehr beobachten. Erwartet werden mqtt-Events.")
    print("=" * 60)
    print()

    sio = socketio.Client(
        reconnection=False,
        logger=True,
        engineio_logger=True,
    )

    counters = {
        "mqtt": 0,
        "connect": 0,
        "disconnect": 0,
    }

    @sio.event
    def connect():
        counters["connect"] += 1
        show("SOCKETIO CONNECT")
        show("SUBSCRIBE join=everything")
        sio.emit("join", "everything")

    @sio.event
    def connect_error(data):
        show("SOCKETIO CONNECT_ERROR", data)

    @sio.event
    def disconnect(reason=None):
        counters["disconnect"] += 1
        show("SOCKETIO DISCONNECT", reason)

    @sio.on("mqtt")
    def mqtt(data):
        counters["mqtt"] += 1
        show("MQTT RAW", data)

        if isinstance(data, dict) and "payload" in data:
            payload = data["payload"]
            if isinstance(payload, str):
                try:
                    decoded = json.loads(payload)
                except Exception as error:
                    show("MQTT PAYLOAD JSON-FEHLER", str(error))
                else:
                    show("MQTT PAYLOAD", decoded)

    show("VERBINDUNG wird aufgebaut")

    try:
        sio.connect(
            URL,
            socketio_path=SOCKETIO_PATH,
            transports=["websocket"],
            wait_timeout=15,
        )
    except Exception as error:
        show("VERBINDUNGSFEHLER", f"{type(error).__name__}: {error}")
        return 3

    deadline = time.monotonic() + seconds

    try:
        while time.monotonic() < deadline and sio.connected:
            remaining = int(deadline - time.monotonic())
            if remaining in {50, 40, 30, 20, 10, 5}:
                show(f"NOCH {remaining} s | MQTT bisher={counters['mqtt']}")
            time.sleep(1)
    except KeyboardInterrupt:
        show("ABBRUCH durch Benutzer")
    finally:
        if sio.connected:
            sio.disconnect()

    print()
    print("=" * 60)
    print("ERGEBNIS")
    print(f"Socket.IO verbunden : {counters['connect']}x")
    print(f"mqtt-Events         : {counters['mqtt']}")
    print(f"Disconnects         : {counters['disconnect']}")
    if counters["connect"] > 0 and counters["mqtt"] == 0:
        print()
        print("BEFUND: Verbindung kam zustande, aber während des Tests")
        print("wurden keine mqtt-Events geliefert.")
    elif counters["mqtt"] > 0:
        print()
        print("BEFUND: BrandMeister liefert mqtt-Events. Dann liegt das")
        print("Problem im CarenDMR-TG-Monitor und nicht am Feed selbst.")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
