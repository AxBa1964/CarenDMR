## 0.2.1.84 – Gemeinsamer Funkkern (Refactoring Schritt 1)

- Neu: `carendmr/bootstrap.py` mit `build_radio_core()`. Der Funkkern (Ereignisse, Empfang, Encoder, Audio, Parrot, `ConnectionManager`, `OperatingController`) wird an genau einer Stelle zusammengesetzt.
- Hauptfenster und Easy-Oberfläche übernehmen diesen Kern, statt ihn jeweils selbst zu verdrahten. Funk-, Audio- und TX-Verhalten unverändert; RX-AGC startet weiterhin diagnosehalber ausgeschaltet.
- Testsuite: `pytest` ist Standard (ein Teil der Tests wird von `unittest discover` nicht gefunden), veraltete Tests auf den aktuellen Stand gebracht, Versions-Pin-Tests durch einen Formattest ersetzt.
- Audio-Benchmark schließt seine SQLite-Verbindungen jetzt zuverlässig (unter Windows blieb die Datenbankdatei sonst gesperrt).

## 0.2.1.64 – RX-Grundpegel +12 dB

## 0.2.1.68

- macOS/Windows MD380-Dynarmic-Build wieder reproduzierbar: der benötigte `native/md380_dynarmic_build/CMakeLists.txt`-Wrapper gehört jetzt zum Projekt.
- `.gitignore` ignoriert nur noch die erzeugten `out*`-Verzeichnisse statt des gesamten CMake-Wrapperordners.
- Das macOS-Buildskript prüft den Wrapper vor dem Build und meldet ein unvollständiges Projektpaket ausdrücklich.


- Fester RX-Grundgain Faktor 4 (+12 dB) nach AGC bzw. vor der PCM16-Ausgabe.
- RX 100 % ergibt damit Faktor 4 gegenüber dem rohen AMBE/mbelib-PCM.
- Der vorhandene Benutzerbereich bis RX 400 % bleibt erhalten; PCM16-Clipping-Schutz bleibt aktiv.
- TX-, BrandMeister-, AMBE-Decoder- und Session-Logik unverändert.
- RX-Pegeldiagnose aus 0.2.1.63 bleibt erhalten.

## 0.2.1.63 – RX-Pegeldiagnose

- Misst den PCM16-Rohpegel direkt nach der AMBE-Decodierung, noch vor AGC, RX-Lautstärkeregler und Windows-Ausgabe.
- Schreibt pro empfangenem Ruf `RX_PCM_LEVEL_ABSCHLUSS` mit Peak, RMS, Peak_dBFS und RMS_dBFS in das TX/RX-Timing-Log.
- Keine Änderung des tatsächlichen RX-Audiopegels.

## 0.2.1.62 – Privatruf-Aktivierung korrigiert

- Privatrufe werden beim Verbinden oder Zielwechsel nicht mehr mit einem stummen DMR-Aktivierungsruf ausgelöst.
- Dadurch startet TG 9990 (BrandMeister Parrot) nicht mehr bereits vor dem ersten echten PTT-Ruf.
- Dynamische Talkgroup-Aktivierung bleibt unverändert für Gruppenrufe erhalten.
- Zusätzliche Schutzprüfung verhindert, dass die Aktivierungsroutine künftig versehentlich mit `call_type="private"` verwendet wird.
- TX/RX-Session-Wiederverwendung, AMBE-/Audio-Pfad und Gruppenrufbetrieb bleiben unverändert.

## 0.2.1.57 – Easy Accessibility Feinschliff

- Easy: Talkgroups werden im Eingabefeld mit getrennten Ziffern dargestellt.
- Easy: PTT-Hilfetext entfernt; PTT bleibt für den Screenreader kurz benannt.
- Easy: transienter Status „Verbindung getrennt“ während des Aufbaus wird nicht mehr angekündigt.
- Easy: Verbinden/PTT reagieren zusätzlich zuverlässig auf Enter.
- Funkkern unverändert.

# Changelog

## 0.2.1.56 – Easy-Oberfläche Stufe 1

- Neue zusätzliche Qt-Easy-Oberfläche für den täglichen barrierefreien Funkbetrieb; Start mit `python main.py --easy`.
- Normaler Tastaturweg bewusst auf **Talkgroup → Verbinden → PTT** reduziert.
- Timeslot und Rufart bleiben außerhalb der Tab-Reihenfolge; `Strg+T` wechselt TS1/TS2, `Strg+R` Gruppe/Privat, jeweils nur im getrennten Zustand.
- `F4` gibt den aktuellen Funkkontext über native Qt-Accessibility aus.
- Keine automatische Ansage des aktuell empfangenen Rufzeichens; das empfangene Funk-Audio bleibt ungestört.
- Easy verwendet `OperatingController` für Verbinden, Trennen und PTT. Es wurde keine zweite BrandMeister-, RX-, TX-, AMBE- oder Audio-Funklogik implementiert.
- `OperatingController` reicht bestehende optionale TX-Callbacks an den stabilen `ConnectionManager` weiter und kann beim Trennen optional auf das tatsächliche RX-Ende warten.
- Die bestehende Desktop-Oberfläche (`--gui`) bleibt unverändert verfügbar.

## 0.2.1.55

- MapTiler-Satellitenlayer auf die von MapTiler für Leaflet dokumentierte HiDPI-URL `@2x.jpg` bei `tileSize: 512` und `zoomOffset: -1` umgestellt.
- Umschaltung **Karte/Satellit** expliziter gemacht: jeweils andere Basiskarte wird entfernt, gewünschte Basiskarte hinzugefügt und hinter Overlays gelegt.
- Verbindungslinie und HAM Grid werden nach Basiskartenwechsel erneut nach vorne bzw. aktualisiert.
- Kleine Kartenquellenanzeige zeigt sichtbar **Karte** oder **Satellit**, damit ein erfolgreicher Layerwechsel unmittelbar erkennbar ist.
- MapTiler-Tilefehler werden mit der betroffenen Tile-URL in der Shell protokolliert.
- Keine Änderung an QRZ-Daten, DMR-, AMBE-, RX/TX-, Audio- oder TG-Monitor-Kern.

## 0.2.1.54

- QRZ-Karte unterstützt jetzt eine echte Satelliten-Basiskarte über MapTiler Satellite v4.
- Optionaler `maptiler_api_key` wird ausschließlich aus `config/qrz.local.json` gelesen und an das QRZ-Fenster übergeben.
- Der Button **Satellit** schaltet zwischen OpenStreetMap und Satellitenansicht um; bei aktiver Satellitenansicht wird er zu **Karte**. Ohne MapTiler-Key bleibt der Button deaktiviert und erklärt im Tooltip die fehlende Konfiguration.
- Leaflet-Layer-Control enthält bei vorhandenem Key ebenfalls **Karte** und **Satellit**.
- HAM Grid deutlich sichtbarer gemacht: bereits in der Weltansicht werden Maidenhead-Felder mit kräftigeren gelben Linien und Feldbezeichnungen angezeigt.
- Bei höherem Zoom werden 4-stellige Maidenhead-Squares gezeichnet und ab Zoom 7 beschriftet.
- HAM Grid bleibt als unabhängiges Overlay sowohl über Karte als auch Satellit nutzbar.
- Flaggen-Pins, Verbindungslinie, Welt/Details, Entfernung/Richtung und QRZ-Datenanzeige bleiben unverändert.
- Keine Änderung am DMR-, AMBE-, RX/TX-, Audio- oder TG-Monitor-Kern.

## 0.2.1.53

- QRZ-Karte zeigt den eigenen Standort und die Gegenstation jetzt als deutlich erkennbare Flaggen-Pins statt einfacher Punktmarker.
- Eigener Standort und Gegenstation verwenden unterschiedliche Pin-/Flaggenfarben und bleiben mit permanentem Rufzeichen beschriftet.
- Klick auf einen Flaggen-Pin zeigt Rolle, Rufzeichen, Name, Locator, Land und Koordinaten.
- Weltansicht berücksichtigt weiterhin beide Standorte; Detailansicht zoomt weiterhin auf die Gegenstation und öffnet deren Stations-Popup.
- Verbindungslinie, Entfernung/Richtung, HAM Grid und der Leaflet-Bounds-Fix aus 0.2.1.52 bleiben erhalten.
- Keine Änderung am Funk-, Audio-, QRZ-Daten- oder TG-Monitor-Kern.

## 0.2.1.52

- Leaflet-Karte erhält unmittelbar beim Erzeugen eine gültige Startansicht (`setView([20, 0], 2)`), bevor Tile-, Marker-, Linien- oder HAM-Grid-Layer hinzugefügt werden.
- HAM-Grid liest Karten-Bounds nur noch, wenn Leaflet den Kartenstatus bereits vollständig geladen hat.
- Größen-Synchronisation verwendet `invalidateSize({pan:false, debounceMoveend:true})` statt animiertem `invalidateSize(true)`, um unnötige Move-/Bounds-Zwischenzustände während Qt-Resize-Ereignissen zu vermeiden.
- Ziel ist die Beseitigung von `Uncaught TypeError: Cannot read properties of undefined (reading 'min')` beim Öffnen des QRZ-Fensters.
- Keine Änderung an QRZ-Daten, Profilansicht, DMR-, AMBE-, RX/TX-, Audio- oder TG-Monitor-Kern.

## 0.2.1.51

- Leaflet-1.9.4-CSS-SRI auf den offiziellen SHA-256-Wert korrigiert. Der zuvor eingetragene falsche Digest führte dazu, dass Qt WebEngine das Leaflet-CSS blockierte.
- QRZ-Karte hält jetzt explizit einen `_map_ready`-Status. Qt führt Karten-JavaScript erst nach erfolgreichem `loadFinished` aus.
- Alle Qt→JavaScript-Aufrufe für `syncMapSize`, `worldView`, `detailView` und `toggleGrid` prüfen zusätzlich per `typeof`, ob die jeweilige Funktion bereits definiert ist.
- Frühe Resize-Events können dadurch kein `ReferenceError: syncMapSize is not defined` mehr auslösen.
- Größenfix aus 0.2.1.50 bleibt erhalten.
- Keine Änderung an QRZ-Daten, DMR-, AMBE-, RX/TX-, Audio- oder TG-Monitor-Kern.

## 0.2.1.50

- QRZ-Leaflet-Karte nach Qt-WebEngine-Größenänderungen synchronisiert.
- `map.invalidateSize(true)` wird jetzt nach dem Kartenladen, beim Wechsel auf **Welt**, beim Wechsel auf **Details** und nach Größenänderungen des QRZ-Fensters ausgeführt.
- Weltansicht wird nach vollständigem Laden des WebViews erneut berechnet.
- HTML-/Body-Overflow deaktiviert; die eingebettete Karte erzeugt keine eigenen horizontalen oder vertikalen Browser-Scrollbalken mehr.
- Kartencontainer füllt den WebView absolut über `inset: 0`.
- Keine Änderung an QRZ-Daten, Markern, Entfernung, HAM Grid, DMR-, AMBE-, RX/TX- oder Audiokern.

## 0.2.1.49

- QRZ.com-Button ohne separaten Platzhalter umgesetzt: Qt `retainSizeWhenHidden` hält den benötigten Platz unsichtbar frei, ohne schwarzen Restbereich und ohne Layout-Sprung.
- QRZ.com-Button im Bereich **Aktuelle Station** weiter nach links gerückt.
- QRZ-Stationsfenster vollständig kompakter gestaltet: Profilbild auf 300×300 px vergrößert, Beschriftungen und Werte enger zusammengeführt, Stationskopf und Infokarte neu gegliedert.
- LoTW/eQSL-Werte `0/1` werden als **Nein/Ja** dargestellt.
- Entfernung und Peilrichtung zwischen eigener QRZ-Station und Gegenstation werden berechnet und angezeigt, sofern beide Koordinaten vorliegen.
- Die bisher statisch gezeichnete Karte wurde durch eine interaktive Leaflet-/OpenStreetMap-Karte in Qt WebEngine ersetzt.
- Karte unterstützt Mausrad-Zoom, Verschieben, Weltansicht, Detailzoom auf die Gegenstation, Marker für eigene Station/Gegenstation und eine Verbindungslinie.
- **HAM Grid** als zuschaltbare Maidenhead-Ebene ergänzt: bei kleinerem Zoom Locator-Felder, bei höherem Zoom feinere 4-stellige Rasterquadrate.
- OSM-Attribution bleibt sichtbar; keine Karten-Vorlade-/Offlinefunktion.
- Satellitenschalter ist architektonisch vorgesehen, aber bewusst deaktiviert, solange kein lizenzierter Kartenanbieter/API-Key konfiguriert ist. Keine Nutzung veralteter oder nicht belastbarer Gratis-Satellitenendpunkte.
- Keine Änderung am DMR-, AMBE-, RX/TX-, Audio-, QRZ-XML- oder TG-Monitor-Kern.

## 0.2.1.48

- DMR-Kanalbereich der Betriebsmaske visuell neu gegliedert: aktueller Kanal links als kompakte Instrumentanzeige, Schnellwahl oben und manuelle Kanalwahl darunter.
- Aktueller Kanal zeigt zusätzlich kompakt `TSx · Gruppe/Privat`.
- Die drei Favoriten-Schnellwahlbuttons bleiben erhalten; daneben gibt es jetzt eine Combobox **Alle Favoriten …** mit sämtlichen gespeicherten Favoriten.
- Auswahl über die Favoriten-Combobox übernimmt wie die Schnellwahl immer vollständig TG, Timeslot und Rufart und verwendet denselben sicheren Ablauf für getrennten bzw. verbundenen Betrieb.
- Timeslot-/Rufart-Hinweise wurden optisch zurückgenommen; Hotkey-Hinweise bleiben dynamisch erhalten.
- QRZ.com-Button im Bereich **Aktuelle Station** ist kompakter. Sein Platz wird dauerhaft reserviert, sodass das Ein-/Ausblenden des Buttons die Maske nicht mehr verschiebt.
- Keine Änderung am DMR-, AMBE-, RX/TX-, Audio-, QRZ-Daten- oder TG-Monitor-Kern.

## 0.2.1.47

- Zentrales Fenstermanagement für CarenDMR-Zusatzfenster ergänzt.
- Position und Größe werden pro Fenstertyp in `config/windows.local.json` gespeichert und beim nächsten Öffnen wiederhergestellt.
- Gespeicherte Fenster, die nach Monitor-/Auflösungswechsel vollständig außerhalb aller sichtbaren Bildschirme liegen, werden automatisch auf einen vorhandenen Bildschirm zurückgeholt.
- QRZ.com-Stationsfenster verwendet einen gemeinsamen Positionsschlüssel unabhängig vom Rufzeichen und öffnet deshalb künftig am zuletzt verwendeten Ort.
- Einstellungen, Audio-Benchmark, Audio Coach und Audio-Tuner nutzen ebenfalls die zentrale Geometriespeicherung.
- Eigenständiger TG-Monitor merkt sich Position/Größe und kann über lokale IPC nach vorne geholt oder geschlossen werden.
- Neues Menü **Fenster** listet Hauptfenster, sichtbare Zusatzfenster und den laufenden TG-Monitor auf.
- Menübefehle **Alle Fenster nach vorne**, **Alle Zusatzfenster schließen** und **Fensterpositionen zurücksetzen** ergänzt.
- Mehrmonitorbetrieb bleibt erhalten: Fenster werden beim Nach-vorne-Holen nicht auf einen anderen Monitor verschoben.
- Keine Änderung am DMR-, AMBE-, QRZ-Daten-, RX-, TX- oder Audiokern.

## 0.2.1.46

- QRZ.com XML Callbook Data Service als vom Funkkern getrenntes Modul ergänzt.
- Lokale Zugangsdaten über `config/qrz.local.json`; Beispiel unter `config/qrz.example.json`. Lokale Zugangsdaten bleiben durch `*.local.json` von Git und Release-ZIP ausgeschlossen.
- Für die aktuelle Station wird asynchron geprüft, ob ein QRZ.com-Datensatz vorhanden ist. Nur bei Treffer erscheint der Button **QRZ.com** im Bereich **Aktuelle Station**.
- Neues nicht-modales Fenster **QRZ.com – <Rufzeichen>** mit Profilbild, Name, Ort, Region, Land, Locator, Koordinaten, CQ-/ITU-Zone und QSL-Informationen.
- Lokale Qt-Karte ohne externen Kartenanbieter: Weltübersicht mit eigener Station und Gegenstation als Flaggenmarker; **Details** zoomt auf die Umgebung der Gegenstation, **Weltkarte** kehrt zurück.
- Button **QRZ.com öffnen** öffnet die öffentliche Profilseite im Browser.
- QRZ-Session-Key wird wiederverwendet und bei erkannten Session-/Timeoutfehlern automatisch erneuert.
- Keine Änderung am DMR-, AMBE-, RX-, TX- oder Audiokern.

## 0.2.1.45

- RX-AGC für einen eindeutigen Praxistest beim Programmstart bewusst ausgeschaltet. Die AGC kann während der laufenden Sitzung weiterhin manuell über die bestehende Checkbox aktiviert werden.
- Timing-Diagnose erweitert: Jede interne RX-Stop-Anforderung schreibt `RX_STOP_ANGEFORDERT` mit Grund, Running-/TX-Pause-Status und Switch-Information in `logs/tx_rx_timing.log`.
- `ConnectionManager` protokolliert zusätzlich `RX_STOP_QUELLE` für Disconnect, Kanalwechsel und den alten TX-Pfad. Damit lässt sich ein unerwarteter RX-Abbruch beim nächsten Auftreten eindeutig einer internen Ursache zuordnen.
- Qt-Fontwarnung beim Beenden adressiert: die visuelle Statusanzeige verwendet keine Pixel-Schriftgröße mehr, deren `pointSize()` intern `-1` ergibt, sondern eine gültige Punktgröße.
- Keine Änderung an DMR-Protokoll, AMBE-Decoder, BrandMeister-Heartbeat oder RX-Zeitbegrenzung.

