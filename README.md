# CarenDMR

**Aktueller Entwicklungsstand: 0.0.28.3 – Qt-Einstellungen Bedienkorrekturen**

Die neue Qt-Oberfläche portiert zunächst ausschließlich den echten Funkbetrieb. Sie wird mit `python main.py --gui` gestartet. Die stabile Tkinter-Oberfläche bleibt mit `python main.py --gui-tk` verfügbar. Accessibility-Sonderlogik folgt erst nach technischer Gleichwertigkeit.

# CarenDMR 0.0.25.2

Aktueller Entwicklungsstand mit TTS- und Fokus-Engine V2. Fokusmeldungen im Betrieb werden vollständig und seriell gesprochen; der Tab-Kreis bleibt auf den vier Betriebsfeldern begrenzt.

# CarenDMR 0.0.25.1.2

**Workflow V1:** Der tägliche Bedienablauf wurde finalisiert: TG direkt überschreiben, Tab auf aktive Auswahl, CONNECT nach Rufart sowie RX erst nach vollständiger Connect-Ansage.

# CarenDMR 0.0.25.0

**State Machine V1:** Eine zentrale Betriebszustandsmaschine steuert Connect, RX, PTT, TX und die Editierbarkeit der Betriebsparameter. Dadurch kann die GUI nicht mehr „Verbunden“ anzeigen, während PTT weiterhin gesperrt ist.

# CarenDMR 0.0.24.6.4

# CarenDMR 0.0.24.3.2

# CarenDMR

**0.0.24.3.1:** Audio-Diagnose speichert pro TX das CarenDMR-Eingangssignal mit 16 kHz und das 8-kHz-Signal direkt vor AMBE.

**Aktueller Stand: 0.0.24.3.1** – moderne Betriebsseite, QSO-Historie und kompakte kategorisierte Einstellungen.

Aktueller Entwicklungsstand: **0.0.22.1**

> Ein freier, konsequent barrierefrei entwickelter DMR-Client für
> BrandMeister.

CarenDMR entsteht für blinde und sehbehinderte Funkamateure. Das konkrete
Ziel ist ein kleiner, zuverlässiger Client, mit dem Caren weltweit – besonders
auf Talkgroup 91 – englischsprachige Funkgespräche führen kann.

Barrierefreiheit ist keine spätere Ergänzung. Eine Funktion gilt erst als
fertig, wenn sie ohne Maus, ohne visuelle Orientierung und mit verständlichen
akustischen beziehungsweise Screenreader-Rückmeldungen bedienbar ist.

## Projektumfang

CarenDMR konzentriert sich ausschließlich auf:

- DMR über das BrandMeister-Netzwerk,
- Empfang und später kontrolliertes Senden von Sprache,
- vollständige Tastaturbedienung,
- VoiceOver unter macOS sowie später NVDA und JAWS unter Windows,
- verständliche Status-, Fehler- und Sicherheitsmeldungen,
- Windows und macOS; Linux bleibt eine unterstützte Entwicklungsplattform.

D-Star, YSF, P25, NXDN, M17, AllStar und ein allgemeines
Digitalfunk-Framework gehören nicht zum Projektumfang.

## Aktueller Stand: 0.0.22.1

Der technische Stand umfasst:

- bestätigten BrandMeister-Login und Heartbeat,
- striktes Parsen und Modellieren von DMRD-Paketen,
- empfangsseitige AMBE+2-Extraktion und einen nativen, nur dekodierenden
  mbelib-Adapter für macOS, Linux und Windows,
- Jitterpuffer und begrenzte PCM-Wiedergabe,
- bestätigten TG91-Live-Empfang,
- ein hart verriegeltes privates Parrot-Testprofil für 9990 auf Timeslot 2,
- lokale Sprachausgabe unter macOS,
- barrierefreies Read-only-Hauptfenster mit Live-QSO-Anzeige,
- aktuelle DMR-ID, Talkgroup, Timeslot und Sprechdauer,
- lokaler Mikrofon-Sendepfad mit Pegelanzeige, Testaufnahme, Wiedergabe und Loopback,
- optionaler, separat bereitgestellter DroidStar-Vocoder über native Bridge,
- lokaler PCM-zu-AMBE-Prüflauf ohne Funkübertragung,
- dynamisch schaltbarer Empfang für frei gewählte Talkgroup und TS1/TS2,
- automatische Rückkehr zum zuvor aktiven Empfang nach einem Parrot-Test,
- weiterhin verfügbare Empfangsdiagnose für Netzwerk, Filter, Decoder und Audio,
- 195 automatisierte Tests im aktuellen Prüfstand.

Der Parrot-Sendepfad bleibt experimentell: Verzögerung und Sendeaudioqualität sind noch nicht optimiert. Freie Aussendungen oder allgemeine Zielwahl sind nicht freigegeben; der Test bleibt fest auf den privaten Parrot 9990/TS2 begrenzt.

Zusätzlich führt die GUI eine lokale QSO-Historie abgeschlossener empfangener Sprechdurchgänge.

## Schnellstart

Repository klonen und die Anleitung für das Betriebssystem verwenden:

- [macOS](INSTALL_MACOS.md)
- [Windows](INSTALL_WINDOWS.md)
- [Linux](INSTALL_LINUX.md)

Der kürzeste plattformunabhängige Prüfablauf nach aktivierter virtueller
Umgebung ist:

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Für den nativen Empfangsdecoder ist zusätzlich ein C-Compiler erforderlich.
Die betriebssystemspezifischen Anleitungen beschreiben den Build.


## TG91-Live-Empfang

