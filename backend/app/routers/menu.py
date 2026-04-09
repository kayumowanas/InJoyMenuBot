from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.db.menu_items import (
    create_menu_item,
    delete_all_menu_items,
    delete_menu_item,
    list_menu_items,
    read_menu_item,
    set_all_menu_items_availability,
    set_menu_item_availability,
    update_menu_item,
)
from app.models.menu_item import (
    MenuItem,
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemUpdateAvailability,
)

router = APIRouter()


@router.get("/", response_model=list[MenuItem])
async def get_menu(
    only_available: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
) -> list[MenuItem]:
    return await list_menu_items(session, only_available=only_available)


@router.post("/", response_model=MenuItem, status_code=status.HTTP_201_CREATED)
async def post_menu_item(
    body: MenuItemCreate,
    session: AsyncSession = Depends(get_session),
) -> MenuItem:
    return await create_menu_item(session, body)


@router.delete("/", response_model=dict[str, int])
async def delete_all_menu_items_endpoint(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    deleted = await delete_all_menu_items(session)
    return {"deleted": deleted}


@router.patch("/availability/all", response_model=dict[str, int | bool])
async def patch_all_menu_item_availability(
    body: MenuItemUpdateAvailability,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int | bool]:
    updated = await set_all_menu_items_availability(session, body.available)
    return {"updated": updated, "available": body.available}


@router.get("/{item_id}", response_model=MenuItem)
async def get_menu_item_endpoint(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> MenuItem:
    item = await read_menu_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=MenuItem)
async def put_menu_item_endpoint(
    item_id: int,
    body: MenuItemUpdate,
    session: AsyncSession = Depends(get_session),
) -> MenuItem:
    item = await update_menu_item(session, item_id=item_id, data=body)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item_endpoint(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await delete_menu_item(session, item_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.patch("/{item_id}/availability", response_model=MenuItem)
async def patch_menu_item_availability(
    item_id: int,
    body: MenuItemUpdateAvailability,
    session: AsyncSession = Depends(get_session),
) -> MenuItem:
    item = await set_menu_item_availability(session, item_id, body.available)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
