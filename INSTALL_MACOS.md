# Installation unter macOS

Getestete Grundlage: macOS auf Intel, Python 3.13 und Xcode Command Line Tools.

## 1. Werkzeuge prüfen

```bash
xcode-select --install
python3 --version
git --version
```

Der erste Befehl meldet möglicherweise, dass die Werkzeuge bereits installiert
sind.

## 2. Repository klonen

```bash
mkdir -p ~/AB_Entwicklung
cd ~/AB_Entwicklung
git clone https://github.com/AxBa1964/CarenDMR.git
cd CarenDMR
```

## 3. Python-Umgebung

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Bei jedem neuen Terminal:

```bash
cd ~/AB_Entwicklung/CarenDMR
source .venv/bin/activate
```

## 4. Nativen Empfangsdecoder bauen

```bash
make -C native check
```

Die erzeugte Datei `native/libcarendmr_mbe.dylib` ist ein lokales,
ignoriertes Build-Artefakt.

## 5. Tests

```bash
python -m unittest discover -s tests -v
python main.py
```

Beim ersten Audiozugriff kann macOS nach Mikrofonberechtigung fragen.
Mikrofonzugriff nur für Funktionen erlauben, die ihn tatsächlich benötigen.

## Aktualisieren

```bash
git status
git pull --ff-only
python -m pip install -r requirements.txt
make -C native check
python -m unittest discover -s tests -v
```

`git pull` nur bei sauberem Arbeitsbaum ausführen.
