# Release- und Deployment-Ablauf – CarenDMR 0.0.13.1

Dieses Dokument beschreibt den verbindlichen Ablauf für einen
Entwicklungsmeilenstein. Installationen stehen getrennt in
[INSTALL_MACOS.md](INSTALL_MACOS.md),
[INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) und
[INSTALL_LINUX.md](INSTALL_LINUX.md).

## 1. Ausgangszustand prüfen

```text
git status
git branch --show-current
git pull --ff-only
```

Der Arbeitsbaum muss vor Beginn sauber sein. Releases entstehen nie direkt
auf `master`, sondern auf einem eigenen Branch.

## 2. Version und Dokumentation

Die verbindliche Versionsquelle ist:

```text
carendmr/version.py
```

Bei einem Release müssen mindestens diese Stellen übereinstimmen:

- `carendmr/version.py`
- `README.md`
- `CHANGELOG.md`
- `RELEASE_INFO.md`
- Überschrift dieses Dokuments

Technische oder nutzerrelevante Änderungen werden zusätzlich in Architektur,
Roadmap, Accessibility-Anforderungen oder Entscheidungen dokumentiert.

## 3. Abhängigkeiten und nativer Build

In aktivierter virtueller Umgebung:

```text
python -m pip install -r requirements.txt
```

Auf macOS:

```text
make -C native check
```

Auf Linux:

```text
make -C native all
```

Native Bibliotheken bleiben lokale Build-Artefakte.

## 4. Vollständige Tests

```text
python -m unittest discover -s tests -v
python main.py
```

Alle Tests müssen mit `OK` enden und die Anwendung muss die geplante Version
melden. Netzwerk- oder Audio-Livetests werden nur durchgeführt, wenn sie zum
Meilenstein gehören und ausdrücklich freigegeben sind.

Automatisierte Sendetests auf öffentlichen Talkgroups sind verboten.

## 5. Release-ZIP prüfen

```text
python tools/create_release_zip.py
```

Das ZIP wird unter `release/` erzeugt und nicht committed. Es darf insbesondere
nicht enthalten:

- `.git`, virtuelle Umgebungen oder Caches,
- `config/*.local.json`,
- Logs, Mitschnitte oder lokale Audioinhalte,
- native Build-Artefakte.

## 6. Diff, Commit und Push

```text
git status
git diff --check
git diff
git add <gezielte Dateien>
git status
git diff --cached
git commit -m "CarenDMR <Version> <kurzer Meilenstein>"
git push -u origin <branch>
```

Anschließend wird ein Draft Pull Request gegen `master` eröffnet. Der PR nennt
Umfang, Motivation, Auswirkungen und ausgeführte Prüfungen.

## 7. Merge und Nachkontrolle

Nach Review und erfolgreichen Prüfungen:

1. Pull Request mergen.
2. Lokalen `master` per Fast-forward aktualisieren.
3. Tests aus dem gemergten Stand erneut ausführen.
4. Erst danach bei Bedarf ein GitHub Release aus dem geprüften Stand erstellen.
