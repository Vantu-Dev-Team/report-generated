"""Ubidots API client — devices, variables, raw values."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx

from shared.exceptions import ExternalServiceError
from shared.settings import settings

logger = logging.getLogger(__name__)

_BASE_V2 = "https://industrial.api.ubidots.com/api/v2.0"
_BASE_V16 = "https://industrial.api.ubidots.com/api/v1.6"


class UbidotsClient:
    """HTTP client for the Ubidots Industrial API."""

    def __init__(self, token: str) -> None:
        self._token = token
        self._headers = {"X-Auth-Token": token}

    async def get_devices(self, page: int, page_size: int, search: str) -> dict[str, Any]:
        """List devices using v2.0 API with optional label search."""
        params: dict[str, Any] = {"page_size": page_size, "page": page}
        if search:
            params["label__icontains"] = search
        logger.info("Fetching Ubidots devices", extra={"page": page, "search": search})
        async with httpx.AsyncClient(timeout=settings.ubidots_api_timeout) as client:
            response = await client.get(
                f"{_BASE_V2}/devices/", headers=self._headers, params=params
            )
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Ubidots devices error {response.status_code}: {response.text[:200]}"
            )
        return response.json()

    async def get_variables(
        self, device_label: str, page: int, page_size: int, search: str
    ) -> dict[str, Any]:
        """List variables for a device using v2.0 ~label syntax."""
        params: dict[str, Any] = {"page_size": page_size, "page": page}
        if search:
            params["label__icontains"] = search
        logger.info(
            "Fetching Ubidots variables", extra={"device": device_label, "page": page}
        )
        async with httpx.AsyncClient(timeout=settings.ubidots_api_timeout) as client:
            response = await client.get(
                f"{_BASE_V2}/devices/~{device_label}/variables/",
                headers=self._headers,
                params=params,
            )
        if response.status_code != 200:
            raise ExternalServiceError(
                f"Ubidots variables error {response.status_code}: {response.text[:200]}"
            )
        return response.json()

    async def fetch_values_all_pages(
        self,
        device_label: str,
        var_label: str,
        start_ms: int,
        end_ms: int,
        tz_offset: float,
    ) -> list[dict[str, Any]]:
        """Fetch all raw values for a variable, following pagination."""
        all_points: list[dict[str, Any]] = []
        url = f"{_BASE_V16}/devices/{device_label}/{var_label}/values/"
        params: dict[str, Any] = {"start": start_ms, "end": end_ms, "page_size": 10000}
        logger.info(
            "Fetching Ubidots values",
            extra={"device": device_label, "variable": var_label},
        )
        async with httpx.AsyncClient(timeout=60) as client:
            while url:
                response = await client.get(url, headers=self._headers, params=params)
                if response.status_code != 200:
                    raise ExternalServiceError(
                        f"Ubidots values error {response.status_code}: {response.text[:200]}"
                    )
                data = response.json()
                results = data.get("results", [])
                tz_delta = timedelta(hours=tz_offset)
                for pt in results:
                    if pt.get("timestamp") is not None:
                        dt = datetime.fromtimestamp(pt["timestamp"] / 1000, tz=timezone.utc)
                        dt_local = dt + tz_delta
                        all_points.append({
                            "timestamp": dt_local.strftime("%Y-%m-%dT%H:%M:%S"),
                            "value": float(pt.get("value") or 0),
                        })
                # Follow pagination — next URL already includes params
                next_url = data.get("next")
                url = next_url if next_url else ""
                params = {}  # already encoded in next URL
        logger.info("Values fetched", extra={"count": len(all_points)})
        return all_points