## 0.2.1.44

- Falsche TG-Monitor-IPC-Fehlermeldung behoben: `waitForBytesWritten()` ist nicht mehr das Erfolgskriterium; maßgeblich ist die tatsächliche Antwort von CarenDMR.
- Menü `Programm` um **TG-Monitor starten** ergänzt. Der Monitor wird als eigener Prozess mit derselben Python-/venv-Umgebung gestartet.
- TG-Monitor als Einzelinstanz abgesichert. Ein zweiter Start wird erkannt und mit dem Hinweis `Der TG-Monitor läuft bereits.` abgewiesen.
- Bestehende Kanalübergabe, BrandMeister-Last-Heard-Monitoring, 3-Sekunden-Mindestdauerfilter und 5-Minuten-TX-Sicherheitslimit bleiben unverändert.
- Keine Änderung am DMR-, AMBE-, RX- oder Audiokern.

## 0.2.1.43

- Historische TX-Sicherheitsabschaltung von 60 Sekunden auf 300 Sekunden (5 Minuten) erhöht.
- Bestehende Installationen mit dem alten gespeicherten Standardwert 60 Sekunden werden beim Start automatisch auf 300 Sekunden migriert; bewusst abweichende Werte bleiben erhalten.
- Zulässige Obergrenze des TX-Sicherheitslimits auf 300 Sekunden erweitert.
- TG-Monitor erhält einen einstellbaren Mindestsprechdauer-Filter, Standard 3 Sekunden. Kurze Verbindungs-/Kerchunk-Tests werden ausgeblendet; 0 Sekunden deaktiviert den Filter.
- Mindestsprechdauer wird in `config/tg_monitor.local.json` gespeichert.
- Keine weiteren Änderungen am DMR-, AMBE-, TX/RX- oder Audiokern.

## 0.2.1.42

- BrandMeister-Last-Heard-Subscription ergänzt: Nach erfolgreichem Socket.IO-Connect sendet der TG-Monitor `join = everything`.
- Live-Test bestätigt: Ohne Subscription kamen 0 `mqtt`-Events; mit Subscription wurden sofort BrandMeister-Events geliefert.
- Diagnose-Logging aus 0.2.1.41 bleibt erhalten und protokolliert nun zusätzlich `SUBSCRIBE join=everything`.
- Keine Änderung am DMR-, AMBE-, TX/RX- oder Audiokern.

## 0.2.1.41

- TG-Monitor um gezieltes Diagnose-Logging in `logs/tg_monitor.log` erweitert.
- Protokolliert Socket.IO-Verbindungsaufbau/-abbau, Fehler, jedes empfangene `mqtt`-Rohereignis, geparste Felder und die Filterentscheidung für überwachte Talkgroups.
- Diagnosefehler bleiben vom Monitorbetrieb entkoppelt; Schreibfehler im Log dürfen den TG-Monitor nicht stoppen.
- Keine Änderung am DMR-, AMBE-, TX/RX- oder Audiokern.

## 0.2.1.40

- Eigenständiges Startprogramm `tg_monitor.py` ergänzt. Der TG-Monitor beobachtet mehrere frei wählbare BrandMeister-Talkgroups über den offiziellen Last-Heard-Socket.IO-Datenweg.
- TG-Monitor läuft unabhängig vom DMR-/AMBE-/Audiokern und kann daher parallel zu CarenDMR betrieben werden.
- Aktivitätsanzeige pro TG mit Status, Station, Name, Dauer und letzter Aktivität.
- Überwachte TGs und gewünschter Übergabe-Timeslot werden lokal in `config/tg_monitor.local.json` gespeichert.
- Lokale Qt-IPC (`QLocalServer`/`QLocalSocket`) zur Übergabe eines markierten Kanals an eine laufende CarenDMR-Instanz.
- CarenDMR weist externe Kanalwechsel während TX oder während Verbindungsaufbau/-abbau ab. Bei bestehender RX-Verbindung erfolgt der vorhandene Ablauf Trennen → Kanal setzen → Verbinden.
- Neue Laufzeitabhängigkeit `python-socketio[client]` für den BrandMeister-Last-Heard-Feed.

## 0.2.1.39

- RX-Lautstärke 100 % gibt gültige PCM16-Samples jetzt unverändert (0 dB) aus; der bisherige `tanh`-Soft-Limiter senkt normale Empfangspegel nicht mehr ab.
- Pegel außerhalb des PCM16-Bereichs werden weiterhin sicher auf -32768 bis +32767 begrenzt, insbesondere nach AGC/Verstärkung.
- Veraltetes separates TX-Zeit/Zähler-Label unter dem TX-Button entfernt; die TX-Laufzeit bleibt ausschließlich im großen TX-Button sichtbar.
- Release-ZIP bereinigt: reproduzierbare `native/vendor`-Quellen und `native/md380_dynarmic_build/out`-Buildartefakte werden nicht mehr mitarchiviert; die benötigten Buildskripte und nativen Quellen bleiben enthalten.

## 0.2.1.38 – Favoriten-Drop sauber neu aufbauen + beste TG-Suche zuerst

- Behebt den rein visuellen Drag&Drop-Fehler, bei dem die verdrängte Favoritenzeile bis zum nächsten Refresh verschwand.
- Die Favoritenreihenfolge wird weiterhin ausschließlich im `FavoriteService` gespeichert.
- Der interne QTableWidget-Zeilenmove wird beim Drop nicht mehr zusätzlich ausgeführt.
- Die Tabelle wird unmittelbar im nächsten Qt-Event-Loop-Schritt aus der gespeicherten Reihenfolge komplett neu aufgebaut.
- Ohne Suchtext bleiben Favoriten geschlossen oben und folgen ihrer Drag&Drop-Reihenfolge.
- Bei aktiver Suche hat Trefferqualität Vorrang vor Favoritenstatus.
- Eine exakt eingegebene TG/DMR-ID steht immer ganz oben, z. B. `262` vor `2621`, `2622`, `2623` usw.
- Danach folgen numerische Präfix-Treffer, dann exakte/beginnende Namen und erst anschließend allgemeine Teiltreffer.
- Funk- und Audiopfad bleiben unverändert.

## 0.2.1.38 – Favoriten per Maus sortieren + TX sichtbar größer

- Favoriten bleiben im Talkgroups-Reiter immer als geschlossener Block ganz oben.
- Nur Favoritenzeilen sind per Maus verschiebbar.
- Die Reihenfolge wird direkt in `favorites.local.json` gespeichert.
- Die neue Reihenfolge bestimmt zugleich die drei Schnellwahl-Buttons im Betrieb.
- Bei aktiven Filtern ist Drag&Drop bewusst gesperrt, damit keine uneindeutige Teilreihenfolge gespeichert wird.
- TX wurde ausdrücklich nach unten vergrößert: feste Höhe 150 px.
- Die bisher separat reservierte TX-Sekundenzeile entfällt; während des Sendens steht die Laufzeit direkt im großen TX-Button.
- Funk- und Audiopfad bleiben unverändert.

## 0.2.1.38 – Schnellwahl, sofortige RX-Liste, breiter TX

- Die ersten drei Einträge der vorhandenen Favoritenliste erscheinen im Betrieb als Schnellwahl-Hotbuttons.
- Ein Hotbutton übernimmt immer den kompletten DMR-Kanal: Ziel/TG, Timeslot und Rufart.
- Im getrennten Zustand verbindet die Schnellwahl nach der Übernahme automatisch.
- Bei bestehender Verbindung läuft der Wechsel strikt `Trennen → Favorit übernehmen → neu verbinden`.
- Schnellwahl ist während TX gesperrt.
- `Zuletzt gehört` wird nun erst nach dem tatsächlichen Speichern des abgeschlossenen Empfangs aktualisiert und zeigt die neue Station sofort.
- TX nutzt nahezu die gesamte Breite der rechten Bedienkarte.
- Funk- und Audiopfad bleiben unverändert.

## 0.2.1.38 – Ziel-Dopplungen entfernt, TX priorisiert

- Entfernt das redundante Feld `Ziel` aus `Aktuelle Station`.
- Entfernt die redundante Spalte `Ziel` aus `Zuletzt gehört`.
- QSO-Status nutzt die frei gewordene Breite in der Stationskarte.
- TX ist deutlich höher und über nahezu die gesamte Breite der rechten Bedienkarte gezogen.
- TX bleibt damit der optisch wichtigste und am schnellsten erfassbare Bedienknopf.
- Funk- und Audiokern unverändert.

## 0.2.1.38 – Betriebsmaske strukturiert und optisch beruhigt

- `Aktuelle Station` wurde neu strukturiert: Beschriftungen sind zurückhaltend, Werte stehen in klar erkennbaren Wertefeldern.
- `Zuletzt gehört` ist jetzt eine echte kompakte Tabelle mit den Spalten Zeit, Rufzeichen, Name, Land und Ziel.
- Angezeigt werden die letzten drei unterschiedlichen Stationen, damit wiederholte Durchgänge derselben Station die Liste nicht verdrängen.
- Die Tabelle bleibt zunächst rein informativ; es wird kein Privatruf ausgelöst.
- Die rechte Funk-/Audiokarte endet direkt nach TX; der bisherige große künstliche Leerraum unter TX entfällt.
- Betriebsinformationen schließen direkt unter den Bedienkarten an.
- Das alte übergroße Fenstermaß aus 0.2.1.33 wird bei der ersten 0.2.1.38-Ausführung einmalig auf 980 × 720 normalisiert; danach werden Position und Größe wieder wie gewohnt gespeichert.
- DMR-Kanal und Audio-Bedienung verwenden die gleiche klare Beschriftungs-/Wertehierarchie.
- Das separate Audio-Tuner-Fenster wurde vollständig neu aufgeteilt: natürlicher Dialogaufbau, Profilzeile, gleichmäßige Reglerzeilen, klar abgegrenzte Werte und erklärender Hinweis.
- Das Audio-Tuner-Fenster verwendet seine natürliche Inhaltshöhe statt freie Fläche zwischen den Zeilen zu verteilen.
- Funk-, BrandMeister- und Audio-Signalpfad bleiben unverändert.

## 0.2.1.38 – Ruhige Betriebsmaske, eigener Audio-Tuner, zuletzt gehört

- Der DMR Audio-Tuner ist aus der Betriebsmaske entfernt und öffnet als eigenes nicht-modales Fenster.
- Öffnen/Schließen des Tuners verschiebt TX, Pegelanzeigen oder andere Bedienelemente nicht mehr.
- In der Betriebsmaske bleibt nur der kompakte Button `Audio-Tuner…`.
- Der redundante große CarenDMR-Kopfblock entfällt; Titel und Version stehen bereits in der Fenstertitelleiste.
- Außenabstände und vertikale Abstände der Betriebsmaske wurden reduziert.
- TX wurde kompakter, ohne seine zentrale Position in der Bedienung zu verlieren.
- Unter `Aktuelle Station` werden die drei zuletzt gehörten Stationen angezeigt.
- Anzeige je Station: Uhrzeit, Rufzeichen bzw. DMR-ID, Name, Land sowie TG/TS.
- Die Liste ist zunächst reine Information; es wird bewusst noch kein Privatruf ausgelöst.
- Betriebsinformationen bleiben durch die gewonnene Höhe besser sichtbar.
- Funk-, BrandMeister- und Audioverarbeitung bleiben unverändert.

## 0.2.1.38 – Audio Coach wartet auf vollständiges Parrot-Echo

- Behebt die vorzeitige Coach-Auswertung nach einem kurzen/stalen Parrot-Terminator.
- Der Coach kennt jetzt die tatsächliche Länge der unmittelbar zuvor gesendeten TX-Aufnahme.
- Ein eingehender Parrot-Terminator beendet den Test nur, wenn mindestens 85 % dieser realen TX-Länge als RX-PCM empfangen wurden.
- Kurze Zwischen-/Alt-Terminatoren werden protokolliert und ignoriert; die PCM-Sammlung läuft weiter.
- Kein künstlicher fester Warte-Timer: Vollständigkeit wird aus der realen TX-Länge plus DMR-Terminator bestimmt.
- Erst danach wird die Parrot-WAV gespeichert und die Analyse gestartet.
- Tuner-/Coach-UI aus 0.2.1.31 bleibt unverändert.

## 0.2.1.38 – Tuner kompakter + Coach-Empfehlungen eindeutig

- Entfernt die sichtbaren Buttons `Parrot vorbereiten` und `Audio-Assistent` aus dem DMR Audio-Tuner.
- Entfernt die zusätzliche Audio-Assistent-Statuszeile unter dem Tuner.
- `Zurücksetzen` bleibt erhalten und sitzt platzsparend neben der Profilauswahl.
- Der Audio Coach bleibt der einzige sichtbare Einstieg für einen Modulationstest.
- Coach-Empfehlungen werden nicht mehr als missverständliche reine Delta-Werte angezeigt.
- Statt `Tiefen -2` bei bereits aktiven `-2 dB` zeigt der Coach nun z. B. `Tiefen → -4 dB (aktuell -2 dB, weitere Änderung -2)`.
- Gleiches gilt für Sprachmitten, Präsenz, Höhen, Dynamik und Mic-Gain.
- Messalgorithmus und Funk-/Audio-Pfad bleiben unverändert.

## 0.2.1.38 – Audio Coach erkennt echten Parrot + RX-AGC-Startzustand

- Audio Coach beendet seine Sitzung nicht mehr direkt nach TX, sondern wartet auf die echte Parrot-Antwort.
- Die reale dekodierte Parrot-Antwort `9990 -> eigene DMR-ID` wird im Audio-Testordner gespeichert und erst am Terminator als vollständig markiert.
- Der TX-Bericht mit vorläufig `echo_received=false` wird beim Coach nicht mehr vor der realen RX-Antwort erzeugt.
- Gespeicherte RX-Audioeinstellungen (Lautstärke, Stumm, AGC) werden beim Programmstart nun tatsächlich in den ReceiveService übernommen.
- Behebt damit den Zustand „AGC im UI aus, intern im RX trotzdem an“, der den hörbaren leisen Satzanfang mit anschließendem Hochregeln verursachte.
- Audio Coach bleibt passiv; kein separater Mikrofon-Vorlauf.
- Fensterposition/-größe aus 0.2.1.29 bleibt erhalten.

## 0.2.1.38 – Audio Coach passiv + Fensterposition merken

- Audio Coach öffnet das Mikrofon nicht mehr vor dem eigentlichen PTT.
- Der Coach benutzt beim Test exakt denselben Live-TX-Pfad wie ein normaler PTT und beobachtet ihn nur.
- Der frühere separate 2-s-Mikrofon-Vorlauf wurde entfernt, weil er WASAPI-/Headset-Zustände verändern konnte.
- Der One-Shot-Test verzögert die TX-Audiokette nicht mehr gegenüber einem normalen PTT.
- Position, Größe und Qt-Fensterzustand des Hauptfensters werden beim Beenden gespeichert und beim nächsten Start wiederhergestellt.
- Liegt eine gespeicherte Position nach einem Monitorwechsel außerhalb aller Bildschirme, wird das Fenster sicher auf einen vorhandenen Bildschirm zurückgeholt.
- Persistente BrandMeister-Session, Private-RX-Filter, MD380, +2 dB und 240-ms-Puffer bleiben unverändert.

## 0.2.1.38 – Privatruf-RX korrekt an eigene DMR-ID

- Behebt den nach Wireshark eindeutig nachgewiesenen RX-Filterfehler bei Privatrufen.
- Gruppenruf bleibt unverändert: empfangen wird die eingestellte Talkgroup.
- Privatruf wird korrekt als eingehender Ruf an die eigene DMR-ID gefiltert.
- Damit wird z. B. die Parrot-Antwort `9990 -> 2632198` nicht mehr verworfen.
- Persistente BrandMeister-Session aus 0.2.1.27, MD380, +2 dB und 240-ms-Puffer bleiben unverändert.

## 0.2.1.38 – Persistente BrandMeister-Session für TX/RX

- RX und TX verwenden jetzt dieselbe angemeldete BrandMeister-UDP-Verbindung.
- Beim Drücken von PTT wird nur der RX-Thread pausiert; Socket, Login und Funkziel bleiben erhalten.
- Nach dem DMR-Terminator wird derselbe Socket unmittelbar wieder vom RX-Thread übernommen.
- Kein Logout/Login und keine erneute Zielaktivierung zwischen TX und RX.
- Bei echtem TG-/TS-/Rufart-Wechsel wird die bestehende Session bewusst geschlossen und für das neue Funkziel neu aufgebaut.
- Neue Timing-Marken dokumentieren Session-Wiederverwendung und den RX↔TX-Handover.
- MD380, +2 dB Eingangspegel und 240-ms-Encoderpuffer bleiben unverändert.

## 0.2.1.38 – Sofortiger RX nach TX

