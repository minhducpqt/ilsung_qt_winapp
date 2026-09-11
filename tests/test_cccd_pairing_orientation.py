import numpy as np

from app.features.cccd_pairing.services.card_detector import rotate_image
from app.features.cccd_pairing.services.orientation import (
    apply_upright_correction,
    cheap_upright_score,
    geometry_score,
    upright_vote,
)
from app.services.cccd_ocr_parser import OCRItem


def _card_with_bottom_band() -> np.ndarray:
    image = np.full((220, 350, 3), 245, dtype=np.uint8)
    image[12:90, 30:130] = (70, 70, 70)
    image[165:208, :] = 245
    for x in range(12, 338, 6):
        image[165:208, x : x + 3] = 20
    return image


def test_back_prefers_mrz_band_at_bottom():
    upright = _card_with_bottom_band()
    flipped = rotate_image(upright, 180)
    assert cheap_upright_score(upright, "back") > cheap_upright_score(flipped, "back")


def test_apply_upright_correction_rotates_upside_down_back():
    from app.features.cccd_pairing.services.orientation import _mrz_band_score

    upright = _card_with_bottom_band()
    flipped = rotate_image(upright, 180)
    assert _mrz_band_score(flipped) < 0
    fixed = apply_upright_correction(flipped, side="back")
    assert _mrz_band_score(fixed) > 0
    assert upright_vote(fixed, side="back") > upright_vote(flipped, side="back")


def test_apply_upright_correction_keeps_upright_back():
    from app.features.cccd_pairing.services.orientation import _mrz_band_score

    upright = _card_with_bottom_band()
    kept = apply_upright_correction(upright, side="back")
    assert _mrz_band_score(kept) > 0


def test_mrz_text_at_top_votes_to_flip():
    items = [OCRItem("IDVNM006209003918<<<<<<<<<<<<<<<", 0.92, box=[[10, 12], [300, 12], [300, 36], [10, 36]])]
    image = _card_with_bottom_band()
    flipped_boxes_on_upright = upright_vote(image, items=items, side="back")
    assert flipped_boxes_on_upright < 0


def test_mrz_box_at_bottom_scores_higher_than_top():
    good = [OCRItem("IDVNM006209003918<<<<<<<<<<<<<<<", 0.92, box=[[10, 180], [300, 180], [300, 205], [10, 205]])]
    bad = [OCRItem("IDVNM006209003918<<<<<<<<<<<<<<<", 0.92, box=[[10, 12], [300, 12], [300, 36], [10, 36]])]
    assert geometry_score(good, (220, 350)) > geometry_score(bad, (220, 350))


def test_busy_top_artwork_does_not_flip_upright_back():
    from app.features.cccd_pairing.services.orientation import _mrz_band_score

    upright = _card_with_bottom_band()
    kept = apply_upright_correction(upright, side="back")
    assert _mrz_band_score(kept) > 0
    assert upright_vote(kept, side="back") > 0


def test_html_encode_keeps_already_upright_back(tmp_path):
    import base64
    from io import BytesIO

    from PIL import Image

    from app.features.cccd_pairing.services.html_exporter import _encode_image
    from app.features.cccd_pairing.services.orientation import _mrz_band_score

    upright = _card_with_bottom_band()
    path = tmp_path / "back.jpg"
    Image.fromarray(upright[:, :, ::-1]).save(path, format="JPEG", quality=95)
    encoded = _encode_image(str(path), "back")
    raw = Image.open(BytesIO(base64.b64decode(encoded.split(",", 1)[1])))
    array = np.array(raw)[:, :, ::-1]
    assert _mrz_band_score(array) > 0
