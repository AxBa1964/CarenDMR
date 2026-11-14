# CarenDMR 0.2.1.90

Vorbereitung für die Windows-Exe mit Installer:

- Programm- und Datenordner getrennt; in der Exe liegen Nutzerdaten unter
  `%LOCALAPPDATA%\CarenDMR`.
- Ersteinrichtung für Station (mit Verbindungstest), Sprach-Codec, Audio und
  Kontaktdaten, barrierefrei; vorbelegte Favoriten.
- Bauplan für PyInstaller und Inno Setup in `packaging/`,
  Anleitung in `docs/RELEASE_BUILD.md`.
- Öffentliche Builds enthalten keine MD380-Firmware. Die Bridge lädt sie zur
  Laufzeit; „Sprach-Codec einrichten“ lädt sie auf Wunsch herunter.

Start aus dem Quellcode:

```text
python main.py --gui
python main.py --easy
python main.py --tg-monitor
```

Tests: `python -m pytest tests`
