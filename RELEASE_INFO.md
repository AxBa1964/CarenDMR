# CarenDMR 0.2.1.88

Vorbereitung für die Windows-Exe mit Installer:

- Programm- und Datenordner getrennt; in der Exe liegen Nutzerdaten unter
  `%LOCALAPPDATA%\CarenDMR`.
- Ersteinrichtung für Station und Sprach-Codec, barrierefrei.
- Bauplan für PyInstaller und Inno Setup in `packaging/`,
  Anleitung in `docs/RELEASE_BUILD.md`.
- Öffentliche Builds enthalten keine MD380-Firmware; die Bridge für das
  Laden zur Laufzeit folgt.

Start aus dem Quellcode:

```text
python main.py --gui
python main.py --easy
python main.py --tg-monitor
```

Tests: `python -m pytest tests`
