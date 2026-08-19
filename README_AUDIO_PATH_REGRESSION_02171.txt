CarenDMR Audio-Pfad-Regression 0.2.1.71

Korrektur gegenüber 0.2.1.70:
Der produktive LivePcmCapture sammelt seine internen TX-Messpuffer nur bei
aktiviertem Audio-Debug. Der erste Regressionstest las diese Puffer bei
deaktiviertem Debug aus und zeigte deshalb fälschlich -120 dBFS.

0.2.1.71 aktiviert Audio-Debug ausschließlich als Beobachter für den
Regressionstest. Der produktive Signalweg selbst bleibt unverändert.

Zusätzliche QS-Sicherung:
Wenn DMR-Voice-Bursts gesendet wurden, aber der Vor-AMBE-Messpuffer leer ist,
bricht der Test mit einem Instrumentierungsfehler ab statt falsche -120-dBFS-
Werte auszugeben.

Start:
  python .\tools\audio_path_regression.py
