# Installation unter Linux

Linux ist derzeit eine Entwicklungsplattform; die primären
Abnahmeplattformen sind macOS und Windows.

## 1. Voraussetzungen (Debian/Ubuntu)

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-dev build-essential libportaudio2
```

Für andere Distributionen die entsprechenden Pakete verwenden.

## 2. Repository und Python-Umgebung

```bash
mkdir -p ~/AB_Entwicklung
cd ~/AB_Entwicklung
git clone https://github.com/AxBa1964/CarenDMR.git
cd CarenDMR
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Nativen Empfangsdecoder bauen

```bash
make -C native all
```

Das Ergebnis `native/libcarendmr_mbe.so` wird nicht in Git aufgenommen.

Hinweis: `make -C native check` verwendet derzeit die macOS-Variante von
`nm`. Unter Linux ist deshalb zunächst `all` der portable Build-Schritt.

## 4. Tests

```bash
python -m pytest tests
python main.py
```

Audio kann je nach Desktop PulseAudio, PipeWire oder ALSA-Konfiguration
benötigen.
