from pathlib import Path
from _ui_sources import main_window_source


def test_main_window_uses_separate_audio_tool_windows():
    source = main_window_source()
    assert 'self.tabs.addTab(self.audio_benchmark_widget, "Audio-Benchmark")' not in source
    assert 'AudioBenchmarkWindow' in source
    assert 'AudioCoachWindow' in source
    assert 'Audio-Benchmark …' in source
    assert 'Audio Coach …' in source


def test_benchmark_widget_no_longer_contains_modulation_comparison():
    source = Path('carendmr/ui_qt/audio_benchmark_widget.py').read_text(encoding='utf-8')
    assert 'Eigene Modulation testen' not in source
    assert 'comparison_table' not in source


def test_audio_coach_owns_modulation_comparison():
    source = Path('carendmr/ui_qt/audio_coach_widget.py').read_text(encoding='utf-8')
    assert 'Eigene Modulation testen' in source
    assert 'ModulationTestTracker' in source
    tracker = Path('carendmr/benchmark/modulation_test.py').read_text(encoding='utf-8')
    assert '04_codec_loopback_8k.wav' in tracker
    assert 'rx_*_parrot_nach_ambe_8k.wav' in tracker
