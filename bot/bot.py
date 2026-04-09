from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Literal

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from config import load_settings
from services.api_client import BackendError, InJoyApiClient
from services.menu_image import render_menu_image


class AdminStates(StatesGroup):
    waiting_add_payload = State()
    waiting_edit_payload = State()
    waiting_add_admin_user_id = State()
    waiting_remove_admin_user_id = State()


settings = load_settings()
api_client = InJoyApiClient(
    base_url=settings.backend_base_url,
    api_token=settings.backend_api_token,
)

# Keep one "live" panel message per chat and edit it to avoid message clutter.
panel_message_ids: dict[int, int] = {}
menu_image_file_ids: dict[str, str] = {}
managed_admin_ids: set[int] = set()
pending_admin_notice_ids: set[int] = set()

ActionName = Literal["edit", "delete", "toggle", "viewall"]
BulkActionName = Literal["hideall", "showall", "deleteall"]


def _is_admin_user(user_id: int | None) -> bool:
    return _is_super_admin_user(user_id) or (
        user_id is not None and user_id in managed_admin_ids
    )


def _is_super_admin_user(user_id: int | None) -> bool:
    return user_id is not None and user_id in settings.super_admin_ids


async def _refresh_admin_cache() -> None:
    global managed_admin_ids
    try:
        managed_admin_ids = set(await api_client.list_admin_user_ids())
    except BackendError:
        return


def _keyboard(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=data) for text, data in row]
            for row in rows
        ]
    )


def _category_button_label(category: str) -> str:
    cleaned = re.sub(r"\s+", " ", category.strip())
    if not cleaned:
        return "Uncategorized"

    if len(cleaned) <= 20:
        return cleaned

    midpoint = len(cleaned) // 2
    left_space = cleaned.rfind(" ", 0, midpoint + 1)
    right_space = cleaned.find(" ", midpoint)

    split_pos = -1
    if left_space == -1:
        split_pos = right_space
    elif right_space == -1:
        split_pos = left_space
    else:
        left_distance = midpoint - left_space
        right_distance = right_space - midpoint
        split_pos = left_space if left_distance <= right_distance else right_space

    if split_pos <= 0 or split_pos >= len(cleaned) - 1:
        return cleaned

    return f"{cleaned[:split_pos]}\n{cleaned[split_pos + 1:]}"


def _consume_pending_admin_notice(user_id: int | None) -> str | None:
    if user_id is None:
        return None
    if not _is_admin_user(user_id):
        pending_admin_notice_ids.discard(user_id)
        return None
    if user_id not in pending_admin_notice_ids:
        return None
    pending_admin_notice_ids.discard(user_id)
    return "You have been granted admin access."


def _home_keyboard(*, is_admin: bool) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = [
        [("🍽 Menu", "menu")],
    ]
    if is_admin:
        rows.append([("⚙️ Admin Panel", "admin")])
    return _keyboard(rows)


def _menu_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = [
        [(_category_button_label(category), f"menucat:{idx}")]
        for idx, category in enumerate(categories)
    ]

    rows.append([("🏠 Home", "home")])
    return _keyboard(rows)


def _menu_category_keyboard(category_index: int) -> InlineKeyboardMarkup:
    return _keyboard(
        [
            [("⬅️ Categories", "menu"), ("🔄 Refresh", f"menucat:{category_index}")],
            [("🏠 Home", "home")],
        ]
    )


def _admin_keyboard() -> InlineKeyboardMarkup:
    return _keyboard(
        [
            [("➕ Add Item", "admin:add")],
            [("✏️ Edit Item", "admin:edit")],
            [("👁 Hide / Show", "admin:toggle")],
            [("🗑 Delete Item", "admin:delete")],
            [("🚫 Hide All", "admin:hideall")],
            [("✅ Show All", "admin:showall")],
            [("🧨 Delete Entire Menu", "admin:deleteall")],
            [("👥 Admin Users", "admin:admins")],
            [("📋 View Full Menu", "admin:viewall")],
            [("🏠 Home", "home")],
        ]
    )


