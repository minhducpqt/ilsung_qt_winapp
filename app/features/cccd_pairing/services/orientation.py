from __future__ import annotations

from pathlib import Path

from app.features.cccd_pairing.services.card_detector import prefer_landscape, rotate_image
from app.features.cccd_pairing.services.side_classifier import classify_side
from app.services.vietnamese_names import fold_vi

FRONT_TOP_HINTS = (
    "can cuoc",
    "cong hoa",
    "socialist",
    "viet nam",
    "so dinh danh",
    "full name",
    "ho va ten",
    "ngay sinh",
    "gioi tinh",
)
MRZ_HINTS = ("idvnm", "<<<<<<")


def _box_center(box) -> tuple[float, float] | None:
    if box is None:
        return None
    try:
        points = list(box)
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        return sum(xs) / len(xs), sum(ys) / len(ys)
    except Exception:
        return None


_FACE_CASCADE = None


def _face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is False:
        return None
    if _FACE_CASCADE is None:
        try:
            import cv2

            cascade_path = getattr(cv2.data, "haarcascades", "") + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(cascade_path)
            _FACE_CASCADE = False if cascade.empty() else cascade
        except Exception:
            _FACE_CASCADE = False
    return None if _FACE_CASCADE is False else _FACE_CASCADE


def _face_boxes(image) -> list[tuple[int, int, int, int]]:
    try:
        import cv2

        cascade = _face_cascade()
        if cascade is None:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(36, 36))
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]
    except Exception:
        return []


def _mrz_band_score(image) -> float:
    """+1 if MRZ-like rows (many B/W transitions, e.g. <<<<<) sit at the bottom."""
    import cv2
    import numpy as np

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if float(binary.mean()) < 127:
        binary = 255 - binary
    height, width = binary.shape
    transitions = np.abs(np.diff(binary.astype(np.int16), axis=1)).sum(axis=1) / 255.0
    threshold = max(width * 0.07, 16.0)
    top = transitions[: max(int(height * 0.36), 1)]
    bottom = transitions[int(height * 0.64) :]
    if bottom.size == 0 or top.size == 0:
        return 0.0
    top_frac = float(np.mean(top >= threshold))
    bot_frac = float(np.mean(bottom >= threshold))
    if bot_frac > top_frac + 0.05 or float(bottom.mean()) > float(top.mean()) * 1.4 + 4:
        return 1.0
    if top_frac > bot_frac + 0.05 or float(top.mean()) > float(bottom.mean()) * 1.4 + 4:
        return -1.0
    return 0.0


def _header_bar_score(image) -> float:
    height, width = image.shape[:2]
    top = image[: max(int(height * 0.22), 1)]
    bottom = image[int(height * 0.78) :]
    if top.size == 0 or bottom.size == 0:
        return 0.0
    return float(top.std() - bottom.std()) / 12.0


def _is_mrz_text(text: str, folded: str) -> bool:
    return any(hint in folded or hint in text.lower() for hint in MRZ_HINTS) or text.count("<") >= 6


def _is_header_text(folded: str) -> bool:
    return any(hint in folded for hint in FRONT_TOP_HINTS)


def geometry_score(items, shape: tuple[int, int]) -> float:
    height = max(shape[0], 1)
    score = 0.0
    for item in items or []:
        text = getattr(item, "text", "") or ""
        folded = fold_vi(text)
        center = _box_center(getattr(item, "box", None))
        confidence = float(getattr(item, "confidence", 0) or 0)
        score += 0.35 * confidence
        if center is None:
            continue
        cy = center[1] / height
        if _is_mrz_text(text, folded):
            score += 3.2 if cy > 0.58 else (-3.2 if cy < 0.42 else 0.0)
        if _is_header_text(folded):
            score += 2.4 if cy < 0.42 else (-2.4 if cy > 0.58 else 0.0)
    return score


