"""Ableitung von Land und wahrscheinlicher Betriebssprache aus Talkgroup-Nummer und Name.

Die Angaben sind Metadaten für Suche und Filter, keine verbindliche Aussage über
jede konkrete Funkrunde. Explizite Sprachbegriffe im Namen haben Vorrang vor der
MCC-basierten Länderableitung.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TalkgroupMetadata:
    country_code: str = ""
    country_name: str = ""
    language: str = ""
    language_source: str = ""
    language_confidence: float = 0.0


# Für die BrandMeister-Liste relevante DMR-MCC-Präfixe. Mehrsprachige Länder
# werden bewusst mit mehreren wahrscheinlichen Betriebssprachen geführt.
_MCC = {
    202: ("GR", "Griechenland", "Griechisch"), 204: ("NL", "Niederlande", "Niederländisch"),
    206: ("BE", "Belgien", "Niederländisch/Französisch"), 208: ("FR", "Frankreich", "Französisch"),
    213: ("AD", "Andorra", "Katalanisch"), 214: ("ES", "Spanien", "Spanisch"),
    216: ("HU", "Ungarn", "Ungarisch"), 218: ("BA", "Bosnien und Herzegowina", "Bosnisch/Kroatisch/Serbisch"),
    219: ("HR", "Kroatien", "Kroatisch"), 220: ("RS", "Serbien", "Serbisch"),
    222: ("IT", "Italien", "Italienisch"), 226: ("RO", "Rumänien", "Rumänisch"),
    228: ("CH", "Schweiz", "Deutsch/Französisch/Italienisch"), 230: ("CZ", "Tschechien", "Tschechisch"),
    231: ("SK", "Slowakei", "Slowakisch"), 232: ("AT", "Österreich", "Deutsch"),
    234: ("GB", "Vereinigtes Königreich", "Englisch"), 235: ("GB", "Vereinigtes Königreich", "Englisch"),
    238: ("DK", "Dänemark", "Dänisch"), 240: ("SE", "Schweden", "Schwedisch"),
    242: ("NO", "Norwegen", "Norwegisch"), 244: ("FI", "Finnland", "Finnisch/Schwedisch"),
    246: ("LT", "Litauen", "Litauisch"), 247: ("LV", "Lettland", "Lettisch"),
    248: ("EE", "Estland", "Estnisch"), 250: ("RU", "Russland", "Russisch"),
    255: ("UA", "Ukraine", "Ukrainisch"), 257: ("BY", "Belarus", "Belarussisch/Russisch"),
    259: ("MD", "Moldau", "Rumänisch/Russisch"), 260: ("PL", "Polen", "Polnisch"),
    262: ("DE", "Deutschland", "Deutsch"), 263: ("DE", "Deutschland", "Deutsch"),
    264: ("DE", "Deutschland", "Deutsch"), 265: ("DE", "Deutschland", "Deutsch"),
    268: ("PT", "Portugal", "Portugiesisch"), 270: ("LU", "Luxemburg", "Luxemburgisch/Deutsch/Französisch"),
    272: ("IE", "Irland", "Englisch"), 274: ("IS", "Island", "Isländisch"),
    278: ("MT", "Malta", "Maltesisch/Englisch"), 280: ("CY", "Zypern", "Griechisch/Türkisch"),
    284: ("BG", "Bulgarien", "Bulgarisch"), 286: ("TR", "Türkei", "Türkisch"),
    294: ("MK", "Nordmazedonien", "Mazedonisch"), 302: ("CA", "Kanada", "Englisch/Französisch"),
    310: ("US", "USA", "Englisch"), 311: ("US", "USA", "Englisch"), 312: ("US", "USA", "Englisch"),
    313: ("US", "USA", "Englisch"), 314: ("US", "USA", "Englisch"), 315: ("US", "USA", "Englisch"),
    316: ("US", "USA", "Englisch"), 317: ("US", "USA", "Englisch"), 318: ("US", "USA", "Englisch"),
    319: ("US", "USA", "Englisch"), 330: ("PR", "Puerto Rico", "Spanisch/Englisch"),
    334: ("MX", "Mexiko", "Spanisch"), 404: ("IN", "Indien", "Hindi/Englisch"),
    440: ("JP", "Japan", "Japanisch"), 450: ("KR", "Südkorea", "Koreanisch"),
    460: ("CN", "China", "Chinesisch"), 466: ("TW", "Taiwan", "Chinesisch"),
    502: ("MY", "Malaysia", "Malaiisch/Englisch"), 505: ("AU", "Australien", "Englisch"),
    510: ("ID", "Indonesien", "Indonesisch"), 515: ("PH", "Philippinen", "Filipino/Englisch"),
    520: ("TH", "Thailand", "Thailändisch"), 525: ("SG", "Singapur", "Englisch"),
    530: ("NZ", "Neuseeland", "Englisch"), 602: ("EG", "Ägypten", "Arabisch"),
    603: ("DZ", "Algerien", "Arabisch/Französisch"), 604: ("MA", "Marokko", "Arabisch/Französisch"),
    655: ("ZA", "Südafrika", "Englisch/Afrikaans"), 704: ("GT", "Guatemala", "Spanisch"),
    706: ("SV", "El Salvador", "Spanisch"), 708: ("HN", "Honduras", "Spanisch"),
    710: ("NI", "Nicaragua", "Spanisch"), 712: ("CR", "Costa Rica", "Spanisch"),
    714: ("PA", "Panama", "Spanisch"), 716: ("PE", "Peru", "Spanisch"),
    722: ("AR", "Argentinien", "Spanisch"), 724: ("BR", "Brasilien", "Portugiesisch"),
    730: ("CL", "Chile", "Spanisch"), 732: ("CO", "Kolumbien", "Spanisch"),
    734: ("VE", "Venezuela", "Spanisch"), 740: ("EC", "Ecuador", "Spanisch"),
    748: ("UY", "Uruguay", "Spanisch"),
}

_LANGUAGE_HINTS = (
    (("english", "englisch"), "Englisch"), (("german", "deutsch"), "Deutsch"),
    (("spanish", "español"), "Spanisch"), (("portuguese", "portug"), "Portugiesisch"),
    (("italian", "italiano"), "Italienisch"), (("french", "francophonie", "français"), "Französisch"),
    (("dutch", "nederland"), "Niederländisch"), (("swedish",), "Schwedisch"),
    (("arabic",), "Arabisch"),
)

_INTERNATIONAL = {1, 2, 8, 9, 91, 92, 93, 94, 95, 98, 901, 902, 903, 907, 918, 955, 969, 973}


def derive_talkgroup_metadata(target: int, name: str) -> TalkgroupMetadata:
    number = int(target)
    folded = str(name).casefold()
    for hints, language in _LANGUAGE_HINTS:
        if any(hint in folded for hint in hints):
            base = _from_mcc(number)
            return TalkgroupMetadata(base.country_code, base.country_name, language, "name", 0.98)
    if number in _INTERNATIONAL or "world" in folded or "europe" in folded or "international" in folded:
        return TalkgroupMetadata("WW", "International", "International/Mehrsprachig", "name", 0.95)
    return _from_mcc(number)


def _from_mcc(number: int) -> TalkgroupMetadata:
    digits = str(abs(number))
    if len(digits) < 3:
        return TalkgroupMetadata()
    mcc = int(digits[:3])
    info = _MCC.get(mcc)
    if not info:
        return TalkgroupMetadata()
    code, country, language = info
    return TalkgroupMetadata(code, country, language, "mcc", 0.82)
