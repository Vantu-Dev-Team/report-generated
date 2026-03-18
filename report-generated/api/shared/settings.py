"""Pydantic Settings — all configuration from environment variables."""

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    aws_region: str = Field(default=os.environ.get("AWS_REGION", "us-east-1"))
    environment: str = Field(default=os.environ.get("ENVIRONMENT", "dev"))
    table_name: str = Field(
        default=os.environ.get("TABLE_NAME", "us-east-1-report-generated-data-dev")
    )
    log_level: str = Field(default=os.environ.get("LOG_LEVEL", "INFO"))

    # Ubidots
    ubidots_token: str = Field(default=os.environ.get("UBIDOTS_TOKEN", ""))
    ubidots_base_url: str = Field(default="https://industrial.api.ubidots.com")
    ubidots_api_timeout: int = 20

    # DynamoDB SK patterns
    sk_report_config: str = "#REPORT_CONFIG"


settings = Settings()
