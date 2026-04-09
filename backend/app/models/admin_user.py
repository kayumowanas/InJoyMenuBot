from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class AdminUser(SQLModel, table=True):
    __tablename__ = "admin_users"

    user_id: int = Field(primary_key=True, index=True, gt=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class AdminUserCreate(SQLModel):
    user_id: int = Field(gt=0)