- Kritischer Funkablauf korrigiert: Live-TX wartet nach dem DMR-Terminator nicht mehr auf ein Parrot-Echo.
- Nach PTT AUS werden Voice-Frames und Terminator beendet; anschließend kehrt die Anwendung sofort in den normalen RX-Pfad zurück.
- Parrot-Antworten werden damit wie jede andere eingehende Funkstation über den normalen Empfang verarbeitet.
- MD380/DroidStar, +2 dB Eingangspegel und der 240-ms-TX-Puffer bleiben unverändert.
- Die spezielle Offline-/Legacy-Parrot-Testfunktion bleibt getrennt und wird von diesem Live-Fix nicht verändert.

## 0.2.1.25 – MD380-Live-TX mit +2 dB Arbeitspunkt

- Übernimmt den Gewinner des kontrollierten Offline-Hörtests: +2 dB unmittelbar vor dem MD380/DroidStar-Vocoder.
- Pegelanhebung erfolgt ausschließlich im `Md380DynarmicEncoder` mit sicherer PCM16-Begrenzung.
- Keine Änderung an 240-ms-TX-Puffer, DMR-Sendetakt, TX/RX-Umschaltung, Audio-Tuner oder RX.
- Ziel des Live-Parrot-Tests: bestätigen, dass die offline bewerteten 8–9/10 auch über BrandMeister erhalten bleiben.

## 0.2.1.25 – Zirkelimport im MD380-Pegeltest behoben

- `carendmr.vocoder` lädt den DMR-Extractor nicht mehr beim Paketimport, sondern erst beim tatsächlichen Aufruf.
- Dadurch kann `NativeMbeReceiveVocoder` im Offline-MD380-Pegeltest ohne `brandmeister <-> vocoder`-Zirkel importiert werden.
- Der Pegeltest aus 0.2.1.23 bleibt unverändert: -2, -1, 0, +1, +2 und +3 dB.
- Keine Änderung am Live-TX, MD380-Puffer, RX oder Klangpfad.

## 0.2.1.25 – MD380-Pegel-Feinhörtest

- Neuer Offline-Test `tools/ambe_md380_level_sweep.py`.
- Vergleicht denselben 8-kHz-PCM-Eingang ausschließlich über MD380/DroidStar bei -2, -1, 0, +1, +2 und +3 dB.
- Keine Änderung am Live-TX, 240-ms-Puffer, RX, Audio-Tuner oder Mikrofonpfad.
- Ziel: besten MD380-Arbeitspunkt für Lautstärke und saubere Wortenden bestimmen.

## 0.2.1.25 – MD380-Live-TX entkoppelt

- Entkoppelt Mikrofon/PCM-Erfassung, MD380-Encoding und den festen 60-ms-DMR-Sendetakt über zwei begrenzte Queues.
- Nutzt den bestehenden 240-ms-TX-Vorlauf zugleich als vier Bursts großen Encoder-Reservepuffer.
- Ziel: gemessene sporadische MD380-Latenzspitzen dürfen den DMR-Sendetakt nicht mehr unterbrechen.
- Neue Diagnosepunkte `TX_ENCODER_PUFFER_BEREIT` und `TX_ENCODER_PUFFER_STATISTIK`.
- Keine Änderung an Audio-Tuner, Mikrofonpegel, RX-Umschaltung oder Parrot-Zustandslogik.

## 0.2.1.25 – Windows-DLL-Ladepfad für MD380

- Registriert unter Windows `C:\msys64\ucrt64\bin` automatisch über `os.add_dll_directory()`, bevor `carendmr_md380_bridge.dll` geladen wird.
- Behebt damit den bestätigten Startfehler durch fehlende Laufzeitauflösung von `libgcc_s_seh-1.dll`, `libwinpthread-1.dll` und `libstdc++-6.dll`.
- Keine manuelle PATH-Erweiterung mehr nötig.
- Live-TX bleibt auf dem MD380/DroidStar-Encoder; keine weitere Klangänderung in diesem Schritt.

## 0.2.1.25 – MD380/DroidStar als Live-TX-Encoder

- Der im kontrollierten Offline-A/B-Test deutlich bessere MD380/DroidStar-Vocoder wird zum bevorzugten Live-TX-Encoder.
- Der bisherige Windows-Vocoder bleibt vorerst als Fallback erhalten, falls die MD380-Bridge auf einer Installation fehlt.
- Parrot und normale Gruppen-/Privat-TX-Wege verwenden dieselbe Encoder-Factory.
- Keine zusätzliche Pegel-, Gate- oder EQ-Änderung: Der Codecwechsel wird zunächst isoliert im echten Parrot-Betrieb bewertet.

## 0.2.1.25 – MD380-Dynarmic Windows-Linkfix

- Behebt den reproduzierbaren Linkfehler `cannot find -lSTATIC` im MD380-Dynarmic-Windows-Build.
- Der festgelegte Upstream-Commit enthält `target_link_libraries(md380_vocoder STATIC dynarmic)`; `STATIC` wird dort fälschlich als Bibliotheksname behandelt.
- Das Build-Script korrigiert ausschließlich diese Zeile reproduzierbar auf `PRIVATE dynarmic`.
- `core_perl` wird für `shasum` automatisch in den PATH aufgenommen.
- `CMAKE_POLICY_VERSION_MINIMUM=3.5` wird im Build-Script selbst gesetzt.
- Keine Änderung am Live-Audio- oder Funkpfad.

## 0.2.1.25 – DroidStar-MD380-A/B

- Der Upstream-Codevergleich belegt: Der festgelegte DroidStar-Stand verwendet für DMR bei aktiviertem `USE_MD380_VOCODER` den Pfad `md380_encode_fec()` statt `MBEVocoder::encode_2450x1150()`.
- Neuer Windows-x86_64-Diagnosepfad über `md380_vocoder_dynarmic`, um diesen Android/DroidStar-Vocoderpfad auf dem N100 vergleichbar zu machen.
- `native/build_md380_dynarmic_windows.ps1` baut eine lokale `carendmr_md380_bridge.dll` aus einem fest fixierten Upstream-Commit.
- `tools/ambe_md380_ab.py` vergleicht dieselbe 10/10-WAV bei +1 dB: bisheriges Vocoder-Plugin A gegen MD380/Dynarmic B; beide werden mit demselben CarenDMR/mbelib-Decoder wiedergegeben.
- Kein Eingriff in Live-TX, DSP, BrandMeister oder GUI.

## 0.2.1.17 – Vocoder-Build A/B

- Neuer Offline-Test `tools/ambe_plugin_ab.py`.
- Vergleicht zwei DroidStar-kompatible Windows-Vocoder-Binaries mit exakt demselben 8-kHz-PCM16-Eingang.
- Fester Encoder-Eingangspegel: +1 dB, der beste Punkt aus dem Feinsweep 0.2.1.16.
- Beide Encoder-Ausgaben werden mit demselben CarenDMR/mbelib-Decoder zurück in PCM gewandelt.
- `report.json` dokumentiert Dateigröße, SHA-256 des Plugins, SHA-256 der erzeugten AMBE-Codewörter sowie ob Binärdateien bzw. AMBE-Ausgaben identisch sind.
- Upstream-Abgleich korrigiert eine frühere Annahme: DroidStar auf Android/iOS lädt ebenfalls externe Vocoder-Plugins; deshalb ist der kontrollierte Vergleich ein Plugin-Build-A/B und kein Plattform-Audiotest.
- Kein Netzwerk, kein BrandMeister, kein TX und keine Änderung am Live-Funkpfad.

## 0.2.1.16 – AMBE-Pegel-Feinsweep korrigiert

- Fehlendes Werkzeug `tools/ambe_level_fine_sweep.py` ergänzt.
- Feste Offline-Teststufen +1, +2, +3, +4 und +5 dB.
- Direkter Skriptstart aus der Projektwurzel funktioniert über abgesicherten Importpfad.
- Clipping-Risiko wird vor dem Encode erkannt; gefährliche Varianten werden übersprungen.
- Ergebnisordner `ambe_level_fine_sweep` enthält Referenz, Loopback-WAVs und `report.json`.
- `DEPLOY.md` nennt exakt das tatsächlich vorhandene Feinsweep-Werkzeug.
- Kein Eingriff in Live-TX, DSP, AMBE-Framing oder BrandMeister.

## 0.2.1.15 – AMBE-Pegel-Feinsweep

- Feinsweep um den bisher besten Encoder-Eingangspegel: +1, +2, +3, +4 und +5 dB.
- Verwendet unverändert dieselbe 10/10-Referenz-WAV und denselben DroidStar-Encoder/CarenDMR-mbelib-Decoder.
- Keine Änderung am Live-Audiopfad; weiterhin vollständig offline.
- Ziel: optimalen Encoder-Eingangspegel zwischen dem guten +3-dB-Ergebnis und dem bereits angekratzten +6-dB-Ergebnis bestimmen.

## 0.2.1.14 – AMBE-Pegelsweep

- Neues Offline-Werkzeug `tools/ambe_level_sweep.py`.
- Verwendet die bereits als 10/10 bewertete `03_vor_ambe_8k.wav` als unveränderte Referenz.
- Testet 0, +3, +6, +9 und +12 dB vor dem AMBE-Encoder.
- Jede Variante läuft durch den realen DroidStar-AMBE-Encoder und den aktuellen CarenDMR/mbelib-Decoder.
- Vor jeder Codierung wird Clipping-Risiko geprüft; gefährliche Varianten werden übersprungen statt hart begrenzt.
- Ausgabe enthält Referenz-WAV, Loopback-WAVs und `report.json` mit RMS/Peak und Codec-Statistik.
- Kein Netzwerk, kein BrandMeister, kein Parrot und keine Änderung am Live-Audiopfad.

## 0.2.1.13 – AMBE Codec Lab korrigiert

- Direkter Start von `tools/ambe_codec_lab.py` aus der Projektwurzel repariert.
- Windows-Build erzeugt jetzt Decoder und DroidStar-Vocoder-Bridge gemeinsam und prüft deren Exporte.
- Zwei verbliebene pytest-Abhängigkeiten in Tests entfernt; vollständiger Lauf wieder mit `unittest` allein möglich.
- DEPLOY auf den aktuellen Entwicklungs- und Offline-Hörtest reduziert.
- Keine Änderung am Funk- oder Audiopfad.


## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.2.1.10 – TX-Ende und Parrot-Signalisierung getrennt

- Der Doppel-Piep wird jetzt unmittelbar nach dem tatsächlich gesendeten DMR-Terminator ausgelöst.
- Die akustische TX-Ende-Quittung wartet nicht mehr auf das vollständige Parrot-Echo.
- Nach Loslassen der PTT bleibt die Oberfläche im Zustand „TX wird beendet“, bis der Terminator gesendet wurde.
- Während des Parrot-Echos zeigt die Oberfläche „Warte auf Antwort“; PTT bleibt bis zur vollständigen RX-Rückkehr gesperrt.
- Erst nach Parrot-Abschluss und Neustart des normalen Empfangs wird der Zustand wieder auf RX gesetzt.
- Keine Änderungen an DMR-Paketierung, AMBE, DSP oder Audioqualität.

## 0.2.1.9 – WASAPI-Ausgabe und Gerätebindung

- Parrot- und normaler RX-Audioausgang verwenden jetzt ausdrücklich das in den Einstellungen gewählte Wiedergabegerät.
- Die Ausgabe öffnet das Gerät mit dessen nativer Abtastrate und resampelt 8-kHz-DMR-Audio programmintern.
- Lokale Start-/Endtöne werden ebenfalls auf eine vom gewählten Gerät unterstützte Rate umgesetzt.
- MME, WASAPI und andere PortAudio-Host-APIs nutzen damit denselben gespeicherten Ausgabepfad.
- DSP, AMBE, BrandMeister-Protokoll und TX-Paketierung blieben unverändert.

## 0.2.1.8 – Mikrofoneingang-Diagnose

- WASAPI/MME-Eingänge protokollieren Geräteindex, Host-API, native Rate, Kanalzahl, Blockgröße, Callback-Anzahl und empfangene Samples.
- RMS und Peak werden je Eingangskanal erfasst; der signalführende Kanal wird im Diagnosebericht ausgewiesen.
- Jeder geführte Audiotest speichert `input_diagnostics.json`.
- Bei stummem Eingang nennt die Fehlermeldung Callback-, Sample- und Kanalwerte.
- Ein Benutzerabbruch schreibt `state = aborted` und `AUDIO_TEST_ABORTED`.
- Keine Änderungen an AMBE, DSP, BrandMeister oder Funkprotokoll.

## 0.2.1.7 – Audio Coach Stabilisierung

- Laufender Modulationstest kann über denselben Button jederzeit abgebrochen werden.
- Der Button wechselt während des Tests sichtbar auf **Abbrechen**.
- Erfolg, Fehler und Benutzerabbruch laufen über eine zentrale Abschlussroutine.
- Bei Fehlern werden Audio-Testzustand, Vorlauf, PTT und laufender TX sauber beendet.
- Status und Button kehren zuverlässig in den Grundzustand zurück.
- Paketweise Konsolendiagnose bleibt ausschließlich an den vorhandenen Diagnosemodus gebunden.

## 0.2.1.6 – Audio Engine V2

- Gemeinsamer Eingabepfad für Live-TX, Audio Coach und lokale Audiotests.
- Audiogeräte werden bevorzugt mit 16 kHz geöffnet; bei Treiberablehnung wird automatisch die native Geräte-Abtastrate verwendet.
- Hochwertiges Polyphasen-Resampling auf den einheitlichen 16-kHz-Verarbeitungspfad und anschließend auf 8 kHz für AMBE.
- WASAPI-Geräte mit abweichender nativer Rate verursachen keinen Fehler `PaErrorCode -9997` mehr.
- `test_metadata.json` dokumentiert native Rate, Zielrate, Resampling und Audio-Engine-Version.
- Neue Zeitmarke `TX_AUDIO_ENGINE_V2` protokolliert Gerät, Host-API und Raten.
- Funkprotokoll, BrandMeister-Logik und Benutzeroberfläche unverändert.

## 0.2.1.4 – Audioqualität messbar machen

- Audio-Test speichert die tatsächlich aktiven Mic-Gain-, DSP-, Profil-, Geräte- und Versionsdaten in `test_metadata.json`.
- Der Audio Coach kennzeichnet klar, mit welchem Profil und Mic-Gain der Vergleich gemessen wurde.
- Empfehlungen werden ausdrücklich als vorgeschlagene Änderungen und nicht als aktive Einstellungen angezeigt.
- TG-Referenzen enthalten zusätzlich Mittelwert, Standardabweichung, Min/Max sowie 10-/90-Perzentile je Kennzahl.
- Funkkern, BrandMeister-Protokoll, QSO-Historie und GUI außerhalb der Audio-Werkzeuge bleiben unverändert.

## 0.2.1.3 – Parrot-Echozeit an Sprachdauer angepasst

- Fehler behoben, durch den das feste 15-Sekunden-Echo-Fenster längere Parrot-Antworten abschnitt.
- Das Echo-Fenster berücksichtigt jetzt die tatsächliche TX-Dauer plus 10 Sekunden für BrandMeister-Anlauf und Nachlauf.
- Die gewählte Fensterdauer und TX-Dauer werden in `logs/tx_rx_timing.log` protokolliert.
- Keine Änderungen an GUI, Audio Coach oder allgemeiner Funkarchitektur.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.2.1 – Audio-Werkzeuge aus der Hauptoberfläche ausgelagert

- Der Hauptreiter **Audio-Benchmark** wurde aus der CarenDMR-Hauptoberfläche entfernt.
- Die Hauptoberfläche enthält wieder nur **Betrieb**, **QSO-Historie** und **Talkgroups**.
- **Audio-Benchmark** und **Audio Coach** öffnen als eigenständige Fenster über das Menü **Programm**.
- Benchmark-Sammlung und Modulationsvergleich verwenden weiterhin denselben langlebigen `AudioBenchmarkService`; es wird keine zweite Funk- oder Benchmark-Instanz erzeugt.
- Die Benchmark-Oberfläche enthält nur Sammlung, Status und Referenzdetails.
- Der Modulationstest und die Vergleichstabelle befinden sich ausschließlich im separaten Audio-Coach-Fenster.
- Funkkern, Benchmark-Service und Qt-Oberflächen bleiben voneinander getrennt.

## 0.2.0 – Eigene Modulation vergleichen

- Neuer Button **Eigene Modulation testen** im Reiter Audio-Benchmark.
- Geführter Parrot-Test mit festem, reproduzierbarem Referenztext.
- Methodisch fairer Vergleich: eigener AMBE-Codec-Loopback gegen empfangene AMBE-Referenzstationen.
- Vergleichstabelle für Pegel, Dynamik, Tiefen, Sprachmitten, Präsenz und Höhen.
- Konkrete, zunächst nur angezeigte Vorschläge für Mic-Gain und Audio-Tuner.
- Automatische Erkennung des abgeschlossenen Audio-Tests.
- Persistenz unter `comparisons/` und `latest_comparison.json`.
- Keine automatische Änderung produktiver Audioeinstellungen.

# Änderungsverlauf

## 0.1.9.4 – Benannte Audio-Referenzen

- bestehende TG91-Benchmarkdaten werden beim ersten Start einmalig nach `data/audio_benchmarks/references/TG91_Global/` migriert
- `benchmark.db`, `current.json`, `reference.json` und `metadata.json` liegen künftig gemeinsam in der benannten Referenz
- `index.json` merkt sich die aktive Referenz und bereitet weitere TG-Referenzen vor
- die Benchmark-Oberfläche zeigt den aktiven Referenznamen an
- Metadaten werden nach jeder Analyse mit Stationen, gültigen QSOs und Sprachzeit aktualisiert
- keine Messdaten werden verworfen oder neu berechnet

