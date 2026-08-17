"""Persönlicher Favorit für einen vollständigen DMR-Kanal."""
from __future__ import annotations

from dataclasses import dataclass

from .dmr_channel import DmrChannel


@dataclass(frozen=True, slots=True)
class FavoriteChannel:
    target: int
    timeslot: int
    call_type: str
    default_name: str = ""
    custom_name: str = ""
    note: str = ""
    position: int = 0

    def normalized(self) -> "FavoriteChannel":
        channel = DmrChannel(self.target, self.timeslot, self.call_type).normalized()
        return FavoriteChannel(
            target=channel.target,
            timeslot=channel.timeslot,
            call_type=channel.call_type,
            default_name=str(self.default_name).strip(),
            custom_name=str(self.custom_name).strip(),
            note=str(self.note).strip(),
            position=max(0, int(self.position)),
        )

    @property
    def display_name(self) -> str:
        return self.custom_name or self.default_name or str(self.target)

    @property
    def call_type_short(self) -> str:
        return "G" if self.call_type == "group" else "P"

    def to_dmr_channel(self) -> DmrChannel:
        return DmrChannel(
            target=self.target,
            timeslot=self.timeslot,
            call_type=self.call_type,
            name=self.display_name,
        ).normalized()
