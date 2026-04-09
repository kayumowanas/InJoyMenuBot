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


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with AsyncSession(engine) as session:
        yield session


def _build_seed_menu_items() -> list[MenuItem]:
    default_volumes = {"S": "250 мл", "M": "300 мл", "L": "450 мл"}

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
                description=f"{title}, размер {size}",
                price=price,
                available=True,
            )
            for size, price in prices.items()
        ]

    items: list[MenuItem] = []

    # Фирменные напитки
    for drink in [
        "Раф птичье молоко",
        "Капучино кекс-клюква",
        "Латте бананелла",
        "Раф бельгийская вафля",
    ]:
        items.extend(
            with_sizes(
                title=drink,
                category="Фирменные напитки",
                prices={"S": 229, "M": 249, "L": 269},
            )
        )

    # Сезонные напитки
    for drink in [
        "Лимонад Нефанта",
        "Лимонад Фейхоа базилик",
        "Лимонад Смородина-фиалка",
        "Лимонад Тархун",
    ]:
        items.extend(
            with_sizes(
                title=drink,
                category="Сезонные напитки",
                prices={"M": 249, "L": 269},
            )
        )

    # Айс напитки
    for drink, price in [
        ("Фраппучино классический", 299),
        ("Фраппучино-баунти", 299),
        ("Милкшейк ванильный", 249),
        ("Милкшейк смородина-баблгам", 249),
        ("Милкшейк малиновый", 249),
        ("Айс латте", 249),
        ("Айс раф", 249),
        ("Айс капучино сникерс", 249),
        ("Эспрессо-тоник", 249),
        ("Айс матча латте", 249),
        ("Бамбл апельсиновый", 249),
        ("Бамбл вишневый", 249),
    ]:
        items.extend(
            with_sizes(
                title=drink,
                category="Айс напитки",
                prices={"M": price},
            )
        )

    # Классические напитки
    items.extend(
        with_sizes(title="Эспрессо", category="Классические напитки", prices={"S": 99})
    )
    items.extend(
        with_sizes(
            title="Двойной эспрессо (60 мл)",
            category="Классические напитки",
            prices={"S": 119},
        )
    )
    items.extend(
        with_sizes(
            title="Флэт уайт", category="Классические напитки", prices={"S": 189}
        )
    )
    items.extend(
        with_sizes(
            title="Американо",
            category="Классические напитки",
            prices={"S": 159, "M": 179, "L": 229},
        )
    )
    items.extend(
        with_sizes(
            title="Капучино",
            category="Классические напитки",
            prices={"S": 169, "M": 189, "L": 239},
        )
    )
    items.extend(
        with_sizes(
            title="Латте",
            category="Классические напитки",
            prices={"S": 169, "M": 189, "L": 239},
        )
    )
    items.extend(
        with_sizes(
            title="Раф",
            category="Классические напитки",
            prices={"S": 199, "M": 239, "L": 269},
        )
    )
    items.extend(
        with_sizes(
            title="Мокко",
            category="Классические напитки",
            prices={"S": 189, "M": 229, "L": 259},
        )
    )
    items.extend(
        with_sizes(
            title="Глясе",
            category="Классические напитки",
            prices={"S": 189, "M": 229, "L": 259},
        )
    )
    items.extend(
        with_sizes(
            title="Фильтр кофе",
            category="Классические напитки",
            prices={"S": 189, "M": 229, "L": 259},
        )
    )

    # Горячие напитки
    items.extend(
        with_sizes(
            title="Чай черный/зеленый",
            category="Горячие напитки",
            prices={"S": 99, "M": 99, "L": 99},
        )
    )
    items.extend(
        with_sizes(
            title="Ягодный чай",
            category="Горячие напитки",
            prices={"S": 149, "M": 149, "L": 149},
        )
    )
    items.extend(
        with_sizes(
            title="Какао",
            category="Горячие напитки",
            prices={"S": 159, "M": 179, "L": 219},
        )
    )
    items.extend(
        with_sizes(
            title="Горячий шоколад",
            category="Горячие напитки",
            prices={"S": 189, "M": 209, "L": 239},
        )
    )
    items.extend(
        with_sizes(
            title="Матча латте",
            category="Горячие напитки",
            # M/L partially covered by reflection on the photo,
            # values are set based on the visible digits and menu pattern.
            prices={"S": 179, "M": 209, "L": 239},
        )
    )

    # Добавки
    items.extend(
        with_sizes(
            title="Маршмеллоу, молоко",
            category="Добавки",
            prices={"S": 30, "M": 30, "L": 30},
        )
    )
    items.extend(
        with_sizes(
            title="Сливки 10%",
            category="Добавки",
            prices={"S": 50, "M": 50, "L": 50},
        )
    )
    items.extend(
        with_sizes(
            title="Взбитые сливки",
            category="Добавки",
            prices={"S": 70, "M": 80, "L": 90},
        )
    )
    items.extend(
        with_sizes(
            title="Любой напиток на растительном молоке",
            category="Добавки",
            prices={"S": 30, "M": 30, "L": 30},
        )
    )
    items.extend(
        with_sizes(
            title="Сироп",
            category="Добавки",
            # Price row is partially hidden by the stand; set to the common add-on price.
            prices={"S": 30, "M": 30, "L": 30},
        )
    )

    # Хот-доги (по отдельной карточке меню)
    for name in ["Французский хот-дог", "Датский хот-дог"]:
        items.append(
            MenuItem(
                name=name,
                category="Хот-доги",
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
