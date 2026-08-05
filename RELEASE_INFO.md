# CarenDMR 0.1.7.3.8 – Talkgroup-Name nach Neustart

Aktueller stabiler Entwicklungsstand: **0.1.7.3.8**.

Der zuletzt verwendete DMR-Kanal wird beim Start vollständig wiederhergestellt. Bei einer bekannten Talkgroup erscheint neben TG, Timeslot und Rufart nun auch der Name wieder korrekt.

# CarenDMR 0.1.7.3.8 – Zentrale DMR-Kanalübernahme

Aktueller stabiler Entwicklungsstand: **0.1.7.3.8**.

Das Talkgroup-Feld bietet jetzt eine lokale Live-Suche nach Nummer oder Name. Ein Treffer übernimmt Talkgroup beziehungsweise DMR-ID, Timeslot und Rufart als vollständigen DMR-Kanal. Die Verbindung wird weiterhin bewusst erst mit F5 oder „Verbinden“ gestartet.

# CarenDMR 0.1.7.2 – DMR-Kanal V1

Aktueller stabiler Entwicklungsstand: **0.1.7.2**.

Dieser erste Baustein führt den fachlichen DMR-Kanal als Kombination aus Talkgroup oder DMR-ID, Timeslot und Rufart ein. Die Betriebsseite verwendet jetzt die Begriffe „DMR-Kanal“ und „Talkgroup“. Funklogik und Bedienablauf bleiben unverändert.

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
