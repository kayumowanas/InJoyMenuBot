from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.admin_user import AdminUser
from app.models.menu_item import MenuItem
from app.settings import settings


def _database_url() -> str:
    db_path = Path(settings.sqlite_path)
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parent.parent / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


engine = create_async_engine(_database_url(), echo=False)

LEGACY_SEED_NAMES = {"Cappuccino", "Chicken Wrap", "Cheesecake"}
OBSOLETE_RU_SEED_CATEGORIES = {
    "Фирменные напитки",
    "Сезонные напитки",
    "Айс напитки",
    "Классические напитки",
    "Горячие напитки",
    "Добавки",
    "Хот-доги",
}


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session


def _build_seed_menu_items() -> list[MenuItem]:
    default_volumes = {"S": "250 ml", "M": "300 ml", "L": "450 ml"}

    def with_sizes(
        *,
        title: str,
        category: str,
        prices: dict[str, int],
        volumes: dict[str, str] | None = None,
    ) -> list[MenuItem]:
        size_volumes = volumes or default_volumes
        return [
            MenuItem(
                name=f"{title} — {size} ({size_volumes[size]})",
                category=category,
                description=f"{title}, size {size}",
                price=price,
                available=True,
            )
            for size, price in prices.items()
        ]

    items: list[MenuItem] = []

    # Signature drinks
    for drink in [
        "Raf Bird's Milk",
        "Cappuccino Cupcake Cranberry",
        "Latte Bananella",
        "Raf Belgian Waffle",
    ]:
        items.extend(
            with_sizes(
                title=drink,
                category="Signature Drinks",
                prices={"S": 229, "M": 249, "L": 269},
            )
        )

    # Seasonal drinks
    for drink in [
        "Lemonade Nefanta",
        "Lemonade Feijoa Basil",
        "Lemonade Currant Violet",
        "Lemonade Tarragon",
    ]:
        items.extend(
            with_sizes(
                title=drink,
                category="Seasonal Drinks",
                prices={"M": 249, "L": 269},
            )
        )

    # Iced drinks
    for drink, price in [
        ("Classic Frappuccino", 299),
        ("Bounty Frappuccino", 299),
        ("Vanilla Milkshake", 249),
        ("Currant Bubblegum Milkshake", 249),
        ("Raspberry Milkshake", 249),
        ("Iced Latte", 249),
        ("Iced Raf", 249),
        ("Iced Snickers Cappuccino", 249),
        ("Espresso Tonic", 249),
        ("Iced Matcha Latte", 249),
        ("Orange Bumble", 249),
        ("Cherry Bumble", 249),
    ]:
        items.extend(
            with_sizes(
                title=drink,
                category="Iced Drinks",
                prices={"M": price},
            )
        )

    # Classic drinks
    items.extend(
        with_sizes(title="Espresso", category="Classic Drinks", prices={"S": 99})
    )
    items.extend(
        with_sizes(
            title="Double Espresso (60 ml)",
            category="Classic Drinks",
            prices={"S": 119},
        )
    )
    items.extend(
        with_sizes(
            title="Flat White", category="Classic Drinks", prices={"S": 189}
        )
    )
    items.extend(
        with_sizes(
            title="Americano",
            category="Classic Drinks",
            prices={"S": 159, "M": 179, "L": 229},
        )
    )
    items.extend(
        with_sizes(
            title="Cappuccino",
            category="Classic Drinks",
            prices={"S": 169, "M": 189, "L": 239},
        )
    )
    items.extend(
        with_sizes(
            title="Latte",
            category="Classic Drinks",
            prices={"S": 169, "M": 189, "L": 239},
        )
    )
    items.extend(
        with_sizes(
            title="Raf",
            category="Classic Drinks",
            prices={"S": 199, "M": 239, "L": 269},
        )
    )
    items.extend(
        with_sizes(
            title="Mocha",
            category="Classic Drinks",
            prices={"S": 189, "M": 229, "L": 259},
        )
    )
    items.extend(
        with_sizes(
            title="Affogato",
            category="Classic Drinks",
            prices={"S": 189, "M": 229, "L": 259},
        )
    )
    items.extend(
        with_sizes(
            title="Filter Coffee",
            category="Classic Drinks",
            prices={"S": 189, "M": 229, "L": 259},
        )
    )

    # Hot drinks
    items.extend(
        with_sizes(
            title="Black/Green Tea",
            category="Hot Drinks",
            prices={"S": 99, "M": 99, "L": 99},
        )
    )
    items.extend(
        with_sizes(
            title="Berry Tea",
            category="Hot Drinks",
            prices={"S": 149, "M": 149, "L": 149},
        )
    )
    items.extend(
        with_sizes(
            title="Cocoa",
            category="Hot Drinks",
            prices={"S": 159, "M": 179, "L": 219},
        )
    )
    items.extend(
        with_sizes(
            title="Hot Chocolate",
            category="Hot Drinks",
            prices={"S": 189, "M": 209, "L": 239},
        )
    )
    items.extend(
        with_sizes(
            title="Matcha Latte",
            category="Hot Drinks",
            # M/L partially covered by reflection on the photo,
            # values are set based on the visible digits and menu pattern.
            prices={"S": 179, "M": 209, "L": 239},
        )
    )

    # Add-ons
    items.extend(
        with_sizes(
            title="Marshmallow, Milk",
            category="Add-ons",
            prices={"S": 30, "M": 30, "L": 30},
        )
    )
    items.extend(
        with_sizes(
            title="Cream 10%",
            category="Add-ons",
            prices={"S": 50, "M": 50, "L": 50},
        )
    )
    items.extend(
        with_sizes(
            title="Whipped Cream",
            category="Add-ons",
            prices={"S": 70, "M": 80, "L": 90},
        )
    )
    items.extend(
        with_sizes(
            title="Any Drink with Plant-Based Milk",
            category="Add-ons",
            prices={"S": 30, "M": 30, "L": 30},
        )
    )
    items.extend(
        with_sizes(
            title="Syrup",
            category="Add-ons",
            # Price row is partially hidden by the stand; set to the common add-on price.
            prices={"S": 30, "M": 30, "L": 30},
        )
    )

    # Hot dogs (from a separate menu card)
    for name in ["French Hot Dog", "Danish Hot Dog"]:
        items.append(
            MenuItem(
                name=name,
                category="Hot Dogs",
                description=f"{name}",
                price=249,
                available=True,
            )
        )

    return items


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        obsolete_ru_items_result = await session.exec(
            select(MenuItem).where(MenuItem.category.in_(tuple(OBSOLETE_RU_SEED_CATEGORIES)))
        )
        obsolete_ru_items = list(obsolete_ru_items_result.all())
        if obsolete_ru_items:
            for item in obsolete_ru_items:
                await session.delete(item)
            await session.commit()

        seed_items = _build_seed_menu_items()
        existing_names_result = await session.exec(select(MenuItem.name))
        existing_names = list(existing_names_result.all())
        existing_name_set = set(existing_names)

        if existing_names and existing_name_set != LEGACY_SEED_NAMES:
            missing_seed_items = [item for item in seed_items if item.name not in existing_name_set]
            if missing_seed_items:
                session.add_all(missing_seed_items)
                await session.commit()
            return

        if existing_names and existing_name_set == LEGACY_SEED_NAMES:
            existing_items_result = await session.exec(select(MenuItem))
            existing_items = list(existing_items_result.all())
            for item in existing_items:
                await session.delete(item)
            await session.commit()

        session.add_all(seed_items)
        await session.commit()
