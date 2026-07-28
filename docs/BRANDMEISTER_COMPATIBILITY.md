# BrandMeister-Kompatibilität der RPTC-Kennungen

## Zweck

Beim Homebrew-Login bestätigt BrandMeister die Stationsdaten im `RPTC`-Paket nur,
wenn die Kennungen in einem akzeptierten Format übertragen werden. Die folgenden
Regeln wurden am 28.07.2026 mit reproduzierbaren Einzeltests gegen den verwendeten
BrandMeister-Master ermittelt.

## Ergebnis

CarenDMR verwendet produktiv:

```text
Software-ID: 20260728_CarenDMR
Package-ID:  MMDVM_CarenDMR_PC
Description: CarenDMR Digital Voice Client
```

Die URL bleibt zunächst leer.

## Nachgewiesene Software-ID-Tests

```text
20181107_Pi-Star       -> RPTACK
CarenDMR 0.0.7.4       -> MSTNAK
20260728_CarenDMR      -> RPTACK
20181107_CarenDMR      -> RPTACK
20260728_Pi-Star       -> RPTACK
```

Daraus ergibt sich für die Software-ID das beobachtete Format:

```text
acht Ziffern + Unterstrich + Bezeichnung
```

## Nachgewiesene Package-ID-Tests

```text
MMDVM_MMDVM_HS_Hat          -> RPTACK
CarenDMR_CarenDMR_HS_Hat    -> MSTNAK
MMDVM_CarenDMR_HS_Hat       -> RPTACK
MMDVM_MMDVM_CarenDMR        -> RPTACK
MMDVM_CarenDMR_Windows      -> RPTACK
TEST_CarenDMR_HS_Hat        -> MSTNAK
MMDV_CarenDMR_Windows       -> MSTNAK
MMDVMX_CarenDMR_Windows     -> RPTACK
MMDVM                       -> RPTACK
XMMDVM_CarenDMR             -> MSTNAK
```

Das beobachtete Mindestkriterium lautet daher:

```text
Die Package-ID beginnt mit MMDVM.
```

## Freie Felder

Eine geänderte Beschreibung und eine geänderte URL wurden jeweils mit `RPTACK`
bestätigt. Diese Felder sind nach den durchgeführten Tests nicht Ursache der
früheren `MSTNAK`-Antworten.

## Einordnung

Die Regeln sind aus realen Tests abgeleitet. Sie belegen das Verhalten des dabei
verwendeten BrandMeister-Masters, stellen aber keine offizielle Zusage für alle
Master oder zukünftige Serverversionen dar. Die Diagnoseoptionen in
`tools/brandmeister_check.py` bleiben deshalb erhalten.
