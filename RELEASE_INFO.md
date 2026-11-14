# CarenDMR 0.2.1.87

Abschluss des Architektur-Umbaus (0.2.1.84 – 0.2.1.87):

- Funkkern und Desktop-Dienste entstehen zentral in `carendmr/bootstrap.py`.
- Hauptfenster und Easy-Oberfläche verbinden, trennen und senden über denselben
  `OperatingController`.
- Das Hauptfenster ist in fachliche Teilmodule aufgeteilt.
- Die Tkinter-Oberfläche (`--gui-tk`) wurde entfernt.

Start:

```text
python main.py --gui
python main.py --easy
```

Tests: `python -m pytest tests`
