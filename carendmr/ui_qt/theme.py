"""Zentrale Qt-Theme-Definition für CarenDMR.

Alle sichtbaren Farben, Fokusrahmen und grundlegenden Schriftgrößen werden
hier gepflegt. UI-Module dürfen keine eigenen Hex-Farben enthalten.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QProxyStyle, QStyle


@dataclass(frozen=True)
class ThemeTokens:
    window: str = "#0F141B"
    surface: str = "#18212C"
    surface_alt: str = "#202C3A"
    surface_input: str = "#111A24"
    border: str = "#4C6078"
    border_strong: str = "#6F87A3"
    text: str = "#F7FAFC"
    text_secondary: str = "#D5DEE8"
    text_muted: str = "#B7C4D2"
    disabled_text: str = "#8B99A8"
    primary: str = "#64B5FF"
    primary_strong: str = "#2E90E8"
    focus: str = "#FFD54A"
    success: str = "#59D98E"
    success_bg: str = "#165C3B"
    warning: str = "#FFD166"
    warning_bg: str = "#6E5415"
    danger: str = "#FF6B73"
    danger_bg: str = "#8E3038"
    danger_bg_active: str = "#C8323D"
    selection: str = "#1677C8"
    table_alt: str = "#212D3A"


@dataclass(frozen=True)
class DesignMetrics:
    """Zentrale Maße für ein konsistentes CarenDMR-Design."""

    action_control_height: int = 50
    status_control_height: int = 40
    connection_control_width: int = 150
    button_min_width: int = 118
    card_radius: int = 9
    focus_width: int = 3
    tab_horizontal_padding: int = 22
    tab_vertical_padding: int = 11
    tab_outer_margin: int = 10
    table_row_height: int = 30


TOKENS = ThemeTokens()
METRICS = DesignMetrics()


def build_stylesheet(tokens: ThemeTokens = TOKENS, metrics: DesignMetrics = METRICS) -> str:
    """Erzeugt das anwendungsweite, kontrastreiche Qt-Stylesheet."""
    t = tokens
    m = metrics
    return f"""
        * {{
            color: {t.text};
            font-size: 13px;
        }}
        QMainWindow, QDialog, QWidget {{
            background-color: {t.window};
            color: {t.text};
        }}
        QWidget#operationPage {{ background-color: {t.window}; }}
        QLabel {{
            background: transparent;
            color: {t.text};
        }}
        QLabel#appTitle {{ font-size: 24px; font-weight: 700; color: {t.text}; }}
        QLabel#appSubtitle {{ color: {t.text_secondary}; }}
        QLabel#sectionTitle {{ color: {t.primary}; font-size: 13px; font-weight: 700; letter-spacing: 1px; }}
        QLabel#fieldCaption, QLabel#secondaryText {{ color: {t.text_secondary}; }}
        QLabel#currentTalkgroup {{ color: {t.text}; font-size: 32px; font-weight: 700; }}
        QLabel#callsignDisplay {{ color: {t.text}; font-size: 30px; font-weight: 700; }}
        QLabel#stationName {{ color: {t.text_secondary}; font-size: 17px; }}
        QLabel#channelMeta {{ color: {t.primary}; font-size: 12px; font-weight: 700; }}
        QLabel#compactHint {{ color: {t.text_muted}; font-size: 11px; }}
        QLabel#qsoStatus {{ color: {t.success}; font-weight: 700; }}
        QLabel#fieldValue, QLabel#qsoStatusValue {{
            background-color: {t.surface_input};
            border: 1px solid {t.border};
            border-radius: 5px;
            padding: 5px 8px;
            color: {t.text};
        }}
        QLabel#qsoStatusValue {{
            color: {t.success};
            font-weight: 700;
        }}
        QLabel#tunerValue {{
            background-color: {t.surface_input};
            border: 1px solid {t.border};
            border-radius: 5px;
            padding: 4px 8px;
            color: {t.text};
            font-weight: 700;
        }}
        QLabel#valueLabel {{ color: {t.text}; font-weight: 700; }}
        QLabel#txStatus {{ color: {t.text_secondary}; font-weight: 700; }}
        QLabel#txSeconds {{ color: {t.text}; font-size: 24px; font-weight: 800; min-height: 30px; }}

        QFrame#headerCard, QFrame#card, QGroupBox {{
            background-color: {t.surface};
            border: 1px solid {t.border};
            border-radius: 9px;
        }}
        QGroupBox {{
            margin-top: 12px;
            padding-top: 10px;
            font-weight: 700;
            color: {t.text};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 5px;
            background-color: {t.surface};
            color: {t.text};
        }}

        QPushButton#qrzCompactButton {{
            min-height: 28px;
            max-height: 28px;
            padding: 0 12px;
            font-size: 12px;
            font-weight: 700;
        }}
        QComboBox#favoriteCombo {{
            min-height: 32px;
            padding: 0 10px;
            font-size: 12px;
        }}

        QMenuBar, QMenu {{ background-color: {t.surface}; color: {t.text}; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background-color: {t.surface_alt}; color: {t.text}; }}
        QMenu::separator {{ background: {t.border}; height: 1px; margin: 4px 8px; }}

        QTabWidget::pane {{ border: 1px solid {t.border}; background-color: {t.window}; margin-top: 4px; }}
        QTabBar {{ margin-left: {m.tab_outer_margin}px; }}
        QTabBar::tab {{
            background-color: {t.surface};
            color: {t.text_secondary};
            padding: {m.tab_vertical_padding}px {m.tab_horizontal_padding}px;
            border: 1px solid {t.border};
            min-width: 82px;
            min-height: 20px;
        }}
        QTabBar::tab:selected {{
            background-color: {t.surface_alt};
            color: {t.text};
            border-bottom: 3px solid {t.primary};
        }}
        QTabBar::tab:focus {{
            border: {m.focus_width}px solid {t.focus};
        }}

        QLineEdit, QComboBox, QKeySequenceEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {t.surface_input};
            color: {t.text};
            border: 1px solid {t.border_strong};
            border-radius: 6px;
            padding: 7px 9px;
            selection-background-color: {t.selection};
            selection-color: {t.text};
        }}
        QLineEdit:focus, QComboBox:focus, QKeySequenceEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus {{ border: 3px solid {t.focus}; padding: 5px 7px; }}
        QComboBox QAbstractItemView {{
            background-color: {t.surface};
            color: {t.text};
            selection-background-color: {t.selection};
            selection-color: {t.text};
            border: 1px solid {t.border_strong};
        }}
        QListWidget#talkgroupSearchPopup {{
            background-color: {t.surface};
            color: {t.text};
            border: 2px solid {t.border_strong};
            padding: 2px;
            font-size: 13px;
        }}
        QListWidget#talkgroupSearchPopup::item {{
            min-height: 28px;
            padding: 4px 8px;
            border-bottom: 1px solid {t.border};
        }}
        QListWidget#talkgroupSearchPopup::item:selected {{
            background-color: {t.selection};
            color: {t.text};
        }}

        QRadioButton, QCheckBox {{
            color: {t.text};
            spacing: 8px;
            background: transparent;
            border: 2px solid transparent;
            border-radius: 6px;
            padding: 5px 7px;
        }}
        QRadioButton::indicator, QCheckBox::indicator {{ width: 18px; height: 18px; }}
        QRadioButton::indicator {{
            border: 2px solid {t.border_strong};
            border-radius: 9px;
            background-color: {t.surface_input};
        }}
        QRadioButton::indicator:checked {{
            border: 5px solid {t.primary};
            background-color: {t.text};
        }}
        QCheckBox::indicator {{
            border: 2px solid {t.border_strong};
            border-radius: 4px;
            background-color: {t.surface_input};
        }}
        QCheckBox::indicator:checked {{
            background-color: {t.primary_strong};
            border-color: {t.primary};
        }}
        QRadioButton:focus, QCheckBox:focus {{
            border: {m.focus_width}px solid {t.focus};
            padding: 4px 6px;
            background-color: {t.surface_alt};
        }}

        QPushButton {{
            background-color: {t.surface_alt};
            color: {t.text};
            border: 1px solid {t.border_strong};
            border-radius: 7px;
            padding: 8px 15px;
            min-height: 24px;
            min-width: {m.button_min_width}px;
            font-weight: 700;
        }}
        QPushButton:hover {{ background-color: {t.border}; }}
        QPushButton:pressed {{ background-color: {t.border_strong}; }}
        QPushButton#segmentButton {{
            min-width: 34px;
            min-height: 24px;
            padding: 2px 7px;
            font-size: 11px;
            font-weight: 650;
            background-color: {t.surface_input};
            border-color: {t.border_strong};
        }}
        QPushButton#segmentButton[selected="true"] {{
            background-color: {t.primary_strong};
            border-color: {t.primary};
            color: {t.text};
        }}
        QPushButton:focus {{ border: {m.focus_width}px solid {t.focus}; padding: 6px 13px; }}
        QPushButton:disabled {{ color: {t.disabled_text}; background-color: {t.surface_alt}; border-color: {t.border}; }}
        QPushButton#connectButton {{ background-color: {t.success_bg}; border-color: {t.success}; }}
        QPushButton#connectButton[visualState="disconnect"] {{ background-color: {t.danger_bg}; border-color: {t.danger}; }}
        QPushButton#pttButton {{ background-color: {t.surface_alt}; border-color: {t.border_strong}; font-size: 18px; font-weight: 800; }}
        QPushButton#pttButton[visualState="ready"] {{ background-color: {t.success_bg}; border-color: {t.success}; }}
        QPushButton#pttButton[visualState="pending"] {{ background-color: {t.warning_bg}; border-color: {t.warning}; }}
        QPushButton#pttButton[visualState="tx"] {{ background-color: {t.danger_bg_active}; border-color: #FF9CA1; }}

        QLabel#connectionBadge {{
            background-color: {t.surface_alt};
            color: {t.text};
            border: 1px solid {t.border_strong};
            border-radius: 16px;
            padding: 7px 14px;
            min-width: {m.connection_control_width}px;
            min-height: {m.status_control_height}px;
            font-weight: 700;
        }}
        QLabel#connectionBadge[visualState="connected"] {{ background-color: {t.success_bg}; border-color: {t.success}; color: {t.text}; }}
        QLabel#connectionBadge[visualState="tx"] {{ background-color: {t.danger_bg}; border-color: {t.danger}; color: {t.text}; }}
        QLabel#connectionBadge[visualState="busy"] {{ background-color: {t.warning_bg}; border-color: {t.warning}; color: {t.text}; }}

        QSlider::groove:horizontal {{ height: 8px; background: #344457; border-radius: 4px; }}
        QSlider::sub-page:horizontal {{ background: {t.primary_strong}; border-radius: 4px; }}
        QSlider::handle:horizontal {{ background: {t.text}; border: 2px solid {t.primary}; width: 18px; margin: -7px 0; border-radius: 10px; }}
        QSlider:focus {{ outline: 3px solid {t.focus}; }}

        QTableWidget, QTableView, QListWidget, QListView, QTreeWidget, QTreeView {{
            background-color: {t.surface_input};
            alternate-background-color: {t.table_alt};
            color: {t.text};
            gridline-color: {t.border};
            border: 1px solid {t.border_strong};
            selection-background-color: {t.selection};
            selection-color: {t.text};
        }}
        QTableWidget::item, QTableView::item {{ min-height: {m.table_row_height}px; }}
        QTableWidget#recentStations {{
            background-color: {t.surface_input};
            border: 1px solid {t.border_strong};
            border-radius: 6px;
        }}
        QTableWidget#recentStations::item {{
            padding: 4px 7px;
        }}
        QTableWidget::item:selected, QTableView::item:selected,
        QListWidget::item:selected, QListView::item:selected,
        QTreeWidget::item:selected, QTreeView::item:selected {{
            background-color: {t.selection};
            color: {t.text};
        }}
        QTableWidget:focus, QTableView:focus, QListWidget:focus, QListView:focus,
        QTreeWidget:focus, QTreeView:focus {{ border: 3px solid {t.focus}; }}
        QHeaderView::section {{
            background-color: {t.surface_alt};
            color: {t.text};
            border: 1px solid {t.border};
            padding: 6px;
            font-weight: 700;
        }}
        QTableCornerButton::section {{ background-color: {t.surface_alt}; border: 1px solid {t.border}; }}

        QScrollBar:vertical, QScrollBar:horizontal {{ background: {t.window}; border: none; }}
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{ background: {t.border_strong}; border-radius: 5px; min-height: 24px; min-width: 24px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}

        QDialogButtonBox {{ background: transparent; }}
        QStatusBar#mainStatusBar, QStatusBar {{
            background-color: {t.surface};
            color: {t.text_secondary};
            border-top: 1px solid {t.border};
        }}
        QToolTip {{ background-color: {t.surface_alt}; color: {t.text}; border: 1px solid {t.focus}; padding: 5px; }}
    """



class CarenProxyStyle(QProxyStyle):
    """Unterdrückt native Fokusrechtecke direkt um Beschriftungstexte."""

    def drawPrimitive(self, element, option, painter, widget=None):  # noqa: N802
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            return
        super().drawPrimitive(element, option, painter, widget)

def build_palette(tokens: ThemeTokens = TOKENS) -> QPalette:
    """Setzt auch native/fallback Farben kontrastreich, falls QSS nicht greift."""
    t = tokens
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(t.window))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(t.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(t.surface_input))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(t.table_alt))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(t.surface_alt))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(t.text))
    palette.setColor(QPalette.ColorRole.Text, QColor(t.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(t.surface_alt))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(t.text))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(t.danger))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(t.selection))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(t.text))
    palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, QColor(t.selection))
    palette.setColor(QPalette.ColorGroup.Inactive, QPalette.ColorRole.HighlightedText, QColor(t.text))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(t.disabled_text))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(t.disabled_text))
    return palette


def apply_theme(app: QApplication, *, suppress_native_focus: bool = True) -> None:
    """Wendet Palette, Fokusdarstellung und QSS zentral an.

    Die normale Desktop-Oberfläche unterdrückt das zusätzliche native
    Fokusrechteck. Easy lässt es bewusst aktiv, damit die Plattform ihre
    gewohnte Tastaturfokus-Markierung zusätzlich zeichnen kann.
    """
    if suppress_native_focus and not isinstance(app.style(), CarenProxyStyle):
        app.setStyle(CarenProxyStyle(app.style()))
    app.setPalette(build_palette())
    app.setStyleSheet(build_stylesheet())
