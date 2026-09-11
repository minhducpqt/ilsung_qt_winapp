from __future__ import annotations

import re

from app.services.vietnamese_names import fold_vi

# 63 tỉnh thành (trước sáp nhập 2025). Khớp cả tên không dấu / viết tắt thường gặp.
PROVINCES_63 = [
    "Hà Nội",
    "Hà Giang",
    "Cao Bằng",
    "Bắc Kạn",
    "Tuyên Quang",
    "Lào Cai",
    "Điện Biên",
    "Lai Châu",
    "Sơn La",
    "Yên Bái",
    "Hoà Bình",
    "Thái Nguyên",
    "Lạng Sơn",
    "Quảng Ninh",
    "Bắc Giang",
    "Phú Thọ",
    "Vĩnh Phúc",
    "Bắc Ninh",
    "Hải Dương",
    "Hải Phòng",
    "Hưng Yên",
    "Thái Bình",
    "Hà Nam",
    "Nam Định",
    "Ninh Bình",
    "Thanh Hóa",
    "Nghệ An",
    "Hà Tĩnh",
    "Quảng Bình",
    "Quảng Trị",
    "Thừa Thiên Huế",
    "Đà Nẵng",
    "Quảng Nam",
    "Quảng Ngãi",
    "Bình Định",
    "Phú Yên",
    "Khánh Hòa",
    "Ninh Thuận",
    "Bình Thuận",
    "Kon Tum",
    "Gia Lai",
    "Đắk Lắk",
    "Đắk Nông",
    "Lâm Đồng",
    "Bình Phước",
    "Tây Ninh",
    "Bình Dương",
    "Đồng Nai",
    "Bà Rịa - Vũng Tàu",
    "Hồ Chí Minh",
    "Long An",
    "Tiền Giang",
    "Bến Tre",
    "Trà Vinh",
    "Vĩnh Long",
    "Đồng Tháp",
    "An Giang",
    "Kiên Giang",
    "Cần Thơ",
    "Hậu Giang",
    "Sóc Trăng",
    "Bạc Liêu",
    "Cà Mau",
]

PROVINCE_ALIASES = [
    "tp ho chi minh",
    "thanh pho ho chi minh",
    "tp hcm",
    "tphcm",
    "sai gon",
    "ba ria vung tau",
    "ba ria - vung tau",
    "brvt",
    "thua thien hue",
    "tt hue",
    "thanh pho ha noi",
    "tp ha noi",
    "thanh pho hai phong",
    "thanh pho da nang",
    "thanh pho can tho",
    "dak lak",
    "dac lac",
    "dak nong",
    "dac nong",
]


def _fold_key(text: str) -> str:
    folded = re.sub(r"[^a-z0-9]+", " ", fold_vi(text))
    return re.sub(r"\s+", " ", folded).strip()


_PROVINCE_KEYS = sorted(
    {_fold_key(name) for name in PROVINCES_63} | {_fold_key(alias) for alias in PROVINCE_ALIASES},
    key=len,
    reverse=True,
)


def contains_province(text: str | None) -> bool:
    """True if the line mentions one of the 63 provinces/cities."""
    if not text:
        return False
    folded = f" {_fold_key(text)} "
    return any(f" {key} " in folded for key in _PROVINCE_KEYS)
