# CarenDMR – offene Punkte

Einzige Quelle für den Projektstand. Stand: 27.11.2026, Version 0.2.1.96.

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
  Pico-H-Firmware in `hardware/keypad/`); mit echter Hardware noch ungetestet.
- 0.2.1.94: CAD-Modell Tastenfeld-Gehäuse (CadQuery, STEP/STL) in `hardware/keypad/cad/`.
- 0.2.1.95: flache Kappen + zweifarbige Kennzeichnungs-Plättchen (PLA schwarz/weiß).
- 0.2.1.96: PTT-Plättchen mit Längsrippe; Plättchen als 3MF (ein Objekt, zwei Teile).

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

- [x] Pico H (RP2040): CircuitPython für den Pico (nicht Pico 2) aufspielen (erledigt 26.11.2026); `hardware/keypad/boot.py`, `pins.py`,
      `code.py` kopieren (Anleitung `hardware/keypad/README.md`).
- [ ] Testaufbau: Tasten zeigen im Terminal `KEY n DOWN/UP`, `ACK` gibt Ton.
- [ ] Prüfen, ob 3,3 V vom Pico das Vibrationsmodul sicher schalten (sonst BC337).
- [ ] Easy mit Tastenfeld: Favorit wählen (Ansage) → Verbinden → PTT halten;
      Trennen; Beenden nach 2 s; USB abziehen während PTT → Senden endet.
- [ ] Lautsprecher und Vibrationsmodul nachmessen (Gehäuse).

## Tastenfeld-Gehäuse (0.2.1.94) – Druck

- [x] Probestreifen gedruckt (27.11.2026): 14,0 (Mitte, 3 Kerben) passt perfekt –
      entspricht der Vorgabe `cut` in `hardware/keypad/cad/tastenfeld.py`.
- [ ] Flache Kappe und PTT-Kappe auf dem Kopf drucken, auf Schalter stecken (klemmt die PTT?).
- [ ] Plättchen zweifarbig drucken, eins aufkleben, mit Caren Fühlbarkeit prüfen
      (Braille 0,5 hoch, Symbole 0,8 hoch – bei Bedarf in `tastenfeld.py` ändern).
- [ ] Unterteil, Tastenplatte, Podestdeckel, Kappen, TPU-Füße drucken.
- [ ] Halterungen für Lautsprecher, Vibrationsmodul, PAM8302, Pico nach dem
      Nachmessen ins Modell aufnehmen.
- [ ] Winkel 7° und Tastenanordnung mit Caren ausprobieren.
- [x] Probekappe (27.11.2026): Sitz auf dem Schalter passt perfekt. Braille auf
      der Kappe wird beim Druck mit Stützen unbrauchbar (nicht sauber fühlbar).

## Plättchen für die PTT-Taste (umgesetzt in 0.2.1.96)

- Entschieden 27.11.2026: Variante 1 – langes Plättchen ca. 53 × 14 über fast
  die ganze PTT-Kappe, zweifarbig wie die übrigen (Grundplatte schwarz), mit
  erhabener weißer **Längsrippe** in der Mitte. Caren fühlt die Mitte der Taste
  und drückt dort, damit beide Schalter gleichmäßig auslösen.
- Flach mit Rippe nach oben drucken, ohne Stützen; aufkleben wie die anderen.
- 3MF mit Platte und Zeichen als ein Objekt: umgesetzt, aber noch **nicht in
  Bambu Studio geprüft** – bitte testen (`out/3mf/plaettchen_alle.3mf`).

## Kappen ohne Zeichen + aufgeklebte Plättchen (umgesetzt in 0.2.1.95)

- Kappen oben **flach, ohne Vertiefung**: auf dem Kopf gedruckt liegt die
  Oberseite vollflächig auf der Platte, Stößel und Wände wachsen nach oben –
  keine Stützen nötig. Alle Kappen gleich (außer PTT).
- Kennzeichnungs-Plättchen ca. 14 × 14 × 1,2 (so groß wie die Kappenoberseite,
  Kanten bündig zum Ertasten der Lage), flach mit Zeichen nach oben gedruckt,
  ohne Stützen; Braille 1–4 bzw. Symbole ◀ ▶ − + Noppe ✕, Beenden als Mulde.
- Plättchen aufkleben (Sekundenkleber oder doppelseitiges Klebeband);
  austauschbar, ohne Kappen neu zu drucken.
- Plättchen **zweifarbig in PLA**: Grundplatte schwarz, Zeichen weiß und
  erhaben (gut fühlbar) – für Caren egal, aber Sehende erkennen die Belegung.
  Dafür Grundplatte und Zeichen als getrennte Teile exportieren, in Bambu Studio
  als ein Objekt mit zwei Teilen laden und je eine Farbe zuweisen.
- Entschieden (27.11.2026): **keine** zusätzliche Ziffer für Sehende auf
  Favorit 1–4 – die Reihenfolge links → rechts = 1–4 reicht. Fokus auf gute
  Fühlbarkeit für Caren (Braille nach Standardmaß, klare erhabene Symbole).

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

- Quelltext-Tests schrittweise durch Verhaltenstests ersetzen; Tests kennzeichnen,
  die echte Audio-/Netzwerkgeräte brauchen.
- Android-Prototyp (Branch `feature/android-arm64-prototype`, muss an die
  Laufzeit-Firmware ab 0.2.1.89 angepasst werden).
- Optional DVSI-Stick (`UsbAmbeEncoder`) als Codec-Alternative.
- Modulationsvergleich: eigener AMBE-Loopback gegen TG-Referenz.
- `ROADMAP.md` ist auf Stand 0.2.1.87 und sollte aktualisiert oder auf diese Datei
  verweisen.
