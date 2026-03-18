"""Pydantic schemas for HTML report generation."""

from typing import Any
from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    config: dict[str, Any]
    components: list[dict[str, Any]]
    all_data: dict[str, list[dict[str, Any]]]


class GenerateReportResponse(BaseModel):
    html: str
