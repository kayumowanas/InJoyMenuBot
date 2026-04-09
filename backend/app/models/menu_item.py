from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class MenuItem(SQLModel, table=True):
    __tablename__ = "menu_items"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    category: str = Field(default="Other", index=True)
    description: str = Field(default="")
    price: float = Field(ge=0)
    available: bool = Field(default=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class MenuItemCreate(SQLModel):
    name: str
    category: str = "Other"
    description: str = ""
    price: float = Field(ge=0)
    available: bool = True


class MenuItemUpdateAvailability(SQLModel):
    available: bool


class MenuItemUpdate(SQLModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, ge=0)
    available: bool | None = None
