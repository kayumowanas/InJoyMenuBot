from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.menu_item import MenuItem, MenuItemCreate, MenuItemUpdate


async def list_menu_items(
    session: AsyncSession, *, only_available: bool = False
) -> list[MenuItem]:
    query = select(MenuItem)
    if only_available:
        query = query.where(MenuItem.available.is_(True))
    query = query.order_by(MenuItem.category, MenuItem.name)
    result = await session.exec(query)
    return list(result.all())


async def create_menu_item(session: AsyncSession, data: MenuItemCreate) -> MenuItem:
    item = MenuItem.model_validate(data.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def read_menu_item(session: AsyncSession, item_id: int) -> MenuItem | None:
    return await session.get(MenuItem, item_id)


async def delete_menu_item(session: AsyncSession, item_id: int) -> bool:
    item = await session.get(MenuItem, item_id)
    if item is None:
        return False
    await session.delete(item)
    await session.commit()
    return True


async def set_menu_item_availability(
    session: AsyncSession, item_id: int, available: bool
) -> MenuItem | None:
    item = await session.get(MenuItem, item_id)
    if item is None:
        return None
    item.available = available
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def set_all_menu_items_availability(session: AsyncSession, available: bool) -> int:
    result = await session.exec(select(MenuItem))
    items = list(result.all())
    if not items:
        return 0

    for item in items:
        item.available = available
        session.add(item)

    await session.commit()
    return len(items)


async def delete_all_menu_items(session: AsyncSession) -> int:
    result = await session.exec(select(MenuItem))
    items = list(result.all())
    if not items:
        return 0

    for item in items:
        await session.delete(item)

    await session.commit()
    return len(items)


async def update_menu_item(
    session: AsyncSession, item_id: int, data: MenuItemUpdate
) -> MenuItem | None:
    item = await session.get(MenuItem, item_id)
    if item is None:
        return None

    update_payload = data.model_dump(exclude_unset=True)
    for field, value in update_payload.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item
