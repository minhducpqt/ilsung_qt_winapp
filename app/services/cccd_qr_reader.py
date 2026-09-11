from __future__ import annotations

import logging
from pathlib import Path

from app.services.image_utils import load_bgr, resize_max_side

logger = logging.getLogger(__name__)


def _decode_qr_image(image) -> list[str]:
    import cv2

    detector = cv2.QRCodeDetector()
    found: list[str] = []

    ok, decoded_list, _points, _ = detector.detectAndDecodeMulti(image)
    if ok and decoded_list is not None:
        for text in decoded_list:
            if text and str(text).strip():
                found.append(str(text).strip())
    if found:
        return found

    text, _points, _ = detector.detectAndDecode(image)
    if text and str(text).strip():
        found.append(str(text).strip())
    return found


def _variants(image) -> list:
    import cv2

    variants = [image]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variants.append(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))

    resized = resize_max_side(image, 1600)
    if resized is not image:
        variants.append(resized)

    contrast = cv2.convertScaleAbs(image, alpha=1.4, beta=10)
    variants.append(contrast)

    for angle in (90, 180, 270):
        if angle == 90:
            variants.append(cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE))
        elif angle == 180:
            variants.append(cv2.rotate(image, cv2.ROTATE_180))
        else:
            variants.append(cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE))
    return variants


def read_qr_payloads(image_path: str | Path) -> list[str]:
    """Decode QR payloads from an image. Stops at the first successful variant."""
    image = load_bgr(image_path)
    if image is None:
        raise FileNotFoundError(str(image_path))

    seen: list[str] = []
    for variant in _variants(image):
        try:
            payloads = _decode_qr_image(variant)
        except Exception:
            logger.debug("QR decode variant failed", exc_info=True)
            continue
        for payload in payloads:
            if payload not in seen:
                seen.append(payload)
        if seen:
            return seen
    return seen
