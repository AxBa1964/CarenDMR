"""Live einstellbarer, leichter DMR-Sprach-Audio-Tuner.

Die Verarbeitung ist zustandsbehaftet und blockweise O(n). Sie verwendet keine
FFT, keine Dateizugriffe und keine Hintergrundanalyse im Echtzeitpfad.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import math


@dataclass(frozen=True, slots=True)
class TxAudioTunerSettings:
    profile: str = "Neutral"
    low_db: float = 0.0
    mids_db: float = 0.0
    presence_db: float = 0.0
    high_db: float = 0.0
    dynamics_percent: int = 0
    limiter_percent: int = 20

    def normalized(self) -> "TxAudioTunerSettings":
        return replace(
            self,
            profile=str(self.profile or "Eigene"),
            low_db=max(-12.0, min(12.0, float(self.low_db))),
            mids_db=max(-12.0, min(12.0, float(self.mids_db))),
            presence_db=max(-12.0, min(12.0, float(self.presence_db))),
            high_db=max(-12.0, min(12.0, float(self.high_db))),
            dynamics_percent=max(0, min(100, int(self.dynamics_percent))),
            limiter_percent=max(0, min(100, int(self.limiter_percent))),
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self.normalized())

    @classmethod
    def from_dict(cls, value: object) -> "TxAudioTunerSettings":
        if not isinstance(value, dict):
            return cls()
        try:
            return cls(
                profile=str(value.get("profile", "Neutral")),
                low_db=float(value.get("low_db", 0.0)),
                mids_db=float(value.get("mids_db", 0.0)),
                presence_db=float(value.get("presence_db", 0.0)),
                high_db=float(value.get("high_db", 0.0)),
                dynamics_percent=int(value.get("dynamics_percent", 0)),
                limiter_percent=int(value.get("limiter_percent", 20)),
            ).normalized()
        except (TypeError, ValueError):
            return cls()


PRESETS: dict[str, TxAudioTunerSettings] = {
    "Neutral": TxAudioTunerSettings(profile="Neutral", limiter_percent=20),
    "Klar": TxAudioTunerSettings(profile="Klar", low_db=-3, mids_db=1, presence_db=3, high_db=1, dynamics_percent=20, limiter_percent=30),
    "DX": TxAudioTunerSettings(profile="DX", low_db=-6, mids_db=3, presence_db=5, high_db=1, dynamics_percent=45, limiter_percent=45),
    "Warm": TxAudioTunerSettings(profile="Warm", low_db=2, mids_db=2, presence_db=-1, high_db=-2, dynamics_percent=15, limiter_percent=25),
}


def preset(name: str) -> TxAudioTunerSettings:
    return PRESETS.get(str(name), TxAudioTunerSettings(profile="Eigene"))


class StreamingTxAudioTuner:
    """Vier grobe Sprachbänder plus sanfte Dynamik und Limiter."""

    def __init__(self, settings: TxAudioTunerSettings, *, sample_rate: int = 16000) -> None:
        self.settings = settings.normalized()
        self.sample_rate = int(sample_rate)
        self._lp250 = 0.0
        self._lp1000 = 0.0
        self._lp3000 = 0.0
        self.input_peak = 0.0
        self.output_peak = 0.0
        self.limited_samples = 0
        self._a250 = self._alpha(250.0)
        self._a1000 = self._alpha(1000.0)
        self._a3000 = self._alpha(3000.0)

    def _alpha(self, cutoff: float) -> float:
        return 1.0 - math.exp(-2.0 * math.pi * cutoff / float(self.sample_rate))

    @staticmethod
    def _gain(db: float) -> float:
        return 10.0 ** (float(db) / 20.0)

    def process(self, samples):
        import numpy as np
        x = np.asarray(samples, dtype=np.float32).reshape(-1)
        if not x.size:
            return np.empty(0, dtype=np.float32)
        self.input_peak = max(self.input_peak, float(np.max(np.abs(x))))
        s = self.settings
        gl, gm, gp, gh = map(self._gain, (s.low_db, s.mids_db, s.presence_db, s.high_db))
        out = np.empty_like(x)
        lp250, lp1000, lp3000 = self._lp250, self._lp1000, self._lp3000
        for i, raw in enumerate(x):
            value = float(raw)
            lp250 += self._a250 * (value - lp250)
            lp1000 += self._a1000 * (value - lp1000)
            lp3000 += self._a3000 * (value - lp3000)
            low = lp250
            mids = lp1000 - lp250
            presence = lp3000 - lp1000
            high = value - lp3000
            out[i] = low * gl + mids * gm + presence * gp + high * gh
        self._lp250, self._lp1000, self._lp3000 = lp250, lp1000, lp3000

        # Sanfter Kompressor ab ca. -18 dBFS. Bei 0 % vollständig transparent.
        amount = s.dynamics_percent / 100.0
        if amount > 0.0:
            threshold = 10.0 ** (-18.0 / 20.0)
            ratio = 1.0 + 4.0 * amount
            mag = np.abs(out)
            over = mag > threshold
            if np.any(over):
                compressed = threshold + (mag[over] - threshold) / ratio
                out[over] = np.sign(out[over]) * compressed

        # Einstellbarer Soft-Limiter. 0 % = nur Sicherheits-Clamp.
        limiter = s.limiter_percent / 100.0
        if limiter > 0.0:
            threshold = 0.98 - 0.20 * limiter
            mag = np.abs(out)
            over = mag > threshold
            if np.any(over):
                span = max(1e-6, 1.0 - threshold)
                mag[over] = threshold + span * np.tanh((mag[over] - threshold) / span)
                out = np.sign(out) * mag
                self.limited_samples += int(np.count_nonzero(over))
        out = np.clip(out, -0.98, 0.98).astype(np.float32, copy=False)
        self.output_peak = max(self.output_peak, float(np.max(np.abs(out))))
        return out

    def diagnostics(self) -> dict[str, object]:
        return {
            **self.settings.to_dict(),
            "input_peak_percent": round(self.input_peak * 100.0, 3),
            "output_peak_percent": round(self.output_peak * 100.0, 3),
            "limited_samples": self.limited_samples,
        }
