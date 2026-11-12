from datetime import datetime, timezone
from pathlib import Path
import ast

from carendmr.qrz.logbook import build_dmr_adif, QrzLogbookConfig

ROOT = Path(__file__).resolve().parents[1]

def read(rel): return (ROOT / rel).read_text(encoding='utf-8')

def test_adif_contains_required_qrz_fields_and_utc():
    adif = build_dmr_adif(
        callsign='ab2zt', station_callsign='do1dpl',
        qso_at=datetime(2026,8,19,22,15,tzinfo=timezone.utc),
        talkgroup=91, timeslot=2,
    )
    assert '<call:5>AB2ZT' in adif
    assert '<station_callsign:6>DO1DPL' in adif
    assert '<qso_date:8>20260819' in adif
    assert '<time_on:4>2215' in adif
    assert '<band:4>70cm' in adif
    assert '<mode:3>DMR' in adif
    assert 'TG 91 TS2' in adif
    assert '<freq:' not in adif.lower()

def test_insert_does_not_use_replace():
    text = read('carendmr/qrz/logbook.py')
    assert '"ACTION": "INSERT"' in text
    assert '"OPTION"' not in text
    assert 'CarenDMR/{__version__}' in text

def test_logbook_key_is_local_only(tmp_path):
    path=tmp_path/'qrz_logbook.local.json'
    QrzLogbookConfig(True,'SECRET').save(path)
    cfg=QrzLogbookConfig.load(path)
    assert cfg.enabled and cfg.api_key == 'SECRET'
    assert '*.local.json' in read('.gitignore')

def test_gui_requires_manual_confirmation_and_records_logid():
    text=read('carendmr/ui_qt/main_window.py')
    history=read('carendmr/ui_qt/history_widget.py')
    assert 'Bei QRZ loggen' in history
    assert 'QSO bei QRZ.com loggen' in text
    assert 'QMessageBox.question' in text
    assert 'record_qrz_log' in text
    assert 'qrz_logid' in text

def test_settings_have_logbook_activation_and_key():
    text=read('carendmr/ui_qt/settings_dialog.py')
    assert 'QRZ.com Logbook verwenden' in text
    assert 'QRZ.com API Access Key' in text
    assert 'QLineEdit.EchoMode.Password' in text
    assert 'qrz_logbook.local.json' in text

def test_qso_none_path_has_no_recursion_regression():
    text=read('carendmr/ui_qt/main_window.py')
    start=text.index('    def _update_current_qso_status')
    end=text.index('    def _mark_current_station_worked', start)
    method=text[start:end]
    assert 'self._update_current_qso_status(None)' not in method

def test_modified_python_syntax():
    for rel in (
        'carendmr/qrz/logbook.py','carendmr/qrz/__init__.py',
        'carendmr/application/qso_history_service.py',
        'carendmr/ui_qt/settings_dialog.py','carendmr/ui_qt/main_window.py'):
        ast.parse(read(rel))
