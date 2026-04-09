# Task 2 - Project Idea and Plan

## Project idea

- End-user:
  - Cafe guests (menu browsing).
  - Cafe staff (menu administration).
- Problem:
  - Guests need a fast digital menu that is easy to access from browser.
  - Staff need a simple way to keep menu data up-to-date without manual database edits.
- Product idea in one sentence:
  - InJoy Menu Platform is a deployable menu system with a guest-facing web client and Telegram-based staff admin panel.
- Core feature:
  - Real-time menu publishing: admins update menu items and guests immediately see the current available menu.

## Version plan

## Version 1 (core value)

- Guest can open web client and browse available menu items grouped by category.
- Backend stores menu in SQLite and serves data through API.
- Staff can update menu through existing admin panel.
- Output:
  - Working dockerized product shown to TA.

## Version 2 (improvements)

- Added public read-only endpoint for web client (`/public/menu`) for cleaner deployment.
- Improved documentation and deployment instructions for Ubuntu VM.
- Added submission artifacts (plan, TA feedback log, slide outline, checklist).
- Reworked README for hackathon requirements and demo assets.

## TA feedback addressed in Version 2

- Ensure product remains usable on VM where Telegram may be restricted.
- Improve submission quality: explicit structure, deployment clarity, and demo materials.
