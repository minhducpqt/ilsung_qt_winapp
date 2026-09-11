from app.features.cccd_pairing.services.mrz_parser import looks_like_mrz, parse_mrz


def test_parse_idvnm_personal_id():
    raw = "IDVNM006209003918<<<<<<<<<<<<<<<\n870241M3001015VNM<<<<<<<<<<<4\nNGUYEN<<VAN<TEST<<<<<<<<<<<<"
    parsed = parse_mrz(raw)
    assert parsed.looks_like_mrz
    assert parsed.personal_id == "006209003918"
    assert parsed.full_name
    assert "NGUYEN" in parsed.full_name


def test_not_mrz_without_structure():
    assert not looks_like_mrz("Ho va ten Nguyen Van Test")
    assert parse_mrz("hello world").personal_id is None
