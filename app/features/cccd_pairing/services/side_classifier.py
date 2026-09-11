from __future__ import annotations

from dataclasses import dataclass

from app.features.cccd_pairing.models import SIDE_BACK, SIDE_FRONT, SIDE_UNKNOWN
from app.features.cccd_pairing.services.mrz_parser import looks_like_mrz
from app.services.vietnamese_names import fold_vi

FRONT_HINTS = (
    "can cuoc cong dan",
    "can cuoc",
    "so dinh danh ca nhan",
    "ho va ten",
    "full name",
    "ngay sinh",
    "gioi tinh",
    "so / no",
    "so/no",
)
BACK_HINTS = (
    "idvnm",
    "dac diem nhan dang",
    "personal identification",
    "ngay cap",
    "date of issue",
    "co gia tri den",
    "date of expiry",
)


@dataclass
class SideDecision:
    side: str
    confidence: float
    front_score: float
    back_score: float


def _count_hints(folded: str, hints: tuple[str, ...]) -> int:
    return sum(1 for hint in hints if hint in folded)


def _face_count(image) -> int:
    try:
        import cv2

        cascade_path = getattr(cv2.data, "haarcascades", "") + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return 0
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
        return len(faces)
    except Exception:
        return 0


def classify_side(image=None, texts: list[str] | None = None, qr_payloads: list[str] | None = None) -> SideDecision:
    blob = " ".join(texts or [])
    folded = fold_vi(blob)
    front = float(_count_hints(folded, FRONT_HINTS))
    back = float(_count_hints(folded, BACK_HINTS))
    if looks_like_mrz(blob):
        back += 4
    if blob.count("<") >= 8:
        back += 2
    if any("|" in item and len(item) > 20 for item in (qr_payloads or [])):
        # QR CCCD thường ở mặt sau mẫu mới, nhưng cũng có trên một số mặt trước.
        back += 1.5
    if image is not None:
        faces = _face_count(image)
        if faces:
            front += 3 + min(faces, 2)
    total = front + back
    if total <= 0:
        return SideDecision(SIDE_UNKNOWN, 0.0, front, back)
    if front >= back + 1.2:
        confidence = min(0.95, 0.45 + front / (total + 1))
        return SideDecision(SIDE_FRONT, confidence, front, back)
    if back >= front + 1.2:
        confidence = min(0.95, 0.45 + back / (total + 1))
        return SideDecision(SIDE_BACK, confidence, front, back)
    return SideDecision(SIDE_UNKNOWN, 0.35, front, back)
