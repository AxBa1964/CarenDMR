"""CarenDMR-Tastenfeld: zweite serielle USB-Schnittstelle für die Daten einschalten.

Wird nur beim Einschalten bzw. nach einem Reset ausgeführt. Danach meldet sich
der Pico mit zwei COM-Ports: Konsole (REPL) und Daten (für CarenDMR).
"""
import usb_cdc

usb_cdc.enable(console=True, data=True)
