# CarenDMR – offene Punkte

Einzige Quelle für den Projektstand. Stand: 26.11.2026, Version 0.2.1.93.

## Stand

- 0.2.1.84–0.2.1.87: Architektur-Umbau abgeschlossen und nach `main` übernommen.
- 0.2.1.88: Vorbereitung Windows-Exe, Programm-/Datenordner, Packaging.
- 0.2.1.89: MD380-Firmware zur Laufzeit, Codec-Download, neue Bridge ohne Firmware.
  Codec-Download und Papagei-Test (9990) erfolgreich.
- 0.2.1.90: Ersteinrichtung mit Verbindungstest, Audio, Kontakte, vorbelegte Favoriten;
  9990 automatisch Privatruf; package_id-Migration.
- 0.2.1.91: Projektordner aufgeräumt, `build_setup.bat`, Setup verschlankt
  (164,5 MB statt 183), Erststart öffnet das Hauptfenster, Log-Rotation TG-Monitor.
- 0.2.1.92: Update-Prüfung auf Anfrage über `versionen.json` (Variante A).
- Setup 0.2.1.92 gebaut und als `CarenDMR-Setup-0.2.1.92.zip` unter
  dk7ee.de/download abgelegt; Projektseite dk7ee.de/carendmr.html bietet den
  Download direkt an, GitHub nur noch unten als Quellcode-Verweis.
- 0.2.1.93: Bedien-Tastenfeld für Easy umgesetzt (`KeypadService`, USB-CDC,
  Pico-2-H-Firmware in `hardware/keypad/`); mit echter Hardware noch ungetestet.

## Nutzer-Handgriffe (offen)

- [ ] Laut Git-Log auf dem Shack-PC ist 0.2.1.90 der letzte Commit auf `main`;
      0.2.1.91 und 0.2.1.92 committen und pushen.
- [ ] `tests/test_release_zip.py` löschen.
- [ ] Alte `logs\tg_monitor.log` (ca. 245 MB) löschen.
- [ ] Alte `CarenDMR-Setup.exe`/`.zip` in `release\installer` löschen.
- [ ] `versionen.json`, Schlüssel `carendmr`: version 0.2.1.92, datum, neu,
      download `https://dk7ee.de/download/CarenDMR-Setup-0.2.1.92.zip`; hochladen.
- [ ] Neue `carendmr.html` per FTP hochladen und Download-Knopf prüfen.
- [ ] BrandMeister-Testpasswort ändern (wurde im Chat gezeigt).

## Tests in der installierten Exe 0.2.1.92

- [ ] QRZ-Karte (QtWebEngine) funktioniert nach dem Verschlanken noch.
- [ ] „Nach Updates suchen“ (Menü Programm bzw. Strg+Umschalt+U in Easy).
- [ ] Papagei 9990 wird automatisch auf Privatruf gestellt.

## Tastenfeld (0.2.1.93) – Test mit Hardware

- [ ] Pico 2 H: CircuitPython aufspielen, `hardware/keypad/boot.py`, `pins.py`,
      `code.py` kopieren (Anleitung `hardware/keypad/README.md`).
- [ ] Testaufbau: Tasten zeigen im Terminal `KEY n DOWN/UP`, `ACK` gibt Ton.
- [ ] Prüfen, ob 3,3 V vom Pico das Vibrationsmodul sicher schalten (sonst BC337).
- [ ] Easy mit Tastenfeld: Favorit wählen (Ansage) → Verbinden → PTT halten;
      Trennen; Beenden nach 2 s; USB abziehen während PTT → Senden endet.
- [ ] Lautsprecher und Vibrationsmodul nachmessen (Gehäuse).

## Offene Entscheidungen

- Tastenfeld: Soll ein Favorit während einer Verbindung direkt wechseln können
  (trennen + neu verbinden mit „Verbinden“)? Umgesetzt ist: erst trennen.

- Sollen die Sendewerte des Nutzers (Mikrofon 74 %, Sprachbearbeitung aus,
  Profil „Eigene“) die Vorgabe für neue Installationen werden?
- Git-Historie bereinigen (alte `carendmr_md380_bridge.dll` mit eingebauter Firmware
  ist noch in der Historie)?
- Exe weiter verkleinern (nur auf Wunsch): QRZ-Karte im externen Browser statt
  QtWebEngine (~200 MB), scipy/matplotlib prüfen.

## Ideen / später

- Tastenfeld: Gehäuse und Deckplatte (PETG) konstruieren, Konzept in
  `docs/TASTENFELD_KONZEPT.md`.
- Quelltext-Tests schrittweise durch Verhaltenstests ersetzen; Tests kennzeichnen,
  die echte Audio-/Netzwerkgeräte brauchen.
- Android-Prototyp (Branch `feature/android-arm64-prototype`, muss an die
  Laufzeit-Firmware ab 0.2.1.89 angepasst werden).
- Optional DVSI-Stick (`UsbAmbeEncoder`) als Codec-Alternative.
- Modulationsvergleich: eigener AMBE-Loopback gegen TG-Referenz.
- `ROADMAP.md` ist auf Stand 0.2.1.87 und sollte aktualisiert oder auf diese Datei
  verweisen.