def _admin_categories_keyboard(action: ActionName, categories: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = [
        [(_category_button_label(category), f"admin:cat:{action}:{idx}")]
        for idx, category in enumerate(categories)
    ]

    rows.append([("⬅️ Admin Panel", "admin")])
    return _keyboard(rows)


def _admin_items_keyboard(
    action: ActionName,
    category_index: int,
    items: list[dict[str, object]],
) -> InlineKeyboardMarkup:
    rows: list[list[tuple[str, str]]] = []

    for item in items:
        item_id = int(item.get("id", 0))
        available = bool(item.get("available", True))
        icon = "🟢" if available else "⚪️"
        name = str(item.get("name") or "Untitled")
        short_name = name if len(name) <= 56 else f"{name[:53]}..."
        label = f"{icon} #{item_id} {short_name}"
        rows.append([(label, f"admin:item:{action}:{item_id}:{category_index}")])

    rows.append(
        [
            ("⬅️ Categories", f"admin:{action}"),
            ("⚙️ Admin", "admin"),
        ]
    )
    return _keyboard(rows)


def _cancel_input_keyboard() -> InlineKeyboardMarkup:
    return _keyboard([[("⬅️ Cancel", "admin:cancel")]])


def _confirm_bulk_keyboard(action: BulkActionName) -> InlineKeyboardMarkup:
    return _keyboard(
        [
            [("✅ Confirm", f"admin:confirm:{action}")],
            [("⬅️ Back to Admin Panel", "admin")],
        ]
    )


def _format_price(value: object) -> str:
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        return "-"
    if as_float.is_integer():
        return str(int(as_float))
    return f"{as_float:.2f}"


def _parse_admin_payload(text: str) -> tuple[str, float, str, str]:
    parts = [part.strip() for part in text.split("|")]
    if len(parts) < 3:
        raise ValueError(
            "Format: Name | Price | Category | Description (optional)"
        )

    name = parts[0]
    if not name:
        raise ValueError("Name cannot be empty.")

    try:
        price = float(parts[1].replace(",", "."))
    except ValueError as exc:
        raise ValueError("Price must be a number.") from exc

    category = parts[2] or "Other"
    description = parts[3] if len(parts) > 3 else ""
    return name, price, category, description


def _parse_user_id_payload(text: str) -> int:
    value = (text or "").strip()
    if not value:
        raise ValueError("Please send a numeric Telegram user_id.")
    try:
        user_id = int(value)
    except ValueError as exc:
        raise ValueError("Telegram user_id must be a number.") from exc
    if user_id <= 0:
        raise ValueError("Telegram user_id must be a positive number.")
    return user_id


def _format_id_list(ids: list[int]) -> str:
    if not ids:
        return "none"
    limit = 15
    preview = ", ".join(str(item) for item in ids[:limit])
    if len(ids) > limit:
        return f"{preview} ... (+{len(ids) - limit})"
    return preview


async def _safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        return


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        return


def _build_panel_text(title: str, lines: list[str]) -> str:
    if not lines:
        return title
    return f"{title}\n\n" + "\n".join(lines)


def _extract_photo_file_id(message: Message | bool) -> str | None:
    if isinstance(message, Message) and message.photo:
        return message.photo[-1].file_id
    return None


async def _update_text_panel(
    bot: Bot,
    *,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    preferred_message_id: int | None = None,
) -> int:
    old_message_id = panel_message_ids.get(chat_id)
    target_message_id = preferred_message_id or old_message_id

    if target_message_id is not None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=target_message_id,
                text=text,
                reply_markup=reply_markup,
            )
            panel_message_ids[chat_id] = target_message_id
            return target_message_id
        except TelegramBadRequest:
            pass

    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    panel_message_ids[chat_id] = sent.message_id

    if old_message_id is not None and old_message_id != sent.message_id:
        await _safe_delete_message(bot, chat_id, old_message_id)

    return sent.message_id


async def _update_menu_panel(
    bot: Bot,
    *,
    chat_id: int,
    image_bytes: bytes,
    caption: str,
    reply_markup: InlineKeyboardMarkup,
    preferred_message_id: int | None = None,
) -> int:
    old_message_id = panel_message_ids.get(chat_id)
    target_message_id = preferred_message_id or old_message_id

    image_hash = hashlib.sha256(image_bytes).hexdigest()
    cached_file_id = menu_image_file_ids.get(image_hash)
    filename = f"menu-{image_hash[:12]}.jpg"

    async def _try_edit(*, use_cached: bool) -> bool:
        nonlocal cached_file_id
        media_source: str | BufferedInputFile
        if use_cached and cached_file_id:
            media_source = cached_file_id
        else:
            media_source = BufferedInputFile(image_bytes, filename=filename)

        try:
            updated_message = await bot.edit_message_media(
                chat_id=chat_id,
                message_id=target_message_id,
                media=InputMediaPhoto(media=media_source, caption=caption),
                reply_markup=reply_markup,
            )
            updated_file_id = _extract_photo_file_id(updated_message)
            if updated_file_id:
                menu_image_file_ids[image_hash] = updated_file_id
            return True
        except TelegramBadRequest:
            if use_cached and cached_file_id:
                menu_image_file_ids.pop(image_hash, None)
                cached_file_id = None
            return False

    if target_message_id is not None:
        if cached_file_id and await _try_edit(use_cached=True):
            panel_message_ids[chat_id] = target_message_id
            return target_message_id

        if await _try_edit(use_cached=False):
            panel_message_ids[chat_id] = target_message_id
            return target_message_id

    photo_source: str | BufferedInputFile = (
        cached_file_id if cached_file_id else BufferedInputFile(image_bytes, filename=filename)
    )
    try:
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=photo_source,
            caption=caption,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest:
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=BufferedInputFile(image_bytes, filename=filename),
            caption=caption,
            reply_markup=reply_markup,
        )

    if sent.photo:
        menu_image_file_ids[image_hash] = sent.photo[-1].file_id

    panel_message_ids[chat_id] = sent.message_id
    if old_message_id is not None and old_message_id != sent.message_id:
        await _safe_delete_message(bot, chat_id, old_message_id)

    return sent.message_id


