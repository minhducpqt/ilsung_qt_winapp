from __future__ import annotations

import logging
from pathlib import Path

from app.models.cccd_result import (
    SOURCE_NONE,
    SOURCE_OCR,
    SOURCE_QR,
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    STATUS_UNRECOGNIZED,
    CCCDResult,
)
from app.services.cccd_ocr_parser import parse_cccd_ocr
from app.services.cccd_ocr_reader import load_ocr_engine, read_ocr_items
from app.services.cccd_qr_parser import parse_cccd_qr
from app.services.cccd_qr_reader import read_qr_payloads
from app.services.image_utils import load_bgr

logger = logging.getLogger(__name__)


class CCCDProcessor:
    def __init__(self) -> None:
        self._ocr_engine = None

    def ensure_ocr_ready(self) -> None:
        if self._ocr_engine is None:
            self._ocr_engine = load_ocr_engine()

    def process_image(self, path: str | Path, status=None) -> CCCDResult:
        file_path = Path(path)
        result = CCCDResult(file_name=file_path.name, file_path=str(file_path))
        logger.info("processing %s", file_path.name)

        if load_bgr(file_path) is None:
            result.source = SOURCE_NONE
            result.status = STATUS_UNRECOGNIZED
            result.note = "Không đọc được file ảnh"
            logger.info("RESULT UNRECOGNIZED")
            return result

        try:
            payloads = read_qr_payloads(file_path)
        except Exception:
            logger.info("QR_ERROR")
            payloads = []

        for payload in payloads:
            parsed = parse_cccd_qr(payload)
            if parsed and parsed.certain and parsed.personal_id:
                result.personal_id = parsed.personal_id
                result.old_id = parsed.old_id
                result.full_name = parsed.full_name
                result.date_of_birth = parsed.date_of_birth
                result.gender = parsed.gender
                result.address = parsed.address
                result.issue_date = parsed.issue_date
                result.cancelled_personal_id = parsed.cancelled_personal_id
                result.father_name = parsed.father_name
                result.mother_name = parsed.mother_name
                result.raw_qr = parsed.raw_qr
                result.source = SOURCE_QR
                result.status = STATUS_CERTAIN
                logger.info("QR_VALID")
                logger.info("RESULT CERTAIN")
                return result

        logger.info("OCR_USED")
        if status:
            status(f"Đang OCR {file_path.name}")
        try:
            self.ensure_ocr_ready()
            items = read_ocr_items(file_path, engine=self._ocr_engine)
        except Exception:
            result.source = SOURCE_NONE
            result.status = STATUS_UNRECOGNIZED
            result.note = "OCR lỗi"
            logger.info("RESULT UNRECOGNIZED")
            return result

        parsed_ocr = parse_cccd_ocr(items)
        result.ocr_confidence = parsed_ocr.ocr_confidence
        if parsed_ocr.personal_id:
            result.personal_id = parsed_ocr.personal_id
            result.old_id = parsed_ocr.old_id
            result.full_name = parsed_ocr.full_name
            result.date_of_birth = parsed_ocr.date_of_birth
            result.gender = parsed_ocr.gender
            result.address = parsed_ocr.address
            result.issue_date = parsed_ocr.issue_date
            result.cancelled_personal_id = parsed_ocr.cancelled_personal_id
            result.father_name = parsed_ocr.father_name
            result.mother_name = parsed_ocr.mother_name
            result.source = SOURCE_OCR
            result.status = STATUS_NEED_REVIEW
            logger.info("RESULT NEED_REVIEW")
            return result

        result.source = SOURCE_OCR if items else SOURCE_NONE
        result.status = STATUS_UNRECOGNIZED
        result.note = "Không tìm thấy CCCD"
        logger.info("RESULT UNRECOGNIZED")
        return result
