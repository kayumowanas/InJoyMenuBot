from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.db.menu_items import list_menu_items
from app.models.menu_item import MenuItem

router = APIRouter()


@router.get("/menu", response_model=list[MenuItem])
async def get_public_menu(
    category: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[MenuItem]:
    items = await list_menu_items(session, only_available=True)

    if category is None:
        return items

    normalized = category.strip().lower()
    if not normalized:
        return items

    return [item for item in items if item.category.strip().lower() == normalized]
