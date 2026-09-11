import numpy as np

from app.features.cccd_pairing.services.card_detector import rotate_image
from app.features.cccd_pairing.services.orientation import (
    cheap_upright_score,
    ensure_print_upright,
    geometry_score,
)
from app.services.cccd_ocr_parser import OCRItem


def _card_with_bottom_band() -> np.ndarray:
    image = np.full((220, 350, 3), 245, dtype=np.uint8)
    image[0:28, :] = (40, 80, 160)
    image[168:210, 16:334] = 15
    for y in (174, 188, 202):
        image[y : y + 3, 20:330] = 230
    return image


def test_back_prefers_mrz_band_at_bottom():
    upright = _card_with_bottom_band()
    flipped = rotate_image(upright, 180)
    assert cheap_upright_score(upright, "back") > cheap_upright_score(flipped, "back")


def test_ensure_print_upright_rotates_upside_down_back():
    from app.features.cccd_pairing.services.orientation import _mrz_band_score

    upright = _card_with_bottom_band()
    flipped = rotate_image(upright, 180)
    assert _mrz_band_score(flipped) < 0
    fixed = ensure_print_upright(flipped, "back")
    assert _mrz_band_score(fixed) > 0
    assert cheap_upright_score(fixed, "back") >= cheap_upright_score(upright, "back") - 0.2


def test_html_encode_rotates_upside_down_back(tmp_path):
    import base64
    from io import BytesIO

    from PIL import Image

    from app.features.cccd_pairing.services.html_exporter import _encode_image

    flipped = rotate_image(_card_with_bottom_band(), 180)
    path = tmp_path / "back.jpg"
    Image.fromarray(flipped[:, :, ::-1]).save(path, format="JPEG", quality=95)
    encoded = _encode_image(str(path), "back")
    assert encoded and encoded.startswith("data:image/jpeg;base64,")
    raw = Image.open(BytesIO(base64.b64decode(encoded.split(",", 1)[1])))
    array = np.array(raw)[:, :, ::-1]
    from app.features.cccd_pairing.services.orientation import _mrz_band_score

    assert _mrz_band_score(array) > 0


def test_mrz_box_at_bottom_scores_higher_than_top():
    good = [OCRItem("IDVNM006209003918<<<<<<<<<<<<<<<", 0.92, box=[[10, 180], [300, 180], [300, 205], [10, 205]])]
    bad = [OCRItem("IDVNM006209003918<<<<<<<<<<<<<<<", 0.92, box=[[10, 12], [300, 12], [300, 36], [10, 36]])]
    assert geometry_score(good, (220, 350)) > geometry_score(bad, (220, 350))
