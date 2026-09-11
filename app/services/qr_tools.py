from __future__ import annotations

from pathlib import Path


def create_qr(text: str, output_path: str | Path) -> Path:
    """Create a QR image from text."""
    import qrcode

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image = qrcode.make(text)
    image.save(str(destination))
    return destination


def find_qrs(image_path: str | Path) -> list[dict[str, object]]:
    """Find and decode QR codes inside a photo. Uses OpenCV QRCodeDetector."""
    import cv2
    import numpy as np

    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(str(image_path))

    detector = cv2.QRCodeDetector()
    found: list[dict[str, object]] = []

    ok, decoded_list, points, _ = detector.detectAndDecodeMulti(image)
    if ok and decoded_list is not None:
        for index, text in enumerate(decoded_list):
            box = None
            if points is not None and index < len(points):
                box = np.array(points[index]).tolist()
            if text:
                found.append({"text": text, "points": box})

    if found:
        return found

    text, points, _ = detector.detectAndDecode(image)
    if text:
        box = points.tolist() if points is not None else None
        found.append({"text": text, "points": box})
    return found


def read_qr(image_path: str | Path) -> str:
    """Return the first decoded QR text, or empty string."""
    results = find_qrs(image_path)
    if not results:
        return ""
    return str(results[0]["text"])