# Änderungsprotokoll

## 0.1.9.3

- Referenz-Engine mit SQLite-Persistenz eingeführt.
- Bestehende 0.1.9.2-Benchmarkfälle werden automatisch aus `current.json` migriert.
- Mehrere QSOs eines Rufzeichens werden zu einer robusten Stationsreferenz aggregiert.
- Neue direkt einstellungsrelevante Kennzahlen: aktive Sprachlautheit, Bass, Sprachmitten, Präsenz, Höhen, Sprechpausen und Pegelstabilität.
- Referenzreife, gültige Sprachzeit, QSO-Anzahl und Qualitätsindex werden live angezeigt.
- Rohfälle liegen in `data/audio_benchmarks/benchmark.db`; `reference.json` enthält die aktuelle TG-Referenz.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.1.9.3

- Audio-Benchmark bleibt jetzt über die gesamte Laufzeit des Hauptfensters dieselbe Service-Instanz.
- Das Aktualisieren von Favoriten ersetzt den Benchmark-Service nicht mehr.
- RX-Ereignisse, PCM-Daten und Benchmark-Anzeige verwenden dadurch wieder denselben Datenstrom.
- Regressionstest gegen eine erneute Trennung von Widget und RX-Service ergänzt.


## 0.1.9.3

- Audio-Benchmark erkennt wiederholte Voice-Aktivitätsmeldungen desselben Streams korrekt und zerlegt einen Sprechdurchgang nicht mehr in Einzelpakete.
- Aktuelle Station, laufende Sprechdauer und Analysewarteschlange werden live angezeigt.
- Fremde oder verspätete Stream-Ende-Ereignisse können den aktiven Testfall nicht mehr beenden.

# 0.1.9.1.2 – RX-Initialisierung für den ersten Parrot-Test

- RX-Ausgabe, Decoder, Jitterpuffer und Audio-Queue werden vor dem ersten TX vollständig initialisiert.
- Vor jeder Parrot-Rückantwort wird der RX-Streamzustand deterministisch zurückgesetzt.
- Der erste gültige Voice-Burst kann einen Stream auch ohne vorher verwertbaren LC-Header eröffnen.
- Neue Timeline-Marken dokumentieren RX-Initialisierung, RX-Bereitschaft und Streamstart.
- Regressionstests sichern den ersten Parrot-Empfang nach Programmstart ab.

# 0.1.9.1.1 – Parrot-Vorbereitung auf TS2 korrigiert

- „Parrot vorbereiten“ setzt nun TG 9990, TS2 und Privatruf.
- Der Audio-Assistent verwendet dieselbe zentrale Parrot-Vorbereitung.
- Regressionstest verhindert eine erneute Umstellung auf TS1.

# 0.1.9.1.1 – DMR Audio-Tuner V1

- Ausklappbarer Live-Audio-Tuner direkt auf der Betriebsseite.
- Profile Neutral, Klar, DX, Warm und Eigene.
- Regler für Tiefen, Sprachmitten, Präsenz, Höhen, Dynamik, Limiter und PTT-Vorlauf.
- Leichte zustandsbehaftete Vierband-Verarbeitung ohne FFT oder Dateizugriffe im Echtzeitpfad.
- Einstellungen werden dauerhaft gespeichert und wirken ab dem nächsten TX.
- „Parrot vorbereiten“ übernimmt TG 9990, TS1 und Privatruf.
- „Audio-Assistent“ startet den passiven geführten Audio-Test und bereitet Parrot vor.
- Neutral bleibt die unveränderte Referenz für A/B-Vergleiche.

# 0.1.9.1.1 – Audioqualität

- Dezente, zustandsbehaftete DMR-Sprachaufbereitung im Live-TX-Pfad.
- 100-Hz-Hochpass gegen Gleichanteile und tieffrequentes Rumpeln.
- Transparenter Soft-Limiter nur für einzelne Spitzen; keine automatische Lautheitsnormalisierung.
- Neue abschaltbare Einstellung „DMR-Sprachaufbereitung (empfohlen)“.
- Geführte Audiotests speichern wieder die Messpunkte vor und nach der Sprachaufbereitung.
- Diagnoseerfassung wurde im normalen Funkbetrieb weiter reduziert.

## 0.1.8.8 – Passiver Audio-Analyzer

- Der geführte Audio-Test aktiviert die allgemeine Audio-Dauerdiagnose nicht mehr.
- Analyzer und Aufzeichnung greifen nicht mehr in RX-/TX-Zustände, Socket-Lebenszyklus oder Audioausgabe ein.
- Der normale Parrot- und Funkablauf bleibt alleiniger Eigentümer der TX→RX-Umschaltung.
- Der Sitzungszustand wird erst nach Abschluss des normalen Übertragungsaufrufs bereinigt.
- Persönliche Audio-Diagnoseeinstellungen bleiben durch den geführten Test unverändert.

## 0.1.8.7 – Geführte Audio-Test-Sitzung V3

- Geführter Audio-Test verwendet exakt einen gemeinsamen `AudioTest_...`-Ordner.
- TX-, Codec-Loopback-, Parrot-RX-, Timeline- und Analyse-Dateien werden derselben Sitzung zugeordnet.
- Der flüchtige Audio-Testzustand wird erst nach Abschluss des Netzwerk-/Parrot-Pfads beendet.
- Doppelte `TX_...`-Ordner während eines geführten Tests werden verhindert.

## 0.1.8.5 – Codec-Loopback korrigiert

- Codec-Loopback verwendet jetzt das tatsächliche `PcmFrame.corrected_errors`-Feld.
- Die Exception pro AMBE-Frame (`PcmFrame` besitzt kein Attribut `errors`) ist beseitigt.
- Timeline wird nicht mehr mit hunderten falschen Loopback-Fehlern geflutet.
- Loopback-WAV und Fehlerstatistik sind wieder belastbar.
- Der normale TX-/BrandMeister-Pfad bleibt unverändert.
- Nächster Praxistest entscheidet, ob der auffällige TX-Jitter durch die Exception-Last verursacht wurde.

## 0.1.8.5 – Stabiler WAV-Datei-Lebenszyklus

- WAV-Zieldateien werden zuerst als rohe Binärdateien geöffnet und erst danach an `wave` übergeben.
- Schlägt das Öffnen durch OneDrive, Zugriffsrechte oder einen ungültigen Pfad fehl, entsteht kein halb initialisiertes `Wave_write`-Objekt mehr.
- Alle produktiven TX-, RX-, Parrot- und Codec-Loopback-WAV-Schreibpfade verwenden dieselbe zentrale Hilfsfunktion.
- Ressourcen werden auch bei Fehlern deterministisch geschlossen.
- Regressionstest für den bisherigen `Wave_write.__del__`-Fehler ergänzt.

## 0.1.8.4 – Codec-Diagnose und TX-Timing

- leere `timeline.json` behoben; Ereignisse werden unabhängig vom optionalen globalen Timing-Log in die Audio-Test-Sitzung geschrieben
- präzise Marker für erstes PCM-Frame, erstes AMBE-Codewort und erstes gesendetes DMRD-Paket
- Codec-Loopback unterscheidet jetzt korrigierte Decoder-Bits von echten Decode-Ausnahmen
- bisher irreführender `codec_loopback_errors`-Wert entfernt
- Diagnose protokolliert Loopback-Frames, korrigierte Bits, Ausnahmen und Samplezahl getrennt
- Funk- und Audio-Sendepfad unverändert

## 0.1.8.4 – Codec-Loopback Hotfix

- Absturz beim Start des Sendens im Audio-Pipeline-Analyzer behoben.
- Ursache: `loopback_errors` wurde in der lokalen Funktion `drain()` verändert, aber nicht als `nonlocal` deklariert.
- Codec-Loopback, normaler TX und Parrot-Test können wieder starten.


## 0.1.8.4 – Audio Pipeline Analyzer

- Codec-Loopback ergänzt: jedes gesendete AMBE-Codewort wird lokal sofort wieder dekodiert.
- Neue Datei `04_codec_loopback_8k.wav` im geführten Audio-Test.
- Zeitachse `timeline.json` mit PTT-, PCM-, Encoder-, Netzwerk- und RX-Ereignissen.
- Abschlussanalyse wird nach TX/Parrot-RX erneut erzeugt und enthält Loopback- und Decoderfehler.
- Bestehender Funkpfad und gesendete AMBE-Daten bleiben unverändert.
## 0.1.8.2 – Geführte Audio-Test-Sitzung V2

- Ein geführter Test erzeugt erst beim tatsächlichen TX einen gemeinsamen Ordner `AudioTest_<Zeitstempel>`.
- TX- und anschließende RX-Messpunkte werden derselben Sitzung zugeordnet.
- Der RX-Pfad legt beim bloßen Verbinden keine leeren Ordner mehr an.
- WAV-Dateien werden nur bei tatsächlich vorhandenen Samples erzeugt.
- Der Testmodus wird nicht dauerhaft in `audio_send.local.json` gespeichert und kann nach einem Neustart keine unbeabsichtigte RX-Aufzeichnung aktivieren.
- Der Mikrofon-Ringpuffer bleibt bis PTT ausschließlich im RAM.
- Ressourcen werden bei Abbruch und Programmende kontrolliert beendet; halb initialisierte WAV-Schreiber werden vermieden.

# 0.1.8.0 – Audio-Labor und Qualitätsdiagnose

- TX-Messpunkte: Mikrofon roh, nach Mic-Gain, vor AMBE und AMBE-Rohframes.
- RX-Messpunkte: nach AMBE-Decoder und nach RX-Gain/AGC direkt vor Lautsprecher.
- Kennzahlen: Peak/RMS dBFS, Crest-Faktor, Clipping, DC-Offset, Nulldurchgänge, dominante Frequenz, Spektralzentrum und Bandenergie.
- Analyse als JSON und HTML; Wellenform, Spektrum und Spektrogramm bei installiertem Matplotlib.
- Getrennte Sitzungsordner unter logs/audio_lab.

# CarenDMR 0.1.8.0 – Talkgroup-Metadaten und Favoritenbedienung

- Im Dialog **DMR-Kanal bearbeiten** kann der Favoritenstatus direkt gesetzt oder entfernt werden.
- Schaltflächen sind deutsch beschriftet und kompakter dimensioniert.
- Im Reiter **Talkgroups** gibt es getrennte Aktionen **Favorit setzen** und **Favorit entfernen**.
- Land und wahrscheinliche Betriebssprache werden aus Talkgroup-Nummer und Name abgeleitet.
- Neue Spalten **Land** und **Sprache** sowie Filter nach Land und Sprache.
- Textsuche berücksichtigt zusätzlich Land und Sprache.
- Die Sprachangabe ist ausdrücklich eine abgeleitete, wahrscheinliche Betriebssprache; persönliche Favoritendaten bleiben unverändert.

# CarenDMR 0.1.7.4.2 – Weltweites Talkgroup-Verzeichnis

- Reiter **Favoriten** heißt jetzt **Talkgroups** und zeigt die vollständige gemeinsame Kanalliste.
- Favoriten sind Sterne innerhalb dieser Gesamtliste, keine separate Datenquelle.
- Weltweite BrandMeister-Talkgroups sind im lokalen Offline-Cache enthalten.
- **BrandMeister aktualisieren** lädt `https://api.brandmeister.network/v2/talkgroup`.
- Persönliche Namen, Notizen, TS, Rufart und Reihenfolge bleiben lokal erhalten.
- Die Betriebssuche und der Reiter Talkgroups verwenden exakt dieselbe Datenbasis.

# CarenDMR 0.1.7.4.2 – Einheitliche DMR-Kanalquelle

- Talkgroup-Suche und Favoriten verwenden nun dieselbe zusammengeführte Kanalliste.
- Favoriten sind Metadaten eines DMR-Kanals statt einer getrennten Auswahlwelt.
- Persönlicher Name, Notiz und Reihenfolge bleiben in `favorites.local.json` erhalten.
- Favoriten werden in der Talkgroup-Suche mit Stern gekennzeichnet und zuerst gezeigt.
- Private Favoriten ohne Eintrag im Basisverzeichnis sind ebenfalls suchbar.
- Die separate Favoriten-Combobox auf der Betriebsseite wurde entfernt.
- Der kleine Stern steht direkt links vor dem Talkgroup-Suchfeld.
- Favoriten-Reiter, Drag-and-drop, Tastatursortierung sowie Import/Export bleiben erhalten.

# CarenDMR 0.1.7.4.2 – DMR-Kanal-Favoriten

- Favoriten-Combobox und Stern direkt im Bereich „DMR-Kanal“.
- Der aktuelle Kanal kann mit vorbelegtem Standardnamen als Favorit gespeichert und persönlich umbenannt werden.
- Mehrzeilige Notiz für Runden, Rundsprüche und andere Hinweise.
- Neuer Hauptreiter „Favoriten“ mit kompakter Tabelle: eigener Name, Standardname, TG/DMR-ID, TS, R und Notizvorschau.
- Reihenfolge per Drag-and-drop sowie Alt+Pfeil hoch/runter; oberste Favoriten stehen in der Combobox zuerst.
- Enter oder Doppelklick übernimmt einen Favoriten auf die Betriebsseite und setzt den Fokus auf „Verbinden“; keine automatische Verbindung.
- Import und Export in CarenDMR-JSON und CSV; Dubletten werden über Ziel, Timeslot und Rufart verhindert.
- Persönliche Namen und Notizen bleiben getrennt vom offiziellen Talkgroup-Verzeichnis.
- Persistenz in `config/favorites.local.json`.

# CarenDMR 0.1.7.3.8 – Gespeicherten Talkgroup-Namen wiederherstellen

- Beim Programmstart wird der Name der zuletzt gespeicherten bekannten Talkgroup erneut aus dem lokalen Verzeichnis aufgelöst.
- TG, Timeslot, Rufart und Name werden über den zentralen DMR-Kanalpfad gemeinsam wiederhergestellt.
- Unbekannte TGs und private DMR-IDs bleiben ohne erfundenen Namen.
- Regressionstest sichert den Neustart mit bekanntem Talkgroup-Namen ab.

# CarenDMR 0.1.7.3.8 – Zentrale DMR-Kanalübernahme

- Talkgroup-Name bleibt nach Enter-Übernahme aus der Suchliste sichtbar.
- Suchtextänderungen verändern den Namen der bereits übernommenen aktuellen TG nicht mehr.
- TG, Name, Timeslot und Rufart werden zentral über einen gemeinsamen Kanalpfad aktualisiert.
- Manuelle TG-Eingabe und Auswahl aus der Trefferliste verwenden denselben Aktualisierungsweg.
- Laufende Statusaktualisierungen lösen den bekannten Talkgroup-Namen erneut auf.
- Regressionstests sichern den Fehler dauerhaft ab.

# CarenDMR 0.1.7.3.6 – Talkgroup-Name bei aktueller TG

- Der bekannte Name des aktuell gewählten DMR-Kanals steht jetzt direkt unter „Aktuelle TG“.
- Die bisherige Namenszeile unter dem Suchfeld wurde entfernt.
- Aktualisierung funktioniert bei manueller TG-Eingabe und bei Auswahl aus der Trefferliste.
- Bei unbekannter TG bleibt die Namenszeile leer.
- Funklogik, Suche, Enter-Verhalten und Pflicht-Hotkeys bleiben unverändert.

# CarenDMR 0.1.7.3.4 – Enter-Shortcut-Konflikt behoben

- Globale Return-/Enter-Shortcuts im Hauptfenster entfernt.
- Enter erreicht dadurch wieder die lokale Talkgroup-Suche und übernimmt den markierten Treffer.
- Die bestehende lokale Behandlung für Pfeiltasten, Escape und Enter bleibt unverändert.
- Buttons verwenden ihr natives Qt-Tastaturverhalten; Pflicht-Hotkeys F5, F6, F7 und Space bleiben unverändert.
- Regressionstest verhindert eine erneute globale Bindung von Return/Enter.

# CarenDMR 0.1.7.3.4 – Talkgroup-Suche Enter-Übernahme zuverlässig


- Enter wird bereits auf der allgemeinen Qt-Event-Ebene abgefangen und übernimmt den markierten Treffer zuverlässig.
- Die markierte Trefferzeile wird unabhängig vom Fokuszustand des Popups intern nachgeführt.
- Enter übernimmt den markierten Treffer jetzt zuverlässig über die interne Trefferliste.
- Pfeil nach unten öffnet eine mit Escape geschlossene Trefferliste erneut, sofern Suchtext vorhanden ist.
- Escape behält Suchtext und Eingabefokus unverändert.
- Trefferliste zeigt nur noch zwei ruhige Spalten: Name und TG/DMR-ID.
- Timeslot und Rufart bleiben Bestandteil des Kanals, werden in der Suchübersicht aber nicht mehr angezeigt.
- Das Suchfeld behält beim Öffnen der Trefferliste den Tastaturfokus.
- Weitere Ziffern und Buchstaben grenzen die Treffer fortlaufend ein.
- Pfeil hoch/runter markiert Treffer, Enter übernimmt den Kanal zuverlässig.
- Escape schließt die Liste, erhält den Suchtext und lässt den Fokus im Talkgroup-Feld.
- Keine automatische Verbindung; F5 bleibt der bewusste Verbindungsbefehl.

# CarenDMR 0.1.7.2 – DMR-Kanal V1