def upright_vote(image, items=None, side: str | None = None) -> float:
    """Positive = keep current pixels. Negative = rotate 180°."""
    if image is None:
        return 0.0
    height, width = image.shape[:2]
    vote = 0.0
    mrz_from_ocr = 0.0
    mrz_hits = 0

    for item in items or []:
        text = getattr(item, "text", "") or ""
        folded = fold_vi(text)
        center = _box_center(getattr(item, "box", None))
        if center is None:
            continue
        cy = center[1] / max(height, 1)
        if _is_mrz_text(text, folded):
            mrz_hits += 1
            mrz_from_ocr += 1.0 if cy > 0.55 else (-1.0 if cy < 0.45 else 0.0)
        if side != "back" and _is_header_text(folded):
            vote += 2.8 if cy < 0.40 else (-2.8 if cy > 0.60 else 0.0)

    if mrz_hits:
        vote += 4.2 * (mrz_from_ocr / mrz_hits)
    elif side == "back":
        vote += 3.4 * _mrz_band_score(image)
    elif side == "front":
        vote += _header_bar_score(image)
    else:
        vote += 2.2 * _mrz_band_score(image)
        vote += _header_bar_score(image)

    if side != "back" and not mrz_hits:
        faces = _face_boxes(image)
        if faces:
            x, _y, face_w, _h = max(faces, key=lambda item: item[2] * item[3])
            cx = (x + face_w / 2.0) / max(width, 1)
            if cx < 0.40:
                vote += 3.2
            elif cx > 0.60:
                vote -= 3.2
    return float(vote)


def cheap_upright_score(image, side: str | None = None) -> float:
    return upright_vote(image, items=None, side=side)


def apply_upright_correction(image, items=None, side: str | None = None, min_flip_vote: float = -0.8):
    """Rotate 180° only when votes say the card is upside down."""
    if image is None:
        return image
    working = prefer_landscape(image)
    vote = upright_vote(working, items=items, side=side)
    if vote <= min_flip_vote:
        return rotate_image(working, 180)
    return working


def ensure_print_upright(image, side: str | None = None, margin: float = 0.35):
    return apply_upright_correction(image, items=None, side=side, min_flip_vote=-1.6)


def pick_upright_cheap(image):
    base = prefer_landscape(image)
    flipped = rotate_image(base, 180)
    if upright_vote(flipped, side=None) > upright_vote(base, side=None) + 1.2:
        return flipped
    return base


def load_display_bgr(path: str | Path | None, side: str | None = None):
    """Load a saved crop/original for preview or HTML. Flip only on a strong visual vote."""
    if not path:
        return None
    source = Path(path)
    if not source.exists():
        return None
    from app.services.image_utils import load_bgr

    image = load_bgr(source)
    if image is None:
        return None
    return apply_upright_correction(image, items=None, side=side, min_flip_vote=-2.2)


def _read_qr_and_ocr(image, engine):
    from app.features.cccd_pairing.services.ocr_adapter import ocr_image
    from app.services.cccd_qr_reader import decode_qr_from_bgr

    try:
        payloads = decode_qr_from_bgr(image)
    except Exception:
        payloads = []
    try:
        items = ocr_image(image, engine=engine)
    except Exception:
        items = []
    return payloads, items, [item.text for item in items]


def _content_score(image, payloads, items) -> float:
    texts = [item.text for item in items]
    decision = classify_side(image, texts=texts, qr_payloads=payloads)
    score = decision.front_score + decision.back_score
    if payloads:
        score += 2.2
    score += geometry_score(items, image.shape[:2])
    return score


def normalize_orientation(image, engine):
    """One cheap 0/180 guess, one OCR, then flip from MRZ/header/face even if QR already decoded."""
    oriented = pick_upright_cheap(image)
    payloads, items, texts = _read_qr_and_ocr(oriented, engine)
    vote = upright_vote(oriented, items=items, side=None)
    if vote <= -0.8:
        oriented = rotate_image(oriented, 180)
        payloads, items, texts = _read_qr_and_ocr(oriented, engine)
        return oriented, payloads, texts, items
    if vote < 0.8 and _content_score(oriented, payloads, items) < 1.2:
        flipped = rotate_image(oriented, 180)
        alt_payloads, alt_items, alt_texts = _read_qr_and_ocr(flipped, engine)
        if upright_vote(flipped, items=alt_items, side=None) > vote:
            return flipped, alt_payloads, alt_texts, alt_items
    return oriented, payloads, texts, items
