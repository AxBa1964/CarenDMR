"""Small sequence-aware jitter buffer for decoded 60 ms DMR voice bursts."""

from __future__ import annotations

from dataclasses import dataclass


DMR_BURST_SAMPLES = 480


@dataclass(frozen=True, slots=True)
class PlayoutBatch:
    frames: tuple[tuple[int, ...], ...]
    concealed_bursts: int = 0


class DmrJitterBuffer:
    """Reorders a few UDP bursts and conceals bounded sequence gaps."""

    def __init__(self, *, prebuffer_bursts: int = 3, reorder_bursts: int = 3):
        if prebuffer_bursts < 1 or reorder_bursts < 1:
            raise ValueError("Jitter-Puffergrenzen müssen positiv sein.")
        self.prebuffer_bursts = prebuffer_bursts
        self.reorder_bursts = reorder_bursts
        self._pending: dict[int, tuple[int, ...]] = {}
        self._expected: int | None = None
        self._started = False

    def reset(self, *, first_voice_sequence: int | None = None) -> None:
        self._pending.clear()
        self._expected = first_voice_sequence
        self._started = False

    def push(self, sequence: int, samples: tuple[int, ...]) -> PlayoutBatch:
        if not 0 <= sequence <= 255:
            raise ValueError("Die DMRD-Sequenz muss zwischen 0 und 255 liegen.")
        if len(samples) != DMR_BURST_SAMPLES:
            raise ValueError("Ein dekodierter DMR-Burst benötigt 480 Samples.")
        if self._expected is None:
            self._expected = sequence
        distance = (sequence - self._expected) & 0xFF
        if distance >= 128:
            return PlayoutBatch(())
        self._pending.setdefault(sequence, samples)

        if not self._started and len(self._pending) < self.prebuffer_bursts:
            return PlayoutBatch(())
        self._started = True
        return self._drain()

    def _drain(self) -> PlayoutBatch:
        ready: list[tuple[int, ...]] = []
        concealed = 0
        while self._expected is not None:
            samples = self._pending.pop(self._expected, None)
            if samples is not None:
                ready.append(samples)
                self._expected = (self._expected + 1) & 0xFF
                continue
            if len(self._pending) < self.reorder_bursts:
                break
            ready.append((0,) * DMR_BURST_SAMPLES)
            concealed += 1
            self._expected = (self._expected + 1) & 0xFF
        return PlayoutBatch(tuple(ready), concealed)

    def flush(self) -> PlayoutBatch:
        if not self._pending:
            return PlayoutBatch(())
        self._started = True
        old_limit = self.reorder_bursts
        self.reorder_bursts = 1
        try:
            return self._drain()
        finally:
            self.reorder_bursts = old_limit
