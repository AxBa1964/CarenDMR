CarenDMR Live-Audiolabor 0.2.1.74 – Integrationskorrektur

0.2.1.73 enthielt den Labor-Service und das Fenster, aber die Einbindung in
main_window.py war nicht vollständig. 0.2.1.74 korrigiert genau diese Punkte.

Installation:
ZIP direkt über C:\ABDevelop\CarenDMR entpacken und ersetzen.

Prüfung:
  python -m pytest .\tests\test_live_audio_lab_02174.py -q

Danach:
  python main.py --gui
