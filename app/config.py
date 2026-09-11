from __future__ import annotations

import sys
from pathlib import Path

COMPANY_NAME = "CÔNG TY CỔ PHẦN IL-SUNG TECH"
COMPANY_SHORT = "IL-SUNG TECH"
APP_NAME = "IL-SUNG Office Tools"
APP_VERSION = "1.0.0"
WINDOW_TITLE = "IL-SUNG Office Tools"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 1040
WINDOW_MIN_HEIGHT = 640

# (group_title, [(page_id, label, status)])
# status: ready = đã có chức năng, soon = đầu mục chuẩn bị
MENU_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    (
        "Tổng quan",
        [
            ("home", "Trang chủ", "ready"),
        ],
    ),
    (
        "Tài liệu & File",
        [
            ("rename_copy", "Đổi tên & copy file", "ready"),
            ("sort_files", "Sắp xếp file theo ngày", "soon"),
            ("file_to_excel", "Xuất danh sách file ra Excel", "soon"),
        ],
    ),
    (
        "Nhận dạng & Số hóa",
        [
            ("ocr_cccd", "Đọc CCCD hàng loạt", "ready"),
            ("qr_find", "Tìm QR trong ảnh", "soon"),
        ],
    ),
    (
        "Excel & Báo cáo",
        [
            ("excel_io", "Đọc / tạo file Excel", "soon"),
            ("excel_merge", "Gộp nhiều sheet", "soon"),
        ],
    ),
    (
        "QR & Mã",
        [
            ("qr_create", "Tạo mã QR", "soon"),
            ("qr_read", "Đọc mã QR từ ảnh", "soon"),
        ],
    ),
    (
        "Hệ thống",
        [
            ("settings", "Cài đặt & môi trường", "ready"),
        ],
    ),
]


def app_base_dir() -> Path:
    """Project root when running from source; bundle root after PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Resolve files in app/resources for both source and frozen builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS) / "app" / "resources"
    else:
        base = Path(__file__).resolve().parent / "resources"
    return base.joinpath(*parts)
