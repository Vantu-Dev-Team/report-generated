"""CRUD routes for report configurations."""

from fastapi import APIRouter

from configs.repository import ConfigRepository
from configs.schemas import (
    ConfigDetail,
    ConfigListResponse,
    SaveConfigRequest,
    UpdateConfigRequest,
)
from configs.service import ConfigService

router = APIRouter(prefix="/configs", tags=["Configs"])


def _get_service() -> ConfigService:
    return ConfigService(ConfigRepository())


@router.get("", response_model=ConfigListResponse, summary="List all saved configurations")
async def list_configs() -> ConfigListResponse:
    return _get_service().list_configs()


@router.get("/{config_id}", response_model=ConfigDetail, summary="Get a configuration by ID")
async def get_config(config_id: str) -> ConfigDetail:
    return _get_service().get_config(config_id)


@router.post(
    "", response_model=ConfigDetail, status_code=201, summary="Save a new configuration"
)
async def save_config(body: SaveConfigRequest) -> ConfigDetail:
    return _get_service().save_config(body.name, body.config, body.components, body.hist_rows)


@router.put(
    "/{config_id}", response_model=ConfigDetail, summary="Update an existing configuration"
)
async def update_config(config_id: str, body: UpdateConfigRequest) -> ConfigDetail:
    return _get_service().update_config(
        config_id, body.name, body.config, body.components, body.hist_rows
    )


@router.delete("/{config_id}", status_code=204, summary="Delete a configuration")
async def delete_config(config_id: str) -> None:
    _get_service().delete_config(config_id)
