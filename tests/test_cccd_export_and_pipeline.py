from pathlib import Path

from app.models.cccd_result import SOURCE_QR, STATUS_CERTAIN, CCCDResult
from app.services.cccd_processor import CCCDProcessor
from app.services.excel_exporter import export_cccd_results
from app.services.qr_tools import create_qr


def test_export_keeps_ids_as_text(tmp_path: Path):
    results = [
        CCCDResult(
            file_name="a.jpg",
            file_path="/tmp/a.jpg",
            personal_id="001234567890",
            old_id="123456789",
            full_name="NGUYEN VAN TEST",
            source=SOURCE_QR,
            status=STATUS_CERTAIN,
        )
    ]
    path = export_cccd_results(tmp_path / "ket_qua_cccd.xlsx", results)
    from openpyxl import load_workbook

    book = load_workbook(path)
    sheet = book.active
    assert sheet["C2"].value == "001234567890"
    assert sheet["C2"].number_format == "@"
    assert sheet["A1"].value == "STT"
    book.close()


def test_processor_reads_valid_qr_as_certain(tmp_path: Path):
    payload = "001234567890|123456789|NGUYEN VAN TEST|15081990|Nam|Ha Noi|01012021"
    image = tmp_path / "sample_qr.png"
    create_qr(payload, image)
    result = CCCDProcessor().process_image(image)
    assert result.status == STATUS_CERTAIN
    assert result.source == SOURCE_QR
    assert result.personal_id == "001234567890"
    assert result.full_name == "NGUYEN VAN TEST"


def test_processor_unrecognized_plain_image(tmp_path: Path):
    from PIL import Image

    image = tmp_path / "blank.png"
    Image.new("RGB", (80, 80), color=(240, 240, 240)).save(image)
    result = CCCDProcessor().process_image(image)
    assert result.status != STATUS_CERTAIN
    assert result.file_name == "blank.png"
