CarenDMR Live-Audiolabor 0.2.1.75 – Importfix

Fehler in 0.2.1.74:
main_window.py importierte LocalAudioLabService korrekt, aber
carendmr/application/__init__.py exportierte die Klasse nicht.

0.2.1.75 ergänzt exakt diesen Export:
  from .local_audio_lab_service import LocalAudioLabService, AudioLabRun

Prüfung:
  python -m pytest .\tests\test_live_audio_lab_02175.py -q

Danach:
  python main.py --gui