async def _fetch_menu(*, include_unavailable: bool) -> list[dict[str, object]]:
    return await api_client.list_menu(only_available=not include_unavailable)


def _categories_from_items(items: list[dict[str, object]]) -> list[str]:
    categories = {str(item.get("category") or "Other") for item in items}
    return sorted(categories)


async def _show_home(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int | None,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    lines = [
        "Choose an action using the buttons below.",
        "Commands are no longer required for normal use.",
    ]
    if notice:
        lines.extend(["", f"{notice}"])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Main Menu", lines),
        reply_markup=_home_keyboard(is_admin=_is_admin_user(user_id)),
        preferred_message_id=preferred_message_id,
    )


async def _show_menu_categories(
    bot: Bot,
    *,
    chat_id: int,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    items = await _fetch_menu(include_unavailable=False)
    categories = _categories_from_items(items)

    if not categories:
        lines = ["There are currently no available menu items."]
        if notice:
            lines.extend(["", notice])
        await _update_text_panel(
            bot,
            chat_id=chat_id,
            text=_build_panel_text("Menu Is Temporarily Empty", lines),
            reply_markup=_keyboard([[("🏠 Home", "home")]]),
            preferred_message_id=preferred_message_id,
        )
        return

    lines = ["Choose a drinks/food category."]
    if notice:
        lines.extend(["", notice])
    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("InJoy Menu", lines),
        reply_markup=_menu_categories_keyboard(categories),
        preferred_message_id=preferred_message_id,
    )


async def _show_menu_category(
    bot: Bot,
    *,
    chat_id: int,
    category_index: int,
    include_unavailable: bool,
    preferred_message_id: int | None,
    back_to_admin: bool,
    notice: str | None = None,
) -> None:
    items = await _fetch_menu(include_unavailable=include_unavailable)
    categories = _categories_from_items(items)

    if category_index < 0 or category_index >= len(categories):
        if back_to_admin:
            await _show_admin_category_picker(
                bot,
                chat_id=chat_id,
                action="viewall",
                preferred_message_id=preferred_message_id,
                notice="This category no longer exists.",
            )
        else:
            await _show_menu_categories(
                bot,
                chat_id=chat_id,
                preferred_message_id=preferred_message_id,
                notice="This category no longer exists.",
            )
        return

    category = categories[category_index]
    category_items = [item for item in items if str(item.get("category") or "Other") == category]

    subtitle_parts = [f"{len(category_items)} items"]
    subtitle_parts.append("all" if include_unavailable else "available only")
    subtitle = " • ".join(subtitle_parts)

    image = render_menu_image(
        category_items,
        title=category,
        subtitle=subtitle,
    )

    if back_to_admin:
        keyboard = _keyboard(
            [
                [("⬅️ Categories", "admin:viewall"), ("⚙️ Admin", "admin")],
                [("🏠 Home", "home")],
            ]
        )
    else:
        keyboard = _menu_category_keyboard(category_index)

    caption = f"{category}"
    if notice:
        caption = f"{category}\n{notice}"

    await _update_menu_panel(
        bot,
        chat_id=chat_id,
        image_bytes=image,
        caption=caption,
        reply_markup=keyboard,
        preferred_message_id=preferred_message_id,
    )


async def _show_admin_dashboard(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int | None,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    if not _is_admin_user(user_id):
        await _show_home(
            bot,
            chat_id=chat_id,
            user_id=user_id,
            preferred_message_id=preferred_message_id,
            notice="You do not have access to the admin panel.",
        )
        return

    lines = [
        "Manage the InJoy menu from here.",
        "Add, edit, delete, and toggle availability in one tap.",
        "Bulk actions are available: hide all, show all, delete all.",
    ]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Admin Panel", lines),
        reply_markup=_admin_keyboard(),
        preferred_message_id=preferred_message_id,
    )


async def _show_admin_users_panel(
    bot: Bot,
    *,
    chat_id: int,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    await _refresh_admin_cache()
    super_admin_ids = sorted(settings.super_admin_ids)
    regular_admin_ids = sorted(
        user_id for user_id in managed_admin_ids if user_id not in settings.super_admin_ids
    )

    lines = [
        f"Main admins: {_format_id_list(super_admin_ids)}",
        f"Regular admins: {_format_id_list(regular_admin_ids)}",
        "Only main admins can add/remove regular admins.",
    ]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Admin Management", lines),
        reply_markup=_keyboard(
            [
                [("➕ Add Admin", "admin:admins:add")],
                [("➖ Remove Admin", "admin:admins:remove")],
                [("⬅️ Admin Panel", "admin")],
            ]
        ),
        preferred_message_id=preferred_message_id,
    )


