from app.services.vietnamese_names import looks_like_vietnamese_name, normalize_person_name, pick_vietnamese_name


def test_normalize_common_vietnamese_name():
    assert normalize_person_name("LUU MINH DUC") == "Lưu Minh Đức"
    assert normalize_person_name("Lưu Minh Đức") == "Lưu Minh Đức"
    assert normalize_person_name("nguyen van anh") == "Nguyễn Văn Anh"


def test_pick_name_from_ocr_lines():
    lines = [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "CĂN CƯỚC CÔNG DÂN",
        "LUU MINH DUC",
        "24101987",
    ]
    assert pick_vietnamese_name(lines) == "Lưu Minh Đức"
    assert looks_like_vietnamese_name("LUU MINH DUC")
    assert not looks_like_vietnamese_name("CĂN CƯỚC CÔNG DÂN")
