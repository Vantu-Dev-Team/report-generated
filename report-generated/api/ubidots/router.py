"""Ubidots proxy routes — devices, variables, values."""

from typing import Any, Optional

from fastapi import APIRouter, Header, Query

from shared.settings import settings
from ubidots.client import UbidotsClient
from ubidots.schemas import FetchValuesRequest, FetchValuesResponse
from ubidots.service import UbidotsService

router = APIRouter(prefix="/ubidots", tags=["Ubidots"])


def _get_service(x_ubidots_token: Optional[str] = None) -> UbidotsService:
    """Build service using header token or fall back to env var."""
    token = x_ubidots_token or settings.ubidots_token
    return UbidotsService(UbidotsClient(token))


@router.get("/devices", summary="List Ubidots devices (paginated, searchable)")
async def get_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str = Query(""),
    x_ubidots_token: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    return await _get_service(x_ubidots_token).get_devices(page, page_size, search)


@router.get(
    "/devices/{device_label}/variables",
    summary="List variables for a device (paginated, searchable)",
)
async def get_variables(
    device_label: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    search: str = Query(""),
    x_ubidots_token: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    return await _get_service(x_ubidots_token).get_variables(device_label, page, page_size, search)


@router.post(
    "/data/values",
    response_model=FetchValuesResponse,
    summary="Fetch raw variable values",
)
async def fetch_values(
    body: FetchValuesRequest,
    x_ubidots_token: Optional[str] = Header(default=None),
) -> FetchValuesResponse:
    return await _get_service(x_ubidots_token).fetch_values(
        body.device_label, body.var_label, body.start_ms, body.end_ms, body.tz_offset
    )
