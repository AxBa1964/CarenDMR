# CarenDMR

CarenDMR ist ein barrierefrei bedienbarer Desktop-Client für DMR-Sprachbetrieb über BrandMeister. Das Projekt basiert auf Python und Qt und richtet sich besonders an Funkamateure, die einen direkt am Rechner bedienbaren DMR-Client mit guter Tastatur- und Screenreader-Unterstützung suchen.

Aktuelle Version: **0.2.1.90**

## Aktueller Stand

Der produktive Funkpfad unterstützt stabilen RX-/TX-Betrieb über BrandMeister. Parrot-Tests und reale QSOs wurden erfolgreich durchgeführt. Die normale Oberfläche und die vereinfachte Easy-Oberfläche verwenden denselben produktiven Audio- und Funkpfad.

Zu den aktuellen Funktionen gehören unter anderem:

- BrandMeister-Verbindung mit Talkgroup- und Timeslot-Auswahl
- Gruppen- und Privatruf
- RX/TX mit PTT-Bedienung und akustischen Start-/Ende-Signalen
- einstellbare RX- und TX-Pegel
- barrierefreie Qt-Oberfläche mit Tastatur- und Screenreader-Bedienung
- Easy-Oberfläche für eine reduzierte Bedienung
- Talkgroup-Verzeichnis mit Suche und Favoriten
- QSO-Historie mit Kennzeichnung bestätigter Gespräche
- QRZ.com-Stationsinformationen
- manuelles QRZ.com-Logbook-Logging aus der QSO-Historie
- WSJT-X-kompatible Logged-ADIF-Weitergabe per UDP, zum Beispiel an Ham Radio Deluxe
- optionale Synchronisation der QSO-Historie und des Logstatus zwischen mehreren Rechnern über einen gemeinsam synchronisierten Ordner
- Diagnose-, Audio- und Testfunktionen für die Weiterentwicklung

## Plattformen

CarenDMR wird derzeit für folgende Systeme entwickelt und getestet:

- **Windows 11** mit Python 3.12
- **macOS** auf Intel mit Python 3.13

Installationshinweise:

- [Release bauen (Exe und Installer)](docs/RELEASE_BUILD.md)
- [Windows](INSTALL_WINDOWS.md)
- [macOS](INSTALL_MACOS.md)
- [Linux](INSTALL_LINUX.md)

## Schnellstart

Repository klonen:

```bash
git clone https://github.com/AxBa1964/CarenDMR.git
cd CarenDMR
```

Virtuelle Python-Umgebung anlegen und Abhängigkeiten installieren. Unter Windows beispielsweise:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Danach CarenDMR starten:

```powershell
python main.py --gui
```

Die Easy-Oberfläche startet mit `python main.py --easy`. Unter Windows gibt es dafür auch die Startdateien `start_gui.bat` und `start_easy.bat`, die direkt das Python aus `.venv` verwenden.

Unter macOS entsprechend mit `python3 -m venv .venv` und `source .venv/bin/activate`.

## BrandMeister-Konfiguration

Die lokale BrandMeister-Konfiguration wird nicht in Git gespeichert. Als Vorlage dient:

```text
config/brandmeister.example.json
```

Die Datei wird lokal als `config/brandmeister.local.json` angelegt und mit den eigenen Zugangsdaten und Stationsdaten gefüllt. Dateien mit der Endung `.local.json` sind über `.gitignore` vom Repository ausgeschlossen.

Für den Betrieb ist eine gültige DMR-ID sowie eine passende BrandMeister-Zugangskonfiguration erforderlich.

## QRZ.com

Für Stationsinformationen dient `config/qrz.example.json` als Vorlage. Die lokale Datei `config/qrz.local.json` enthält die persönlichen QRZ-Zugangsdaten und wird nicht eingecheckt.

Für das optionale QRZ.com-Logbook gibt es zusätzlich `config/qrz_logbook.example.json`. Auch hier bleibt der API-Key ausschließlich in einer lokalen Konfigurationsdatei.

CarenDMR trägt bei direkt über BrandMeister geführten DMR-QSOs bewusst keine erfundene HF-Frequenz ein. Geloggt werden unter anderem Band `70CM`, Mode `DIGITALVOICE`, Submode `DMR` sowie Talkgroup/Timeslot als Zusatzinformation.

## QSO-Historie und Synchronisation

Die lokale QSO-Historie wird in einer SQLite-Datenbank im lokalen Datenbereich geführt. Die Datenbank selbst wird nicht über Git synchronisiert.

Für mehrere Rechner kann CarenDMR stattdessen optionale Synchronisations-Snapshots in einem gemeinsam synchronisierten Ordner verwenden, zum Beispiel in OneDrive, Dropbox oder einem vergleichbaren Dienst. Jeder Rechner behält dabei seine eigene lokale SQLite-Datenbank.

## Datenschutz und lokale Daten

Nicht für Git vorgesehen sind insbesondere:

- `*.local.json`
- lokale QSO-Datenbanken
- Logs und Diagnoseausgaben
- virtuelle Python-Umgebungen
- lokale Build-Artefakte

Vor einem Commit sollte trotzdem immer `git status` geprüft werden.

## Entwicklung

Der aktuelle Hauptzweig ist `main`. Änderungen sollten klein, nachvollziehbar und testbar bleiben. Der Funk-, Audio- und GUI-Code wird bewusst getrennt gehalten, soweit dies technisch sinnvoll ist.

Tests können mit folgendem Befehl gestartet werden. Bitte pytest verwenden: Ein Teil der Tests ist als einfache `test_…`-Funktion geschrieben und wird von `unittest discover` nicht gefunden.

```powershell
python -m pytest tests
```

Weitere technische Details stehen unter anderem in:

- [DEPLOY.md](DEPLOY.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CHANGELOG.md](CHANGELOG.md)
- [ROADMAP.md](ROADMAP.md)

## Lizenz

CarenDMR steht unter der **GNU General Public License Version 3 (GPLv3)**. Siehe [LICENSE](LICENSE).

Externe Komponenten und Bibliotheken können eigenen kompatiblen Lizenzbedingungen unterliegen. Deren Hinweise und Quellverweise sind zu beachten.

## Hinweis

CarenDMR ist ein unabhängiges Amateurfunkprojekt und kein offizielles Produkt von BrandMeister oder QRZ.com. Für die Nutzung gelten die jeweiligen Regeln, Zugangsvoraussetzungen und Nutzungsbedingungen der angebundenen Dienste.
