# CarenDMR

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

## Aktueller Stand: 0.0.18.3

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
- Empfangslautstärke bis 400 Prozent, zuschaltbare langsame AGC und Ausgangspegelanzeige,
- 168 automatisierte Tests im aktuellen Prüfstand.

Noch nicht enthalten sind eine allgemeine PTT-Schnittstelle, ein
Sprachencoder und Talkgroup-Wechsel. Öffentliche automatisierte
Sendetests sind dauerhaft verboten.

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
Mikrofon und Lautsprecher gemeinsam. Version 0.0.18.3 besitzt weiterhin keine PTT,
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
