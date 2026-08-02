from playwright.sync_api import sync_playwright
import json
import time

GERMAN_TGS = {262, 2621, 2622, 2623, 263, 910}

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Starte Hoseline…")
        page.goto("https://hose.brandmeister.network/")

        print("Verbunden. Warte auf Live-Daten…")

        while True:
            try:
                # Hoseline speichert Live-Daten in window.store.lastheard
                data = page.evaluate("window.store.lastheard")

                if not data:
                    time.sleep(1)
                    continue

                for entry in data:
                    tg = entry.get("talkgroup")
                    dur = entry.get("duration")
                    call = entry.get("callsign")

                    if tg in GERMAN_TGS and dur and dur > 3:
                        print(f"TG {tg}: {call} spricht seit {dur} Sekunden")

                time.sleep(1)

            except Exception as e:
                print("Fehler:", e)
                time.sleep(2)

if __name__ == "__main__":
    main()
from playwright.sync_api import sync_playwright
import json
import time

GERMAN_TGS = {262, 2621, 2622, 2623, 263, 910}

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Starte Hoseline…")
        page.goto("https://hose.brandmeister.network/")

        print("Verbunden. Warte auf Live-Daten…")

        while True:
            try:
                # Hoseline speichert Live-Daten in window.store.lastheard
                data = page.evaluate("window.store.lastheard")

                if not data:
                    time.sleep(1)
                    continue

                for entry in data:
                    tg = entry.get("talkgroup")
                    dur = entry.get("duration")
                    call = entry.get("callsign")

                    if tg in GERMAN_TGS and dur and dur > 3:
                        print(f"TG {tg}: {call} spricht seit {dur} Sekunden")

                time.sleep(1)

            except Exception as e:
                print("Fehler:", e)
                time.sleep(2)

if __name__ == "__main__":
    main()
