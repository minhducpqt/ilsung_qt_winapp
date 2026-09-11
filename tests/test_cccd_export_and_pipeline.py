from pathlib import Path

from app.models.cccd_result import SOURCE_QR, STATUS_CERTAIN, CCCDResult
from app.services.cccd_processor import CCCDProcessor, analyze_image_path, batch_worker_count
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


def test_batch_worker_count_stays_in_range():
    assert batch_worker_count(0) == 1
    assert batch_worker_count(1) == 1
    assert 2 <= batch_worker_count(20) <= 6


def test_analyze_image_path_is_picklable():
    import pickle

    pickle.dumps(analyze_image_path)


def test_processor_reads_valid_qr_as_certain(tmp_path: Path):
    payload = "001234567890|123456789|NGUYEN VAN TEST|15081990|Nam|Ha Noi|01012021"
    image = tmp_path / "sample_qr.png"
    create_qr(payload, image)
    result = CCCDProcessor().process_image(image)
    assert result.status == STATUS_CERTAIN
    assert result.source == SOURCE_QR
    assert result.personal_id == "001234567890"
    assert result.full_name == "Nguyễn Văn Test"


def test_processor_unrecognized_plain_image(tmp_path: Path):
    from PIL import Image

    image = tmp_path / "blank.png"
    Image.new("RGB", (80, 80), color=(240, 240, 240)).save(image)
    result = CCCDProcessor().process_image(image)
    assert result.status != STATUS_CERTAIN
    assert result.file_name == "blank.png"


def test_processor_reads_qr_on_phone_like_card_photo(tmp_path: Path):
    """OpenCV often misses a clear QR on a resized phone photo of a card."""
    from PIL import Image, ImageDraw

    from app.services.cccd_qr_reader import read_qr_payloads

    payload = "033087003934|145262302|Lưu Minh Đức|24101987|Nam|Hoàng Mai, Hà Nội|10072022"
    qr_path = tmp_path / "qr.png"
    create_qr(payload, qr_path)

    canvas = Image.new("RGB", (3000, 1900), (20, 50, 110))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((180, 220, 2820, 1680), radius=24, fill=(236, 232, 220))
    qr = Image.open(qr_path).convert("RGB").resize((200, 200))
    canvas.paste(qr, (2420, 1340))
    photo = canvas.resize((1280, 810), Image.Resampling.BILINEAR)
    image = tmp_path / "phone_card.jpg"
    photo.save(image, quality=80)

    assert read_qr_payloads(image)
    result = CCCDProcessor().process_image(image)
    assert result.status == STATUS_CERTAIN
    assert result.source == SOURCE_QR
    assert result.personal_id == "033087003934"
    assert result.full_name == "Lưu Minh Đức"
