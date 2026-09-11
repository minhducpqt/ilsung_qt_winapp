from app.services.vietnamese_provinces import contains_province


def test_detects_old_63_provinces():
    assert contains_province("Hà Nội")
    assert contains_province("Thành phố Hồ Chí Minh")
    assert contains_province("TP. HCM")
    assert contains_province("Bà Rịa - Vũng Tàu")
    assert contains_province("Nam Định")
    assert contains_province("Đắk Lắk")


def test_ignores_nationality_or_gender_only():
    assert not contains_province("Việt Nam")
    assert not contains_province("Nam")
    assert not contains_province("Quốc tịch / Nationality")
