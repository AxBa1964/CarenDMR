# CarenDMR 0.0.14 – Read-only-Grundfenster und Anwendungsschicht

## Ziel

Version 0.0.14 trennt die Bedienoberfläche von BrandMeister-, Audio- und
Vocoder-Technik. Der bereits bestätigte TG91-/Timeslot-2-Empfang bleibt
fachlich unverändert und erhält zusätzlich ein erstes barrierefreies
Read-only-Hauptfenster.

## Schichten

```text
Benutzeroberflächen (Tk-GUI und Konsole)
              |
              v
Anwendungsschicht (ReceiveService, StateStore, EventService)
              |
              v
Fachmodelle (ApplicationState, Ereignisse, Statistik)
              |
              v
Technik (BrandMeister, Netzwerk, Audio, Vocoder)
```

Die GUI importiert keine UDP-, DMRD-, Audio- oder ctypes-Funktionen. Sie kennt
nur den `ReceiveService`, den Anwendungszustand und neutrale Ereignisse.

## Anwendungsschicht

- `ApplicationStateStore` verwaltet einen unveränderlichen Gesamtzustand.
- `EventService` hält ein begrenztes, thread-sicheres Ereignisprotokoll.
- `ReceiveService` lädt die lokale Konfiguration, startet den vorhandenen
  Empfang in einem Hintergrundthread und übersetzt Fortschritt und Ergebnis
  in neutrale Zustände.
- Das Beenden erfolgt kooperativ über `stop_requested`; Netzwerk, Decoder und
  Audio werden weiterhin im bestehenden technischen Empfangspfad geschlossen.

## GUI

Start:

```text
python main.py --gui
```

Das Fenster zeigt ausschließlich:

- Verbindungsstatus,
- verbundenen Server,
- Talkgroup 91 und Timeslot 2,
- Audiozustand,
- Empfangsstatistik,
- verständliches Ereignisprotokoll.

Bedienbare Aktionen sind `Verbinden und empfangen`, `Trennen` und `Beenden`.
Die Fokusreihenfolge folgt der Erstellungsreihenfolge. Alle Zustände sind als
Text vorhanden; Farbe und Symbole transportieren keine alleinige Information.
Tastenkürzel: Strg+R, Strg+T, Esc und Strg+Q.

## Sicherheitsgrenze

Die neue Anwendungsschicht führt keine Sendeoperation ein. Das Hauptfenster
besitzt keine PTT, keine Zielwahl und keinen Zugriff auf eine DMRD-Sendefläche.
Der Empfang bleibt fest auf TG91 und Timeslot 2 begrenzt.
