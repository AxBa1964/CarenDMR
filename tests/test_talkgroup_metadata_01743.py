from carendmr.application.talkgroup_metadata import derive_talkgroup_metadata


def test_german_talkgroup_uses_mcc_metadata():
    metadata = derive_talkgroup_metadata(2623, "Niedersachsen/Bremen")
    assert metadata.country_code == "DE"
    assert metadata.country_name == "Deutschland"
    assert metadata.language == "Deutsch"
    assert metadata.language_source == "mcc"


def test_explicit_language_name_has_priority():
    metadata = derive_talkgroup_metadata(913, "English")
    assert metadata.language == "Englisch"
    assert metadata.language_source == "name"


def test_worldwide_is_marked_international():
    metadata = derive_talkgroup_metadata(91, "World-wide")
    assert metadata.country_code == "WW"
    assert metadata.language == "International/Mehrsprachig"
