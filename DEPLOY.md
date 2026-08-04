# CarenDMR 0.0.26.5 – Qt Stable Baseline

## Ziel

Dieser Stand korrigiert ausschließlich die Radiobutton-Initialisierung beim ersten Programmstart.

## Start

```powershell
python main.py --gui
```

## Verbindlicher Funktionstest

1. Programm mit gespeicherten Werten **TS2** und **Privatruf** starten.
2. Vom Feld **Neue Talkgroup** mit Tab weitergehen.
3. Der Fokus muss direkt auf **Timeslot 2** landen.
4. Nochmals Tab drücken: Der Fokus muss direkt auf **Privatruf** landen.
5. F6 und F7 umschalten und den Ablauf erneut prüfen.
6. Danach Verbindung, PTT und Parrot wie in 0.0.26.4 testen.

## Bedienregel

- F5: Verbinden/Trennen; neue TG wird vor dem Verbinden übernommen.
- F6: Timeslot 1/2.
- F7: Gruppenruf/Privatruf.
- Leertaste: fokussierten Button aktivieren; andernfalls PTT toggeln.
- Enter: fokussierten Button aktivieren.

---

# CarenDMR 0.0.26.4 – Qt-Betrieb Stable Baseline

## Ziel

Dieser Stand bereinigt ausschließlich die Tastaturpriorität des funktionierenden Qt-Betriebs.

## Start

```powershell
python main.py --gui
```

## Verbindlicher Funktionstest

1. Programm starten. Der Fokus steht in **Neue Talkgroup**.
2. Ohne Eingabe **F5** drücken: Verbindung mit der aktuellen Talkgroup wird aufgebaut; der Button zeigt **Trennen**.
3. **F5** erneut drücken: Verbindung wird getrennt und der Fokus kehrt in **Neue Talkgroup** zurück.
4. Neue TG eintragen und **F5** drücken: Die neue TG wird als aktuelle TG übernommen und genau mit ihr verbunden.
5. Mit Tab bis **Verbinden/Trennen** gehen:
   - **Enter** aktiviert den fokussierten Button.
   - **Leertaste** aktiviert den fokussierten Button und löst dort kein PTT aus.
6. Außerhalb eines fokussierten Buttons toggelt **Leertaste** bei bestehender Verbindung PTT ein und aus.
7. Parrot-Test mit TG 9990, TS2 und Privatruf durchführen.

## Bedienregel

- **F5:** Verbinden/Trennen; eine eingetragene neue TG wird vor dem Verbinden übernommen.
- **F6:** Timeslot 1/2.
- **F7:** Gruppenruf/Privatruf.
- **Leertaste:** fokussierten Button aktivieren; andernfalls PTT toggeln.
- **Enter:** fokussierten Button aktivieren.
- Im Feld **Neue Talkgroup** besitzt Enter bewusst keine Sonderfunktion.

---

# CarenDMR 0.0.26.3 – Qt-Betrieb: Hotkeys und Zustände

## Start

```powershell
python main.py --gui
```

## Funktionstest

1. Im getrennten Zustand **F5** drücken: Fokus muss im leeren Feld **Neue Talkgroup** stehen.
2. TG eingeben und **Enter** drücken: Die TG erscheint bei **Aktuelle Talkgroup**, das Eingabefeld wird geleert und der Fokus steht auf **Verbinden**.
3. **F6** mehrfach drücken: Timeslot 1 und 2 müssen sichtbar wechseln.
4. **F7** mehrfach drücken: Gruppenruf und Privatruf müssen sichtbar wechseln.
5. Mit TG 9990, TS2, Privatruf verbinden und per PTT senden.
6. PTT beenden und Parrot-Antwort abwarten: unten muss **Empfang aktiv** stehen; **Senden aktiv** darf nicht stehen bleiben.
7. Trennen und das Fenster schließen.

---

# CarenDMR 0.0.26.0 – Qt-Migration, Stufe 1: funktionaler Betrieb

## Ziel dieser Version

Diese Version beginnt die echte Migration der stabilen Version 0.0.25.2 von Tkinter nach PySide6/Qt.

Es handelt sich **nicht** um einen Accessibility-Prototyp und **nicht** um einen Mock. Der Qt-Reiter „Betrieb“ verwendet die vorhandenen produktiven Komponenten für BrandMeister, Empfang, Audio, AMBE und PTT.

Eigene Desktop-TTS und besondere Screenreader-Hilfetexte sind in der Qt-Oberfläche bewusst nicht enthalten. Zuerst wird die technische Gleichwertigkeit hergestellt.

## Installation unter Windows

1. ZIP in einen neuen Ordner entpacken.
2. Die lokalen Konfigurationsdateien aus dem funktionierenden Ordner 0.0.25.2 übernehmen, soweit vorhanden:

```text
config/brandmeister.local.json
config/audio.local.json
config/audio_send.local.json
config/operating.local.json
config/hotkeys.local.json
```

3. Im neuen Projektordner die virtuelle Umgebung aktivieren.
4. Abhängigkeiten installieren:

```powershell
python -m pip install -r requirements.txt
```

5. Tests ausführen:

```powershell
python -m pytest -q
```

Erwartung:

```text
279 passed, 20 subtests passed
```

## Programm starten

Neue Qt-Oberfläche:

```powershell
python main.py --gui
```

Stabile Tkinter-Oberfläche als Vergleich und Rückfallebene:

```powershell
python main.py --gui-tk
```

## Technischer Praxistest

Den Test zunächst ohne Narrator, NVDA oder andere Assistenzsoftware durchführen.

1. Qt-Oberfläche starten.
2. Prüfen, dass unten „AMBE-Encoder bereit“ erscheint. Andernfalls ist PTT gesperrt und die konkrete Ursache wird angezeigt.
3. TG 9990, Timeslot 2 und Privatruf auswählen.
4. „Verbinden“ oder F5 drücken.
5. Erst wenn der reale Empfangszustand verbunden ist, wird PTT freigegeben.
6. PTT-Schaltfläche oder Leertaste einmal drücken: Senden startet.
7. Sprechen.
8. PTT-Schaltfläche oder Leertaste erneut drücken: Senden endet.
9. Prüfen, dass der Empfang automatisch zurückkehrt und das Parrot-Echo abgespielt wird.
10. Mit F5 trennen.

## Umfang dieser Migrationsstufe

Enthalten:

- echter BrandMeister-Verbindungsaufbau
- Trennen
- TG, TS und Rufart
- realer Empfang
- Anzeige der aktuellen Station
- vorhandener AMBE-Encoder
- Mikrofon-/Audio-Sendepfad
- Desktop-PTT als Toggle
- automatische Rückkehr TX zu RX
- F5, F6, F7 und Leertaste
- Tkinter als Rückfallebene

Noch nicht nach Qt portiert:

- Audio- und Mikrofoneinstellungen
- QSO-Historie
- vollständige Einstellungen und Diagnose
- Hotkey-Konfiguration
- Informationsmanager-Oberfläche
- Accessibility-Optimierung

Diese Bereiche bleiben bis zu ihrer Qt-Migration über `--gui-tk` verfügbar.
