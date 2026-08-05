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

# Änderungsverlauf

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
