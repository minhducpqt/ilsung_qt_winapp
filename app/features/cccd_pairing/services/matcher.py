from __future__ import annotations

from collections import defaultdict

from app.features.cccd_pairing.models import (
    DUPLICATE,
    FRONT_ONLY,
    MANUAL_MATCH,
    MATCH_CERTAIN,
    NEED_REVIEW,
    SIDE_BACK,
    SIDE_FRONT,
    SIDE_UNKNOWN,
    SOURCE_MRZ_EXACT,
    SOURCE_OCR,
    STATUS_CERTAIN,
    STATUS_NEED_REVIEW,
    CCCDPairImageResult,
    CCCDPersonPairRecord,
    PairingBatchResult,
    PairingStats,
)
from app.features.cccd_pairing.services.mrz_parser import apply_ocr_confusion, normalize_mrz_text
from app.services.cccd_qr_parser import is_cccd_id


def id_in_text(personal_id: str | None, text: str | None) -> bool:
    if not is_cccd_id(personal_id) or not text:
        return False
    return personal_id in normalize_mrz_text(text)


def fuzzy_id_suggestion(text: str | None, known_ids: set[str]) -> str | None:
    compact = apply_ocr_confusion(text)
    digits = "".join(ch for ch in compact if ch.isdigit())
    best = None
    best_distance = 99
    for item in known_ids:
        if not is_cccd_id(item):
            continue
        for index in range(0, max(len(digits) - 11, 0)):
            window = digits[index : index + 12]
            distance = sum(a != b for a, b in zip(window, item))
            if distance < best_distance:
                best_distance = distance
                best = item
    if best is not None and best_distance <= 1:
        return best
    return None


def _copy_front_fields(person: CCCDPersonPairRecord, front: CCCDPairImageResult) -> None:
    person.personal_id = person.personal_id or front.personal_id
    person.old_id = front.old_id
    person.full_name = front.full_name
    person.date_of_birth = front.date_of_birth
    person.gender = front.gender
    person.address = front.address
    person.issue_date = front.issue_date
    person.father_name = front.father_name
    person.mother_name = front.mother_name
    person.front_file_name = front.file_name
    person.front_file_path = front.file_path
    person.front_crop = front.crop_path
    person.front_recognition_status = front.recognition_status


def _attach_back(person: CCCDPersonPairRecord, back: CCCDPairImageResult) -> None:
    person.back_file_name = back.file_name
    person.back_file_path = back.file_path
    person.back_crop = back.crop_path
    person.back_recognition_status = back.recognition_status
    if not person.personal_id:
        person.personal_id = back.personal_id
    if not person.full_name and back.full_name:
        person.full_name = back.full_name


def draft_batch_from_images(images: list[CCCDPairImageResult], total: int | None = None) -> PairingBatchResult:
    """Pass-1 snapshot: keep extracted content, do not pair front/back yet."""
    fronts = [item for item in images if item.side == SIDE_FRONT]
    backs = [item for item in images if item.side == SIDE_BACK]
    unknowns = [item for item in images if item.side == SIDE_UNKNOWN]
    persons: list[CCCDPersonPairRecord] = []
    for front in fronts:
        person = CCCDPersonPairRecord(match_status=FRONT_ONLY, note=front.note)
        _copy_front_fields(person, front)
        persons.append(person)
    stats = PairingStats(
        total=len(images) if total is None else total,
        processed=len(images),
        front=len(fronts),
        back=len(backs),
        unknown=len(unknowns),
        paired=0,
        front_only=len(persons),
        orphan_back=len(backs),
        duplicate=0,
    )
    return PairingBatchResult(
        images=list(images),
        persons=persons,
        orphan_backs=list(backs),
        unknowns=unknowns,
        stats=stats,
    )


