# CarenDMR 0.2.1.9 prüfen

1. Virtuelle Umgebung aktivieren.
2. `pytest -q` ausführen.
3. CarenDMR starten und das WASAPI-Mikrofon auswählen.
4. Geführten Modulationstest starten und sprechen.
5. Bei Stille den Test abbrechen.
6. Im neuen `AudioTest_*`-Ordner `input_diagnostics.json`, `manifest.json` und `timeline.json` prüfen.
7. `manifest.json` muss bei Abbruch `state: aborted` enthalten.