- Bereich „Funkziel“ auf der Betriebsseite in „DMR-Kanal“ umbenannt.
- Eingabefeld fachlich einheitlich als „Talkgroup“ bezeichnet.
- Neues zentrales Domain-Modell `DmrChannel` für Ziel, Timeslot und Rufart.
- Modell ist bereits für Namen, Land und Beschreibung des späteren TG-Verzeichnisses vorbereitet.
- Keine Änderung an Funklogik, Hotkeys, Fokusfolge oder Verbindungsvorgang.

# CarenDMR 0.1.7.1 – Betriebsanzeigen V1

- Nicht klickbare LED-/Displayanzeige für Getrennt, Verbindet, Empfang, Senden und Fehler.
- Sichtbares MIC-/TX-Pegelmeter mit Peak-Hold.
- Sichtbares RX-Pegelmeter mit Peak-Hold.
- Beide Pegelanzeigen sind nicht fokussierbar und erzeugen keine eigenen Screenreader-Ausgaben.
- Der AMBE-Bereitschaftstext wurde von der Betriebsseite entfernt; Codec-Prüfung bleibt unter Einstellungen → Codec / Decoder.
- Hotkeys, Tab-Reihenfolge, PTT-Vorlauf, AudioCue und Funklogik bleiben unverändert.

# CarenDMR 0.1.6.8 – TS/RA Keyboard Workflow Final

- Timeslot und Rufart bleiben sichtbar und per Maus bedienbar.
- Beide Statusgruppen sind aus der Tab-Reihenfolge entfernt.
- Tastaturbedienung erfolgt ausschließlich über die konfigurierten Hotkeys.
- Hotkey-Hinweise werden dynamisch aus dem Eingabemanager angezeigt.
- F6/F7 beziehungsweise die individuell belegten Tasten erzeugen genau eine kurze Fachansage.
- Verbinden, PTT, Timeslot und Rufart sind Pflicht-Hotkeys und können nicht gelöscht werden.

# CarenDMR 0.1.6.7 – AudioCue Initialisierungsfix

- Startabsturz behoben: `AudioCuePlayer` verwendet den bereits initialisierten `AudioSendService`.
- Keine Installationsänderung erforderlich.
- Radio Controls, Accessibility und Funklogik unverändert.

---

# CarenDMR 0.1.6.6 – Field-Test Audio & Accessibility Final

- Programmstart setzt den Fokus direkt auf „Neue Talkgroup“.
- Timeslot und Rufart haben kurze Accessibility-Namen ohne zusätzliche Hilfetexte.
- F6/F7 erzeugen keine zweite parallele Manager-Ansage mehr.
- PTT-Vorlauf wird explizit aus der Einstellung verwendet und hängt nicht mehr von der unzuverlässigen Qt-Erkennung des Screenreaders ab.
- Ein eigener lokaler heller Start-Beep erklingt vollständig vor dem tatsächlichen TX.
- Nach sicher beendetem TX erklingen zwei kurze lokale End-Beeps.
- Quittungstöne werden über das gewählte Wiedergabegerät abgespielt und gelangen nicht in den Mikrofon-/Sendepfad.

# CarenDMR 0.1.6.6 – Accessibility Field-Test Polish


## Accessibility Field-Test Polish

- Timeslot und Rufart geben beim Tabben den aktuellen Wert in der zugänglichen Beschreibung aus.
- Verbinden/Trennen besitzt in jedem Zustand einen eindeutigen zugänglichen Namen.
- Eigener heller Doppelton (1200/1600 Hz) direkt vor dem tatsächlichen TX-Start.
- Übergeordnete Betriebsseite liefert keine unnötige Gruppenansage mehr.
- Funklogik, Layout und Hotkeys unverändert.

## Korrektur

- Der getrennte Initialzustand mit der historischen Default-TG 91 überschreibt nicht mehr die aus `config/operating.local.json` geladene letzte Talkgroup.
- TG, Timeslot und Rufart erscheinen nach einem Neustart wieder exakt wie vor dem Beenden.


- Letzte Talkgroup, Timeslot und Rufart werden dauerhaft gespeichert und beim Start geladen.
- F6/F7 sowie Mausklicks speichern TS und Rufart unmittelbar.
- TS1/TS2 und Gruppe/Privat besitzen feste Breiten; das Layout verschiebt sich beim Umschalten nicht.
- Der Sendebutton heißt durchgehend TX: grün sendebereit, rot während tatsächlichem TX.
- Der Sekundenzähler läuft nur während tatsächlichem TX, stoppt sofort und wird danach geleert.

- TS und Rufart als kleine, optisch zurückhaltende TG-Flags
- Maus wählt direkt; Tastatur schaltet weiterhin ausschließlich mit F6/F7
- Tab erreicht jeweils den aktiven TS- und Rufart-Status
- TX-Zähler stoppt und verschwindet sofort beim Wechsel zurück zu RX
- TX/RX-Schaltfläche bleibt positionsstabil
- eigener lokaler 880-Hz-Funkton statt Windows-Systemton
- tatsächlicher TX startet erst nach vollständig abgespieltem Startton

# CarenDMR 0.1.6.1 – Radio Controls Polish

- TS1/TS2 und Gruppe/Privat sind jetzt normale, nicht checkbare Segment-Schaltflächen. Dadurch meldet der Screenreader keine Checkbox-/Kontrollkästchen-Rolle mehr.
- CarenDMR verwaltet die Auswahl intern und kennzeichnet den aktiven Segment-Schalter nur optisch sowie mit einem kurzen fachlichen AccessibleName.
- Tab-Reihenfolge korrigiert: Neue TG → aktiver Timeslot → aktive Rufart → Verbinden.
- Segment-Schaltflächen kleiner und dezenter gestaltet, damit sie die Betriebsseite nicht dominieren.
- Der TX-Sekundenzähler reserviert dauerhaft seinen Platz. Der TX/RX-Button bewegt sich beim Ein- und Ausblenden der Zahl nicht mehr.
- Der Zähler enthält nur während tatsächlichem TX eine Zahl, beginnt bei jeder Aussendung wieder bei 0 und bleibt für Screenreader stumm.
- Bei aktivem nativen Accessibility-System ertönt nach dem eingestellten PTT-Vorlauf ein kurzer lokaler Signalton. Erst 150 ms danach werden Mikrofon und DMR-TX gestartet; der Ton gelangt nicht in den Sendepfad.
- Funkkern, F5/F6/F7, Space, Audio, QSO-Historie und bestehende Konfiguration bleiben unverändert.

# CarenDMR 0.1.5.0 – Radio Workflow

- PTT-Bedienung auf kurze Funkbegriffe umgestellt: `TX` im Empfang und `RX` während einer laufenden Sendung.
- Bei aktivem nativen Accessibility-System wartet CarenDMR 1,2 Sekunden, bevor Mikrofon und DMR-TX tatsächlich starten. Dadurch kann Narrator/VoiceOver die kurze `RX`-Ansage beenden, bevor die Aussendung beginnt.
- Sichtbarer TX-Sekundenzähler zählt 0, 1, 2, 3 … hoch.
- Der Sekundenzähler ist nicht fokussierbar und besitzt keinen zugänglichen Namen; er wird nicht vorgelesen.
- Timeslot und Rufart verwenden auch sichtbar die vollständigen Bezeichnungen `Timeslot 1/2`, `Gruppenruf` und `Privatruf`, damit Screenreader den fachlichen Namen sicher erhalten.
- Zweiter Druck während des Screenreader-Vorlaufs bricht den noch nicht gestarteten TX sauber ab.
- Funkkern, Verbindung, Hotkeys, Tab-Reihenfolge, Einstellungen und QSO-Historie bleiben unverändert.

# CarenDMR 0.1.3.5 – Funkorientierte Accessibility

- Eigene Ansagen während der TG-Eingabe vollständig entfernt.
- Keine zusätzlichen Accessibility-Ereignisse mehr für einzelne Ziffern oder Backspace.
- Narrator/NVDA/JAWS/VoiceOver übernehmen das native Zeichen-Echo allein.
- Beim Verbinden wird der tatsächlich im Feld stehende Wert genau einmal ziffernweise als neue Talkgroup bestätigt.
- Funklogik, Layout, Hotkeys und Tab-Reihenfolge unverändert.

# CarenDMR 0.1.3.2 – Accessibility-Ereigniskette bereinigt

- Verbindungsbutton bleibt während Aufbau/Trennung fokussierbar; kein Zwischenfokus auf Mic-Gain.
- Keine gesprochenen Übergangsmeldungen für CONNECTING/DISCONNECTING.
- Nach F5: Fokus auf PTT, danach genau eine kurze Meldung „Verbunden“.
- Startkontext-Timer wird beim Verbindungsaufbau gestoppt, damit keine verspätete Vollansage dazwischenfunkt.
- Wiederholte State-Updates erzeugen keine zusätzlichen Ansagen.

# CarenDMR 0.1.3.1.1 – Accessibility Workflow Fix

- Native Qt-Ankündigungen über QAccessibleAnnouncementEvent.
- Nach erfolgreichem F5-Verbinden springt der Fokus auf PTT.
- Nach Trennen bleibt der Fokusablauf Neue Talkgroup erhalten.
- Kurze Accessibility-Namen für Mic-Gain und RX-Lautstärke ohne doppelte Beschreibung.

- Mic-Gain und RX-Lautstärke besitzen eindeutige native Accessibility-Namen und Prozentwerte.
- Beim Programmstart und beim Wechsel auf Betrieb wird der aktuelle Funkkontext kompakt bereitgestellt.
- Verbinden, Trennen, Senden und Rückkehr zum Empfang melden kurze native Zustandsänderungen.
- QSO-Historienzellen liefern zusätzlich zum Zellinhalt die jeweilige Spaltenüberschrift.
- Keine eigene Desktop-TTS; Narrator, NVDA, JAWS und VoiceOver bleiben für die Sprachausgabe zuständig.
- Keine Änderung an Funklogik, Hotkeys, Tab-Reihenfolge oder sichtbarem Layout.

# CarenDMR 0.1.2.1 – Design-System-Fix

- Initialisierungsfehler im Hotkey-Reiter beim Öffnen der Einstellungen behoben.
- Native Fokusrechtecke direkt um Reitertexte entfernt; gelber Fokus bleibt um das vollständige Bedienelement.
- Statusanzeige und Verbindungsbutton semantisch getrennt: Status flacher, Aktion höher, beide bündig und gleich breit.
- Keine Änderung an Funklogik, Hotkeys, Tab-Reihenfolge oder QSO-Historie.

# CarenDMR 0.1.1 – Theme Engine & Accessibility

- Alle Qt-Farben und Grundstile zentral in `carendmr/ui_qt/theme.py`.
- Dark Theme anwendungsweit auf Hauptfenster, Historie, Einstellungen und Dialoge angewendet.
- Schwarz-auf-Schwarz-Darstellung beseitigt.
- Kontrast für Text, Tabellen, Formulare, Gruppenfelder und deaktivierte Zustände erhöht.
- Gelber, deutlich sichtbarer Fokusrahmen für Tastaturbedienung.
- Bestehendes Layout, Tab-Reihenfolge, Hotkeys und Fachlogik unverändert.

# CarenDMR 0.0.28.3 – Qt-Einstellungen Bedienkorrekturen

- Betriebsseite wieder für normale Fenstergröße verdichtet.
- Mic-Gain und RX-Lautstärke stehen kompakt nebeneinander; Stumm und AGC bleiben direkt erreichbar.
- RX-Lautstärke auf der Betriebsseite auf 0 bis 100 Prozent begrenzt. Erweiterte Verstärkung bis 400 Prozent bleibt im Audio-Reiter als Zusatzverstärkung verfügbar.
- RadioID-Aktualisierungsstatus wird unmittelbar in der RadioID-Kachel angezeigt.
- Vocoder-Plugins ohne klassische Dateiendung werden angezeigt und im Pluginordner automatisch erkannt.
- Keine Änderungen an Funkbetrieb, QSO-Historie oder Bedienlogik.

# CarenDMR 0.0.28.1

- Rekursion in der Tab-Behandlung der QSO-Historie behoben.
- Tab verlässt die Tabelle jetzt über feste Fokusziele; Shift+Tab kehrt stabil zurück.
- QSO-Status der aktuellen Station auf der Betriebsseite ergänzt.
- Änderungen an „Gesprochen“ werden sofort zwischen Historie und Betrieb synchronisiert.

# CarenDMR 0.0.28.0

- QSO-Historie als zweiter Qt-Hauptreiter portiert.
- Vorhandene SQLite-Daten werden unverändert genutzt.
- Suche, Stationsübersicht, Detailansicht und QSO-Bestätigung ergänzt.
- Tabellenbedienung mit Pfeiltasten sowie sauberem Tab-Ausstieg.
- F8 Betrieb, F9 Historie und F11 QSO bestätigen angebunden.
- Funkbetrieb und Einstellungen unverändert.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.0.27.3 – Einstellungen abgeschlossen

- Sicherheitsabfrage vor dem Vormerken der Hotkey-Werkseinstellungen.
- Werkseinstellungen werden weiterhin erst mit Übernehmen oder OK dauerhaft gespeichert.
- Abbrechen verwirft vorgemerkte Änderungen.
- Hotkey-Tabelle verhält sich als Auswahlliste: Zeilenwechsel mit Pfeiltasten.
- Tab verlässt die Tabelle und setzt die normale Dialognavigation fort.
- Keine Änderungen am Funkbetrieb oder an der bestehenden Bedienlogik.

## 0.0.27.2 – Eingabemanager V1

- Freie Hotkey-Textfelder entfernt.
- Tastenkombinationen werden über echte Qt-Tastaturereignisse erfasst.
- Übersicht mit Funktion und aktueller Zuordnung ergänzt.
- Freie, belegte und gesperrte Kombinationen werden unmittelbar angezeigt.
- Bereits belegte Kombinationen können nach Rückfrage neu zugeordnet werden.
- Die bisherige Funktion bleibt danach ohne Zuordnung.
- Einzelne Zuordnungen können entfernt werden.
- Nicht zugeordnete Funktionen werden dauerhaft gespeichert.
- Werkseinstellungen können vorgemerkt und mit Übernehmen oder OK gespeichert werden.
- Änderungen werden ohne Programmneustart aktiv.
- Funkbetrieb und Betriebsinformationen aus 0.0.27.1 bleiben unverändert.

## 0.0.27.2 – Qt-Einstellungen, Stufe 1

- Separates Qt-Einstellungsfenster über Programm > Einstellungen oder Strg+,
- Mikrofon und Wiedergabegerät auswählen und neu einlesen.
- Mic-Gain und Empfangslautstärke einstellen.
- Empfang stummschalten und AGC schalten.
- Diagnosemodus und Audio-Diagnose-WAV schalten.
- Änderungen mit Übernehmen oder OK speichern; Abbrechen verwirft sie.
- Stabiler Qt-Betrieb aus 0.0.26.5 bleibt unverändert.

- Radiobutton-Gruppen werden bereits beim Programmstart korrekt in den Tabpfad eingebunden.
- Tab landet bei Timeslot und Rufart sofort auf dem aktuell ausgewählten Radiobutton.
- Nach jeder Umschaltung folgt der Tabfokus weiterhin dem ausgewählten Wert.
- Keine weiteren Funktions- oder Layoutänderungen.

# CarenDMR 0.0.26.4 – Qt-Betrieb Stable Baseline

- Enter aktiviert den aktuell fokussierten Button.
- Leertaste aktiviert einen fokussierten Button statt global PTT auszulösen.
- Außerhalb eines fokussierten Buttons bleibt Leertaste der PTT-Toggle.
- Enter-Sonderbehandlung im TG-Eingabefeld entfernt.
- Keine weiteren Funktions- oder Layoutänderungen.

# CarenDMR 0.0.26.3 – F5-Verbindung und Talkgroup-Übernahme

- F5 toggelt Verbinden und Trennen.
- Beim Verbinden wird eine eingetragene neue Talkgroup zuerst übernommen.
- Nach dem Trennen springt der Fokus in „Neue Talkgroup“.
- Enter übernimmt die neue Talkgroup und fokussiert „Verbinden“.
- Timeslot 1 und 2 sind echte Radiobuttons; F6 schaltet sichtbar um.

# CarenDMR 0.0.26.3 – Qt-Betrieb: Hotkeys und Zustände

- F5 setzt den Fokus in das Feld **Neue Talkgroup**.
- Zwei-Felder-Bedienung: aktuelle TG als Anzeige, neue TG als leeres Eingabefeld.
- Enter übernimmt die neue TG und setzt den Fokus auf **Verbinden**.
- F6 schaltet Timeslot 1/2 sichtbar um.
- F7 schaltet Gruppenruf/Privatruf sichtbar um.
- Nach TX setzt ein aktiver RX-Zustand Statusleiste und TX-Anzeige auf **Empfang aktiv** zurück.

---

# CarenDMR 0.0.26.0 – Qt-Migration, Stufe 1: funktionaler Betrieb

- Neuaufbau auf Basis der stabilen 0.0.25.2.
- Funktionaler Qt-Betrieb statt Accessibility-Mock.
- Echte BrandMeister-, RX-, Audio-, AMBE- und PTT-Anbindung.
- Desktop-PTT als Toggle per Schaltfläche oder Leertaste.
- Tkinter bleibt mit `--gui-tk` als Rückfallebene erhalten.
- Keine eigene TTS und keine Screenreader-Sonderlogik in dieser Stufe.
- 279 Tests und 20 Untertests bestanden.

# 0.0.25.2

