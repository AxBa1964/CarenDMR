# CarenDMR Bedienmodell V2 – 0.0.24.5

## Ziel

Der tägliche Betrieb folgt einem kleinen, eindeutigen Zustandsmodell. Die Oberfläche verhält sich wie ein Funkgerät. Unnötige Dialoge, Rückfragen und lange Erklärungen entfallen.

## Zustände

- **GETRENNT:** TG, Timeslot und Rufart können eingestellt werden. PTT ist gesperrt.
- **VERBINDEN:** Bedienung und PTT sind gesperrt. Nach erfolgreicher Statusansage wird RX freigegeben.
- **VERBUNDEN:** RX und PTT sind verfügbar.
- **SENDEN:** Nur TX läuft; Caren Assist schweigt.
- **TG_WECHSEL:** RX und PTT sind gesperrt. TG, Timeslot und Rufart werden direkt in der Betriebsseite geändert.

## Grundbedienung

- **F2:** TG-Wechsel beginnen. Betrieb öffnen, Fokus auf Talkgroup.
- **Tab:** Talkgroup, aktiver Timeslot und aktive Rufart durchlaufen.
- **Enter:** Eingestellte Werte unmittelbar übernehmen und verbinden. Kein Übernehmen-Feld, keine Rückfrage.
- **Escape:** Wechsel abbrechen; vorherige Werte und bei Bedarf vorherige Verbindung wiederherstellen.
- **F3:** Nur Betriebsstatus sprechen; Fokus wird ignoriert.
- **F5:** Verbinden oder trennen.
- **Leertaste:** PTT nur im Zustand VERBUNDEN und nur im Reiter Betrieb.

## Sprachregeln

- Fokusansagen entstehen nur durch bewusste Tab-Navigation.
- Automatische Fokusänderungen und die Rückkehr ins Fenster bleiben still.
- Fokusmeldungen sind kurz: „Talkgroup 91“, „Timeslot zwei“, „Rufart Gruppe“.
- Status: „Verbunden. Talkgroup 91. Timeslot zwei. Rufart Gruppe.“
- Disconnect: „Verbindung getrennt.“
- Hilfe und Erklärungen werden ausschließlich über F1 ausgegeben.

## Sicherheitsregeln

- PTT ist bei getrenntem Zustand, Verbindungsaufbau, TG-Wechsel, Dialogen und außerhalb des Reiters Betrieb gesperrt.
- Bei F2 wird laufender Empfang beendet, bevor Einstellungen geändert werden.
- RX wird nach Connect oder Wechsel erst nach vollständiger Statusansage hörbar freigegeben.
