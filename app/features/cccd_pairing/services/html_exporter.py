from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from app.features.cccd_pairing.models import CCCDPersonPairRecord

CARD_CSS_MM = 95
PRINT_MAX_SIDE = 1400
JPEG_QUALITY = 92

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title></title>
  <style>
    @page {{ size: A4 portrait; margin: 10mm 12mm; }}
    body {{ margin: 0; }}
    .person-page {{
      width: 100%;
      box-sizing: border-box;
      break-after: page;
      page-break-after: always;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .person-page:last-child {{ break-after: auto; page-break-after: auto; }}
    .card-block {{ text-align: center; margin: 0 0 10mm 0; }}
    .id-card-image {{
      width: {card_mm}mm;
      height: auto;
      object-fit: contain;
    }}
  </style>
</head>
<body>
{pages}
</body>
</html>
"""


def _encode_image(path: str | None) -> str | None:
    if not path:
        return None
    source = Path(path)
    if not source.exists():
        return None
    from PIL import Image, ImageOps

    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        longest = max(image.size)
        if longest > PRINT_MAX_SIDE:
            scale = PRINT_MAX_SIDE / float(longest)
            image = image.resize((int(image.width * scale), int(image.height * scale)))
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _card_html(crop_path: str | None, fallback_path: str | None) -> str:
    encoded = _encode_image(crop_path) or _encode_image(fallback_path)
    if not encoded:
        return ""
    return f'<div class="card-block"><img class="id-card-image" src="{encoded}"></div>'


def _page_html(person: CCCDPersonPairRecord) -> str:
    if not person.front_file_path and not person.front_crop:
        return ""
    front = _card_html(person.front_crop, person.front_file_path)
    if not front:
        return ""
    back = _card_html(person.back_crop, person.back_file_path)
    return f'<section class="person-page">{front}{back}</section>'


def export_pairing_html(path: str | Path, persons: list[CCCDPersonPairRecord]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pages = []
    for person in persons:
        page = _page_html(person)
        if page:
            pages.append(page)
    destination.write_text(
        HTML_TEMPLATE.format(card_mm=CARD_CSS_MM, pages="\n".join(pages)),
        encoding="utf-8",
    )
    return destination


def html_page_count(html_text: str) -> int:
    return html_text.count('class="person-page"')
