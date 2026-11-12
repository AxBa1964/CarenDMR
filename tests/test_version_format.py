import re

from carendmr.version import __version__, get_version


def test_version_has_four_numeric_parts():
    """Ersetzt die früheren, an eine feste Release-Nummer gebundenen Tests."""
    assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", __version__)
    assert get_version() == __version__
