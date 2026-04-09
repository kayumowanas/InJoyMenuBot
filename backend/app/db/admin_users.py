from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.admin_user import AdminUser, AdminUserCreate


async def list_admin_users(session: AsyncSession) -> list[AdminUser]:
    result = await session.exec(select(AdminUser).order_by(AdminUser.user_id))
    return list(result.all())


async def read_admin_user(session: AsyncSession, user_id: int) -> AdminUser | None:
    return await session.get(AdminUser, user_id)


async def create_admin_user(session: AsyncSession, data: AdminUserCreate) -> AdminUser:
    existing = await session.get(AdminUser, data.user_id)
    if existing is not None:
        return existing

    admin = AdminUser.model_validate(data.model_dump())
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def delete_admin_user(session: AsyncSession, user_id: int) -> bool:
    admin = await session.get(AdminUser, user_id)
    if admin is None:
        return False
    await session.delete(admin)
    await session.commit()
    return True
