# CarenDMR 0.1.7.3.8 – Talkgroup-Name nach Neustart

## 1. Update installieren und starten

```powershell
cd C:\Users\abaru\OneDrive\AB_Entwicklung\CarenDMR
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py --gui
```

## 2. Automatische Prüfung

```powershell
python -m pytest -q
python tools\release_check.py
```

## 3. Praxistest

1. Eine bekannte Talkgroup aus der Suche übernehmen, zum Beispiel `2623` Niedersachsen Bremen.
2. Prüfen, dass Nummer und Name unter **Aktuelle TG** erscheinen.
3. CarenDMR vollständig beenden.
4. CarenDMR erneut starten.
5. Prüfen, dass TG, Name, Timeslot und Rufart wieder vollständig angezeigt werden.
6. Eine unbekannte TG testen; dafür darf kein Name erfunden werden.
7. Talkgroup-Suche, Enter auf **Verbinden**, F5 sowie einen kurzen Parrot-Test prüfen.

## 4. Git-Sicherung

```powershell
git status
git add .
git commit -m "Release 0.1.7.3.8 - Talkgroup-Name nach Neustart"
git tag -a v0.1.7.3.8 -m "CarenDMR 0.1.7.3.8"
git push origin feature/0.0.22-ui-redesign
git push origin v0.1.7.3.8
git status
```
