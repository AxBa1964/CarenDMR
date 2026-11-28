# CarenDMR – offene Punkte

Einzige Quelle für den Projektstand. Stand: 27.11.2026, Version 0.2.1.101.

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
- 0.2.1.93: CarenDMR.box Schritt 1 – Codec-Bridge für Linux/aarch64
  (`native/build_md380_dynarmic_linux.sh`) und `python main.py --codec-benchmark`;
  Probelauf unter Linux x86_64 erfolgreich (11 % eines 20-ms-Rahmens).
- 0.2.1.94: QSO-Verlauf sortiert bei gleicher Endzeit stabil (Testfehler unter
  Windows auf dem Laptop).
- 0.2.1.95: FM-Funknetz Schritt 1 – anmelden und empfangen (`--fm-listen`),
  `docs/FM_FUNKNETZ.md`; lokal gegen Test-Reflektor geprüft, echter Server noch offen.
- Setup 0.2.1.92 gebaut und als `CarenDMR-Setup-0.2.1.92.zip` unter
  dk7ee.de/download abgelegt; Projektseite dk7ee.de/carendmr.html bietet den
  Download direkt an, GitHub nur noch unten als Quellcode-Verweis.

## Nutzer-Handgriffe (offen)

- [x] 0.2.1.91 und 0.2.1.92 sind auf `main` (Commit 4a246f4); 0.2.1.93 am 27.11.2026
      nach `main` übernommen. Lokal: `git pull` auf `main`.
- [ ] `tests/test_release_zip.py` löschen.
- [ ] Alte `logs\tg_monitor.log` (ca. 245 MB) löschen.
- [ ] Alte `CarenDMR-Setup.exe`/`.zip` in `release\installer` löschen.
- [ ] `versionen.json`, Schlüssel `carendmr`: version 0.2.1.92, datum, neu,
      download `https://dk7ee.de/download/CarenDMR-Setup-0.2.1.92.zip`; hochladen.
- [ ] Neue `carendmr.html` per FTP hochladen und Download-Knopf prüfen.
- [ ] BrandMeister-Testpasswort ändern (wurde im Chat gezeigt).

## FM-Funknetz (Nutzer-Test)

- [x] Erster echter Test 27.11.2026 (Laptop): Anmeldung als `DK7EE-APP`
      erfolgreich (Protokoll 2.0, HMAC passt). Danach trennt der Server:
      „Software/Version nicht zugelassen: CarenDMR 0.2.1.95“ – der Reflektor
      prüft die Software-Angabe (NodeInfo `sw`/`swVer`) gegen eine Freigabeliste.
- [ ] **CarenFM wartet auf Antwort von Jens (DJ1JAY)**: welcher Name und welches
      Versionsformat für die Freischaltung. Code (0.2.1.96) fertig, Kennung „CarenFM“.
      Sobald die Antwort da ist: Name/Version in `fm_funknetz.local.json` eintragen
      (ggf. `software_version` noch einstellbar machen) und mit `--fm-listen` prüfen.
      Keine fremde Software-Kennung vortäuschen.
      (Der Monitor-Screenshot mit DK7EE-APP stammte von JayTRX, nicht von CarenFM.)
- [ ] Danach: Senden (zuerst Papagei TG 9990/9998), Einbindung in
      Hauptfenster/Easy/Box, FM-Favoriten, `libopus-0.dll` ins Windows-Setup.

## CarenDMR-Box: Web-Verwaltung (begonnen 0.2.1.97)

- [x] Gerüst, Verwaltungskennwort, Übersicht, DMR-Station mit Verbindungstest
      (`python main.py --box-web`).
- [x] Talkgroups/Favoriten je Netz mit Hotliste 1–4 und Import/Export (0.2.1.98).
- [x] Audio: Geräte, Probeton, Lautstärke/Mikrofonpegel (0.2.1.99).
- [x] FM-Funknetz: Zugang speichern und testen (0.2.1.100).
- [x] System: Kennwort ändern, Neustart/Herunterfahren, Sicherung (0.2.1.101).
- [x] Einrichtungsassistent als abbrechbare Schritt-Liste (0.2.1.101).
- [ ] Noch offen: WLAN-Einrichtung (im Einrichtungsmodus), Sprach-Codec-Seite,
      Update-Funktion, Sicherung wieder einspielen (Restore).
