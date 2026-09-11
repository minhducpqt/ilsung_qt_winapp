from __future__ import annotations

from pathlib import Path

from app.features.cccd_pairing.models import (
    SOURCE_NONE,
    SOURCE_OCR,
    SOURCE_QR,
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDPairImageResult,
)
from app.features.cccd_pairing.services.ocr_adapter import items_to_text, ocr_image
from app.services.cccd_ocr_parser import parse_cccd_ocr
from app.services.cccd_qr_parser import is_cccd_id, parse_cccd_qr
from app.services.cccd_qr_reader import decode_qr_from_bgr


def _apply_parsed(result: CCCDPairImageResult, parsed) -> None:
    result.personal_id = parsed.personal_id
    result.old_id = getattr(parsed, "old_id", None)
    result.full_name = getattr(parsed, "full_name", None)
    result.date_of_birth = getattr(parsed, "date_of_birth", None)
    result.gender = getattr(parsed, "gender", None)
    result.address = getattr(parsed, "address", None)
    result.issue_date = getattr(parsed, "issue_date", None)
    result.father_name = getattr(parsed, "father_name", None)
    result.mother_name = getattr(parsed, "mother_name", None)


def process_front(
    image,
    engine=None,
    file_path: str | Path | None = None,
    payloads: list[str] | None = None,
    ocr_items=None,
) -> CCCDPairImageResult:
    path = Path(file_path) if file_path else Path("front.jpg")
    result = CCCDPairImageResult(file_name=path.name, file_path=str(path))
    if payloads is None:
        try:
            payloads = decode_qr_from_bgr(image)
        except Exception:
            payloads = []
    for payload in payloads:
        parsed = parse_cccd_qr(payload)
        if parsed and parsed.certain and is_cccd_id(parsed.personal_id):
            _apply_parsed(result, parsed)
            result.qr_raw = parsed.raw_qr
            result.source = SOURCE_QR
            result.recognition_status = STATUS_CERTAIN
            return result

    try:
        items = list(ocr_items) if ocr_items is not None else ocr_image(image, engine=engine)
    except Exception:
        result.source = SOURCE_NONE
        result.recognition_status = STATUS_UNRECOGNIZED
        result.note = "OCR lỗi"
        return result
    result.ocr_text = items_to_text(items)
    parsed = parse_cccd_ocr(items)
    if parsed.personal_id and is_cccd_id(parsed.personal_id):
        _apply_parsed(result, parsed)
        result.source = SOURCE_OCR
        result.recognition_status = STATUS_NEED_REVIEW
        return result
    result.source = SOURCE_OCR if items else SOURCE_NONE
    result.recognition_status = STATUS_UNRECOGNIZED
    result.note = "Không tìm thấy CCCD"
    if parsed.full_name:
        result.full_name = parsed.full_name
    return result
