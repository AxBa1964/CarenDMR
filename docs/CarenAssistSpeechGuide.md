# Caren Assist – Sprachrichtlinie

## Grundsatz

Caren Assist beschreibt den Betriebszustand und die nächste sinnvolle Handlung. Es liest nicht pauschal die grafische Oberfläche vor.

## Meldungsarten

### Fokus

Fokusmeldungen beantworten ausschließlich: Wo befindet sich der Bedienfokus?

- `Fokus Talkgroup 9990.`
- `Fokus Timeslot eins.`
- `Fokus Rufart Privatruf.`

Bedienhinweise gehören nicht in jede Fokusmeldung. Sie werden über Hilfe oder einen geführten Dialog angeboten.

### Betriebszustand

Die Statusabfrage ist unabhängig vom Fokus und verwendet immer dieselbe Reihenfolge:

1. Verbindungsstatus
2. Talkgroup
3. Timeslot
4. Rufart

Beispiel: `Verbunden. Talkgroup 91. Timeslot zwei. Rufart Gruppenruf.`

### Direkte Aktion

Nach einer direkten Umschaltung wird nur das Ergebnis gesprochen:

- `Timeslot zwei.`
- `Rufart Privatruf.`
- `Disconnect.`

### Bewusster Verbindungs- oder Zielwechsel

Die vollständige Rückmeldung wird beendet, bevor RX-Audio freigegeben wird:

`Talkgroup 91. Timeslot zwei. Rufart Gruppenruf. Verbunden.`

## Formulierungsregeln

- Feldname und Wert zusammen nennen.
- `eins` und `zwei` statt missverständlicher Ordnungszahlen.
- Immer `Rufart Gruppenruf` oder `Rufart Privatruf`.
- Keine technischen Zwischenzustände sprechen, wenn das Ergebnis genügt.
- Keine veralteten Fokusmeldungen nach einem Bereichs- oder Hotkeywechsel.
- Funkverkehr darf nicht gleichzeitig mit einer bewusst ausgelösten Betriebsansage wiedergegeben werden.