async def _show_admin_category_picker(
    bot: Bot,
    *,
    chat_id: int,
    action: ActionName,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    items = await _fetch_menu(include_unavailable=True)
    categories = _categories_from_items(items)

    if not categories:
        await _update_text_panel(
            bot,
            chat_id=chat_id,
            text=_build_panel_text("Admin Panel", ["There are no menu items yet."]),
            reply_markup=_admin_keyboard(),
            preferred_message_id=preferred_message_id,
        )
        return

    action_title = {
        "edit": "Edit",
        "delete": "Delete",
        "toggle": "Hide / Show",
        "viewall": "View Full Menu",
    }[action]

    lines = ["Choose a category for the next step."]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text(action_title, lines),
        reply_markup=_admin_categories_keyboard(action, categories),
        preferred_message_id=preferred_message_id,
    )


async def _show_admin_items_picker(
    bot: Bot,
    *,
    chat_id: int,
    action: ActionName,
    category_index: int,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    items = await _fetch_menu(include_unavailable=True)
    categories = _categories_from_items(items)
    if category_index < 0 or category_index >= len(categories):
        await _show_admin_category_picker(
            bot,
                chat_id=chat_id,
                action=action,
                preferred_message_id=preferred_message_id,
                notice="Category not found.",
            )
        return

    category = categories[category_index]
    category_items = [item for item in items if str(item.get("category") or "Other") == category]

    if not category_items:
        await _show_admin_category_picker(
            bot,
                chat_id=chat_id,
                action=action,
                preferred_message_id=preferred_message_id,
                notice="There are no items in this category yet.",
            )
        return

    action_title = {
        "edit": "Choose an item to edit",
        "delete": "Choose an item to delete",
        "toggle": "Choose an item to hide/show",
        "viewall": "Choose a category to preview",
    }[action]

    lines = [f"Category: {category}", f"Items: {len(category_items)}"]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text(action_title, lines),
        reply_markup=_admin_items_keyboard(action, category_index, category_items),
        preferred_message_id=preferred_message_id,
    )


async def _prompt_add_form(
    bot: Bot,
    *,
    chat_id: int,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    lines = [
        "Send data in one message:",
        "Name | Price | Category | Description (optional)",
        "Example: Halva Latte | 249 | Signature Drinks | Latte with halva syrup",
    ]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Add Item", lines),
        reply_markup=_cancel_input_keyboard(),
        preferred_message_id=preferred_message_id,
    )


async def _prompt_edit_form(
    bot: Bot,
    *,
    chat_id: int,
    item: dict[str, object],
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    lines = [
        f"Current ID: #{item.get('id')}",
        f"Current: {item.get('name')} | {_format_price(item.get('price'))} | {item.get('category')}",
        "Send updated data in one message:",
        "Name | Price | Category | Description (optional)",
    ]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Edit Item", lines),
        reply_markup=_cancel_input_keyboard(),
        preferred_message_id=preferred_message_id,
    )


async def _prompt_add_admin_user_form(
    bot: Bot,
    *,
    chat_id: int,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    lines = [
        "Send the new admin's Telegram user_id as a single number.",
        "Example: 821709304",
    ]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Add Admin", lines),
        reply_markup=_cancel_input_keyboard(),
        preferred_message_id=preferred_message_id,
    )


async def _prompt_remove_admin_user_form(
    bot: Bot,
    *,
    chat_id: int,
    preferred_message_id: int | None = None,
    notice: str | None = None,
) -> None:
    lines = [
        "Send the Telegram user_id of the admin to remove.",
        "Main admins cannot be removed.",
    ]
    if notice:
        lines.extend(["", notice])

    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text("Remove Admin", lines),
        reply_markup=_cancel_input_keyboard(),
        preferred_message_id=preferred_message_id,
    )


async def _notify_new_admin_access(bot: Bot, user_id: int) -> bool:
    pending_admin_notice_ids.add(user_id)
    notice_text = "You have been granted admin access."
    try:
        sent = await bot.send_message(
            chat_id=user_id,
            text=notice_text,
            reply_markup=_home_keyboard(is_admin=True),
        )
        panel_message_ids[user_id] = sent.message_id
        await _show_admin_dashboard(
            bot,
            chat_id=user_id,
            user_id=user_id,
            preferred_message_id=sent.message_id,
            notice=notice_text,
        )
    except TelegramAPIError:
        return False
    pending_admin_notice_ids.discard(user_id)
    return True


