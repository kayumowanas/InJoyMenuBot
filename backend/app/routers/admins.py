from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.db.admin_users import (
    create_admin_user,
    delete_admin_user,
    list_admin_users,
    read_admin_user,
)
from app.models.admin_user import AdminUser, AdminUserCreate

router = APIRouter()


@router.get("/", response_model=list[AdminUser])
async def get_admin_users(
    session: AsyncSession = Depends(get_session),
) -> list[AdminUser]:
    return await list_admin_users(session)


@router.post("/", response_model=AdminUser, status_code=status.HTTP_201_CREATED)
async def post_admin_user(
    body: AdminUserCreate,
    session: AsyncSession = Depends(get_session),
) -> AdminUser:
    return await create_admin_user(session, body)


@router.get("/{user_id}", response_model=AdminUser)
async def get_admin_user(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> AdminUser:
    admin = await read_admin_user(session, user_id)
    if admin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
    return admin


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    deleted = await delete_admin_user(session, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")
