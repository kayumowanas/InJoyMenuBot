from __future__ import annotations

import httpx


class BackendError(Exception):
    pass


class InJoyApiClient:
    def __init__(self, *, base_url: str, api_token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_token = api_token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_token}"}

    async def list_menu(self, *, only_available: bool = True) -> list[dict[str, object]]:
        payload = await self._request_json(
            "GET", "/menu/", params={"only_available": str(only_available).lower()}
        )
        if isinstance(payload, list):
            return payload
        return []

    async def add_menu_item(
        self,
        *,
        name: str,
        price: float,
        category: str = "Other",
        description: str = "",
        available: bool = True,
    ) -> dict[str, object]:
        payload = await self._request_json(
            "POST",
            "/menu/",
            json={
                "name": name,
                "price": price,
                "category": category,
                "description": description,
                "available": available,
            },
        )
        if isinstance(payload, dict):
            return payload
        return {}

    async def list_admin_user_ids(self) -> list[int]:
        payload = await self._request_json("GET", "/admins/")
        if not isinstance(payload, list):
            return []

        ids: list[int] = []
        for raw_item in payload:
            if not isinstance(raw_item, dict):
                continue
            user_id = raw_item.get("user_id")
            try:
                ids.append(int(user_id))
            except (TypeError, ValueError):
                continue
        return sorted(set(ids))

    async def add_admin_user(self, *, user_id: int) -> dict[str, object]:
        payload = await self._request_json("POST", "/admins/", json={"user_id": user_id})
        if isinstance(payload, dict):
            return payload
        return {}

    async def remove_admin_user(self, *, user_id: int) -> None:
        await self._request("DELETE", f"/admins/{user_id}")

    async def delete_menu_item(self, *, item_id: int) -> None:
        await self._request("DELETE", f"/menu/{item_id}")

    async def delete_all_menu_items(self) -> dict[str, object]:
        payload = await self._request_json("DELETE", "/menu/")
        if isinstance(payload, dict):
            return payload
        return {}

    async def get_menu_item(self, *, item_id: int) -> dict[str, object]:
        payload = await self._request_json("GET", f"/menu/{item_id}")
        if isinstance(payload, dict):
            return payload
        return {}

    async def set_availability(self, *, item_id: int, available: bool) -> dict[str, object]:
        payload = await self._request_json(
            "PATCH",
            f"/menu/{item_id}/availability",
            json={"available": available},
        )
        if isinstance(payload, dict):
            return payload
        return {}

    async def set_all_availability(self, *, available: bool) -> dict[str, object]:
        payload = await self._request_json(
            "PATCH",
            "/menu/availability/all",
            json={"available": available},
        )
        if isinstance(payload, dict):
            return payload
        return {}

    async def update_menu_item(
        self,
        *,
        item_id: int,
        name: str,
        price: float,
        category: str,
        description: str,
        available: bool | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "name": name,
            "price": price,
            "category": category,
            "description": description,
        }
        if available is not None:
            payload["available"] = available

        response = await self._request_json("PUT", f"/menu/{item_id}", json=payload)
        if isinstance(response, dict):
            return response
        return {}

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> dict[str, object] | list[dict[str, object]]:
        response = await self._request(method, path, params=params, json=json)
        payload = response.json()
        if isinstance(payload, dict | list):
            return payload
        return {}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
                response = await client.request(
                    method,
                    path,
                    headers=self._headers(),
                    params=params,
                    json=json,
                )
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            detail = detail[:250] if detail else exc.response.reason_phrase
            raise BackendError(f"Backend returned {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise BackendError(f"Failed to connect to backend: {exc}") from exc
