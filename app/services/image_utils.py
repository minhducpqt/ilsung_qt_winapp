from __future__ import annotations

from pathlib import Path

import numpy as np


def load_bgr(image_path: str | Path):
    """Load an image as BGR numpy array without writing files. Applies EXIF orientation."""
    from PIL import Image, ImageOps

    try:
        with Image.open(image_path) as image:
            image = ImageOps.exif_transpose(image)
            image = image.convert("RGB")
            array = np.array(image)
    except Exception:
        return None
    return array[:, :, ::-1].copy()


def resize_max_side(image, max_side: int = 1600):
    import cv2

    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_side:
        return image
    scale = max_side / float(longest)
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def enhance_for_ocr(image):
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contrast = cv2.convertScaleAbs(gray, alpha=1.35, beta=8)
    sharpened = cv2.addWeighted(contrast, 1.2, cv2.GaussianBlur(contrast, (0, 0), 1.2), -0.2, 0)
    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
