# InJoy Menu Bot

Telegram bot for InJoy cafe menu.

## Features

- User flow is button-based (inline keyboard), without command-heavy UX
- Bot uses text panels for navigation/admin, and image render only for menu cards
- Menu is rendered as readable image cards per category (mobile-friendly)
- Bot keeps one "live" panel message and edits it, so chat history stays clean
- Staff admins can open `/admin` panel and manage dishes via buttons:
  - add
  - edit
  - delete
  - hide/show availability
  - hide/show all menu positions in one tap
  - delete all menu positions in one tap (with confirmation)
  - view all categories including unavailable positions
- Main admins can add/remove regular admins directly from bot
- Backend API with persistent SQLite storage
- Automatic seed of menu data from your attached cafe photos (`backend/data/injoy.db`)

## Project structure

- `backend/` - FastAPI app with menu CRUD
- `bot/` - aiogram Telegram bot
- `docker-compose.yml` - local run configuration

## Quick start

1. Create env file:

```bash
cp .env.example .env
```

2. Set real `BOT_TOKEN`.
   `BOT_SUPER_ADMIN_IDS` - main admins (can manage other admins).
   `BOT_ADMIN_IDS` - backward-compatible fallback if `BOT_SUPER_ADMIN_IDS` is empty.
   Supported separators: comma, space, semicolon.
   You can run `/admin` in bot chat to see your Telegram user id.

3. Run services:

```bash
docker compose up --build
```

If you changed `.env` values (for example `BOT_TOKEN`), recreate bot container:

```bash
docker compose up -d --force-recreate bot
```

4. Open backend docs: `http://localhost:8000/docs`

## API overview

All `/menu/*` endpoints require header:

```text
Authorization: Bearer <BACKEND_API_TOKEN>
```

- `GET /health`
- `GET /menu/?only_available=true`
- `POST /menu/`
- `DELETE /menu/` (delete all items)
- `PATCH /menu/availability/all` (set availability for all items)
- `GET /menu/{item_id}`
- `PUT /menu/{item_id}`
- `DELETE /menu/{item_id}`
- `PATCH /menu/{item_id}/availability`
- `GET /admins/`
- `POST /admins/`
- `GET /admins/{user_id}`
- `DELETE /admins/{user_id}`

## Seeded database

- SQLite file: `backend/data/injoy.db`
- Current seed contains menu items with size-specific prices (S/M/L split into separate rows)
- Also includes hot-dogs from the attached menu photo:
  - Французский хот-дог — 249 ₽
  - Датский хот-дог — 249 ₽

## Local dev without docker

Backend:

```bash
cd backend
uv run --project . --python 3.12 python -m app.run
```

Bot:

```bash
cd bot
uv run --project . python bot.py
```
# InJoyMenuBot
