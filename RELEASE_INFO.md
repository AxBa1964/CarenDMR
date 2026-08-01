# CarenDMR 0.0.18.3 – Audio-Komfort

## Zweck

Dieses Release schließt den lokalen Audiopfad vor dem privaten Parrot-Sendezweig ab. Es verändert keine DMR-Sendefunktion und sendet keine DMRD-Pakete.

## Enthalten

- Empfangslautstärke von 0 bis 400 Prozent
- zuschaltbare, langsam regelnde AGC für gleichmäßigere Sprachlautheit
- Soft-Limiter gegen harte Übersteuerung bei Verstärkung
- sichtbarer DMR-Ausgangspegel
- DMR-Audio wird während lokaler Testwiedergabe stummgeschaltet
- Mikrofonverstärkung, Ausgabelautstärke, Mute und AGC werden lokal gespeichert
- samplegenaue fünfsekündige Testaufnahme mit 80.000 Samples bei 16 kHz
- 168 automatisierte Tests

## Sicherheitsgrenze

Version 0.0.18.3 enthält keine PTT, keinen AMBE-Encoder und keine DMRD-Sendefunktion. Alle neuen Audiofunktionen wirken ausschließlich lokal auf Aufnahme und Wiedergabe.

## Start

```powershell
python main.py --gui
```
