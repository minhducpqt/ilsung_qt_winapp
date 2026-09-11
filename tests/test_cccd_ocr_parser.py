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
    assert parsed.full_name == "NGUYEN VAN TEST"
    assert parsed.date_of_birth == "15/08/1990"
    assert parsed.gender == "Nam"
    assert parsed.address == "Ha Noi, Viet Nam"
    assert parsed.issue_date == "01/01/2021"
    assert parsed.father_name == "NGUYEN VAN CHA"
    assert parsed.mother_name == "TRAN THI ME"
    assert parsed.old_id == "123456789"


def test_missing_fields_stay_empty():
    parsed = parse_cccd_ocr([OCRItem("So CCCD 001234567890")])
    assert parsed.personal_id == "001234567890"
    assert parsed.full_name is None
    assert parsed.address is None


def test_non_cccd_text():
    parsed = parse_cccd_ocr([OCRItem("Hoa don mua hang"), OCRItem("Tong tien 150000")])
    assert parsed.personal_id is None


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
    assert parsed.full_name == "TRAN THI TEST"
