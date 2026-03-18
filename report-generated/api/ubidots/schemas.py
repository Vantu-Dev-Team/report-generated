"""Pydantic schemas for Ubidots proxy endpoints."""

from pydantic import BaseModel


class FetchValuesRequest(BaseModel):
    device_label: str
    var_label: str
    start_ms: int
    end_ms: int
    tz_offset: float = -5


class DataPoint(BaseModel):
    timestamp: str
    value: float


class FetchValuesResponse(BaseModel):
    points: list[DataPoint]
    count: int
