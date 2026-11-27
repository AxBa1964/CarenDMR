# CarenDMR 0.2.1.95

Vorbereitung für die Windows-Exe mit Installer:

- Programm- und Datenordner getrennt; in der Exe liegen Nutzerdaten unter
  `%LOCALAPPDATA%\CarenDMR`.
- Ersteinrichtung für Station (mit Verbindungstest), Sprach-Codec, Audio und
  Kontaktdaten, barrierefrei; vorbelegte Favoriten.
- Bauplan für PyInstaller und Inno Setup in `packaging/`,
  Anleitung in `docs/RELEASE_BUILD.md`.
- Öffentliche Builds enthalten keine MD380-Firmware. Die Bridge lädt sie zur
  Laufzeit; „Sprach-Codec einrichten“ lädt sie auf Wunsch herunter.

Update-Prüfung auf Anfrage (Menü Programm bzw. Strg+Umschalt+U).

CarenDMR.box (Raspberry Pi): Codec-Bridge für Linux
(`native/build_md380_dynarmic_linux.sh`) und Codec-Messung
(`python main.py --codec-benchmark`), Anleitung in
`docs/CARENDMR_BOX_PI_EINRICHTUNG.md`.

QSO-Verlauf: stabile Reihenfolge bei gleicher Endzeit (0.2.1.94).

FM-Funknetz: anmelden und empfangen mit `python main.py --fm-listen`
(nur Empfang), Anleitung in `docs/FM_FUNKNETZ.md`.

Setup bauen: `build_setup.bat` (Tests, Exe, Installer in einem Schritt).

Start aus dem Quellcode:

```text
python main.py --gui
python main.py --easy
python main.py --tg-monitor
```

Tests: `python -m pytest tests`
