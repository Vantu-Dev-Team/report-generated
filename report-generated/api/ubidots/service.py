"""Service layer for Ubidots proxy operations."""

import logging
from typing import Any

from ubidots.client import UbidotsClient
from ubidots.schemas import DataPoint, FetchValuesResponse

logger = logging.getLogger(__name__)


class UbidotsService:
    def __init__(self, client: UbidotsClient) -> None:
        self._client = client

    async def get_devices(self, page: int, page_size: int, search: str) -> dict[str, Any]:
        return await self._client.get_devices(page, page_size, search)

    async def get_variables(
        self, device_label: str, page: int, page_size: int, search: str
    ) -> dict[str, Any]:
        return await self._client.get_variables(device_label, page, page_size, search)

    async def fetch_values(
        self,
        device_label: str,
        var_label: str,
        start_ms: int,
        end_ms: int,
        tz_offset: float,
    ) -> FetchValuesResponse:
        points = await self._client.fetch_values_all_pages(
            device_label, var_label, start_ms, end_ms, tz_offset
        )
        return FetchValuesResponse(
            points=[DataPoint(**p) for p in points],
            count=len(points),
        )