- [ ] Einrichtungsassistent (abbrechbar, Schritt für Schritt).
- [ ] Erst auf dem Pi testen; mDNS-Name carendmr-box.local einrichten.

## CarenDMR.box (nach Lieferung des Pi 4)

- [ ] Pi einrichten und Codec messen nach `docs/CARENDMR_BOX_PI_EINRICHTUNG.md`;
      Ausgabe von `--codec-benchmark` zurückmelden.
- [ ] Soundkarte und Mikrofonkapsel mit `arecord`/`aplay` prüfen.
- [ ] Danach Messung auf dem Zero 2 W (entscheidet über das Zielgerät).

## Tests in der installierten Exe 0.2.1.92

- [ ] QRZ-Karte (QtWebEngine) funktioniert nach dem Verschlanken noch.
- [ ] „Nach Updates suchen“ (Menü Programm bzw. Strg+Umschalt+U in Easy).
- [ ] Papagei 9990 wird automatisch auf Privatruf gestellt.

## Offene Entscheidungen

- Sollen die Sendewerte des Nutzers (Mikrofon 74 %, Sprachbearbeitung aus,
  Profil „Eigene“) die Vorgabe für neue Installationen werden?
- Git-Historie bereinigen (alte `carendmr_md380_bridge.dll` mit eingebauter Firmware
  ist noch in der Historie)?
- Exe weiter verkleinern (nur auf Wunsch): QRZ-Karte im externen Browser statt
  QtWebEngine (~200 MB), scipy/matplotlib prüfen.

## Ideen / später

- Bedien-Tastenfeld für Caren (USB-CDC): Konzept in `docs/TASTENFELD_KONZEPT.md`;
  CarenDMR-Seite: Qt-freier `KeypadService`, Belegung `config/keypad.local.json`.
- Easy-Oberfläche für das Tastenfeld umbauen.
- CarenDMR.box: eigenständiger Client auf dem Raspberry Pi (Pi 4 bestellt, Ziel ggf.
  Zero 2 W), Web-Verwaltung im Heimnetz, nur Betrieb (kein QRZ/Logbuch/Monitoring).
  Konzept in `docs/CARENDMR_BOX_KONZEPT.md`. Bestellt (27.11.2026): Pi 4 mit Lüfter,
  UGREEN-Soundkarte, Elektret-Kapseln. Erster Schritt: Codec-Messung auf ARM64.
- FM-Funknetz (SvxReflector, Opus) zusätzlich zu DMR in Box und Client: getrennte
  Einstellungen und Favoriten je Netz, QRZ/ADIF im PC-Client für beide Netze,
  Box ohne QRZ/ADIF, Favoriten-Import/-Export im Web. Details im Box-Konzept. Zugang erhalten (27.11.2026), Rufzeichen `DK7EE-APP`/`DK7EE-TRX`; Test nur in
  TG 20, Papageien TG 9990/9998;
  erlaubte Protokollversion (2 oder 3 mit Zertifikat) beim Netzbetreiber klären.
- Quelltext-Tests schrittweise durch Verhaltenstests ersetzen; Tests kennzeichnen,
  die echte Audio-/Netzwerkgeräte brauchen.
- Android-Prototyp (Branch `feature/android-arm64-prototype`, muss an die
  Laufzeit-Firmware ab 0.2.1.89 angepasst werden).
- Optional DVSI-Stick (`UsbAmbeEncoder`) als Codec-Alternative.
- Modulationsvergleich: eigener AMBE-Loopback gegen TG-Referenz.
- `ROADMAP.md` ist auf Stand 0.2.1.87 und sollte aktualisiert oder auf diese Datei
  verweisen.
