from __future__ import annotations

from app.services.cccd_ocr_parser import OCRItem
from app.services.cccd_ocr_reader import load_ocr_engine
from app.services.image_utils import enhance_for_ocr, resize_max_side


def ocr_image(image, engine=None) -> list[OCRItem]:
    """OCR a BGR numpy image without writing files. Reuses the shared RapidOCR engine."""
    if image is None:
        return []
    ocr = engine or load_ocr_engine()
    working = resize_max_side(image, 1800)
    items = _run(ocr, working)
    if items:
        return items
    return _run(ocr, enhance_for_ocr(working))


def items_to_text(items: list[OCRItem]) -> str:
    return "\n".join(item.text for item in items)


def _run(engine, image) -> list[OCRItem]:
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
