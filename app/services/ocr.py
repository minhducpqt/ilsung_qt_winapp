from __future__ import annotations

from pathlib import Path

_engine = None


def _load_engine():
    global _engine
    if _engine is not None:
        return _engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        from rapidocr import RapidOCR
    _engine = RapidOCR()
    return _engine


def extract_text(image_path: str | Path) -> str:
    """OCR an image to plain text. Intended for photos such as CCCD."""
    engine = _load_engine()
    result, _elapsed = engine(str(image_path))
    if not result:
        return ""
    lines: list[str] = []
    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            lines.append(str(item[1]))
        else:
            lines.append(str(item))
    return "\n".join(lines).strip()
