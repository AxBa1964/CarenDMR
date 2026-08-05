# CarenDMR 0.1.6.8 – TS/RA Keyboard Workflow Final

- Timeslot und Rufart bleiben sichtbar und per Maus bedienbar.
- Beide Statusgruppen sind aus der Tab-Reihenfolge entfernt.
- Tastaturbedienung erfolgt ausschließlich über die konfigurierten Hotkeys.
- Hotkey-Hinweise werden dynamisch aus dem Eingabemanager angezeigt.
- F6/F7 beziehungsweise die individuell belegten Tasten erzeugen genau eine kurze Fachansage.
- Verbinden, PTT, Timeslot und Rufart sind Pflicht-Hotkeys und können nicht gelöscht werden.

Der AudioCuePlayer wird jetzt mit dem vorhandenen AudioSendService initialisiert. Dadurch startet die Qt-Oberfläche wieder ohne `AttributeError`.

---

# CarenDMR 0.1.6.6 – Field-Test Audio & Accessibility Final

- TS/Rufart mit aktuellem Wert beim Tabben
- Verbinden/Trennen eindeutig benannt
- heller lokaler TX-Doppelton vor Sendestart
- reduzierte Container-/Gruppenansagen