def apply_known_ids_to_backs(backs: list[CCCDPairImageResult], known_ids: set[str]) -> None:
    for back in backs:
        haystack = "\n".join(part for part in (back.mrz_raw, back.ocr_text, back.qr_raw) if part)
        exact = next((item for item in known_ids if id_in_text(item, haystack)), None)
        if exact:
            back.personal_id = exact
            back.source = SOURCE_MRZ_EXACT
            back.recognition_status = STATUS_CERTAIN
            back.suggested_id = None
            if back.note and "Gợi ý" in back.note:
                back.note = None
            continue
        if back.personal_id and back.personal_id in known_ids:
            continue
        suggestion = fuzzy_id_suggestion(haystack, known_ids)
        if suggestion:
            back.suggested_id = suggestion
            back.personal_id = suggestion
            back.source = SOURCE_OCR
            back.recognition_status = STATUS_NEED_REVIEW
            back.note = back.note or "Gợi ý số CCCD (OCR lỗi, cần check lại)"


def build_pairing_result(images: list[CCCDPairImageResult]) -> PairingBatchResult:
    fronts = [item for item in images if item.side == SIDE_FRONT]
    backs = [item for item in images if item.side == SIDE_BACK]
    unknowns = [item for item in images if item.side == SIDE_UNKNOWN]
    known_ids = {item.personal_id for item in fronts if is_cccd_id(item.personal_id)}
    apply_known_ids_to_backs(backs, known_ids)

    fronts_by_id: dict[str, list[CCCDPairImageResult]] = defaultdict(list)
    backs_by_id: dict[str, list[CCCDPairImageResult]] = defaultdict(list)
    fronts_no_id: list[CCCDPairImageResult] = []
    for front in fronts:
        if is_cccd_id(front.personal_id):
            fronts_by_id[front.personal_id].append(front)
        else:
            fronts_no_id.append(front)
    for back in backs:
        if is_cccd_id(back.personal_id):
            backs_by_id[back.personal_id].append(back)

    persons: list[CCCDPersonPairRecord] = []
    used_backs: set[int] = set()
    duplicate_ids: set[str] = set()

    for personal_id, group in fronts_by_id.items():
        back_group = backs_by_id.get(personal_id, [])
        if len(group) > 1 or len(back_group) > 1:
            duplicate_ids.add(personal_id)
            for front in group:
                person = CCCDPersonPairRecord(match_status=DUPLICATE, note="Phát hiện nhiều ảnh cùng CCCD")
                _copy_front_fields(person, front)
                persons.append(person)
            continue
        front = group[0]
        person = CCCDPersonPairRecord()
        _copy_front_fields(person, front)
        if back_group:
            back = back_group[0]
            _attach_back(person, back)
            used_backs.add(id(back))
            if back.recognition_status == STATUS_NEED_REVIEW and back.suggested_id:
                person.match_status = NEED_REVIEW
                person.note = back.note
            else:
                person.match_status = MATCH_CERTAIN
        else:
            person.match_status = FRONT_ONLY
        persons.append(person)

    for front in fronts_no_id:
        person = CCCDPersonPairRecord(match_status=FRONT_ONLY, note=front.note or "Mặt trước chưa đọc được số CCCD")
        _copy_front_fields(person, front)
        persons.append(person)

    orphans = [back for back in backs if id(back) not in used_backs]
    for back in orphans:
        if is_cccd_id(back.personal_id) and back.personal_id in duplicate_ids:
            back.note = back.note or "Phát hiện nhiều ảnh cùng CCCD"

    stats = PairingStats(
        total=len(images),
        processed=len(images),
        front=len(fronts),
        back=len(backs),
        unknown=len(unknowns),
        paired=sum(1 for item in persons if item.match_status in {MATCH_CERTAIN, MANUAL_MATCH}),
        front_only=sum(1 for item in persons if item.match_status == FRONT_ONLY),
        orphan_back=len(orphans),
        duplicate=sum(1 for item in persons if item.match_status == DUPLICATE),
    )
    return PairingBatchResult(
        images=images,
        persons=persons,
        orphan_backs=orphans,
        unknowns=unknowns,
        stats=stats,
    )


def manual_pair(person: CCCDPersonPairRecord, back: CCCDPairImageResult) -> CCCDPersonPairRecord:
    _attach_back(person, back)
    person.match_status = MANUAL_MATCH
    person.user_edited = True
    person.note = "Ghép thủ công"
    return person