- TTS- und Fokus-Engine V2 mit dauerhaftem Windows-SAPI-Prozess.
- Fokusmeldungen werden als vollständige atomare Sätze ausgegeben.
- Schnelle Fokuswechsel werden auf die zuletzt erreichte Position reduziert.
- Geschlossener Tab-Kreis im Betrieb: Neue TG → Timeslot → Rufart → Connect → Neue TG.
- Keine Änderungen an DMR-, Audio-, Verbindungs- oder State-Machine-Kern.

# 0.0.25.1.2

- Talkgroup-Bedienung stabilisiert: aktuelle TG als Anzeige, separates leeres Feld „Neue TG“.
- Neue TG wird nur bei Eingabe übernommen; leer verwendet weiterhin die aktuelle TG.
- Fokusansagen für Timeslot und Rufart werden als vollständige, atomare Meldungen ausgegeben.
- Tab-Reihenfolge, Enter-Connect und verzögerte RX-Freigabe bleiben unverändert.


- Talkgroup wird beim Fokus vollständig markiert.
- Fokusansagen für Timeslot und Rufart werden als vollständige Meldungen ausgegeben.
- CONNECT ist per Enter und Ziffernblock-Enter auslösbar.
- Keine weiteren Workflow- oder DMR-Änderungen.

# 0.0.25.1

- Workflow V1 für Trennen, Einstellen und Verbinden.
- Talkgroup nach Disconnect vollständig markiert.
- Tab springt nur auf aktiven Timeslot und aktive Rufart.
- CONNECT folgt direkt nach Rufart.
- RX-Wiedergabe erst nach vollständiger Connect-Ansage.
- Disconnect-TTS wird vollständig beendet, bevor der Fokus auf Talkgroup gesetzt wird.
- TTS-Warteschlange wird bei Zustandswechseln bereinigt.

# 0.0.25.0

- Zentrales `carendmr/ui/design_system.py` eingeführt.
- Vier visuelle Elementklassen: Information, Eingabe, Auswahl und Aktion.
- Einheitliche semantische Farbpalette, Schriften, Abstände und Fokusrahmen.
- Talkgroup ist als helles Eingabefeld eindeutig erkennbar und im verbundenen Zustand sichtbar gesperrt.
- Timeslot und Rufart besitzen klar unterscheidbare aktive, inaktive und gesperrte Zustände.
- CONNECT/DISCONNECT und PTT nutzen einheitliche Aktionszustände mit Hover, Fokus und Deaktivierung.
- Statusflächen reagieren nicht wie Schaltflächen.
- TX-Kachel zeigt getrennt zusätzlich „Keine Verbindung“.
- Serveradresse wird nur bei tatsächlicher Verbindung angezeigt.
- Design-System-Regeln in `docs/DesignSystem.md` dokumentiert.

# 0.0.24.6.5

- Zentrale `RadioStateMachine` mit den Zuständen `DISCONNECTED`, `CONNECTING`, `CONNECTED`, `TRANSMITTING`, `DISCONNECTING` und `ERROR`.
- PTT-Freigabe, CONNECT/DISCONNECT und Editierbarkeit von TG, TS und Rufart werden nur noch aus diesem Zustand abgeleitet.
- Nach erfolgreichem Connect wird die TX-Taste zuverlässig freigegeben.
- TX-Start und TX-Ende synchronisieren denselben zentralen Betriebszustand.
- Technische RX-Zustände können die State Machine nach Thread-Ende oder Fehler wieder an die Realität angleichen.
- Regressionstests für erlaubte und verbotene Zustandswechsel ergänzt.

# 0.0.24.6.4

- TG-Wechsel-Schaltfläche aus dem Betriebsbereich entfernt.
- Talkgroup, Timeslot und Rufart sind nur im getrennten Zustand editierbar.
- Nach erfolgreichem Connect springt der Fokus auf PTT.
- Nach Disconnect ist PTT gesperrt und der Fokus springt auf Talkgroup.
- Interne BrandMeister-RX-Wiederanmeldungen nach TX bleiben sprachlich stumm.
- Talkgroups werden durch Caren Assist überall ziffernweise gesprochen.

# 0.0.24.6.3

- Fokusumrandung deutlich verstärkt.
- PTT global und unabhängig von Reiter/Fokus sicher beendet.
- TX-Taste nach Sendestart wieder bedienbar.
- Reiterwechsel und Programmende lösen sicheren TX-Abbruch aus.
- ConnectionManager bereinigt stale RX-Zustände vor Connect.
- Verbindungsfehler werden in GUI und Ereignislog abgefangen.
- Regressionstests für Fokus, PTT und stale RX ergänzt.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.0.27.3 – Einstellungen abgeschlossen

- Sicherheitsabfrage vor dem Vormerken der Hotkey-Werkseinstellungen.
- Werkseinstellungen werden weiterhin erst mit Übernehmen oder OK dauerhaft gespeichert.
- Abbrechen verwirft vorgemerkte Änderungen.
- Hotkey-Tabelle verhält sich als Auswahlliste: Zeilenwechsel mit Pfeiltasten.
- Tab verlässt die Tabelle und setzt die normale Dialognavigation fort.
- Keine Änderungen am Funkbetrieb oder an der bestehenden Bedienlogik.

## 0.0.24.6.1

- Lokaler 10-Sekunden-Mikrofontest ohne Funkübertragung.
- Live-Anzeige von TX-Pegel, Peak und Bewertung während der Mic-Gain-Kalibrierung.
- Talkgroup-Eingabe auf Ziffern begrenzt.
- Reiterwechsel beendet eine laufende PTT sicher.


## 0.0.24.5
Qualitätssprint für kurze Sprachmeldungen, vereinfachten F2-Ablauf und zuverlässige Connect-/Disconnect-Audiofolge.

- F2 öffnet Betrieb und fokussiert direkt die Talkgroup; der zusätzliche Assistentendialog entfällt.
- Fokusmeldungen wurden auf Feldname und Wert verkürzt.
- F3 verwirft ausstehende Fokusmeldungen und spricht ausschließlich den Betriebszustand.
- F5 hält RX bis zum Ende der vollständigen Verbindungsansage gesperrt.
- TG-/TS-/Rufart-Wechsel setzt die RX-Sperre vor Beginn des technischen Wechsels.
- Nach Disconnect wird erst nach beendetem RX-Abbau „Verbindung getrennt“ gesprochen.

Bedienungs- und Hotkey-Framework V1 mit geführtem Talkgroup-Wechsel, konfigurierbaren Bedienfunktionen, Fokusansagen und Kontext-Hilfe.

# 0.0.24.3.2 – Audio Manager V1

- Funk-Audio und Caren Assist werden erstmals koordiniert.
- Vor TX spricht Caren Assist kurz „Senden“; die Mikrofonaufnahme startet erst nach Ende der Ansage plus 150 ms Reserve.
- Nach TX spricht Caren Assist unmittelbar „Empfang“.
- Parrot-RX-Audio wird bis zum Ende der kurzen Empfangsansage gepuffert und anschließend vollständig wiedergegeben.
- Technische Zwischenmeldungen beim TG-Wechsel werden zu einer kompakten Betriebsansage zusammengefasst.
- Veraltete TTS-Warteschlangeneinträge werden vor TX/RX-Ansagen verworfen.
- DMR-, AMBE- und TX-Timingkern bleiben unverändert.

# 0.0.24.3.1 – Caren Assist V1 und letzter Betriebszustand

- Erste abschaltbare, lokale Sprachausgabe für wichtige Betriebszustände.
- TTS läuft über eine eigene Queue und blockiert weder GUI noch DMR-Kern.
- Letzte Talkgroup, Timeslot und Rufart werden sofort lokal gespeichert und beim Start wiederhergestellt.
- Sprachaktivierung wird ebenfalls lokal gespeichert.
- Strukturierte Meldungen für Verbindung, Empfang, TX und Fehler ergänzt.
- Keine Änderung am DMR-, AMBE- oder Audiokern.

## 0.0.24.3.1 – Caren Assist Framework V1

- Informationsereignisse um Bedienkontext und strukturierte Metadaten erweitert.
- Getrennte Kanäle für GUI, spätere Sprachführung und Diagnose-/Logausgabe.
- Ringpuffer-Historie mit letzter Meldung und letzten Ereignissen für spätere Wiederholfunktionen.
- Leichtgewichtige Laufzeitdiagnose für Gesamtverteilung, GUI, Sprache und Logging.
- Queue-Tiefe, Maximalwert und Warnschwellen bei 5, 20 und 50 Millisekunden.
- Betrieb, QSO-Historie und Einstellungen setzen ihren Bedienkontext automatisch.
- DMR-, Audio- und TX/RX-Kern unverändert.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.0.27.3 – Einstellungen abgeschlossen

- Sicherheitsabfrage vor dem Vormerken der Hotkey-Werkseinstellungen.
- Werkseinstellungen werden weiterhin erst mit Übernehmen oder OK dauerhaft gespeichert.
- Abbrechen verwirft vorgemerkte Änderungen.
- Hotkey-Tabelle verhält sich als Auswahlliste: Zeilenwechsel mit Pfeiltasten.
- Tab verlässt die Tabelle und setzt die normale Dialognavigation fort.
- Keine Änderungen am Funkbetrieb oder an der bestehenden Bedienlogik.

## 0.0.24.1 – Bedienungsframework V1

- Timeslot 1/2 als direkt erreichbare, vertikal angeordnete Auswahlschalter umgesetzt.
- Rufart Gruppe/Privat als direkt erreichbare, vertikal angeordnete Auswahlschalter umgesetzt.
- Aktive Auswahl wird nicht nur farblich, sondern zusätzlich mit Text und gedrücktem Zustand angezeigt.
- Pfeiltasten hoch/runter wechseln innerhalb der beiden Auswahlgruppen.
- Plattformneutrales Fokusmodell mit Steuerelement-ID, GUI-Name, Assist-Name und Rolle eingeführt.
- Änderungen an Timeslot und Rufart erzeugen strukturierte Betriebsereignisse für GUI und spätere Sprachausgabe.
- DMR-, Audio-, TX/RX- und Verbindungslogik unverändert.

## 0.0.24.0

- Zentralen Informationsmanager mit getrennten visuellen und sprachlichen Ausgabekanälen eingeführt.
- Strukturierte Meldungen besitzen Code, Kurztext, Langtext, Kategorie, Priorität und Handlungshinweis.
- Bestehendes Ereignisprotokoll bleibt kompatibel und nutzt intern den Informationsmanager.
- Bereichswechsel und Startbereitschaft liefern erstmals strukturierte Betriebsinformationen.
- Grundlage für Caren Assist und die spätere Raspberry-Pi-Sprachführung geschaffen.

## 0.0.23.9

- WAV-Audiodiagnose im Bereich Einstellungen > Diagnose schaltbar.
- Standardmäßig deaktiviert, um unnötige WAV-Dateien im Normalbetrieb zu vermeiden.
- Einstellung wird sofort lokal gespeichert.
- TX- und Parrot-RX-Diagnosedateien werden nur bei aktivierter Option erzeugt.

## 0.0.23.8 – Gefilterter TX-Sprachresampler

- Ersetzt die einfache Paarmittelung bei 16→8 kHz durch einen kontinuierlichen 63-Tap-FIR-Sprachtiefpass.
- Verhindert Aliasanteile oberhalb des AMBE-Sprachbands.
- PCM-Framebildung, AMBE-Encoder, DMR-Paketierung und TX/RX-Timing bleiben unverändert.
- TX- und Parrot-RX-Diagnose-WAVs bleiben aktiv.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.0.27.3 – Einstellungen abgeschlossen

- Sicherheitsabfrage vor dem Vormerken der Hotkey-Werkseinstellungen.
- Werkseinstellungen werden weiterhin erst mit Übernehmen oder OK dauerhaft gespeichert.
- Abbrechen verwirft vorgemerkte Änderungen.
- Hotkey-Tabelle verhält sich als Auswahlliste: Zeilenwechsel mit Pfeiltasten.
- Tab verlässt die Tabelle und setzt die normale Dialognavigation fort.
- Keine Änderungen am Funkbetrieb oder an der bestehenden Bedienlogik.

## 0.0.23.8 – Parrot-RX-Audiodiagnose

- Speichert das vom BrandMeister-Parrot empfangene und nach AMBE decodierte PCM als 8-kHz-WAV.
- Die Datei entsteht nur bei einem echten Parrot-Test auf 9990 / TS2 / Privat.
- Ablage unter `logs/audio_debug/` als `rx_..._03_parrot_nach_ambe_8k.wav`.
- Protokolliert den Dateipfad und die Sampleanzahl als `RX_AUDIO_DEBUG_WAV`.
- Keine Änderung an TX-Takt, Encoder, Audiopegel oder TX/RX-Umschaltung.

## 0.0.23.5 – Geglätteter TX-Sendetakt

- Windows-Timerauflösung während TX auf 1 ms angehoben.
- Hybrider Burst-Scheduler: grobes Warten per Sleep, präzise Endphase für den 60-ms-Takt.
- Ziel: gemessenen TX-Jitter von rund 9 ms deutlich reduzieren, ohne die schnelle TX/RX-Umschaltung zu verlieren.
- TX-Jitter-, Encoder- und Queue-Diagnose bleiben zur Erfolgskontrolle aktiv.

## 0.0.23.3 – Live-TX-Takt und schneller RX-Rückweg

- DMR-Sprachbursts werden nun anhand eines absoluten 60-ms-Zeitplans gesendet.
- Encoder-, Python- und Socket-Laufzeiten addieren sich nicht mehr auf jeden Burst.
- Ein wachsender Audio-Rückstand bei längeren Durchgängen wird dadurch vermieden.
- Die zusätzliche feste 250-ms-Audiowartezeit beim RX-Aufbau entfällt.
- Diagnoseprotokoll meldet Taktkorrekturen weiterhin in `logs/tx_rx_timing.log`.

## 0.0.23.1 – Echtes Live-TX-Streaming

- Mikrofon-Audio wird während gedrückter PTT fortlaufend in 8-kHz-PCM umgewandelt, AMBE-codiert und als DMR-Sprachbursts gesendet.
- Die während des schnellen RX-Abbaus aufgenommenen ersten Audioblöcke werden gepuffert und anschließend ohne Silbenverlust übertragen.
- Nach dem Loslassen folgen nur noch ein angefangener Sprachburst und der DMR-Terminator; die Wartezeit wächst nicht mehr mit der Sprechdauer.
- Parrot 9990/TS2 privat verwendet weiterhin dieselbe Verbindung zum Empfang und zur Wiedergabe des Echos.
- Normale Gruppen- und Privatrufe wechseln nach dem Streamabschluss sofort zurück auf RX.
- Millisekundenmessung bleibt zur Kontrolle des realen Live-TX-Verhaltens aktiv.

## 0.0.22.9 – TX/RX-Zeitmessung

- Persistente Millisekundenmessung für den vollständigen PTT-, TX- und RX-Rückkehrpfad ergänzt.
- Gemessen werden RX-Stopp, Mikrofonaufnahme, TX-Login, erster und letzter DMR-Frame, RX-Neustart, Audioöffnung, BrandMeister-Login und Zielaktivierung.
- Messergebnisse werden automatisch unter `logs/tx_rx_timing.log` gespeichert.
- Noch keine Änderung an Netzwerkwartezeiten oder am stabilen DMR-Kern.

## 0.0.22.8.1 – TX-Ziel korrekt übernommen

- TX verwendet jetzt die aktuell eingestellte Ziel-ID/Talkgroup, den Timeslot und die Rufart.
- Nur 9990 / TS2 / Privat wird als Parrot-Test behandelt und auf Echo überwacht.
- Normale Privat- und Gruppenrufe warten nicht mehr auf ein Parrot-Echo.
- RX-Rückkehr stellt Ziel, Timeslot und Rufart vollständig wieder her.

## 0.0.22.8 – TX-Start beschleunigt

- Mikrofonaufnahme startet unmittelbar beim Drücken der PTT.
- RX-Abbau und TX-Aufnahme laufen parallel; erste Wörter gehen während des Empfangsstopps nicht mehr verloren.
- Vor die Nutzsprache werden 240 ms DMR-Vorlauf gesetzt, damit Header und erster Sprachburst sicher aufgebaut sind.
- Nach TX wird die zuvor aktive Talkgroup-/Timeslot-Kombination weiterhin automatisch wiederhergestellt.
- QSO-Historie aus 0.0.22.7.1 bleibt unverändert.

## 0.0.22.6 – UI-Konsolidierung

- Moderne Betriebsseite aus 0.0.22.2 beibehalten.
- Moderne stationsweise QSO-Historie aus 0.0.22.3 wiederhergestellt.
- Kompakte kategorisierte Einstellungen aus 0.0.22.4 beibehalten.
- Dauerhaft gespeicherter Status „QSO bestätigt“ wieder aktiv.
- UI-Regressionstests für alle drei Hauptbereiche ergänzt.
- DMR-Kern und Funkbetrieb unverändert.

# Änderungsprotokoll

## 0.0.22.4 – Neue kompakte Einstellungen

