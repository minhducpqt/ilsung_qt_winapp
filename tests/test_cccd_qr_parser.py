from app.services.cccd_qr_parser import is_cccd_id, parse_cccd_qr


def test_valid_12_digit_id_only():
    parsed = parse_cccd_qr("001234567890")
    assert parsed is not None
    assert parsed.certain
    assert parsed.personal_id == "001234567890"


def test_invalid_11_and_13_digits():
    assert parse_cccd_qr("00123456789") is None
    assert parse_cccd_qr("0012345678901") is None
    assert not is_cccd_id("00123456789")
    assert not is_cccd_id("0012345678901")


def test_unrelated_qr_invalid():
    assert parse_cccd_qr("https://example.com/abc") is None
    assert parse_cccd_qr("HELLO-WORLD") is None


def test_adult_schema():
    raw = "001234567890|123456789|NGUYEN VAN TEST|15081990|Nam|Ha Noi|01012021"
    parsed = parse_cccd_qr(raw)
    assert parsed is not None
    assert parsed.certain
    assert parsed.schema == "adult_v1"
    assert parsed.full_name == "Nguyễn Văn Test"
    assert parsed.date_of_birth == "15/08/1990"
    assert parsed.gender == "Nam"
    assert parsed.address == "Ha Noi"
    assert parsed.issue_date == "01/01/2021"
    assert parsed.old_id == "123456789"


def test_child_schema_with_parents():
    raw = (
        "001234567890||NGUYEN VAN BE|01012018|Nam|Ha Noi|15032024|"
        "01012016|079000000001|NGUYEN VAN CHA|TRAN THI ME"
    )
    parsed = parse_cccd_qr(raw)
    assert parsed is not None
    assert parsed.certain
    assert parsed.father_name == "Nguyễn Văn Cha"
    assert parsed.mother_name == "Trần Thị Me"
    assert parsed.cancelled_personal_id == "079000000001"


def test_empty_optional_fields():
    raw = "001234567890||NGUYEN VAN TEST|01011990|Nữ||01012021"
    parsed = parse_cccd_qr(raw)
    assert parsed is not None
    assert parsed.old_id is None
    assert parsed.address is None
    assert parsed.gender == "Nữ"


def test_typical_seven_field_qr_with_empty_old_id():
    raw = "001087003934||Lưu Minh Đức|24101987|Nam|12A14 - Hh1b - Linh Đàm, Hoàng Liệt, Hoàng Mai, Hà Nội|10072022"
    parsed = parse_cccd_qr(raw)
    assert parsed is not None
    assert parsed.certain
    assert parsed.old_id is None
    assert parsed.full_name == "Lưu Minh Đức"
    assert parsed.date_of_birth == "24/10/1987"
    assert parsed.gender == "Nam"
    assert "Hoàng Mai" in (parsed.address or "")
    assert parsed.issue_date == "10/07/2022"


def test_typical_seven_field_qr_with_old_id():
    raw = "001087003934|145262302|Luu Minh Duc|24101987|Nam|Hoang Mai, Ha Noi|10072022"
    parsed = parse_cccd_qr(raw)
    assert parsed is not None
    assert parsed.certain
    assert parsed.old_id == "145262302"
    assert parsed.full_name == "Lưu Minh Đức"


def test_partial_qr_still_trusted():
    parsed = parse_cccd_qr("001234567890|123456789|Lưu Minh Đức")
    assert parsed is not None
    assert parsed.certain
    assert parsed.full_name == "Lưu Minh Đức"
    assert parsed.old_id == "123456789"


def test_malformed_missing_fields():
    assert parse_cccd_qr("") is None
    assert parse_cccd_qr("   ") is None
    assert parse_cccd_qr(None) is None


def test_qr_payload_with_bom_and_prefix():
    raw = "\ufeffCCCD:001234567890|123456789|Lưu Minh Đức|15081990|Nam|Ha Noi|01012021"
    parsed = parse_cccd_qr(raw)
    assert parsed is not None
    assert parsed.certain
    assert parsed.personal_id == "001234567890"
    assert parsed.full_name == "Lưu Minh Đức"