async def _show_bulk_confirmation(
    bot: Bot,
    *,
    chat_id: int,
    action: BulkActionName,
    preferred_message_id: int | None = None,
) -> None:
    content_map: dict[BulkActionName, tuple[str, list[str]]] = {
        "hideall": (
            "Hide Entire Menu",
            [
                "This action marks all items as unavailable.",
                "Items are not deleted. You can restore them via 'Show All'.",
            ],
        ),
        "showall": (
            "Show Entire Menu",
            [
                "This action marks all items as available.",
                "Users will see all menu items again.",
            ],
        ),
        "deleteall": (
            "Delete Entire Menu",
            [
                "This action deletes all items permanently.",
                "Use it only if you really want to clear the entire menu.",
            ],
        ),
    }

    title, lines = content_map[action]
    await _update_text_panel(
        bot,
        chat_id=chat_id,
        text=_build_panel_text(title, lines),
        reply_markup=_confirm_bulk_keyboard(action),
        preferred_message_id=preferred_message_id,
    )


async def _ensure_admin_callback(callback: CallbackQuery) -> bool:
    if _is_admin_user(callback.from_user.id if callback.from_user else None):
        return True
    await callback.answer("No access to the admin panel", show_alert=True)
    return False


async def _ensure_super_admin_callback(callback: CallbackQuery) -> bool:
    if _is_super_admin_user(callback.from_user.id if callback.from_user else None):
        return True
    await callback.answer("Main admin access only", show_alert=True)
    return False


async def on_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _refresh_admin_cache()
    user_id = message.from_user.id if message.from_user else None
    notice = _consume_pending_admin_notice(user_id)

    if notice and _is_admin_user(user_id):
        await _show_admin_dashboard(
            message.bot,
            chat_id=message.chat.id,
            user_id=user_id,
            preferred_message_id=panel_message_ids.get(message.chat.id),
            notice=notice,
        )
        return

    await _show_home(
        message.bot,
        chat_id=message.chat.id,
        user_id=user_id,
        notice=notice,
    )


async def on_admin_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _refresh_admin_cache()
    await _safe_delete_user_message(message)
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        lines = ["Could not determine Telegram ID."]
    else:
        lines = [str(user_id)]
    await _update_text_panel(
        message.bot,
        chat_id=message.chat.id,
        text=_build_panel_text("Your Telegram ID", lines),
        reply_markup=_home_keyboard(is_admin=_is_admin_user(user_id)),
        preferred_message_id=panel_message_ids.get(message.chat.id),
    )


async def on_home_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else None
    notice = _consume_pending_admin_notice(user_id)

    if notice and _is_admin_user(user_id):
        await _show_admin_dashboard(
            callback.bot,
            chat_id=callback.message.chat.id,
            user_id=user_id,
            preferred_message_id=callback.message.message_id,
            notice=notice,
        )
        await callback.answer()
        return

    await _show_home(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=user_id,
        preferred_message_id=callback.message.message_id,
        notice=notice,
    )
    await callback.answer()


async def on_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    try:
        await _show_menu_categories(
            callback.bot,
            chat_id=callback.message.chat.id,
            preferred_message_id=callback.message.message_id,
        )
    except BackendError as exc:
        await _show_home(
            callback.bot,
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id if callback.from_user else None,
            preferred_message_id=callback.message.message_id,
            notice=str(exc),
        )
    await callback.answer()


async def on_menu_category_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    raw = callback.data.removeprefix("menucat:")
    try:
        category_index = int(raw)
    except ValueError:
        await callback.answer("Invalid category")
        return

    try:
        await _show_menu_category(
            callback.bot,
            chat_id=callback.message.chat.id,
            category_index=category_index,
            include_unavailable=False,
            preferred_message_id=callback.message.message_id,
            back_to_admin=False,
        )
    except BackendError as exc:
        await _show_menu_categories(
            callback.bot,
            chat_id=callback.message.chat.id,
            preferred_message_id=callback.message.message_id,
            notice=str(exc),
        )
    await callback.answer()


async def on_admin_dashboard_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if not await _ensure_admin_callback(callback):
        return

    await _show_admin_dashboard(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id if callback.from_user else None,
        preferred_message_id=callback.message.message_id,
    )
    await callback.answer()


async def on_admin_add_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_admin_callback(callback):
        return

    await state.clear()
    await state.set_state(AdminStates.waiting_add_payload)
    await _prompt_add_form(
        callback.bot,
        chat_id=callback.message.chat.id,
        preferred_message_id=callback.message.message_id,
    )
    await callback.answer()


async def on_admin_users_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_super_admin_callback(callback):
        return

    await state.clear()
    await _show_admin_users_panel(
        callback.bot,
        chat_id=callback.message.chat.id,
        preferred_message_id=callback.message.message_id,
    )
    await callback.answer()


