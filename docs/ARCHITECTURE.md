# CarenDMR – Architektur

Stand: Version 0.2.1.87

## Schichten

```text
Oberflächen (Qt-Hauptfenster, Easy, Konsole)
      |
bootstrap.py  (gemeinsamer Startpunkt, setzt alles zusammen)
      |
Application-Services  (OperatingController, ConnectionManager, Receive-/AudioSend-Service …)
      |
Domain-Modelle
      |
BrandMeister / Netzwerk / Audio / Vocoder / Encoder
```

## Abhängigkeitsregeln

- Oberflächen sprechen ausschließlich mit Application-Services. Sie öffnen
  keine UDP-Verbindung, laden keine native Bibliothek und steuern keine
  Audioausgabe direkt.
- Oberflächen erzeugen keine Dienste selbst. Funkkern und Zusatzdienste kommen
  aus `carendmr/bootstrap.py`.
- Verbinden, Trennen und Senden laufen in jeder Oberfläche über den
  `OperatingController`. Seine `RadioStateMachine` ist die einzige Quelle für
  den Bedienzustand (Getrennt, Verbinde, Verbunden, TX, Trenne, Fehler).
- Oberflächen dürfen reine Datentypen und Fehlerklassen aus tieferen Paketen
  verwenden (z. B. `AudioDirection`, `QrzProfile`, `QrzNotFound`), aber keine
  Infrastruktur erzeugen oder Konfigurationsdateien direkt lesen.
- Application-Services importieren weder Qt noch Oberflächenmodule.
- BrandMeister, Netzwerk, Audio und Vocoder kennen weder Application-Services
  noch Oberflächen.
- Domain-Modelle enthalten keine Netzwerk-, Audio-, SQLite- oder
  Dateisystemabhängigkeit.

## Startpunkt: `carendmr/bootstrap.py`

- `build_radio_core(project_root)` liefert den `RadioCore`: Ereignisse,
  Empfang, Encoder, Audio, Parrot, `ConnectionManager` und
  `OperatingController`. Hauptfenster und Easy-Oberfläche verwenden genau
  diesen Kern; dadurch ist der Funkpfad in beiden identisch.
- `build_desktop_services(core)` liefert die Zusatzdienste des Hauptfensters:
  Stationseinstellungen, QRZ-Abfrage, QRZ-Logbook, ADIF-UDP, Hotkeys,
  Favoriten, Talkgroup-Verzeichnis, QSO-Mitschnitt, Audio-Labor und Benchmark.
- Beide Funktionen sind Qt-frei und können von weiteren Oberflächen
  (Hardwarebedienung, Android) wiederverwendet werden.

## OperatingController

- Synchrone Methoden: `connect`, `disconnect`, `ptt`.
- Asynchrone Methoden für Oberflächen: `connect_async`, `disconnect_async`,
  `start_ptt`, `stop_ptt`. Rückmeldungen kommen über `on_done`/`on_error` im
  Hintergrund-Thread; die Oberfläche übergibt sie selbst in ihren GUI-Thread.
- Der Controller leitet den Bedienzustand aus dem `ApplicationStateStore` des
  Empfangsdienstes ab. Während TX und während eines Verbindungsaufbaus werden
  interne Zwischenzustände des Empfangs nicht als Bedienzustand gemeldet.

## Funkablauf

Vor TX wird die RX-Session vollständig geschlossen; TX meldet sich frisch bei
BrandMeister an; danach startet der Empfang mit einer frischen Session neu.
Plattformunterschiede liegen ausschließlich in technischen Adaptern (Audio,
Timer, DLL-/dylib-Bridges).

## Qt-Oberfläche

- `ui_qt/main_window.py` enthält Aufbau, Ereignisverarbeitung und
  Zustandsanzeige des Hauptfensters. Fachlich zusammenhängende Teile liegen in
  eigenen Modulen, die `MainWindow` als Mixins einbindet:
  - `main_window_radio.py` – Verbinden, Trennen, PTT/TX, Bedienfreigaben
  - `main_window_channels.py` – Talkgroup, Timeslot, Rufart, Favoriten, Schnellwahl
  - `main_window_audio.py` – Audio-Bedienung, Audio-Tuner, Benchmark, Mitschnitt
  - `main_window_logbook.py` – QSO-Historie, QRZ.com, ADIF-UDP
  - `main_window_windows.py` – Menü, Zusatzfenster, Fenstergeometrie
- `ui_qt/easy_window.py` ist die reduzierte Oberfläche für den täglichen
  barrierefreien Betrieb.
- Die frühere Tkinter-Oberfläche wurde mit 0.2.1.87 entfernt.

## Sicherheitsgrenze

Automatisierte Sendetests verwenden ausschließlich den verriegelten
Parrot-Privatruf (siehe ADR-0017). Öffentliche automatisierte Sendetests
bleiben verboten.

## Tests

`python -m pytest tests`. Ein Teil der Tests prüft Quelltext; Tests für das
Hauptfenster lesen den Quelltext über `tests/_ui_sources.py`, damit die
Aufteilung auf mehrere Module keine Rolle spielt. Neue Tests sollen Verhalten
prüfen, nicht Schreibweisen.
