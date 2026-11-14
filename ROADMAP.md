# CarenDMR Roadmap

Stand: 0.2.1.87

## Abgeschlossen: Architektur-Umbau (0.2.1.84 – 0.2.1.87)

- Gemeinsamer Startpunkt `bootstrap.py` für Funkkern und Desktop-Dienste
- Hauptfenster und Easy-Oberfläche über denselben `OperatingController`
- Hauptfenster in fachliche Teilmodule aufgeteilt
- Tkinter-Oberfläche entfernt, Testsuite auf pytest umgestellt

## Als Nächstes

- Branch `refactor/bootstrap-controller` nach `main` übernehmen
- Quelltext-Tests schrittweise durch Verhaltenstests ersetzen
- Prüfen, welche Tests echte Audio- oder Netzwerkgeräte benötigen, und diese
  kennzeichnen, damit die Suite überall gleich schnell und stabil läuft
- Android-Prototyp (Branch `feature/android-arm64-prototype`) auf Basis von
  `bootstrap.py` und `OperatingController`

## Offen aus früheren Planungen

- Modulationsvergleich: eigener AMBE-Loopback gegen benannte TG-Referenz,
  Abweichungen auf Tuner-Empfehlungen abbilden (ohne automatische Übernahme)
