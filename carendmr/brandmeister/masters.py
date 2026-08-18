"""Bekannte BrandMeister-Master für die zentrale Serverauswahl."""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BrandMeisterMaster:
    key: str
    label: str
    host: str
    port: int = 62031

MASTERS: tuple[BrandMeisterMaster, ...] = (
    BrandMeisterMaster("BM_2621_Germany", "BM_2621_Germany", "master1.bm262.de"),
    BrandMeisterMaster("BM_2622_Germany", "BM_2622_Germany", "master2.bm262.de"),
)

def by_host(host: str, port: int = 62031) -> BrandMeisterMaster | None:
    normalized = host.strip().lower()
    for master in MASTERS:
        if master.host.lower() == normalized and master.port == int(port):
            return master
    return None