Nach aktivierter virtueller Umgebung und gebautem nativen Decoder startet der
bereits vorhandene, rein empfangende Live-Test mit:

```text
python main.py --listen
```

Der Lauf ist fest auf TG91 und Timeslot 2 begrenzt und endet mit Strg+C oder
optional mit `--duration`. Er sendet keine DMRD-Pakete. Vor dem Netzempfang
wird der lokale Audioweg mit einem kurzen Prüfton kontrolliert.

## Read-only-Hauptfenster

```text
python main.py --gui
```

Das Fenster zeigt BrandMeister-, Empfangs- und Audiozustand sowie die aktuelle
DMR-ID, Talkgroup, Timeslot und Sprechdauer. Strg+R startet den Empfang,
Strg+T trennt ihn, Esc oder Strg+Q beendet das Programm.

## Lokaler Audio-Sendepfad

Im Reiter **„Senden – lokaler Audiotest“** können Mikrofone eingelesen und
ausgewählt, eine fünfsekündige Testaufnahme erstellt, der Pegel beobachtet und
die Aufnahme lokal wiedergegeben werden. Ein viersekündiger Loopback-Test prüft
Mikrofon und Lautsprecher gemeinsam. Version 0.0.18.2 besitzt weiterhin keine PTT,
keinen AMBE-Encoder und keine Netzwerk-Sendefunktion.

## Dokumentation

- [Roadmap](ROADMAP.md)
- [Mitarbeiten](CONTRIBUTING.md)
- [Architektur](docs/ARCHITECTURE.md)
- [Verbindliche Accessibility-Anforderungen](docs/ACCESSIBILITY_REQUIREMENTS.md)
- [BrandMeister-Kompatibilität](docs/BRANDMEISTER_COMPATIBILITY.md)
- [Upstream-Provenienz und Lizenzgrenzen](docs/UPSTREAM_PROVENANCE.md)
- [Release- und Deployment-Ablauf](DEPLOY.md)
- [Änderungsverlauf](CHANGELOG.md)

## Sicherheit und sensible Daten

Lokale Dateien `config/*.local.json` dürfen Zugangsdaten enthalten und werden
von Git sowie vom Release-ZIP ausgeschlossen. Passwörter, DMR-Zugangsdaten,
Paketmitschnitte mit persönlichen Inhalten und lokale Audioaufnahmen gehören
niemals in Issues, Commits oder Logs.

Sendefunktionen werden fail-closed entwickelt: keine freie Zielwahl, keine
unbegrenzten Wiederholungen und keine automatisierten Tests auf öffentlichen
Talkgroups.

## Lizenz

CarenDMR steht unter
[GNU GPL Version 3 oder später](LICENSE). Herkunft und Lizenzgrenzen
adaptierter Referenzbestandteile sind in
[UPSTREAM_PROVENANCE.md](docs/UPSTREAM_PROVENANCE.md) dokumentiert.


## Längerer TG91-Empfang

`python main.py --listen` läuft rein empfangend bis Strg+C. Mit `python main.py --listen --duration 600` wird der Lauf auf zehn Minuten begrenzt. Alle 30 Sekunden werden Diagnosewerte ausgegeben.


## Dynamischer Talkgroup-Empfang

Im Reiter **Empfang** werden Talkgroup und Timeslot vor dem Verbinden eingetragen. Nach der Anmeldung sendet CarenDMR einen kurzen stummen DMRD-Gruppenruf-Impuls über die bestehende UDP-Verbindung. Dadurch wird die gewählte Talkgroup dynamisch aktiviert. Ein BrandMeister-API-Key ist nicht erforderlich. Für einen Zielwechsel zuerst trennen, neues Ziel eintragen und erneut verbinden.

## Neue Oberfläche ab 0.0.22.1

Die Betriebsseite verwendet ein modernes dunkles Kartenlayout. Alle vorhandenen Funkfunktionen bleiben erreichbar: CONNECT/DISCONNECT, TG wechseln, TS1/TS2, Gruppe/Privat, Stumm und die rastende TX-Taste. Ausführliche PowerShell-Diagnosen sind standardmäßig ausgeschaltet und können unter Einstellungen gezielt aktiviert werden.


## TX/RX-Zeitmessung

Version 0.0.24.3.1 schreibt bei jedem Sendedurchgang eine Millisekunden-Zeitleiste nach `logs/tx_rx_timing.log`. Die Datei dient ausschließlich dazu, den langsamen Abschnitt zwischen RX, TX und erneutem RX eindeutig zu bestimmen.

### Parrot-RX-Audiodiagnose ab 0.0.24.3.1

Bei einem Parrot-Test auf 9990 / TS2 / Privat speichert CarenDMR zusätzlich das empfangene, nach AMBE decodierte Echo als `logs/audio_debug/rx_..._03_parrot_nach_ambe_8k.wav`. Zusammen mit den beiden TX-WAV-Dateien lässt sich der komplette Signalweg vergleichen.


## Eingabemanager

Hotkeys werden unter `Programm > Einstellungen …` nicht als Text eingegeben. Eine Funktion wird ausgewählt und die gewünschte Tastenkombination tatsächlich gedrückt. Konflikte können gezielt neu zugeordnet, Zuordnungen entfernt und Standardwerte wiederhergestellt werden.


## QSO-Historie in Qt

Der zweite Hauptreiter zeigt die vorhandene lokale SQLite-Historie als Stationsübersicht. F9 öffnet die Historie, Pfeiltasten wechseln die Station, Tab verlässt die Tabelle und F11 bestätigt oder widerruft das ausgewählte QSO.
