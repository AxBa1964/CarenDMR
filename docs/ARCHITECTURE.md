# CarenDMR – Verbindliche Architektur

Stand: Version 0.0.18

## Schichten

```text
GUI / Konsole
      |
Application Services
      |
Domain-Modelle
      |
BrandMeister / Netzwerk / Audio / Vocoder
```

## Abhängigkeitsregeln

- GUI und Konsole rufen ausschließlich Application-Services auf.
- Die GUI öffnet keine UDP-Verbindung, lädt keine native Bibliothek und steuert
  keine Audioausgabe direkt.
- Application-Services koordinieren Abläufe und übertragen neutrale Zustände
  und Ereignisse.
- Domain-Modelle enthalten keine Tk-, Netzwerk-, Audio-, SQLite- oder
  Dateisystemabhängigkeit.
- BrandMeister, Netzwerk, Audio und Vocoder kennen keine Fenster oder
  Bedienelemente.
- Der Konsolen- und GUI-Empfang verwenden dieselbe Empfangstechnik.

## Aktuelle Komponenten

- `carendmr/ui`: barrierefreies Read-only-Hauptfenster
- `carendmr/application`: Empfang, Zustand, Ereignisprotokoll und aktueller
  Sprechdurchgang
- `carendmr/domain`: unveränderliche Fachmodelle
- `carendmr/brandmeister`: Login, Heartbeat, DMRD und rein empfangender Lauf
- `carendmr/network`: UDP-Transport und Diagnose
- `carendmr/audio`: Geräte und PCM-Ausgabe
- `carendmr/vocoder`: AMBE+2-Extraktion und nativer Receive-only-Decoder

## Aktuelle Station

Der technische Empfang meldet nur neutrale `LiveCallActivity`-Daten. Der
`CurrentCallService` erkennt Sprechbeginn, Sprecherwechsel und Sprechende und
aktualisiert das Domain-Modell `CurrentCall`. GUI und Konsole stellen diese
Informationen dar, ohne DMRD-Pakete selbst auszuwerten.

## Sicherheitsgrenze

Der normale Empfangspfad besitzt keine allgemeine DMRD-Sendeschnittstelle.
Öffentliche automatisierte Sendetests bleiben dauerhaft verboten.

## Lokaler Audio-Sendepfad ab 0.0.18

Der `AudioSendService` gehört zur Anwendungsschicht. Er verwendet die bestehende
Audio-Infrastruktur, speichert Testaufnahmen nur im Arbeitsspeicher und kennt
weder BrandMeister noch DMRD. Die GUI darf ausschließlich diesen Service
aufrufen. PTT, Encoder und Netzwerkversand bleiben außerhalb dieses Releases.
