from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class AppConfig:
    tg_api_key: str
    admin_group_id: int
    webhook_url: str
    webhook_secret: str
    vk_access_token: str | None
    vk_api_version: str
    tg_proxy: str | None
    tg_mode: str
    actual_tables: tuple[int, ...]
    state_file: Path
    http_port: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        tg_api_key = os.getenv("TG_API_KEY")
        if not tg_api_key:
            raise ConfigError("TG_API_KEY не задан")

        admin_group_id_raw = os.getenv("ADMIN_GROUP_ID")
        if not admin_group_id_raw:
            raise ConfigError("ADMIN_GROUP_ID не задан")
        try:
            admin_group_id = int(admin_group_id_raw)
        except ValueError:
            raise ConfigError("ADMIN_GROUP_ID должен быть целым числом")

        webhook_url = os.getenv("WEBHOOK_URL", "")
        webhook_secret = os.getenv("WEBHOOK_SECRET", "")

        tables_raw = os.getenv("ACTUAL_TABLES", "")
        if tables_raw:
            try:
                actual_tables = tuple(int(t.strip()) for t in tables_raw.split(",") if t.strip())
            except ValueError:
                raise ConfigError("ACTUAL_TABLES должен быть списком чисел через запятую")
        else:
            actual_tables = (
                1, 2, 3, 4, 5, 6,
                11, 12, 13, 14, 15, 16, 17, 18,
                21, 22, 23, 24, 25,
                31, 32, 33, 34, 35, 36, 37, 38, 39,
            )

        return cls(
            tg_api_key=tg_api_key,
            admin_group_id=admin_group_id,
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            vk_access_token=os.getenv("VK_ACCESS_TOKEN"),
            vk_api_version=os.getenv("VK_API_VERSION", "5.199"),
            tg_proxy=os.getenv("TG_PROXY") or None,
            tg_mode=os.getenv("TG_MODE", "webhook").lower(),
            actual_tables=actual_tables,
            state_file=Path(os.getenv("STATE_FILE", "data/state.json")),
            http_port=int(os.getenv("HTTP_PORT", "8000")),
        )
