# InJoy Menu Platform

Menu management platform for a cafe: guests browse the menu in web UI, and staff manage items through Telegram admin bot.

## Demo

- `docs/screenshots/user-menu.png` - web client for end users (categories and menu cards).
- `docs/screenshots/admin-panel.png` - Telegram admin panel flow for staff.

![Web client menu](docs/screenshots/user-menu.png)
![Telegram admin panel](docs/screenshots/admin-panel.png)

## Product context

### End users

- Cafe guests who need a quick menu on mobile browser.
- Cafe staff/admins who maintain menu content.

### Problem that your product solves for end users

Guests need an always-available digital menu that works on university VM deployment without Telegram limitations, while staff need fast in-chat menu administration.

### Your solution

The product combines a FastAPI backend with SQLite, a web menu client for guests, and a Telegram admin bot for staff operations.

## Features

### Implemented features

- Public web client (`frontend/`) for browsing available menu items by category.
- FastAPI backend with persistent SQLite storage.
- Read-only public endpoint: `GET /public/menu`.
- Protected admin API endpoints under `/menu/*` and `/admins/*` with bearer token.
- Telegram admin bot with inline-keyboard admin panel:
  - add/edit/delete items
  - hide/show single item
  - hide/show all items
  - delete full menu with confirmation
  - add/remove regular admins (main admin only)
- Dockerized deployment via `docker compose` for backend, bot, and frontend.

### Not yet implemented features

- Customer ordering and payment flow.
- Authentication for web admin dashboard.
- Admin activity timeline/audit log UI.
- Automated tests for frontend user flows.

## Usage

### End-user web flow

1. Open `http://<VM_IP>:8080`.
2. Browse all available items.
3. Select category in dropdown to filter.
4. Press `Refresh` to sync current menu state from backend.

### Staff/admin flow (Telegram)

1. Ensure your Telegram `user_id` is in `BOT_SUPER_ADMIN_IDS` or `admin_users`.
2. Open bot chat and run `/start`.
3. Open `Admin Panel`.
4. Manage menu content using buttons.

## Deployment

### Which OS the VM should run on

- Ubuntu 24.04 LTS.

### What should be installed on the VM

- `git`
- Docker Engine
- Docker Compose plugin (`docker compose`)

### Step-by-step deployment instructions

1. Clone repository and enter project directory.
2. Create env file:

```bash
cp .env.example .env
```

3. Fill required `.env` values:
   - `BACKEND_API_TOKEN`
   - `BOT_TOKEN`
   - `BOT_SUPER_ADMIN_IDS` (or `BOT_ADMIN_IDS`)
   - optionally `BACKEND_HOST_PORT` and `FRONTEND_HOST_PORT`
4. Build and run all services:

```bash
docker compose up -d --build
```

5. Verify backend:

```bash
curl -sS http://localhost:8000/health
```

6. Open services:
   - Web client: `http://<VM_IP>:8080`
   - Backend docs: `http://<VM_IP>:8000/docs`
7. After env/config changes, recreate containers:

```bash
docker compose up -d --force-recreate
```

## Lab 9 Artifacts

- Task 2 plan: `docs/lab9/task2-project-plan.md`
- Task 3 feedback log: `docs/lab9/task3-feedback-log.md`
- Task 5 slide outline: `docs/lab9/task5-presentation-outline.md`
- Submission checklist: `docs/lab9/submission-checklist.md`
