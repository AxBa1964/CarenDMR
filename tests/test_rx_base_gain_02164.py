from carendmr.audio.pcm_output import BufferedPcmOutput

def test_rx_base_gain_source_contains_fixed_x4():
    import inspect
    source = inspect.getsource(BufferedPcmOutput._callback)
    assert "base_gain = 4.0" in source
    assert "factor = base_gain * user_factor" in source

def test_pcm16_limiter_still_clips():
    assert BufferedPcmOutput._limit_pcm16(40000) == 32767
    assert BufferedPcmOutput._limit_pcm16(-40000) == -32768
    assert BufferedPcmOutput._limit_pcm16(1234) == 1234
