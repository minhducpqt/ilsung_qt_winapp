from __future__ import annotations

from pathlib import Path

from app.features.cccd_pairing.models import (
    SOURCE_MRZ,
    SOURCE_MRZ_EXACT,
    SOURCE_NONE,
    SOURCE_OCR,
    SOURCE_QR,
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDPairImageResult,
)
from app.features.cccd_pairing.services.mrz_parser import (
    apply_ocr_confusion,
    extract_digit_candidates,
    looks_like_mrz,
    normalize_mrz_text,
    parse_mrz,
)
from app.features.cccd_pairing.services.ocr_adapter import items_to_text, ocr_image
from app.services.cccd_qr_parser import is_cccd_id, parse_cccd_qr
from app.services.cccd_qr_reader import decode_qr_from_bgr


def _mrz_roi(image):
    height = image.shape[0]
    top = int(height * 0.58)
    return image[top:height, :]


def _exact_known_id(text: str | None, known_ids: set[str]) -> str | None:
    compact = normalize_mrz_text(text)
    if not compact:
        return None
    for item in known_ids:
        if item and item in compact:
            return item
    return None


def _fuzzy_known_id(text: str | None, known_ids: set[str]) -> str | None:
    compact = apply_ocr_confusion(text)
    digits = "".join(ch for ch in compact if ch.isdigit() or ch in "OILBSZoilbsz")
    digits = apply_ocr_confusion(digits)
    for item in known_ids:
        if not item:
            continue
        if item in digits:
            return item
        for index in range(0, max(len(digits) - 11, 0)):
            window = digits[index : index + 12]
            if len(window) != 12:
                continue
            distance = sum(a != b for a, b in zip(window, item))
            if distance <= 1:
                return item
    return None


def process_back(
    image,
    engine=None,
    file_path: str | Path | None = None,
    known_front_ids: set[str] | None = None,
    allow_full_ocr: bool = True,
) -> CCCDPairImageResult:
    path = Path(file_path) if file_path else Path("back.jpg")
    result = CCCDPairImageResult(file_name=path.name, file_path=str(path))
    known = {item for item in (known_front_ids or set()) if is_cccd_id(item)}

    try:
        payloads = decode_qr_from_bgr(image)
    except Exception:
        payloads = []
    for payload in payloads:
        parsed = parse_cccd_qr(payload)
        result.qr_raw = payload
        if parsed and is_cccd_id(parsed.personal_id):
            result.personal_id = parsed.personal_id
            result.source = SOURCE_QR
            result.recognition_status = STATUS_CERTAIN
            if parsed.full_name:
                result.full_name = parsed.full_name
            return result

    mrz_items = []
    try:
        mrz_items = ocr_image(_mrz_roi(image), engine=engine)
    except Exception:
        mrz_items = []
    mrz_text = items_to_text(mrz_items)
    result.mrz_raw = mrz_text or None
    exact = _exact_known_id(mrz_text, known)
    if exact:
        result.personal_id = exact
        result.source = SOURCE_MRZ_EXACT
        result.recognition_status = STATUS_CERTAIN
        return result

    parsed_mrz = parse_mrz(mrz_text)
    if parsed_mrz.personal_id and is_cccd_id(parsed_mrz.personal_id):
        result.personal_id = parsed_mrz.personal_id
        result.source = SOURCE_MRZ
        result.recognition_status = STATUS_CERTAIN if parsed_mrz.looks_like_mrz else STATUS_NEED_REVIEW
        result.full_name = parsed_mrz.full_name
        return result

    if not allow_full_ocr:
        result.recognition_status = STATUS_UNRECOGNIZED
        result.note = "Chưa đọc được số CCCD mặt sau"
        return result

    try:
        items = ocr_image(image, engine=engine)
    except Exception:
        result.source = SOURCE_NONE
        result.recognition_status = STATUS_UNRECOGNIZED
        result.note = "OCR lỗi"
        return result
    full_text = items_to_text(items)
    result.ocr_text = full_text
    if looks_like_mrz(full_text) and not result.mrz_raw:
        result.mrz_raw = full_text
    exact = _exact_known_id(full_text, known) or _exact_known_id(full_text, set(extract_digit_candidates(full_text)))
    if exact and is_cccd_id(exact):
        result.personal_id = exact
        result.source = SOURCE_OCR if exact not in known else SOURCE_MRZ_EXACT
        result.recognition_status = STATUS_CERTAIN if exact in known else STATUS_NEED_REVIEW
        return result
    parsed = parse_mrz(full_text)
    if parsed.personal_id and is_cccd_id(parsed.personal_id):
        result.personal_id = parsed.personal_id
        result.source = SOURCE_OCR
        result.recognition_status = STATUS_NEED_REVIEW
        return result
    fuzzy = _fuzzy_known_id(full_text + "\n" + (mrz_text or ""), known)
    if fuzzy:
        result.suggested_id = fuzzy
        result.personal_id = fuzzy
        result.source = SOURCE_OCR
        result.recognition_status = STATUS_NEED_REVIEW
        result.note = "Gợi ý số CCCD (OCR lỗi, cần check lại)"
        return result
    result.source = SOURCE_OCR if items else SOURCE_NONE
    result.recognition_status = STATUS_UNRECOGNIZED
    result.note = "Không tìm thấy CCCD mặt sau"
    return result
