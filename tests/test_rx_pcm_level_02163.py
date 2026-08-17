from carendmr.brandmeister.listen import _format_pcm_level, _pcm_level_dbfs


def test_pcm_level_full_scale_peak_is_zero_dbfs():
    peak_dbfs, rms_dbfs = _pcm_level_dbfs(32767, 32767 * 32767, 1)
    assert abs(peak_dbfs) < 0.01
    assert abs(rms_dbfs) < 0.01


def test_pcm_level_half_scale_is_about_minus_six_dbfs():
    sample = 16384
    peak_dbfs, rms_dbfs = _pcm_level_dbfs(sample, sample * sample, 1)
    assert -6.1 < peak_dbfs < -6.0
    assert -6.1 < rms_dbfs < -6.0


def test_pcm_level_format_contains_required_diagnostics():
    text = _format_pcm_level(
        peak=8192,
        sum_squares=8192 * 8192 * 4,
        count=4,
        source_id=9990,
        stream_id=1,
    )
    assert "Src=9990" in text
    assert "Samples=4" in text
    assert "Peak=8192" in text
    assert "Peak_dBFS=" in text
    assert "RMS_dBFS=" in text
