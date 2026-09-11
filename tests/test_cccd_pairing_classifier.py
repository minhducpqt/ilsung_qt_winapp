from app.features.cccd_pairing.models import SIDE_BACK, SIDE_FRONT, SIDE_UNKNOWN
from app.features.cccd_pairing.services.side_classifier import classify_side


def test_front_keywords():
    decision = classify_side(
        texts=["CĂN CƯỚC CÔNG DÂN", "Họ và tên / Full name", "Số / No.", "Ngày sinh", "Giới tính"]
    )
    assert decision.side == SIDE_FRONT
    assert decision.confidence > 0.4


def test_back_mrz_keywords():
    decision = classify_side(texts=["IDVNM006209003918<<<<<<<<<<<<<<<", "Đặc điểm nhân dạng", "<<<<"])
    assert decision.side == SIDE_BACK
    assert decision.confidence > 0.4


def test_unknown_without_signals():
    decision = classify_side(texts=["hoa don mua hang", "tong tien"])
    assert decision.side == SIDE_UNKNOWN
