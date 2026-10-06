from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from seomind.google_oauth import GoogleOAuth, google_oauth


class GSCError(RuntimeError):
    pass


class SearchConsoleClient:
    def __init__(self, oauth: GoogleOAuth = google_oauth) -> None:
        self.oauth = oauth

    async def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {await self.oauth.access_token()}"}

    async def list_properties(self) -> list[dict[str, str]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://www.googleapis.com/webmasters/v3/sites",
                headers=await self._headers(),
            )
        if response.is_error:
            raise GSCError(f"Could not list Search Console properties: {response.text[:500]}")
        items = response.json().get("siteEntry", [])
        return [
            {
                "site_url": str(item.get("siteUrl", "")),
                "permission": str(item.get("permissionLevel", "")),
            }
            for item in items
            if item.get("siteUrl")
        ]

    async def query(
        self,
        site_url: str,
        *,
        start_date: str,
        end_date: str,
        dimensions: list[str] | None = None,
        row_limit: int = 25000,
        max_rows: int = 50000,
    ) -> list[dict[str, Any]]:
        endpoint = (
            "https://www.googleapis.com/webmasters/v3/sites/"
            f"{quote(site_url, safe='')}/searchAnalytics/query"
        )
        all_rows: list[dict[str, Any]] = []
        start_row = 0
        dims = dimensions or []
        headers = await self._headers()

        async with httpx.AsyncClient(timeout=60) as client:
            while start_row < max_rows:
                limit = min(row_limit, max_rows - start_row)
                payload: dict[str, Any] = {
                    "startDate": start_date,
                    "endDate": end_date,
                    "rowLimit": limit,
                    "startRow": start_row,
                    "dataState": "final",
                    "type": "web",
                }
                if dims:
                    payload["dimensions"] = dims
                response = await client.post(endpoint, headers=headers, json=payload)
                if response.is_error:
                    raise GSCError(f"Search Analytics query failed: {response.text[:700]}")
                rows = response.json().get("rows", []) or []
                all_rows.extend(rows)
                if len(rows) < limit:
                    break
                start_row += len(rows)
        return all_rows

    async def inspect_url(self, site_url: str, inspection_url: str, language: str) -> dict[str, Any]:
        payload = {
            "inspectionUrl": inspection_url,
            "siteUrl": site_url,
            "languageCode": language,
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers=await self._headers(),
                json=payload,
            )
        if response.is_error:
            raise GSCError(f"URL Inspection failed: {response.text[:700]}")
        return response.json()


gsc = SearchConsoleClient()