- Einstellungsbereich vollständig in das dunkle CarenDMR-Kartenlayout überführt.
- Linke Kategorienavigation für **Audio**, **Netzwerk**, **Daten**, **Bedienung**, **Diagnose** und **Erweiterungen** ergänzt.
- Suchfeld springt per Suchbegriff direkt zur passenden Einstellungsgruppe.
- Mikrofon, Wiedergabe und AMBE-Codec in deutlich kleinere, getrennte Karten aufgeteilt.
- BrandMeister-Profil wird ohne Passwort als kompakte Statuskarte angezeigt.
- RadioID-Kontaktdaten und QSO-Datenbank logisch im Bereich **Daten** gebündelt.
- Diagnosemodus bleibt standardmäßig ausgeschaltet und ist gezielt aktivierbar.
- Platz für UDP-Logbuch, APRS, Stream Deck/Fußtaster und Plugins vorbereitet.
- Betriebsseite, BrandMeister-Protokoll, Empfang, TG-Wechsel und TX/RX-Logik unverändert.

## 0.0.22.1 – GUI-Startkorrektur

- Ungültige `padx`/`pady`-Optionen aus `tk.Listbox` entfernt.
- GUI-Start unter Tkinter geprüft.
- DMR-Kern unverändert.

## 0.0.22.0 – UI/UX-Redesign, Phase 1

- Betriebsseite als modernes dunkles Funk-Dashboard mit Kartenstruktur neu aufgebaut.
- Verbindungsleiste mit TG, Timeslot, Rufart, **TG wechseln** sowie CONNECT/DISCONNECT zusammengeführt.
- Gegenstation, Funksteuerung, Pegel und Ereignisse visuell klar priorisiert.
- Große rastende TX-Taste, Stumm-Funktion und sämtliche bestehende Funklogik unverändert weiterverwendet.
- Ausführliche `[DIAG]`-PowerShell-Ausgaben sind im Normalbetrieb standardmäßig ausgeschaltet.
- Diagnosemodus kann unter **Einstellungen → Diagnose** ein- und ausgeschaltet werden und wird lokal gespeichert.
- Zentrales Farbsystem und wiederverwendbare UI-Stile als Grundlage der weiteren Neugestaltung ergänzt.
- Keine Änderung an BrandMeister-Login, dynamischer TG-Aktivierung, Decoder, Audio, Parrot oder TX→RX-Rückkehr.

## 0.0.21.1 – Funkgeräte-Betriebsmaske

- CONNECT/DISCONNECT als zentraler Verbindungs-Toggle im Kanalbereich.
- Rufart Gruppe/Privat neben Talkgroup und Timeslot; dynamische Aktivierung und Empfangsfilter berücksichtigen die Rufart.
- Stumm-Schalter auf der Betriebsseite; Netzwerkempfang und Historie laufen stumm weiter.
- Große TX-Taste bleibt als TX AUS/TX EIN-Toggle. Beim Beenden erscheint kein irritierender Zwischenzustand mehr.
- Parrot-Ergebnis und 60-Sekunden-Sicherheitsabschaltung stehen nur noch im Ereignisprotokoll.
- Beenden bleibt als separate Schaltfläche unterhalb des Betriebsbereichs.

## 0.0.21.0 – Funkgeräte-Oberfläche

- Empfang und PTT im gemeinsamen Reiter **Betrieb** zusammengeführt.
- Hauptnavigation auf **Betrieb**, **QSO-Historie** und **Einstellungen** reduziert.
- Große rastende TX-Taste ergänzt: einmal drücken startet TX (rot), erneut drücken beendet TX und kehrt automatisch zum Empfang zurück.
- TX-Sicherheitsabschaltung verbindlich auf 60 Sekunden gesetzt.
- Technische Mikrofon-, Audio-, Kontakt- und Encoderfunktionen in die Einstellungen verschoben.
- Gespeicherten AMBE-Encoder beim Programmstart automatisch laden und prüfen; Meldung nur bei Fehler, Empfang bleibt verfügbar.
- QSO-Historie um vorbereiteten Kontaktstatus „Nur gehört“ ergänzt.
- Bestehende dynamische TG-/TS-Umschaltung sowie automatische TX→RX-Rückkehr unverändert weiterverwendet.
- Parrot-Ziel 9990 / TS2 bleibt vorerst fest verriegelt; freies Senden ist nicht Bestandteil dieser Version.

## 0.0.20.2 – Automatische Rückkehr von Parrot zu Empfang

- Zentrale `ConnectionManager`-Steuerung für Verbinden, Trennen, TG-/TS-Wechsel und TX-Rückkehr ergänzt.
- Ein vor dem Parrot-Test aktiver Empfang wird kontrolliert beendet und nach Erfolg oder Fehler automatisch mit derselben TG-/TS-Kombination wieder gestartet.
- Manuelles Drücken auf „Verbinden und empfangen“ nach dem Parrot-Test ist nicht mehr vorgesehen.
- Empfang bleibt aus, wenn der Parrot-Test bei zuvor getrennter Verbindung gestartet wurde.
- Gleichzeitige Verbindungsoperationen werden zentral gesperrt.
- Diagnosecode aus 0.0.20.1 bleibt für spätere Fehleranalysen enthalten.
- BrandMeister-API und API-Key bleiben vollständig ungenutzt.

## 0.0.20.1-DIAG – Vollständige Empfangsdiagnose

- Protokolliert BrandMeister-Anmeldung, Ziel-TG und Timeslot sowie den Aktivierungsruf.
- Zeigt jedes eingehende DMRD-Paket mit Quelle, Ziel, Timeslot, Rufart, Frame-Typ und Stream-ID.
- Protokolliert für jedes verworfene Paket den genauen Filtergrund.
- Zeigt Decoder-Aufrufe, erzeugte PCM-Samples und Übergaben an die Audioausgabe.
- Gibt alle fünf Sekunden sowie beim Beenden eine kompakte Empfangsstatistik aus.
- Keine Änderung am BrandMeister-Protokoll, Aktivierungsruf oder Decoderverfahren.

# Changelog

## 0.2.1.12 – AMBE Codec Lab

- Neuer Offline-Test `tools/ambe_codec_lab.py`: kein BrandMeister, kein TX und kein Parrot erforderlich.
- Eine vorhandene `03_vor_ambe_8k.wav` wird unverändert als feste Hörreferenz verwendet.
- Dasselbe AMBE-Codewort wird über zwei Decoderpfade verglichen: aktueller CarenDMR-mbelib-Decoder und das konfigurierte DroidStar-Vocoder-Plugin.
- Die native Vocoder-Bridge stellt dafür zusätzlich `decode_2450x1150` bereit.
- Ausgabe: Eingang, CarenDMR/mbelib-Loopback, DroidStar-Plugin-Loopback, AMBE-Frames und `report.json`.
- Keine Änderung an Live-TX, DMR-Paketierung, DSP, Mic-Gain oder BrandMeister-Verhalten.

## 0.2.1.11 – Pegelpfad vor AMBE messbar

- Geführte Audio-Tests erzeugen zusätzlich `level_path.json`.
- Der Bericht weist RMS, Peak und Crest-Faktor für Mikrofon roh, nach Mic-Gain, nach Sprachaufbereitung und unmittelbar vor AMBE aus.
- Für jede Stufe wird die Pegeländerung gegenüber der vorherigen Stufe in dB ausgewiesen.
- `test_metadata.json` enthält nun zusätzlich den linearen Mic-Gain-Faktor und dessen dB-Wert.
- `tx_rx_timing.log` erhält `TX_PEGELPFAD` mit Mic-Gain-Prozent, Faktor und dB-Wert.
- Wichtig: Die Messung bestätigt die bestehende Semantik: 100 % Mic-Gain = 0 dB; 25 % = Faktor 0,25 = ungefähr -12,04 dB. An der Audiobearbeitung selbst wurde bewusst noch nichts verändert.
- Keine Änderungen an DMR-Protokoll, AMBE, Parrot-Steuerung oder RX-Audio.

## 0.0.27.3 – Einstellungen abgeschlossen

- Sicherheitsabfrage vor dem Vormerken der Hotkey-Werkseinstellungen.
- Werkseinstellungen werden weiterhin erst mit Übernehmen oder OK dauerhaft gespeichert.
- Abbrechen verwirft vorgemerkte Änderungen.
- Hotkey-Tabelle verhält sich als Auswahlliste: Zeilenwechsel mit Pfeiltasten.
- Tab verlässt die Tabelle und setzt die normale Dialognavigation fort.
- Keine Änderungen am Funkbetrieb oder an der bestehenden Bedienlogik.

## 0.0.20.0 – Empfang mit automatisch schaltbarer TG-/Timeslot-Kombination

- Talkgroup und Timeslot 1 oder 2 bleiben während des Empfangs bearbeitbar.
- Neue Schaltfläche „TG / Timeslot umschalten“ ergänzt.
- CarenDMR beendet beim Umschalten den bisherigen Empfang kontrolliert, übernimmt die neue Kombination und verbindet automatisch erneut.
- Keine manuelle Trennung und kein erneuter Klick auf „Verbinden und empfangen“ mehr erforderlich.
- Doppelte gleichzeitige Umschaltvorgänge werden verhindert.
- Strg+U als barrierefreies Tastenkürzel für den TG-/TS-Wechsel ergänzt.
- Empfang weiterhin ohne BrandMeister-API und ohne API-Key.
- Sendepfad und Parrot-Test bewusst nicht verändert.
- Automatische Testreihe um den TG-/TS-Wechsel erweitert.

## 0.0.19.7 – Gültiger stummer Gruppenruf zur dynamischen TG-Aktivierung

- Den wirkungslosen 2-Paket-Nullimpuls aus 0.0.19.6 entfernt.
- Vollständigen DMR-Gruppenruf mit gültiger Voice-LC, sechs stummen Sprachbursts und Terminator erzeugt.
- Pakete im DMR-Takt über die bestehende angemeldete UDP-Verbindung gesendet.
- Weiterhin keine BrandMeister-API und kein API-Key.
- PowerShell-Dateien werden gemäß DEPLOY.md direkt nach dem Entpacken mit `Unblock-File` freigeschaltet.

## 0.0.19.6 – Dynamischer TG-Empfang ohne BrandMeister-API

- Talkgroup und Timeslot können im Empfangsreiter vor dem Verbinden frei gewählt werden.
- Nach erfolgreichem Homebrew-Login aktiviert CarenDMR die gewählte Talkgroup über einen kurzen DMRD-Gruppenruf-Impuls auf derselben UDP-Verbindung.
- Kein BrandMeister-API-Key und kein HTTP-API-Aufruf erforderlich.
- Der Impuls enthält keinen Sprachinhalt und endet unmittelbar mit einem Terminator.
- Eingehende DMRD-Pakete werden dynamisch nach der gewählten Talkgroup und dem gewählten Timeslot gefiltert.
- Zielwahl ist während einer laufenden Verbindung gesperrt; für einen Wechsel wird getrennt und neu verbunden.
- Das eigenständige Test2-Referenzprogramm ist nicht Bestandteil der Version 0.0.19.6.
- Automatische Testreihe auf 190 Tests erweitert.

## 0.0.19.4 – PTT-Status korrigiert und TX-Sicherheitslimit flexibel

- PTT-Loslassen beendet die Aufnahme sofort über das gemeinsame Stop-Ereignis.
- Der Aufnahme-Timer stoppt beim Loslassen und überschreibt die Statusanzeige während Kodierung, Versand und Echo-Wartezeit nicht mehr.
- Das TX-Sicherheitslimit ist in der GUI zwischen 5 und 180 Sekunden einstellbar.
- Standardwert bleibt 15 Sekunden; der Wert wird lokal in `config/audio_send.local.json` gespeichert.
- Das Limit bleibt ausschließlich eine Notbremse, falls ein Loslassen-Ereignis ausbleibt.
- Weiterhin ausschließlich fest verriegelter Privatruf an 9990 auf Timeslot 2; keine freie Zielwahl.

## 0.0.19.1

- Fest verriegelter Parrot-Sprachtest: DMR-ID 9990, Privatruf, Timeslot 2.
- Fünf Sekunden Mikrofonaufnahme, PCM→AMBE, einmalige DMRD-Übertragung und Echoempfang.
- Harte Sendegrenze zehn Sekunden; keine freie Zielwahl und keine Gruppenrufe.


## 0.0.19.1 – DroidStar-Plugin-ABI unter Windows korrigiert

- Tatsächlichen DroidStar-Export `destroy` unterstützt; der historische Tippfehler `destry` bleibt als Fallback kompatibel.
- Präzise Diagnose ergänzt, welcher Plugin-Export fehlt beziehungsweise ob das Vocoder-Objekt nicht erzeugt werden konnte.
- Windows-Bridge statisch gelinkt und auf unerwünschte MSYS2-Laufzeitabhängigkeiten geprüft.
- Weiterhin ausschließlich lokaler PCM→AMBE-Test; keine PTT und kein DMRD-Versand.

## 0.0.19.0 – Optionale Vocoder-Plugin-Integration

- Neutrale `AmbeEncoder`-Schnittstelle ergänzt.
- Separat bereitgestellte DroidStar-kompatible Vocoder-Plugins über eine native C++-Bridge angebunden.
- Plugin-Auswahl, lokaler Pfadspeicher und erneute Prüfung in der GUI ergänzt.
- Rein lokalen PCM-zu-AMBE-Test mit 160 PCM-Samples und 9 Byte AMBE-Ausgabe ergänzt.
- USB-AMBE-Backend als ausdrücklich noch nicht implementierte Erweiterungsgrenze vorbereitet.
- Keine PTT, keine DMRD-Aussendung und keine freie Zielwahl ergänzt.

## 0.0.18.2 – Audiopegel, Stumm und samplegenaue Aufnahme

- Mikrofonverstärkung wird während des Ziehens sofort angewendet, aber erst 600 ms nach der letzten Änderung gespeichert.
- Testaufnahmen sammeln bei 16 kHz exakt 80.000 Samples und zeigen 5,00 Sekunden an.
- Ausgabelautstärke von 0 bis 100 Prozent für den DMR-Empfang ergänzt.
- Benutzer-Stummschaltung mit Strg+M ergänzt; Empfang, Decoder und QSO-Historie laufen weiter.
- Benutzer-Stumm und temporäres Aufnahme-Stumm bleiben intern getrennt.
- Audioeinstellungen werden beim Beenden zusätzlich gesichert.
- Keine PTT, kein AMBE-Encoder und keine DMRD-Sendefunktion ergänzt.

## 0.0.18 – Lokaler Audio-Sendepfad

- Eigenen, von Empfang und GUI getrennten `AudioSendService` ergänzt.
- Mikrofone in der GUI einlesen und auswählen.
- Fünfsekündige PCM-Testaufnahme mit 16 kHz, Mono und Pegelanzeige ergänzt.
- Lokale Wiedergabe der Testaufnahme und viersekündigen Loopback-Test ergänzt.
- Diagnose für Gerät, Samplerate, Kanalzahl, Sampleanzahl und Spitzenpegel ergänzt.
- Keine PTT, kein AMBE-Encoder und keine DMRD-Sendefunktion ergänzt.
- Vollständige Testreihe auf 157 Tests erweitert.

## 0.0.17 – Dauerempfang und QSO-Historie

- Periodischen BrandMeister-Heartbeat während des Live-Empfangs ergänzt; MSTPONG-Antworten werden im gemeinsamen Empfangskanal sicher verarbeitet.
- GUI-Empfang läuft ohne feste Zeitgrenze bis Trennen oder Programmende.
- Eigenen barrierefrei per Tastatur erreichbaren Reiter „QSO-Historie“ ergänzt.
- Abgeschlossene Sprechdurchgänge lokal in `data/qso_history.db` gespeichert.
- Historie zeigt Zeit, Rufzeichen, Name, Land, DMR-ID, Talkgroup/Timeslot und Dauer.
- SQLite-Verbindungen werden explizit geschlossen; lokale Historie bleibt aus Git und Release ausgeschlossen.
- Keine Sendefunktion ergänzt.

## 0.0.15 – Aktuelle Station und Live-QSO-Informationen

- Aktuellen DMR-Sprecher als UI-unabhängiges Domain-Modell ergänzt.
- Sprechbeginn, Sprecherwechsel und Sprechende aus dem vorhandenen DMRD-Empfang abgeleitet.
- DMR-ID, Talkgroup, Timeslot und laufende Sprechdauer im Hauptfenster angezeigt.
- Sprecherwechsel und beendete Sprechdurchgänge im zugänglichen Ereignisprotokoll ergänzt.
- Identische Sprecherinformationen im Konsolenempfang ausgegeben.
- Application-Service zwischen Bedienoberfläche und Empfangstechnik ergänzt; keine GUI-Abhängigkeit in Netzwerk, Decoder oder Audio.
- Keine externe Kontaktdatenbank, keine neue Sendefunktion und keine Änderung der Projektstruktur.

## 0.0.14.1 – Konsistente Betriebszustände

- BrandMeister-Verbindung, Empfang und Audio in der GUI getrennt dargestellt.
- Erfolgreiche Anmeldung und Start des TG91/TS2-Empfangs werden einmalig im Ereignisprotokoll bestätigt.
- Veralteten Eindruck „Verbindung wird hergestellt“ bei bereits laufendem Empfang beseitigt.
- Keine DMR-, Netzwerk-, Decoder- oder Sendefunktion geändert.

## 0.0.13.5 – Längerer TG91-Empfang und Windows-Buildbereinigung

- Rein empfangenden TG91-/Timeslot-2-Lauf ohne feste 60-Sekunden-Grenze ergänzt; Ende mit Strg+C.
- Option `--duration` für begrenzte Läufe zwischen 1 und 3600 Sekunden ergänzt.
- Laufende Diagnoseausgabe im 30-Sekunden-Intervall ergänzt.
- Sauberes Schließen von Netzwerk, Decoder und Audio nach Strg+C automatisiert geprüft.
- Windows-Buildskript für MSYS2-UCRT64 korrigiert: Compilererkennung, Laufzeitpfad und mathematische Konstanten.
- Keine Sendeoberfläche und keine DMRD-Aussendung ergänzt.

