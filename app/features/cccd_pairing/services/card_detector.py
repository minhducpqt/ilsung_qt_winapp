from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.image_utils import resize_max_side

CARD_ASPECT = 85.60 / 53.98
ASPECT_MIN = 1.20
ASPECT_MAX = 2.05
MIN_AREA_RATIO = 0.08
BORDER_RATIO = 0.03
HIGH_CONFIDENCE = 0.55


@dataclass
class CropResult:
    image: np.ndarray
    confidence: float
    used_crop: bool


def _order_points(pts):
    rect = np.zeros((4, 2), dtype=np.float32)
    total = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(total)]
    rect[2] = pts[np.argmax(total)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _aspect(width: float, height: float) -> float:
    if min(width, height) <= 1:
        return 0.0
    return max(width, height) / min(width, height)


def _pad_quad(pts, image_shape, ratio: float = BORDER_RATIO):
    center = pts.mean(axis=0)
    padded = center + (pts - center) * (1.0 + ratio)
    height, width = image_shape[:2]
    padded[:, 0] = np.clip(padded[:, 0], 0, width - 1)
    padded[:, 1] = np.clip(padded[:, 1], 0, height - 1)
    return padded.astype(np.float32)


def _warp(image, pts):
    import cv2

    rect = _order_points(pts)
    width_a = np.linalg.norm(rect[2] - rect[3])
    width_b = np.linalg.norm(rect[1] - rect[0])
    height_a = np.linalg.norm(rect[1] - rect[2])
    height_b = np.linalg.norm(rect[0] - rect[3])
    width = max(int(width_a), int(width_b), 80)
    height = max(int(height_a), int(height_b), 50)
    if _aspect(width, height) < 1.2:
        width, height = max(width, height), min(width, height)
    dest = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(rect, dest)
    return cv2.warpPerspective(image, matrix, (width, height))


def detect_card(image) -> CropResult:
    """Find a CCCD-like quad. Low confidence returns the original image."""
    import cv2

    if image is None:
        raise ValueError("image is required")
    original = image
    height, width = original.shape[:2]
    area = float(width * height)
    working = resize_max_side(original, 1400)
    scale = width / float(working.shape[1])
    gray = cv2.cvtColor(working, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    best_score = 0.0
    for contour in contours:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        contour_area = cv2.contourArea(approx)
        if contour_area / (working.shape[0] * working.shape[1]) < MIN_AREA_RATIO:
            continue
        pts = approx.reshape(4, 2).astype(np.float32)
        ordered = _order_points(pts)
        w = np.linalg.norm(ordered[1] - ordered[0])
        h = np.linalg.norm(ordered[3] - ordered[0])
        ratio = _aspect(w, h)
        if not (ASPECT_MIN <= ratio <= ASPECT_MAX):
            continue
        aspect_score = 1.0 - min(abs(ratio - CARD_ASPECT) / 0.5, 1.0)
        area_score = min(contour_area / (working.shape[0] * working.shape[1] * 0.6), 1.0)
        score = 0.55 * aspect_score + 0.45 * area_score
        if score > best_score:
            best_score = score
            best = ordered * scale

    if best is None or best_score < HIGH_CONFIDENCE:
        return CropResult(image=original, confidence=best_score, used_crop=False)

    padded = _pad_quad(best, original.shape)
    cropped = _warp(original, padded)
    if cropped.size == 0 or min(cropped.shape[:2]) < 40:
        return CropResult(image=original, confidence=best_score, used_crop=False)
    return CropResult(image=cropped, confidence=float(best_score), used_crop=True)


def rotate_image(image, angle: int):
    import cv2

    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def prefer_landscape(image):
    import cv2

    height, width = image.shape[:2]
    if height > width * 1.05:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image