async def on_admin_users_add_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_super_admin_callback(callback):
        return

    await state.clear()
    await state.set_state(AdminStates.waiting_add_admin_user_id)
    await _prompt_add_admin_user_form(
        callback.bot,
        chat_id=callback.message.chat.id,
        preferred_message_id=callback.message.message_id,
    )
    await callback.answer()


async def on_admin_users_remove_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_super_admin_callback(callback):
        return

    await state.clear()
    await state.set_state(AdminStates.waiting_remove_admin_user_id)
    await _prompt_remove_admin_user_form(
        callback.bot,
        chat_id=callback.message.chat.id,
        preferred_message_id=callback.message.message_id,
    )
    await callback.answer()


async def on_admin_bulk_action_prepare(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_admin_callback(callback):
        return

    await state.clear()
    action = callback.data.removeprefix("admin:")
    if action not in {"hideall", "showall", "deleteall"}:
        await callback.answer("Unknown action")
        return

    await _show_bulk_confirmation(
        callback.bot,
        chat_id=callback.message.chat.id,
        action=action,  # type: ignore[arg-type]
        preferred_message_id=callback.message.message_id,
    )
    await callback.answer()


async def on_admin_bulk_action_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_admin_callback(callback):
        return

    await state.clear()
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid action")
        return

    action = parts[2]
    if action not in {"hideall", "showall", "deleteall"}:
        await callback.answer("Unknown action")
        return

    try:
        if action == "hideall":
            payload = await api_client.set_all_availability(available=False)
            updated = int(payload.get("updated", 0))
            notice = f"Hidden items: {updated}."
        elif action == "showall":
            payload = await api_client.set_all_availability(available=True)
            updated = int(payload.get("updated", 0))
            notice = f"Shown items: {updated}."
        else:
            payload = await api_client.delete_all_menu_items()
            deleted = int(payload.get("deleted", 0))
            notice = f"Deleted items: {deleted}."
    except BackendError as exc:
        await _show_admin_dashboard(
            callback.bot,
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id if callback.from_user else None,
            preferred_message_id=callback.message.message_id,
            notice=str(exc),
        )
        await callback.answer()
        return

    await _show_admin_dashboard(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id if callback.from_user else None,
        preferred_message_id=callback.message.message_id,
        notice=notice,
    )
    await callback.answer()


async def on_admin_action_categories(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_admin_callback(callback):
        return

    await state.clear()
    action = callback.data.removeprefix("admin:")
    if action not in {"edit", "delete", "toggle", "viewall"}:
        await callback.answer("Unknown action")
        return

    try:
        await _show_admin_category_picker(
            callback.bot,
            chat_id=callback.message.chat.id,
            action=action,  # type: ignore[arg-type]
            preferred_message_id=callback.message.message_id,
        )
    except BackendError as exc:
        await _show_admin_dashboard(
            callback.bot,
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id if callback.from_user else None,
            preferred_message_id=callback.message.message_id,
            notice=str(exc),
        )
    await callback.answer()


async def on_admin_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_admin_callback(callback):
        return

    await state.clear()
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer("Invalid selection")
        return

    _, _, action, index_raw = parts
    try:
        category_index = int(index_raw)
    except ValueError:
        await callback.answer("Invalid category index")
        return

    try:
        if action == "viewall":
            await _show_menu_category(
                callback.bot,
                chat_id=callback.message.chat.id,
                category_index=category_index,
                include_unavailable=True,
                preferred_message_id=callback.message.message_id,
                back_to_admin=True,
            )
        else:
            await _show_admin_items_picker(
                callback.bot,
                chat_id=callback.message.chat.id,
                action=action,  # type: ignore[arg-type]
                category_index=category_index,
                preferred_message_id=callback.message.message_id,
            )
    except BackendError as exc:
        await _show_admin_dashboard(
            callback.bot,
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id if callback.from_user else None,
            preferred_message_id=callback.message.message_id,
            notice=str(exc),
        )
    await callback.answer()


async def on_admin_item_selected(callback: CallbackQuery, state: FSMContext) -> None:
    if not await _ensure_admin_callback(callback):
        return

    await state.clear()
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Invalid selection")
        return

    _, _, action, item_id_raw, category_index_raw = parts
    try:
        item_id = int(item_id_raw)
        category_index = int(category_index_raw)
    except ValueError:
        await callback.answer("Invalid id")
        return

    try:
        if action == "delete":
            await api_client.delete_menu_item(item_id=item_id)
            await _show_admin_items_picker(
                callback.bot,
                chat_id=callback.message.chat.id,
                action="delete",
                category_index=category_index,
                preferred_message_id=callback.message.message_id,
                notice=f"Item #{item_id} deleted.",
            )
        elif action == "toggle":
            item = await api_client.get_menu_item(item_id=item_id)
            if not item:
                raise BackendError("Item not found")
            updated = await api_client.set_availability(
                item_id=item_id,
                available=not bool(item.get("available", True)),
            )
            state_text = "available" if updated.get("available") else "hidden"
            await _show_admin_items_picker(
                callback.bot,
                chat_id=callback.message.chat.id,
                action="toggle",
                category_index=category_index,
                preferred_message_id=callback.message.message_id,
                notice=f"Item #{item_id} is now {state_text}.",
            )
        elif action == "edit":
            item = await api_client.get_menu_item(item_id=item_id)
            if not item:
                raise BackendError("Item not found")
            await state.set_state(AdminStates.waiting_edit_payload)
            await state.update_data(item_id=item_id)
            await _prompt_edit_form(
                callback.bot,
                chat_id=callback.message.chat.id,
                item=item,
                preferred_message_id=callback.message.message_id,
            )
        else:
            await callback.answer("Action not supported")
            return
    except BackendError as exc:
        await _show_admin_items_picker(
            callback.bot,
            chat_id=callback.message.chat.id,
            action=action,  # type: ignore[arg-type]
            category_index=category_index,
            preferred_message_id=callback.message.message_id,
            notice=str(exc),
        )

    await callback.answer()


async def on_admin_cancel_input(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if not await _ensure_admin_callback(callback):
        return

    await _show_admin_dashboard(
        callback.bot,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id if callback.from_user else None,
        preferred_message_id=callback.message.message_id,
        notice="Action canceled.",
    )
    await callback.answer()


async def on_admin_add_payload(message: Message, state: FSMContext) -> None:
    if not _is_admin_user(message.from_user.id if message.from_user else None):
        await state.clear()
        await _safe_delete_user_message(message)
        await _show_home(
            message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            notice="No access to the admin panel.",
        )
        return

    text = (message.text or "").strip()
    try:
        name, price, category, description = _parse_admin_payload(text)
        item = await api_client.add_menu_item(
            name=name,
            price=price,
            category=category,
            description=description,
            available=True,
        )
    except (ValueError, BackendError) as exc:
        await _prompt_add_form(
            message.bot,
            chat_id=message.chat.id,
            preferred_message_id=panel_message_ids.get(message.chat.id),
            notice=str(exc),
        )
        await _safe_delete_user_message(message)
        return

    await state.clear()
    await _safe_delete_user_message(message)
    await _show_admin_dashboard(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
        preferred_message_id=panel_message_ids.get(message.chat.id),
        notice=f"Added: #{item.get('id')} {item.get('name')}.",
    )


async def on_admin_edit_payload(message: Message, state: FSMContext) -> None:
    if not _is_admin_user(message.from_user.id if message.from_user else None):
        await state.clear()
        await _safe_delete_user_message(message)
        await _show_home(
            message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            notice="No access to the admin panel.",
        )
        return

    data = await state.get_data()
    item_id = data.get("item_id")
    if not isinstance(item_id, int):
        await state.clear()
        await _show_admin_dashboard(
            message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            preferred_message_id=panel_message_ids.get(message.chat.id),
            notice="Edit session expired. Please choose the item again.",
        )
        return

    text = (message.text or "").strip()
    try:
        name, price, category, description = _parse_admin_payload(text)
        existing = await api_client.get_menu_item(item_id=item_id)
        if not existing:
            raise BackendError("Item not found")
        updated = await api_client.update_menu_item(
            item_id=item_id,
            name=name,
            price=price,
            category=category,
            description=description,
            available=bool(existing.get("available", True)),
        )
    except (ValueError, BackendError) as exc:
        current_item = await api_client.get_menu_item(item_id=item_id)
        if not current_item:
            await state.clear()
            await _show_admin_dashboard(
                message.bot,
                chat_id=message.chat.id,
                user_id=message.from_user.id if message.from_user else None,
                preferred_message_id=panel_message_ids.get(message.chat.id),
                notice=f"Error: {exc}",
            )
            await _safe_delete_user_message(message)
            return

        await _prompt_edit_form(
            message.bot,
            chat_id=message.chat.id,
            item=current_item,
            preferred_message_id=panel_message_ids.get(message.chat.id),
            notice=str(exc),
        )
        await _safe_delete_user_message(message)
        return

    await state.clear()
    await _safe_delete_user_message(message)
    await _show_admin_dashboard(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
        preferred_message_id=panel_message_ids.get(message.chat.id),
        notice=f"Item #{updated.get('id')} updated.",
    )


async def on_add_admin_user_payload(message: Message, state: FSMContext) -> None:
    if not _is_super_admin_user(message.from_user.id if message.from_user else None):
        await state.clear()
        await _safe_delete_user_message(message)
        await _show_home(
            message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            notice="No access to admin management.",
        )
        return

    text = (message.text or "").strip()
    try:
        user_id = _parse_user_id_payload(text)
        if user_id in settings.super_admin_ids:
            raise ValueError("This user_id is already a main admin.")
        await api_client.add_admin_user(user_id=user_id)
        managed_admin_ids.add(user_id)
        await _refresh_admin_cache()
        notified = await _notify_new_admin_access(message.bot, user_id)
        if notified:
            notice = (
                f"User {user_id} was added as admin. "
                "Notification and admin panel were sent."
            )
        else:
            notice = (
                f"User {user_id} was added as admin. "
                "Could not send a notification: user should open the bot and press /start."
            )
    except (ValueError, BackendError) as exc:
        await _prompt_add_admin_user_form(
            message.bot,
            chat_id=message.chat.id,
            preferred_message_id=panel_message_ids.get(message.chat.id),
            notice=str(exc),
        )
        await _safe_delete_user_message(message)
        return

    await state.clear()
    await _safe_delete_user_message(message)
    await _show_admin_users_panel(
        message.bot,
        chat_id=message.chat.id,
        preferred_message_id=panel_message_ids.get(message.chat.id),
        notice=notice,
    )


async def on_remove_admin_user_payload(message: Message, state: FSMContext) -> None:
    if not _is_super_admin_user(message.from_user.id if message.from_user else None):
        await state.clear()
        await _safe_delete_user_message(message)
        await _show_home(
            message.bot,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else None,
            notice="No access to admin management.",
        )
        return

    text = (message.text or "").strip()
    try:
        user_id = _parse_user_id_payload(text)
        if user_id in settings.super_admin_ids:
            raise ValueError("Main admin cannot be removed.")
        await api_client.remove_admin_user(user_id=user_id)
        managed_admin_ids.discard(user_id)
        pending_admin_notice_ids.discard(user_id)
        await _refresh_admin_cache()
        notice = f"User {user_id} removed from admins."
    except (ValueError, BackendError) as exc:
        await _prompt_remove_admin_user_form(
            message.bot,
            chat_id=message.chat.id,
            preferred_message_id=panel_message_ids.get(message.chat.id),
            notice=str(exc),
        )
        await _safe_delete_user_message(message)
        return

    await state.clear()
    await _safe_delete_user_message(message)
    await _show_admin_users_panel(
        message.bot,
        chat_id=message.chat.id,
        preferred_message_id=panel_message_ids.get(message.chat.id),
        notice=notice,
    )


async def on_free_text(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return

    text = (message.text or "").strip()
    if re.match(r"^/start(?:@\w+)?(?:\s|$)", text, flags=re.IGNORECASE):
        return

    await _safe_delete_user_message(message)
    await _show_home(
        message.bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
        preferred_message_id=panel_message_ids.get(message.chat.id),
        notice="Use the buttons under the card, it is much more convenient.",
    )


async def main() -> None:
    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher()

    dispatcher.message.register(on_start, Command("start"))
    dispatcher.message.register(on_admin_command, Command("admin"))

    dispatcher.callback_query.register(on_home_callback, F.data == "home")
    dispatcher.callback_query.register(on_menu_callback, F.data == "menu")
    dispatcher.callback_query.register(on_menu_category_callback, F.data.startswith("menucat:"))

    dispatcher.callback_query.register(on_admin_dashboard_callback, F.data == "admin")
    dispatcher.callback_query.register(on_admin_users_callback, F.data == "admin:admins")
    dispatcher.callback_query.register(on_admin_users_add_prompt, F.data == "admin:admins:add")
    dispatcher.callback_query.register(on_admin_users_remove_prompt, F.data == "admin:admins:remove")
    dispatcher.callback_query.register(on_admin_add_callback, F.data == "admin:add")
    dispatcher.callback_query.register(
        on_admin_bulk_action_prepare,
        F.data.in_({"admin:hideall", "admin:showall", "admin:deleteall"}),
    )
    dispatcher.callback_query.register(on_admin_bulk_action_confirm, F.data.startswith("admin:confirm:"))
    dispatcher.callback_query.register(
        on_admin_action_categories,
        F.data.in_({"admin:edit", "admin:delete", "admin:toggle", "admin:viewall"}),
    )
    dispatcher.callback_query.register(on_admin_category_selected, F.data.startswith("admin:cat:"))
    dispatcher.callback_query.register(on_admin_item_selected, F.data.startswith("admin:item:"))
    dispatcher.callback_query.register(on_admin_cancel_input, F.data == "admin:cancel")

    dispatcher.message.register(on_admin_add_payload, AdminStates.waiting_add_payload)
    dispatcher.message.register(on_admin_edit_payload, AdminStates.waiting_edit_payload)
    dispatcher.message.register(on_add_admin_user_payload, AdminStates.waiting_add_admin_user_id)
    dispatcher.message.register(
        on_remove_admin_user_payload,
        AdminStates.waiting_remove_admin_user_id,
    )
    dispatcher.message.register(on_free_text, F.text)

    await _refresh_admin_cache()
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
