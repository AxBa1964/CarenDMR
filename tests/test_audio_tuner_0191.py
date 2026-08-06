from carendmr.audio import StreamingTxAudioTuner, TxAudioTunerSettings, tuner_preset


def test_neutral_tuner_preserves_shape_and_range():
    samples = [0.0, 0.1, -0.1, 0.4, -0.4] * 100
    tuner = StreamingTxAudioTuner(TxAudioTunerSettings(), sample_rate=16000)
    out = tuner.process(samples)
    assert len(out) == len(samples)
    assert max(abs(float(v)) for v in out) <= 0.98


def test_dx_preset_is_voice_focused():
    settings = tuner_preset("DX")
    assert settings.low_db < 0
    assert settings.presence_db > 0
    assert settings.dynamics_percent > 0


def test_settings_roundtrip_and_limits():
    settings = TxAudioTunerSettings.from_dict({
        "profile": "Eigene", "low_db": -99, "high_db": 99,
        "dynamics_percent": 200, "limiter_percent": -5,
    })
    assert settings.low_db == -12
    assert settings.high_db == 12
    assert settings.dynamics_percent == 100
    assert settings.limiter_percent == 0
    assert TxAudioTunerSettings.from_dict(settings.to_dict()) == settings
