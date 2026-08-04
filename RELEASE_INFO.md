# CarenDMR 0.0.25.2

TTS- und Fokus-Engine V2 beseitigt abgeschnittene Satzanfänge und verhindert, dass der Tab-Fokus den Betriebsbereich verlässt. Die Windows-Sprachausgabe bleibt dauerhaft geöffnet und spricht Fokusmeldungen seriell und vollständig.

# CarenDMR 0.0.25.1.2

Workflow V1 perfektioniert den täglichen Ablauf Trennen → Talkgroup/Timeslot/Rufart einstellen → Verbinden. Fokus, Tab-Reihenfolge und TTS-/RX-Koordination sind jetzt eindeutig.

# CarenDMR 0.0.25.0

Design System V1 vereinheitlicht die visuelle Sprache der Oberfläche. Informationen, Eingaben, Auswahlen und Aktionen sind für sehende Nutzer sofort unterscheidbar. Der DMR-, Audio-, Netzwerk- und Zustandskern bleibt unverändert.

# CarenDMR 0.0.24.6.5

State Machine V1 als Stabilitätsbasis für den Funkbetrieb. GUI, PTT, TX und Betriebsparameter verwenden eine gemeinsame Zustandswahrheit. Der gemeldete Fehler „Verbunden“ bei gleichzeitigem „TX NICHT VERFÜGBAR“ wird damit behoben.

# CarenDMR 0.0.24.6.4

Stabilitätsfix für deutlich sichtbaren Fokus, globale PTT-Beendigung und synchronisierten RX-/Verbindungszustand.

# CarenDMR 0.0.24.6.1

Lokaler Mikrofontest mit Live-Pegel, numerische TG-Eingabe und sichere TX-Beendigung beim Reiterwechsel.

# CarenDMR 0.0.24.5

Qualitätssprint für Sprachlogik und Audiofolge.

# CarenDMR 0.0.24.4

Bedienungs- und Hotkey-Framework V1 mit geführtem Talkgroup-Wechsel, konfigurierbaren Bedienfunktionen, Fokusansagen und Kontext-Hilfe.

# CarenDMR 0.0.24.3.2 – Audio Manager V1

Diese Version koordiniert Caren Assist erstmals mit dem Funk-Audio.

## Funkablauf

- TX-Taste: „Senden“, danach 150 ms Reserve und erst dann Mikrofonfreigabe.
- Während TX: keine weiteren Assist-Meldungen.
- TX-Ende: unmittelbar „Empfang“.
- Gleichzeitig eintreffendes Parrot-Audio wird kurz gepuffert und danach lückenlos ausgegeben.
- Ein TG-Wechsel wird nach erfolgreicher Verbindung als ein Ergebnis gesprochen, nicht als Folge technischer Zwischenzustände.

## Unverändert

- BrandMeister-Protokoll
- AMBE-Codec
- Live-TX-Scheduler
- RX-Decoder
