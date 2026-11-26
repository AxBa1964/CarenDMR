"""Feste Regeln für besondere DMR-Ziele (Qt-frei)."""
from __future__ import annotations

# BrandMeister-Echotest („Papagei“) antwortet nur auf einen Privatruf.
PARROT_TARGET = 9990
PARROT_NOTICE = "9990 Papagei: Rufart auf Privatruf umgestellt."


def required_call_type(target: int, call_type: str) -> tuple[str, str | None]:
    """Liefert die zu verwendende Rufart und ggf. eine Ansage dazu."""
    if int(target) == PARROT_TARGET and call_type != "private":
        return "private", PARROT_NOTICE
    return call_type, None
