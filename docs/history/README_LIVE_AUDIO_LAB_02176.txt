CarenDMR Live-Audiolabor 0.2.1.76 – Widget-Importfix

Fehler in 0.2.1.75:
AudioLabWindow war vorhanden, aber audio_tool_windows.py importierte
AudioLabWidget nicht. Dadurch entstand beim Öffnen des Fensters:
  NameError: name 'AudioLabWidget' is not defined

0.2.1.76 ergänzt genau diesen Import:
  from carendmr.ui_qt.audio_lab_widget import AudioLabWidget

Prüfung:
  python -m pytest .\tests\test_live_audio_lab_02176.py -q

Danach:
  python main.py --gui
