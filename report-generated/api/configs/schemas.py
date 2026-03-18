"""Pydantic schemas for report configuration CRUD."""

from typing import Any
from pydantic import BaseModel, Field


class SaveConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    config: dict[str, Any]
    components: list[dict[str, Any]]
    hist_rows: list[dict[str, Any]] = []


class UpdateConfigRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    config: dict[str, Any]
    components: list[dict[str, Any]]
    hist_rows: list[dict[str, Any]] = []


class ConfigSummary(BaseModel):
    config_id: str
    name: str
    component_count: int
    created_at: str
    updated_at: str


class ConfigDetail(ConfigSummary):
    config: dict[str, Any]
    components: list[dict[str, Any]]
    hist_rows: list[dict[str, Any]]


class ConfigListResponse(BaseModel):
    items: list[ConfigSummary]
    count: int
