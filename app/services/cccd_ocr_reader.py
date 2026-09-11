from __future__ import annotations

import logging
from pathlib import Path

from app.services.cccd_ocr_parser import OCRItem
from app.services.image_utils import enhance_for_ocr, load_bgr, resize_max_side

logger = logging.getLogger(__name__)

_engine = None


def load_ocr_engine():
    global _engine
    if _engine is not None:
        return _engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        from rapidocr import RapidOCR
    _engine = RapidOCR()
    return _engine


def _run_engine(engine, image) -> list[OCRItem]:
    result, _elapsed = engine(image)
    items: list[OCRItem] = []
    for item in result or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        text = str(item[1]).strip()
        if not text:
            continue
        confidence = float(item[2]) if len(item) > 2 and item[2] is not None else None
        items.append(OCRItem(text=text, confidence=confidence))
    return items


def read_ocr_items(image_path: str | Path, engine=None) -> list[OCRItem]:
    """OCR an image in memory. Tries a light original pass, then enhanced if empty."""
    image = load_bgr(image_path)
    if image is None:
        raise FileNotFoundError(str(image_path))

    ocr = engine or load_ocr_engine()
    working = resize_max_side(image, 1800)
    items = _run_engine(ocr, working)
    if items:
        return items
    enhanced = enhance_for_ocr(working)
    return _run_engine(ocr, enhanced)
