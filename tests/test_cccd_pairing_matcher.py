from app.features.cccd_pairing.models import (
    DUPLICATE,
    FRONT_ONLY,
    MANUAL_MATCH,
    MATCH_CERTAIN,
    NEED_REVIEW,
    SIDE_BACK,
    SIDE_FRONT,
    SOURCE_OCR,
    STATUS_NEED_REVIEW,
    CCCDPairImageResult,
)
from app.features.cccd_pairing.services.matcher import (
    build_pairing_result,
    draft_batch_from_images,
    fuzzy_id_suggestion,
    id_in_text,
    manual_pair,
)


def _front(name: str, personal_id: str | None) -> CCCDPairImageResult:
    return CCCDPairImageResult(
        file_name=name,
        file_path=f"/tmp/{name}",
        side=SIDE_FRONT,
        personal_id=personal_id,
        full_name="Nguyễn Văn Test",
    )


def _back(name: str, personal_id: str | None = None, mrz: str | None = None, **kwargs) -> CCCDPairImageResult:
    return CCCDPairImageResult(
        file_name=name,
        file_path=f"/tmp/{name}",
        side=SIDE_BACK,
        personal_id=personal_id,
        mrz_raw=mrz,
        **kwargs,
    )


def test_draft_pass1_does_not_pair():
    front = _front("f.jpg", "006209003918")
    back = _back("b.jpg", personal_id="006209003918", mrz="IDVNM006209003918<<<<<<<<<<<<<<<")
    draft = draft_batch_from_images([front, back])
    assert len(draft.persons) == 1
    assert draft.persons[0].match_status == FRONT_ONLY
    assert draft.persons[0].back_file_name is None
    assert len(draft.orphan_backs) == 1
    assert draft.stats.paired == 0


def test_exact_id_and_mrz_text_match_certain():
    front = _front("f.jpg", "006209003918")
    back = _back("b.jpg", mrz="IDVNM006209003918<<<<<<<<<<<<<<<")
    result = build_pairing_result([front, back])
    assert len(result.persons) == 1
    assert result.persons[0].match_status == MATCH_CERTAIN
    assert result.persons[0].back_file_name == "b.jpg"
    assert id_in_text("006209003918", back.mrz_raw)


def test_fuzzy_ocr_is_need_review_not_certain():
    suggestion = fuzzy_id_suggestion("0062O9003918", {"006209003918"})
    assert suggestion == "006209003918"
    back = _back(
        "b.jpg",
        personal_id="006209003918",
        ocr_text="0062O9003918",
        source=SOURCE_OCR,
        recognition_status=STATUS_NEED_REVIEW,
        suggested_id="006209003918",
        note="Gợi ý số CCCD (OCR lỗi, cần check lại)",
    )
    result = build_pairing_result([_front("f.jpg", "006209003918"), back])
    assert result.persons[0].match_status == NEED_REVIEW
    assert result.persons[0].match_status != MATCH_CERTAIN


def test_front_only_and_orphan_back():
    result = build_pairing_result(
        [
            _front("f.jpg", "001234567890"),
            _back("orphan.jpg", personal_id="009999999999"),
        ]
    )
    assert result.persons[0].match_status == FRONT_ONLY
    assert len(result.orphan_backs) == 1
    assert result.orphan_backs[0].file_name == "orphan.jpg"


def test_duplicate_fronts_not_auto_paired():
    result = build_pairing_result(
        [
            _front("f1.jpg", "001234567890"),
            _front("f2.jpg", "001234567890"),
            _back("b.jpg", personal_id="001234567890"),
        ]
    )
    assert all(person.match_status == DUPLICATE for person in result.persons)
    assert len(result.orphan_backs) == 1


def test_duplicate_backs_not_auto_paired():
    result = build_pairing_result(
        [
            _front("f.jpg", "001234567890"),
            _back("b1.jpg", personal_id="001234567890"),
            _back("b2.jpg", personal_id="001234567890"),
        ]
    )
    assert result.persons[0].match_status == DUPLICATE
    assert result.persons[0].back_file_name is None
    assert len(result.orphan_backs) == 2


def test_manual_pair_is_not_certain():
    person = build_pairing_result([_front("f.jpg", "001234567890")]).persons[0]
    back = _back("b.jpg", personal_id="001234567890")
    manual_pair(person, back)
    assert person.match_status == MANUAL_MATCH
    assert person.match_status != MATCH_CERTAIN
