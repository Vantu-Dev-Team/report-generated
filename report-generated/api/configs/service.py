"""Business logic for report configuration management."""

import logging
from typing import Any

from configs.repository import ConfigRepository
from configs.schemas import ConfigDetail, ConfigListResponse, ConfigSummary

logger = logging.getLogger(__name__)


class ConfigService:
    def __init__(self, repository: ConfigRepository) -> None:
        self._repo = repository

    def list_configs(self) -> ConfigListResponse:
        items = self._repo.list_all()
        summaries = [
            ConfigSummary(
                config_id=i["config_id"],
                name=i["name"],
                component_count=int(i.get("component_count", 0)),
                created_at=i.get("created_at", ""),
                updated_at=i.get("updated_at", ""),
            )
            for i in items
        ]
        return ConfigListResponse(items=summaries, count=len(summaries))

    def get_config(self, config_id: str) -> ConfigDetail:
        item = self._repo.get(config_id)
        return ConfigDetail(**{k: item[k] for k in ConfigDetail.model_fields if k in item})

    def save_config(
        self, name: str, config: dict[str, Any], components: list, hist_rows: list
    ) -> ConfigDetail:
        item = self._repo.save(name, config, components, hist_rows)
        return ConfigDetail(**{k: item[k] for k in ConfigDetail.model_fields if k in item})

    def update_config(
        self,
        config_id: str,
        name: str,
        config: dict[str, Any],
        components: list,
        hist_rows: list,
    ) -> ConfigDetail:
        item = self._repo.update(config_id, name, config, components, hist_rows)
        return ConfigDetail(**{k: item[k] for k in ConfigDetail.model_fields if k in item})

    def delete_config(self, config_id: str) -> None:
        self._repo.delete(config_id)
