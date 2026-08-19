"""Separate Fenster für Audio-Benchmark und Audio Coach."""
from __future__ import annotations

from PySide6.QtWidgets import QMainWindow

from carendmr.ui_qt.audio_benchmark_widget import AudioBenchmarkWidget
from carendmr.ui_qt.audio_coach_widget import AudioCoachWidget
from carendmr.ui_qt.audio_lab_widget import AudioLabWidget


class AudioBenchmarkWindow(QMainWindow):
    def __init__(self, service, *, current_target, reconnect_request, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CarenDMR – Audio-Benchmark")
        self.resize(920, 720)
        self.widget = AudioBenchmarkWidget(
            service,
            current_target=current_target,
            reconnect_request=reconnect_request,
            parent=self,
        )
        self.setCentralWidget(self.widget)


class AudioCoachWindow(QMainWindow):
    def __init__(self, service, *, start_modulation_test, cancel_modulation_test=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CarenDMR – Audio Coach")
        self.resize(920, 700)
        self.widget = AudioCoachWidget(
            service,
            start_modulation_test=start_modulation_test,
            cancel_modulation_test=cancel_modulation_test,
            parent=self,
        )
        self.setCentralWidget(self.widget)


class AudioLabWindow(QMainWindow):
    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("CarenDMR – Live-Audiolabor")
        self.resize(1180, 760)
        self.widget = AudioLabWidget(service, parent=self)
        self.setCentralWidget(self.widget)
