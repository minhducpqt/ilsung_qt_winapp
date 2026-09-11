from __future__ import annotations

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


def _face_boxes(image) -> list[tuple[int, int, int, int]]:
    try:
        import cv2

        cascade_path = getattr(cv2.data, "haarcascades", "") + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(36, 36))
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]
    except Exception:
        return []


def _face_score(image, side: str | None) -> float:
    faces = _face_boxes(image)
    if not faces:
        return 0.0
    height, width = image.shape[:2]
    score = 2.4 * min(len(faces), 2)
    x, _y, face_w, face_h = max(faces, key=lambda item: item[2] * item[3])
    cx = (x + face_w / 2.0) / max(width, 1)
    if side != "back":
        if cx < 0.42:
            score += 2.8
        elif cx > 0.58:
            score -= 2.8
    return score


def _band_edge_density(gray, y0: int, y1: int) -> float:
    import cv2

    region = gray[max(y0, 0) : max(y1, 1)]
    if region.size == 0:
        return 0.0
    edges = cv2.Canny(region, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 1))
    lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    return float(lines.mean())


def _mrz_band_score(image) -> float:
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height = gray.shape[0]
    top = _band_edge_density(gray, 0, int(height * 0.36))
    bottom = _band_edge_density(gray, int(height * 0.64), height)
    if bottom > top * 1.25 + 0.25:
        return 1.0
    if top > bottom * 1.25 + 0.25:
        return -1.0
    return 0.0


def _header_bar_score(image) -> float:
    """Vietnamese front cards usually have a colored title strip near the top."""
    height, width = image.shape[:2]
    top = image[: max(int(height * 0.22), 1)]
    bottom = image[int(height * 0.78) :]
    if top.size == 0 or bottom.size == 0:
        return 0.0
    return float(top.std() - bottom.std()) / 12.0


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
        is_mrz = any(hint in folded or hint in text.lower() for hint in MRZ_HINTS) or text.count("<") >= 6
        is_header = any(hint in folded for hint in FRONT_TOP_HINTS)
        if is_mrz:
            score += 3.2 if cy > 0.58 else (-3.2 if cy < 0.42 else 0.0)
        if is_header:
            score += 2.4 if cy < 0.42 else (-2.4 if cy > 0.58 else 0.0)
    return score


def cheap_upright_score(image, side: str | None = None) -> float:
    if image is None:
        return 0.0
    score = _face_score(image, side)
    mrz = _mrz_band_score(image)
    if side == "back":
        score += 4.2 * mrz
    elif side == "front":
        score += _header_bar_score(image)
    else:
        score += 2.4 * mrz
        score += _header_bar_score(image)
    height, width = image.shape[:2]
    if width >= height:
        score += 0.3
    return float(score)


def ensure_print_upright(image, side: str | None = None, margin: float = 0.35):
    """Cheap 0/180 correction for print/export. No OCR."""
    if image is None:
        return image
    working = prefer_landscape(image)
    rotated = rotate_image(working, 180)
    needed = 0.9 if side == "front" else margin
    if cheap_upright_score(rotated, side) > cheap_upright_score(working, side) + needed:
        return rotated
    return working


def score_variant(image, engine) -> tuple[float, list[str], list[str]]:
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
    texts = [item.text for item in items]
    decision = classify_side(image, texts=texts, qr_payloads=payloads)
    score = decision.front_score + decision.back_score
    if payloads:
        score += 2.2
    score += geometry_score(items, image.shape[:2])
    score += cheap_upright_score(image, "front" if decision.front_score > decision.back_score else "back" if decision.back_score > decision.front_score else None)
    if image.shape[1] >= image.shape[0]:
        score += 0.4
    return score, payloads, texts


def normalize_orientation(image, engine):
    """Try 0/90/180/270 and keep the most upright landscape card. Always compare 180°."""
    best_image = prefer_landscape(image)
    best_score = -1e9
    best_payloads: list[str] = []
    best_texts: list[str] = []
    for angle in (0, 180, 90, 270):
        variant = prefer_landscape(rotate_image(image, angle))
        score, payloads, texts = score_variant(variant, engine)
        if score > best_score:
            best_score = score
            best_image = variant
            best_payloads = payloads
            best_texts = texts
    return best_image, best_payloads, best_texts
