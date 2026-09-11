import numpy as np

from app.features.cccd_pairing.services.card_detector import detect_card


def test_detects_light_card_on_dark_background():
    image = np.zeros((600, 900, 3), dtype=np.uint8)
    image[:] = (20, 20, 20)
    image[180:420, 180:720] = (230, 230, 230)
    result = detect_card(image)
    assert result.image is not None
    if result.used_crop:
        height, width = result.image.shape[:2]
        assert width > height
        assert result.confidence >= 0.55


def test_keeps_original_when_no_card():
    image = np.full((200, 200, 3), 40, dtype=np.uint8)
    result = detect_card(image)
    assert result.used_crop is False
    assert result.image.shape[:2] == (200, 200)