## 0.0.13.4 – Windows-Empfangsdecoder

- Windows-DLL-Pfad für den nativen mbelib-Empfangsdecoder ergänzt.
- Reproduzierbares PowerShell-Buildskript für MSYS2/MinGW-w64 ergänzt.
- DLL-Exporte auf exakt drei reine Empfangsfunktionen begrenzt und geprüft.
- Native DLLs aus Release-ZIPs ausgeschlossen.
- Windows-Installation, Deployment und Live-Empfang dokumentiert.
- Keine neue DMR-, Netzwerk-, Audio- oder Sendefunktion ergänzt.

## 0.0.13.3 – Reproduzierbarer TG91-Live-Empfang

- Vorhandenen rein empfangenden TG91-/Timeslot-2-Pfad über `python main.py --listen` eindeutig erreichbar gemacht.
- Laufzeit weiterhin fest auf maximal 60 Sekunden begrenzt.
- Start- und Abschlussausgabe für Authentifizierung, Audio, Sprachbursts, AMBE-Dekodierung und Ressourcenabschluss vereinheitlicht.
- Fehlerpfad bestätigt weiterhin ausdrücklich, dass kein DMRD-Paket gesendet wurde.
- Automatisierte Einstiegspunkt- und Fail-Closed-Tests ergänzt.
- Keine neue DMR-, Netzwerk-, Audio- oder Sendefunktion ergänzt.

## 0.0.13.2 – Verifizierbare Projektbasis

- Python-Paketstruktur korrigiert: sämtliche Laufzeitmodule liegen wieder unter `carendmr/`.
- Native mbelib-Buildprüfung für macOS und Linux portabel gemacht.
- Veralteten Hinweis entfernt, dass noch keine BrandMeister-Verbindung existiere.
- Startstatus an den vorhandenen BrandMeister-Login und DMR-Empfang angepasst.
- Vollständige automatisierte Testreihe und Release-ZIP-Erstellung verifiziert.
- Keine DMR-, Netzwerk-, Audio- oder Sendefunktion geändert.

## 0.0.13.1 – Project Foundation

- README als zentralen Einstieg für Ziel, Stand, Sicherheit, Installation,
  Dokumentation und Lizenz überarbeitet.
- Roadmap und Beitragsrichtlinien ergänzt.
- getrennte Installationsanleitungen für macOS, Windows und Linux ergänzt.
- Architektur auf den tatsächlichen Stand mit BrandMeister, DMRD-Empfang,
  Software-Vocoder, Jitterpuffer und verriegeltem Parrot-Test aktualisiert.
- Release-, Test-, Commit- und Pull-Request-Ablauf vereinheitlicht.
- Keine DMR-, Netzwerk-, Audio- oder Sendefunktion geändert.

## 0.0.13 – Verriegeltes privates Parrot-Testprofil

- Dauerhafte Sicherheitsregel ergänzt: automatisierte Sendetests dürfen
  niemals eine öffentliche Gruppen-Talkgroup verwenden.
- Offline-Profil hart auf BrandMeister Parrot, Ziel 9990, Privatruf und
  Timeslot 2 verriegelt.
- Maximale zukünftige Sendezeit auf 10 Sekunden und Echo-Beobachtung auf
  exakt 15 Sekunden festgesetzt, ohne Laufzeitparameter.
- Privatrufbit und Voice-LC-FLCO bytegenau mit Referenzpayloads geprüft.
- Früheres automatisiertes TG91-Gruppenrufwerkzeug dauerhaft fail-closed
  deaktiviert und seinen Sendeloop entfernt.
- Genau einen autorisierten privaten Live-Test ausgeführt: acht Pakete in
  0,440 Sekunden, sechs Echo-Sprachbursts, keine Wiederholung und vollständige
  Bereinigung.
- Lokale gesprochene Phasenansagen und Echoausgabe über den bestehenden
  Software-Empfangspfad bestätigt; die gesendete Fixture blieb stumm.

## 0.0.12 – Begrenzte Live-Empfangswiedergabe

- Callback-gesteuerte, auf zwei Sekunden begrenzte PCM-Ausgabe für das
  Standard-Wiedergabegerät ergänzt.
- DMRD-Sequenzpuffer mit drei Bursts Vorlauf, kleiner Umsortierung und
  Stille-Verdeckung fehlender Bursts ergänzt.
- Empfangsdecoder ausschließlich für TG91/Timeslot 2 an die lokale
  Audioausgabe angebunden.
- 180-ms-Syntheseprüfung sowie begrenzten 60-s-Live-Empfang erfolgreich
  ausgeführt.
- Im Live-Test 407 Sprachbursts und 1.221 AMBE-Codewörter ohne Dekodierfehler
  verarbeitet; kein DMRD-Paket gesendet.
- Keine Aufnahme-, Persistenz-, Upload-, Dashboard- oder TX-Funktion ergänzt.

## 0.0.11 – Empfangsseitiger Software-Vocoder

- Austauschbare, zustandsbehaftete Empfangs-Vocoder-Grenze ergänzt.
- Drei AMBE+2-Codewörter evidenzgetreu aus jedem DMR-Sprachburst extrahiert.
- Minimalen nativen DroidStar/mbelib-Decoder für AMBE 2450/1150 auf macOS
  isoliert; Encoder, MD380-Firmware und Codec2 bleiben ausgeschlossen.
- Nicht-personalen Stummvektor deterministisch in 480 PCM-Samples dekodiert
  und Ergebnis, Fehleranzahl sowie ungültige Eingaben automatisiert geprüft.
- ISC-Hinweise, geprüften Upstream-Commit und getrennte Patentprüfung
  dokumentiert.
- Keine Wiedergabe, Live-Sprachbewertung, Netzwerk- oder Sendefunktion ergänzt.

## 0.0.10 – Empfangsereignisse und Accessibility-Anforderungen

- Live beobachtete DMRD-Ablehnungen strukturell und ohne Nutzdaten untersucht:
  gültige 55-Byte-Pakete mit Stream-ID null statt Transportmüll.
- Empfangsparser akzeptiert Stream-ID null als fehlende Metainformation;
  lokale Paketkonstruktion verlangt weiterhin eine von null verschiedene ID.
- Payloadfreie, unveränderliche `DmrdReceiveEvent`-Grenze für Rufbeginn,
  Sprache, Rufende und Signalisierung ergänzt.
- Vollständige VoiceOver-Bedienbarkeit und die Trennung sensibler
  Verbindungseinrichtung von der Betriebsansicht als verbindliche
  Produktanforderungen dokumentiert.
- Empfangsverifikation nach der Änderung ohne Parserablehnung abgeschlossen.
- Keine GUI, Audio-/AMBE-Dekodierung oder neue Sendefunktion ergänzt.

## 0.0.9 – Deterministische DMR-Stummruf-Fixture

- Projektlizenz bewusst als GPLv3-or-later festgelegt.
- Herkunft und Lizenzgrenze der minimal adaptierten DroidStar-DMR-Hilfen
  dokumentiert.
- Offline-Kodierung für Voice-LC-Header, einen aus sechs Bursts bestehenden
  AMBE-Stummrahmen und Terminator-with-LC ergänzt.
- Ziel unverändert fest auf Gruppenruf TG91, Timeslot 2 und Color Code 1
  begrenzt.
- Alle 33-Byte-Payloads bytegenau gegen einen unabhängigen DroidStar-C++-
  Referenzgenerator geprüft.
- Separates, fest auf eine einzige Acht-Paket-Sequenz begrenztes
  Live-Diagnosewerkzeug mit Anmeldung, 60-ms-Taktung, Empfangsmonitor und
  garantiertem Schließen ergänzt.
- Erfolgreicher kontrollierter Einmaltest ohne Wiederholung bestätigt.
- Keine allgemeine Laufzeit-Sendeschnittstelle, kein Audio und keine
  BrandMeister-Konfigurationsänderung ergänzt.

## 0.0.8.1 – BrandMeister-Gerätekennung

- Produktive Package-ID von der projektspezifischen Kennung auf
  `MMDVM_HS_Hat` umgestellt.
- Software-ID `20260728_CarenDMR` unverändert beibehalten.
- Beispielkonfiguration, lokale Laufzeitkonfiguration, Tests und
  Kompatibilitätsdokumentation angeglichen.
- Login-only-Prüfung mit `MMDVM_HS_Hat` erfolgreich gegen BrandMeister
  bestätigt.
- DMRD-Paketdomäne aus 0.0.8 bleibt unverändert und weiterhin ohne
  Netzwerksendeschnittstelle.

## 0.0.8 – DMRD-Paketdomäne

- Unveränderliches Modell für vollständige 55-Byte-DMRD-Pakete ergänzt.
- Strikte Empfangsprüfung für Kennung, Länge, IDs, Timeslot, Ruftyp,
  Rahmenklasse, Stream-ID und 33-Byte-DMR-Nutzdaten implementiert.
- Sprach-LC-Header, Sprach-Synchronrahmen, Sprachrahmen 0 bis 5 und
  Terminator-with-LC als getrennte Konstruktionsprimitive ergänzt.
- Zielbetrieb auf Gruppenruf TG91, Timeslot 2, als explizite und getestete
  Konstante festgelegt.
- Netzwerkversand, Talkgroup-Aktivierung, LC-Kodierung, AMBE und Audio bleiben
  bewusst außerhalb dieses Meilensteins.

## 0.0.7.6 – Eigene BrandMeister-Kennung

- Produktive Software-ID auf `20260728_CarenDMR` gesetzt.
- Produktive Package-ID auf `MMDVM_CarenDMR_PC` gesetzt.
- Beschreibung auf `CarenDMR Digital Voice Client` gesetzt.
- Konfigurationsprüfung für die experimentell bestätigten BrandMeister-Formate ergänzt.
- Vollständige Testmatrix in `docs/BRANDMEISTER_COMPATIBILITY.md` dokumentiert.
- Diagnoseparameter aus 0.0.7.5 bleiben erhalten.

## 0.0.7.5 – Freie RPTC-Kennungen testen

- `brandmeister_check.py` um `--software-value` und `--package-value` erweitert.
- Beliebige Software- und Package-IDs können einzeln gegen das akzeptierte Referenzprofil getestet werden.
- Gegenseitig widersprüchliche Parameter werden mit einer verständlichen Fehlermeldung abgewiesen.
- Zusätzliche Regressionstests für frei gewählte Kennungen ergänzt.

## 0.0.7.4 – BrandMeister-RPTC-Diagnose

- `tools/brandmeister_check.py` um ein reproduzierbares DroidStar-Referenzprofil erweitert.
- Einzeltests für Software-ID, Package-ID, Beschreibung und URL ergänzt.
- Aktives RPTC-Profil wird vor dem Login vollständig angezeigt.
- Lokales Standardprofil bleibt ohne Parameter unverändert.
- 62 automatisierte Tests erfolgreich.

# 0.0.7.1

- RPTC-Koordinatenformat bytegenau an DroidStar angepasst.
- Regressionstest für das nicht-personale Koordinatenformat ergänzt.
- Lokale Konfigurationsdateien werden nicht im Update-Paket ausgeliefert.


## 0.0.7 – BrandMeister-Login

- DroidStar-kompatiblen DMR-Master-Handshake implementiert
- `RPTL`, `RPTK`, `RPTC`, `RPTPING` und `RPTCL` implementiert
- SHA-256-Authentifizierung aus vier Byte Challenge plus Hotspot-Passwort
  implementiert
- `RPTACK`, `MSTNAK` und `MSTPONG` ausgewertet
- explizite Login-Zustände ergänzt
- lokales, von Git auszuschließendes BrandMeister-Konfigurationsformat ergänzt
- einmaliges Diagnosewerkzeug `tools/brandmeister_check.py` ergänzt
- Protokoll- und Clienttests ergänzt
- noch keine DMRD- oder Sprachdatenübertragung

## 0.0.6 – Netzwerkgrundlage

- UDP-Transport, DNS-Auflösung, Netzwerkdiagnose und Heartbeat-Grundlage

## 0.0.5.1 – Audio-Startfehler

- direkter Skriptstart korrigiert

## 0.0.5 – Audio

- Gerätescan, Speicherung und Selbsttest

## 0.0.4 – Core

- EventBus, StatusManager und Accessibility-Grundlage

## 0.0.3 – DroidStar-Analyse

- Architektur- und Protokollanalyse

## 0.0.2 – Release-Werkzeug

- Release-Erzeugung

## 0.0.1 – Projektgrundgerüst

- Projektstart

## 0.0.7.3 – BrandMeister-Referenztest

- Neuer Referenztest mit den exakt aus dem funktionierenden DroidStar-Mitschnitt ermittelten RPTC-Metadaten.
- Der Test verändert `config/brandmeister.local.json` nicht und übernimmt daraus nur Zugangsdaten und Rufzeichen.
- Referenzprofil mit nicht-personalen Testwerten für Beschreibung, URL,
  Software-/Package-ID und Koordinaten ergänzt.


## 0.0.19.5
- Test2 als Referenzimplementierung integriert (tools/brandmeister_dynamic_receiver.py).
- Dynamische TG-Umschaltung per API + UDP-Trigger übernommen.
- Keine statische BrandMeister-Subscription erforderlich.

## Änderungen

- Timeslot 1 und Timeslot 2 liefern wieder einen eindeutigen Auswahlzustand.
- Gruppenruf und Privatruf liefern wieder einen eindeutigen Auswahlzustand.
- F6 kündigt nur den neu gewählten Timeslot kurz an.
- F7 kündigt nur die neu gewählte Rufart kurz an.
- TG-Eingabe, Funklogik, Layout und Tab-Reihenfolge bleiben unverändert.

## 0.1.8.1 – Geführter Audio-Test

- Einmaliger Audio-Test statt dauerhafter Hintergrundaufnahme.
- Zwei Sekunden Mikrofon-Vorlauf werden ausschließlich im RAM gepuffert.
- Die nächste TX-Sendung erzeugt automatisch Roh-, Gain-, AMBE- und Analyse-Dateien.
- Nach Abschluss wird die Diagnoseaufnahme automatisch deaktiviert.
- Der Vorlauf wird separat als `00_vor_ptt_mikrofon_16k.wav` gespeichert, aber niemals gesendet.
- Diagnose-Reiter mit Start-/Abbrechen-Schaltfläche und eindeutigem Status.
- Matplotlib, SciPy, SoundFile und librosa als Analyseabhängigkeiten aufgenommen.

## 0.1.9.2 – DMR-Audio-Benchmark V1

- Neuer Reiter **Audio-Benchmark** für passive Referenzmessungen auf der aktuell verbundenen Talkgroup.
- Messreihen können gestartet, pausiert, über Programmneustarts fortgesetzt und gezielt beendet werden.
- Ein Sprechdurchgang wird ab fünf Sekunden als eigener Testfall erfasst; Analyse und Speicherung laufen in einem getrennten Hintergrundthread.
- Der RX-Echtzeitpfad schreibt nur kurze PCM-Blöcke in eine begrenzte Queue und wartet niemals auf FFT, Statistik oder Datenträgerzugriffe.
- Live-Anzeige für Laufzeit, Rufzeichen, gültige und verworfene Testfälle, Wiederverbindungsstatus und wachsende Referenzwerte.
- Robuste Referenz aus dem besten technisch gültigen Durchgang je Rufzeichen mit Median und Quartilbereich.
- Bei BrandMeister-Verlust bis zu fünf automatische Wiederverbindungsversuche; danach kontrollierter Abbruch ohne Datenverlust.
- Zwischenstand wird nach jedem abgeschlossenen Sprecher atomar unter `data/audio_benchmarks/current.json` gesichert.

## 0.2.1.1 – Modulationstest stabilisiert

- Fachlicher, Qt-unabhängiger `ModulationTestTracker` ergänzt.
- Geführter Test erhält im AudioTest-Ordner ein atomar geschriebenes `manifest.json`.
- Statusschritte zeigen TX-Erkennung, Parrot-Empfang, Abschluss und Fehler eindeutig an.
- Vergleich startet erst nach vollständiger, größenstabiler Parrot-WAV und `echo_received: true`.
- Audio Coach steuert weder Funkkern noch RX/TX-Zustände; er beobachtet nur abgeschlossene Artefakte.

## 0.2.1.6 – WASAPI-Aufnahmepfad
- WASAPI-USB-Eingänge werden bei mehrkanaligen Endpunkten nativ geöffnet; CarenDMR wählt anschließend den tatsächlich signalführenden Kanal für den gemeinsamen Mono-Pfad.
- Der geführte Modulationstest erkennt einen geöffneten, aber stummen Eingang innerhalb der ersten 1,5 Sekunden und sendet dann keine Sprachframes.
- Manifest-Dateien werden bei kurzfristigen Windows-/OneDrive-Sperren mehrfach atomar geschrieben; Messdaten bleiben bei einer Sperre erhalten.

## 0.2.1.82
- QSO-Synchronisation über gemeinsamen Ordner ohne geteilte aktive SQLite-Datei.
- Pro Rechner eigene atomare JSON-Snapshots für konfliktärmeren OneDrive/Dropbox/iCloud-Abgleich.
- Synchronisiert Historie, Gesprochen/Nur-gehört-Status inklusive Rücknahme und QRZ-LOGID.
- Manueller Synchronisieren-Button in der QSO-Historie und Konfiguration unter Datenbanken.
