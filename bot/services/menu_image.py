from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Palette:
    background: str = "#F4F6FA"
    card: str = "#FFFFFF"
    title: str = "#0D1B2A"
    text: str = "#102A43"
    muted: str = "#6B7280"
    accent: str = "#14532D"
    unavailable: str = "#991B1B"
    border: str = "#E6EAF0"


PALETTE = Palette()
_MENU_RENDER_CACHE: OrderedDict[str, bytes] = OrderedDict()
_MENU_RENDER_CACHE_LIMIT = 96


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[Path] = []
    if bold:
        candidates.extend(
            [
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
            ]
        )
    else:
        candidates.extend(
            [
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
            ]
        )

    for path in candidates:
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue

    return ImageFont.load_default()


def _text_height(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return max(1, bottom - top)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    if not text:
        return []

    words = text.split()
    if not words:
        return [text]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width:
            current = candidate
            continue
        lines.append(current)
        current = word

    lines.append(current)
    return lines


def _format_price(value: object) -> str:
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        return "-"

    if float_value.is_integer():
        return f"{int(float_value)} ₽"
    return f"{float_value:.2f} ₽"


def _menu_cache_key(items: list[dict[str, object]], *, title: str, subtitle: str) -> str:
    normalized_items: list[dict[str, object]] = []
    for item in items:
        try:
            price_value = round(float(item.get("price", 0)), 2)
        except (TypeError, ValueError):
            price_value = 0.0

        normalized_items.append(
            {
                "name": str(item.get("name") or ""),
                "description": str(item.get("description") or ""),
                "price": price_value,
                "available": bool(item.get("available", True)),
            }
        )

    payload = {
        "title": title,
        "subtitle": subtitle,
        "items": normalized_items,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def render_menu_image(
    items: list[dict[str, object]],
    *,
    title: str,
    subtitle: str,
) -> bytes:
    cache_key = _menu_cache_key(items, title=title, subtitle=subtitle)
    cached = _MENU_RENDER_CACHE.get(cache_key)
    if cached is not None:
        _MENU_RENDER_CACHE.move_to_end(cache_key)
        return cached

    width = 1080
    page_margin = 44
    content_padding_x = 36
    content_padding_y = 24
    row_gap = 14
    header_height = 190

    title_font = _load_font(50, bold=True)
    subtitle_font = _load_font(28)
    row_title_font = _load_font(34, bold=True)
    row_desc_font = _load_font(24)
    price_font = _load_font(34, bold=True)
    badge_font = _load_font(22, bold=True)

    draft = Image.new("RGB", (width, 100), color=PALETTE.background)
    draw = ImageDraw.Draw(draft)

    body_width = width - (page_margin * 2)
    row_text_width = body_width - content_padding_x * 2 - 210

    rendered_rows: list[dict[str, object]] = []
    total_rows_height = 0

    for item in items:
        name = str(item.get("name") or "Без названия")
        desc = str(item.get("description") or "").strip()
        available = bool(item.get("available", True))
        price_text = _format_price(item.get("price"))

        name_lines = _wrap_text(draw, name, row_title_font, row_text_width)
        desc_lines = _wrap_text(draw, desc, row_desc_font, row_text_width) if desc else []

        row_height = content_padding_y
        for line in name_lines:
            row_height += _text_height(draw, line, row_title_font) + 6

        if desc_lines:
            row_height += 8
            for line in desc_lines:
                row_height += _text_height(draw, line, row_desc_font) + 4

        if not available:
            row_height += _text_height(draw, "Недоступно", badge_font) + 10

        row_height += content_padding_y

        rendered_rows.append(
            {
                "name_lines": name_lines,
                "desc_lines": desc_lines,
                "available": available,
                "price_text": price_text,
                "height": row_height,
            }
        )

        total_rows_height += row_height + row_gap

    if total_rows_height > 0:
        total_rows_height -= row_gap

    image_height = page_margin + header_height + 24 + total_rows_height + page_margin
    image = Image.new("RGB", (width, max(image_height, 700)), color=PALETTE.background)
    draw = ImageDraw.Draw(image)

    # Header area
    header_box = [page_margin, page_margin, width - page_margin, page_margin + header_height]
    draw.rounded_rectangle(header_box, radius=28, fill=PALETTE.card, outline=PALETTE.border, width=2)
    draw.text(
        (page_margin + 34, page_margin + 34),
        title,
        font=title_font,
        fill=PALETTE.title,
    )
    draw.text(
        (page_margin + 34, page_margin + 110),
        subtitle,
        font=subtitle_font,
        fill=PALETTE.muted,
    )

    y = page_margin + header_height + 24
    for row in rendered_rows:
        row_height = int(row["height"])
        row_box = [page_margin, y, width - page_margin, y + row_height]
        draw.rounded_rectangle(row_box, radius=24, fill=PALETTE.card, outline=PALETTE.border, width=2)

        text_x = page_margin + content_padding_x
        text_y = y + content_padding_y

        for line in row["name_lines"]:
            draw.text((text_x, text_y), line, font=row_title_font, fill=PALETTE.text)
            text_y += _text_height(draw, line, row_title_font) + 6

        if row["desc_lines"]:
            text_y += 6
            for line in row["desc_lines"]:
                draw.text((text_x, text_y), line, font=row_desc_font, fill=PALETTE.muted)
                text_y += _text_height(draw, line, row_desc_font) + 4

        if not bool(row["available"]):
            text_y += 8
            draw.text((text_x, text_y), "Недоступно", font=badge_font, fill=PALETTE.unavailable)

        price_text = str(row["price_text"])
        price_w = draw.textbbox((0, 0), price_text, font=price_font)[2]
        draw.text(
            (width - page_margin - content_padding_x - price_w, y + content_padding_y),
            price_text,
            font=price_font,
            fill=PALETTE.accent,
        )

        y += row_height + row_gap

    output = BytesIO()
    image.save(output, format="JPEG", quality=92, optimize=True)
    image_bytes = output.getvalue()

    _MENU_RENDER_CACHE[cache_key] = image_bytes
    _MENU_RENDER_CACHE.move_to_end(cache_key)
    while len(_MENU_RENDER_CACHE) > _MENU_RENDER_CACHE_LIMIT:
        _MENU_RENDER_CACHE.popitem(last=False)

    return image_bytes


def render_info_image(*, title: str, lines: list[str]) -> bytes:
    width = 1080
    margin = 44

    title_font = _load_font(52, bold=True)
    line_font = _load_font(30)

    draft = Image.new("RGB", (width, 100), color=PALETTE.background)
    draw = ImageDraw.Draw(draft)

    wrapped_lines: list[str] = []
    text_width = width - margin * 2 - 80
    for line in lines:
        wrapped_lines.extend(_wrap_text(draw, line, line_font, text_width))
        wrapped_lines.append("")
    if wrapped_lines and wrapped_lines[-1] == "":
        wrapped_lines.pop()

    height = margin + 180
    for line in wrapped_lines:
        if not line:
            height += 18
            continue
        height += _text_height(draw, line, line_font) + 8
    height += margin

    image = Image.new("RGB", (width, max(height, 700)), color=PALETTE.background)
    draw = ImageDraw.Draw(image)

    card = [margin, margin, width - margin, max(height, 700) - margin]
    draw.rounded_rectangle(card, radius=28, fill=PALETTE.card, outline=PALETTE.border, width=2)

    draw.text((margin + 40, margin + 34), title, font=title_font, fill=PALETTE.title)

    y = margin + 130
    for line in wrapped_lines:
        if not line:
            y += 18
            continue
        draw.text((margin + 40, y), line, font=line_font, fill=PALETTE.text)
        y += _text_height(draw, line, line_font) + 8

    output = BytesIO()
    image.save(output, format="JPEG", quality=92, optimize=True)
    return output.getvalue()
