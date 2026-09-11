from app.services.cccd_ocr_parser import OCRItem, parse_cccd_ocr


def test_find_cccd_and_core_fields():
    items = [
        OCRItem("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"),
        OCRItem("Số / No: 001234567890"),
        OCRItem("Họ và tên / Full name"),
        OCRItem("NGUYEN VAN TEST"),
        OCRItem("Ngày sinh / Date of birth: 15/08/1990"),
        OCRItem("Giới tính / Sex: Nam"),
        OCRItem("Nơi thường trú / Place of residence"),
        OCRItem("Ha Noi, Viet Nam"),
        OCRItem("Ngày cấp: 01/01/2021"),
        OCRItem("Họ tên cha: NGUYEN VAN CHA"),
        OCRItem("Họ tên mẹ: TRAN THI ME"),
        OCRItem("CMND: 123456789"),
    ]
    parsed = parse_cccd_ocr(items)
    assert parsed.personal_id == "001234567890"
    assert parsed.full_name == "Nguyễn Văn Test"
    assert parsed.date_of_birth == "15/08/1990"
    assert parsed.gender == "Nam"
    assert parsed.address == "Ha Noi, Viet Nam"
    assert parsed.issue_date == "01/01/2021"
    assert parsed.father_name == "Nguyễn Văn Cha"
    assert parsed.mother_name == "Trần Thị Me"
    assert parsed.old_id == "123456789"


def test_missing_fields_stay_empty():
    parsed = parse_cccd_ocr([OCRItem("So CCCD 001234567890")])
    assert parsed.personal_id == "001234567890"
    assert parsed.full_name is None
    assert parsed.address is None


def test_unlabeled_name_and_compact_dob():
    items = [
        OCRItem("CĂN CƯỚC CÔNG DÂN"),
        OCRItem("LUU MINH DUC"),
        OCRItem("24101987"),
        OCRItem("Nam"),
    ]
    parsed = parse_cccd_ocr(items)
    assert parsed.full_name == "Lưu Minh Đức"
    assert parsed.date_of_birth == "24/10/1987"
    assert parsed.gender == "Nam"


def test_non_cccd_text():
    parsed = parse_cccd_ocr([OCRItem("Hoa don mua hang"), OCRItem("Tong tien 150000")])
    assert parsed.personal_id is None


def test_name_skips_full_name_label_on_next_line():
    items = [
        OCRItem("Số / No: 001234567890"),
        OCRItem("Họ và tên / Full name:"),
        OCRItem("I Full name"),
        OCRItem("LƯU MINH ĐỨC"),
        OCRItem("Ngày sinh / Date of birth: 24/10/1987"),
    ]
    parsed = parse_cccd_ocr(items)
    assert parsed.full_name == "Lưu Minh Đức"
    assert "Full" not in (parsed.full_name or "")


def test_residence_joins_second_line_when_it_has_province():
    items = [
        OCRItem("001234567890"),
        OCRItem("Nơi thường trú / Place of residence"),
        OCRItem("12A14 - Hh1b - Linh Đàm, Hoàng Liệt, Hoàng Mai"),
        OCRItem("Hà Nội"),
        OCRItem("Có giá trị đến / Date of expiry"),
        OCRItem("01/01/2030"),
    ]
    parsed = parse_cccd_ocr(items)
    assert parsed.address is not None
    assert "Hoàng Mai" in parsed.address
    assert "Hà Nội" in parsed.address
    assert "giá trị" not in parsed.address.lower()


def test_residence_does_not_join_next_guide_line():
    items = [
        OCRItem("001234567890"),
        OCRItem("Nơi thường trú / Place of residence"),
        OCRItem("Hoàng Liệt, Hoàng Mai, Hà Nội"),
        OCRItem("Có giá trị đến / Date of expiry"),
        OCRItem("01/01/2030"),
    ]
    parsed = parse_cccd_ocr(items)
    assert parsed.address == "Hoàng Liệt, Hoàng Mai, Hà Nội"


def test_gender_female_and_dash_date():
    items = [
        OCRItem("001987654321"),
        OCRItem("Họ và tên"),
        OCRItem("TRAN THI TEST"),
        OCRItem("Ngày sinh 01-12-2001"),
        OCRItem("Giới tính Nữ"),
    ]
    parsed = parse_cccd_ocr(items)
    assert parsed.personal_id == "001987654321"
    assert parsed.gender == "Nữ"
    assert parsed.date_of_birth == "01/12/2001"
    assert parsed.full_name == "Trần Thị Test"
