"""DynamoDB repository for report configurations."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from shared.exceptions import ConfigNotFoundException
from shared.settings import settings

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ConfigRepository:
    """DynamoDB repository for report configurations.

    Data model:
        PK: config_id (UUID)
        SK: #REPORT_CONFIG (fixed)
    """

    def __init__(self) -> None:
        self._table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
            settings.table_name
        )

    def list_all(self) -> list[dict[str, Any]]:
        """Return summary of all configs sorted by updated_at desc."""
        logger.info("Listing all report configs", extra={"table": settings.table_name})
        response = self._table.scan(
            FilterExpression=Key("SK").eq(settings.sk_report_config),
            ProjectionExpression="config_id, #n, created_at, updated_at, component_count",
            ExpressionAttributeNames={"#n": "name"},
        )
        items = response.get("Items", [])
        while "LastEvaluatedKey" in response:
            response = self._table.scan(
                FilterExpression=Key("SK").eq(settings.sk_report_config),
                ProjectionExpression="config_id, #n, created_at, updated_at, component_count",
                ExpressionAttributeNames={"#n": "name"},
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return sorted(items, key=lambda x: x.get("updated_at", ""), reverse=True)

    def get(self, config_id: str) -> dict[str, Any]:
        """Return full config or raise ConfigNotFoundException."""
        logger.info("Getting config", extra={"config_id": config_id})
        response = self._table.get_item(
            Key={"PK": config_id, "SK": settings.sk_report_config}
        )
        item = response.get("Item")
        if not item:
            raise ConfigNotFoundException(config_id)
        return item

    def save(
        self,
        name: str,
        config: dict[str, Any],
        components: list[dict[str, Any]],
        hist_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create a new config. Returns saved item."""
        config_id = str(uuid.uuid4())
        now = _now_iso()
        item: dict[str, Any] = {
            "PK": config_id,
            "SK": settings.sk_report_config,
            "config_id": config_id,
            "name": name,
            "created_at": now,
            "updated_at": now,
            "component_count": len(components),
            "config": config,
            "components": components,
            "hist_rows": hist_rows,
        }
        logger.info("Saving config", extra={"config_id": config_id, "name": name})
        self._table.put_item(Item=item)
        return item

    def update(
        self,
        config_id: str,
        name: str,
        config: dict[str, Any],
        components: list[dict[str, Any]],
        hist_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Update existing config. Raises ConfigNotFoundException if missing."""
        existing = self.get(config_id)  # raises if not found
        now = _now_iso()
        item = {
            **existing,
            "name": name,
            "updated_at": now,
            "component_count": len(components),
            "config": config,
            "components": components,
            "hist_rows": hist_rows,
        }
        logger.info("Updating config", extra={"config_id": config_id, "name": name})
        self._table.put_item(Item=item)
        return item

    def delete(self, config_id: str) -> None:
        """Delete config. Raises ConfigNotFoundException if missing."""
        self.get(config_id)  # raises if not found
        logger.info("Deleting config", extra={"config_id": config_id})
        self._table.delete_item(Key={"PK": config_id, "SK": settings.sk_report_config})
