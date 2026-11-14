CarenDMR – gemeinsamer DMR-Sessionablauf macOS/Windows

Dieses Overlay vereinheitlicht den fachlichen RX→TX→RX-Ablauf im ConnectionManager:
- RX-Session vor TX vollständig schließen
- TX mit frischer BrandMeister-Anmeldung
- nach TX RX mit frischer BrandMeister-Anmeldung neu starten
- kein plattformabhängiger Darwin-/Windows-Zweig mehr im ConnectionManager

Nicht angefasst werden:
- native Windows-DLLs / macOS-dylibs
- Windows-Timerauflösung
- Audio-Backends und andere systemtypische Adapter

Voraussetzung:
Der bereits getestete B-Stand von live_voice_transmit.py bleibt bestehen
(Sequence=0, 250-ms Login-Settle, Header nach AMBE-Prebuffer für macOS+Windows).
