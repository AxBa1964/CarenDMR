CarenDMR 0.2.1.77 – QRZ-Logging in der QSO-Historie

- „Bei QRZ loggen“ von der flüchtigen aktuellen Station entfernt.
- QRZ-Logging liegt jetzt in QSO-Historie > QSO-Details.
- Es wird immer das ausgewählte, bereits bestätigte QSO verwendet.
- QRZ-Status und LOGID werden direkt in den QSO-Details angezeigt.
- Bereits erfolgreich geloggte QSOs können nicht versehentlich doppelt gesendet werden.
- QRZ-Fehler verändern den lokalen QSO-Eintrag nicht.

Test:
  python -m pytest .\tests\test_qrz_history_02177.py -q
