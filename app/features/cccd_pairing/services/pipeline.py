from __future__ import annotations

import logging
from pathlib import Path

from app.config import user_data_dir
from app.features.cccd_pairing.models import (
    SIDE_BACK,
    SIDE_FRONT,
    SIDE_UNKNOWN,
    CCCDPairImageResult,
)
from app.features.cccd_pairing.services.back_processor import process_back
from app.features.cccd_pairing.services.card_detector import detect_card, prefer_landscape
from app.features.cccd_pairing.services.front_processor import process_front
from app.features.cccd_pairing.services.matcher import build_pairing_result
from app.features.cccd_pairing.services.ocr_adapter import items_to_text
from app.features.cccd_pairing.services.orientation import ensure_print_upright, normalize_orientation
from app.features.cccd_pairing.services.side_classifier import classify_side
from app.services.cccd_ocr_reader import load_ocr_engine
from app.services.image_utils import load_bgr, resize_max_side

logger = logging.getLogger(__name__)


def cache_dir() -> Path:
    path = user_data_dir() / "cccd_pairing_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_working_jpeg(image, dest: Path, max_side: int = 1500, quality: int = 92) -> Path:
    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    working = resize_max_side(image, max_side)
    rgb = working[:, :, ::-1]
    Image.fromarray(rgb).save(dest, format="JPEG", quality=quality, optimize=True)
    return dest


def process_one_image(path: str | Path, engine, known_front_ids: set[str] | None = None) -> CCCDPairImageResult:
    file_path = Path(path)
    logger.info("pairing process %s", file_path.name)
    original = load_bgr(file_path)
    if original is None:
        return CCCDPairImageResult(
            file_name=file_path.name,
            file_path=str(file_path),
            side=SIDE_UNKNOWN,
            note="Không đọc được ảnh",
        )
    crop = detect_card(original)
    working = crop.image if crop.used_crop else original
    try:
        oriented, payloads, texts = normalize_orientation(working, engine)
    except Exception:
        oriented, payloads, texts = prefer_landscape(working), [], []
        if crop.used_crop:
            try:
                oriented, payloads, texts = normalize_orientation(original, engine)
                crop.used_crop = False
                crop.confidence = 0.0
            except Exception:
                pass
    decision = classify_side(oriented, texts=texts, qr_payloads=payloads)
    side_hint = "front" if decision.side == SIDE_FRONT else "back" if decision.side == SIDE_BACK else None
    oriented = ensure_print_upright(oriented, side_hint)

    if decision.side == SIDE_FRONT:
        result = process_front(oriented, engine=engine, file_path=file_path)
        if result.recognition_status != "CERTAIN" and crop.used_crop:
            fallback = process_front(original, engine=engine, file_path=file_path)
            if fallback.personal_id and not result.personal_id:
                result = fallback
    elif decision.side == SIDE_BACK:
        result = process_back(oriented, engine=engine, file_path=file_path, known_front_ids=known_front_ids)
        if not result.personal_id and crop.used_crop:
            fallback = process_back(original, engine=engine, file_path=file_path, known_front_ids=known_front_ids)
            if fallback.personal_id:
                result = fallback
    else:
        front = process_front(oriented, engine=engine, file_path=file_path)
        back = process_back(oriented, engine=engine, file_path=file_path, known_front_ids=known_front_ids, allow_full_ocr=False)
        if front.personal_id and not back.personal_id:
            result = front
            decision.side = SIDE_FRONT
        elif back.personal_id and not front.personal_id:
            result = back
            decision.side = SIDE_BACK
        else:
            result = CCCDPairImageResult(
                file_name=file_path.name,
                file_path=str(file_path),
                side=SIDE_UNKNOWN,
                note="Không xác định mặt",
                ocr_text=items_to_text([]),
            )

    side_hint = "front" if decision.side == SIDE_FRONT else "back" if decision.side == SIDE_BACK else None
    oriented = ensure_print_upright(oriented, side_hint)
    dest = cache_dir() / f"{file_path.stem}_{decision.side.lower()}.jpg"
    try:
        save_working_jpeg(oriented, dest)
        crop_path = str(dest)
    except Exception:
        crop_path = None

    result.side = decision.side
    result.side_confidence = decision.confidence
    result.crop_path = crop_path
    result.crop_confidence = crop.confidence
    if payloads and not result.qr_raw:
        result.qr_raw = payloads[0]
    if texts and not result.ocr_text:
        result.ocr_text = "\n".join(texts)
    return result


def run_pass1(files: list[str], engine=None, should_cancel=None, on_image=None) -> list[CCCDPairImageResult]:
    ocr = engine or load_ocr_engine()
    results: list[CCCDPairImageResult] = []
    for path in files:
        if should_cancel and should_cancel():
            break
        try:
            result = process_one_image(path, ocr)
        except Exception:
            logger.info("pairing file failed")
            result = CCCDPairImageResult(
                file_name=Path(path).name,
                file_path=str(path),
                side=SIDE_UNKNOWN,
                note="Không đọc được ảnh",
            )
        results.append(result)
        if on_image:
            on_image(result, len(results), len(files))
    return results


def run_pass2(images: list[CCCDPairImageResult]):
    return build_pairing_result(images)
