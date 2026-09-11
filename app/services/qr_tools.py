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
    """Find and decode QR codes inside a photo."""
    from app.services.cccd_qr_reader import read_qr_payloads

    return [{"text": text, "points": None} for text in read_qr_payloads(image_path)]


def read_qr(image_path: str | Path) -> str:
    """Return the first decoded QR text, or empty string."""
    results = find_qrs(image_path)
    if not results:
        return ""
    return str(results[0]["text"])
