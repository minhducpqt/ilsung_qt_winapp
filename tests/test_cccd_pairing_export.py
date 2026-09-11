from pathlib import Path

from app.features.cccd_pairing.models import FRONT_ONLY, MATCH_CERTAIN, CCCDPersonPairRecord
from app.features.cccd_pairing.services.excel_exporter import export_pairing_xlsx
from app.features.cccd_pairing.services.html_exporter import export_pairing_html, html_page_count


def _person(personal_id: str, has_back: bool, front: Path | None = None, back: Path | None = None) -> CCCDPersonPairRecord:
    return CCCDPersonPairRecord(
        personal_id=personal_id,
        full_name="Nguyễn Văn Test",
        date_of_birth="15/08/1990",
        gender="Nam",
        address="Hà Nội",
        front_file_name="front.jpg",
        front_file_path=str(front) if front else "/tmp/front.jpg",
        front_crop=str(front) if front else None,
        back_file_name="back.jpg" if has_back else None,
        back_file_path=str(back) if back else None,
        back_crop=str(back) if back else None,
        match_status=MATCH_CERTAIN if has_back else FRONT_ONLY,
        user_edited=True,
    )


def test_xlsx_keeps_ids_as_text_and_edits(tmp_path: Path):
    person = _person("001234567890", has_back=True)
    person.full_name = "Tên đã sửa"
    path = export_pairing_xlsx(tmp_path / "ket_qua_cccd_2_mat.xlsx", [person])
    from openpyxl import load_workbook

    book = load_workbook(path)
    sheet = book.active
    assert sheet.title == "Danh sách CCCD"
    assert sheet["B2"].value == "001234567890"
    assert sheet["B2"].number_format == "@"
    assert sheet["D2"].value == "Tên đã sửa"
    assert sheet["A1"].value == "STT"
    book.close()


def _tiny_jpeg(path: Path) -> Path:
    from PIL import Image

    Image.new("RGB", (120, 76), color=(20, 80, 140)).save(path, format="JPEG", quality=90)
    return path


def test_html_one_page_per_front_person(tmp_path: Path):
    front = _tiny_jpeg(tmp_path / "front.jpg")
    back = _tiny_jpeg(tmp_path / "back.jpg")
    persons = [
        _person("001234567890", True, front, back),
        _person("009999999999", False, front, None),
        CCCDPersonPairRecord(
            personal_id="008888888888",
            back_file_name="only_back.jpg",
            back_file_path=str(back),
            match_status=FRONT_ONLY,
        ),
    ]
    path = export_pairing_html(tmp_path / "in_cccd_2_mat.html", persons)
    text = path.read_text(encoding="utf-8")
    assert html_page_count(text) == 2
    assert "95mm" in text
    assert "size: A4" in text
    assert "id-card-image" in text
    assert "100%" not in text.split(".id-card-image")[1][:80]
    assert text.count("<img ") == 3
    assert "THÔNG TIN" not in text
    assert "Số CCCD" not in text
    assert "Nguyễn" not in text
    assert "Không có ảnh" not in text
    assert "MẶT TRƯỚC" not in text
    assert "MẶT SAU" not in text
    assert persons[2].front_file_path is None
