from __future__ import annotations

import logging
from pathlib import Path

from app.services.image_utils import load_bgr, resize_max_side

logger = logging.getLogger(__name__)

_zxing = None
_opencv_detector = None
_aruco_detector = None


def _zxing_mod():
    global _zxing
    if _zxing is False:
        return None
    if _zxing is None:
        try:
            import zxingcpp

            _zxing = zxingcpp
        except ImportError:
            _zxing = False
            return None
    return _zxing


def _opencv_detectors():
    import cv2

    global _opencv_detector, _aruco_detector
    if _opencv_detector is None:
        _opencv_detector = cv2.QRCodeDetector()
        if hasattr(_opencv_detector, "setUseAlignmentMarkers"):
            _opencv_detector.setUseAlignmentMarkers(True)
    if _aruco_detector is None and hasattr(cv2, "QRCodeDetectorAruco"):
        try:
            _aruco_detector = cv2.QRCodeDetectorAruco()
        except Exception:
            _aruco_detector = False
    return _opencv_detector, _aruco_detector if _aruco_detector else None


def _unique(texts) -> list[str]:
    seen: list[str] = []
    for text in texts:
        value = str(text).strip()
        if value and value not in seen:
            seen.append(value)
    return seen


def _decode_zxing(image) -> list[str]:
    zxingcpp = _zxing_mod()
    if zxingcpp is None or image is None:
        return []
    try:
        barcodes = zxingcpp.read_barcodes(
            image,
            formats=zxingcpp.BarcodeFormat.QRCode,
            try_rotate=True,
            try_downscale=True,
            try_invert=True,
        )
    except Exception:
        logger.debug("zxing decode failed", exc_info=True)
        return []
    found: list[str] = []
    for item in barcodes or []:
        text = getattr(item, "text", "") or ""
        if text.strip() and getattr(item, "valid", True):
            found.append(text.strip())
    return _unique(found)


def _decode_opencv_one(detector, image) -> list[str]:
    if detector is None or image is None:
        return []
    found: list[str] = []
    try:
        ok, decoded_list, _points, _ = detector.detectAndDecodeMulti(image)
        if ok and decoded_list is not None:
            found.extend(decoded_list)
    except Exception:
        logger.debug("OpenCV detectAndDecodeMulti failed", exc_info=True)
    if not _unique(found):
        try:
            text, _points, _ = detector.detectAndDecode(image)
            if text:
                found.append(text)
        except Exception:
            logger.debug("OpenCV detectAndDecode failed", exc_info=True)
    if not _unique(found) and hasattr(detector, "detectAndDecodeCurved"):
        try:
            text, _points, _ = detector.detectAndDecodeCurved(image)
            if text:
                found.append(text)
        except Exception:
            logger.debug("OpenCV detectAndDecodeCurved failed", exc_info=True)
    return _unique(found)


def _decode_opencv(image) -> list[str]:
    detector, aruco = _opencv_detectors()
    found = _decode_opencv_one(detector, image)
    if found:
        return found
    return _decode_opencv_one(aruco, image)


def _gray(image):
    import cv2

    if image.ndim == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _upscale(image, target_side: int):
    import cv2

    height, width = image.shape[:2]
    longest = max(height, width)
    if longest >= target_side:
        return image
    scale = target_side / float(longest)
    return cv2.resize(
        image,
        (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_CUBIC,
    )


def _enhance(image):
    import cv2

    return cv2.convertScaleAbs(image, alpha=1.45, beta=12)


def _decode_pass(image) -> list[str]:
    found = _decode_zxing(image)
    if found:
        return found
    return _decode_opencv(image)


def decode_qr_from_bgr(image) -> list[str]:
    """Decode QR texts from a BGR or grayscale numpy image."""
    if image is None:
        return []

    found = _decode_pass(image)
    if found:
        return found

    height, width = image.shape[:2]
    longest = max(height, width)

    # Phone photos of a card are often ~1000-1600px; OpenCV misses those unless upscaled.
    extra = []
    if longest > 2000:
        extra.append(resize_max_side(image, 1600))
    if longest < 1800:
        extra.append(_upscale(image, 1800))
    extra.append(_gray(image))
    extra.append(_enhance(image))

    seen: list[str] = []
    for variant in extra:
        try:
            payloads = _decode_pass(variant)
        except Exception:
            logger.debug("QR decode variant failed", exc_info=True)
            continue
        for payload in payloads:
            if payload not in seen:
                seen.append(payload)
        if seen:
            return seen
    return seen


def read_qr_payloads(image_path: str | Path) -> list[str]:
    """Decode QR payloads from an image. Stops at the first successful variant."""
    image = load_bgr(image_path)
    if image is None:
        raise FileNotFoundError(str(image_path))
    return decode_qr_from_bgr(image)
