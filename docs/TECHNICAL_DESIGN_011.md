# CarenDMR 0.0.10 – Empfangsereignisse und Stream-ID-Kompatibilität

## Beobachtung

Nach dem kontrollierten TG91-Aktivierungstest wurden DMRD-Datagramme zunächst
vom strikten Modell abgewiesen. Eine weitere begrenzte, rein empfangende
Messung erfasste ausschließlich strukturelle Zähler:

- alle beobachteten Datagramme waren 55 Byte lang,
- alle trugen die DMRD-Kennung,
- es gab keine reservierten Rahmenflags oder beschädigten Paketlängen,
- die einzige Ablehnungsursache war eine Stream-ID von null.

Damit handelt es sich nicht um Transportmüll und nicht um eine abweichende
Paketlänge.

## Upstream-Abgleich

Der geprüfte DroidStar-Empfangspfad verarbeitet 55-Byte-DMRD-Pakete und
übernimmt die Stream-ID, ohne null zurückzuweisen. Der geprüfte
MMDVMHost-Empfangspfad wertet die Stream-ID des Netzwerkpakets überhaupt nicht
als Gültigkeitsbedingung aus. Dessen Sendepfad erzeugt dagegen absichtlich
eine zufällige, von null verschiedene Stream-ID.

Daraus folgt die asymmetrische Regel:

- Empfang: Stream-ID null ist zulässige, aber fehlende Metainformation.
- Lokale Konstruktion/Sendung: Stream-ID muss weiterhin ungleich null sein.

Andere Validierungen werden nicht gelockert.

## Empfangsereignisgrenze

`DmrdReceiveEvent` ist die stabile Grenze zwischen Paketparser und späteren
Status-/Protokollverbrauchern. Das Ereignis enthält:

- Sequenznummer,
- Quelle und Ziel,
- Talkgroup-/Timeslot-Einordnung,
- Gruppen- oder Privatruf,
- Aktivität `CALL_START`, `VOICE`, `CALL_END` oder `SIGNALING`,
- Rahmenklasse und optionale Rahmennummer,
- optionale Stream-ID.

Der 33-Byte-Burst wird bewusst nicht in das Ereignis übernommen. Audio- oder
FEC-Verarbeitung bleibt Aufgabe einer späteren, getrennten Schicht.

Eine Stream-ID null wird im Ereignis zu `None`. Sie verhindert weder die
Einordnung des Sprachrahmens noch die spätere zugängliche Statusanzeige.

## Sicherheitsgrenze

Dieser Meilenstein ergänzt:

- keinen Netzwerk-Sendepfad,
- keine PTT-Funktion,
- keine Audio- oder AMBE-Dekodierung,
- keine GUI.

Die Ereignisgrenze kann später einen minimalen, VoiceOver-zugänglichen
Verbindungs- und Aktivitätsstatus speisen, ohne DMR-Nutzdaten an die UI
weiterzugeben.
