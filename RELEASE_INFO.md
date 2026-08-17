# CarenDMR 0.2.1.56 – Easy-Oberfläche Stufe 1

Auf Basis des eingefrorenen Stable-Stands 0.2.1.55 wurde ein zusätzlicher Einstieg für die extrem reduzierte Blind-/Easy-Oberfläche ergänzt.

Start:

```text
python main.py --easy
```

Der tägliche Fokusweg lautet **Talkgroup → Verbinden → PTT**. Timeslot und Rufart werden nur bei Bedarf über `Strg+T` bzw. `Strg+R` geändert. `F4` meldet den aktuellen Funkstatus über native Qt-Accessibility.

Die Easy-Oberfläche enthält keine eigene Funkimplementierung. Verbinden, Trennen und PTT laufen über den vorhandenen `OperatingController` und damit über denselben stabilen ConnectionManager/RX/TX-/Audio-/AMBE-Pfad wie bisher. Die Desktop-Oberfläche bleibt erhalten.
