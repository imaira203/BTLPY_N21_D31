from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_CLIENT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _CLIENT_ROOT / ".env"

logger = logging.getLogger("jobhub.client")


class ClientSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_base_url: str = Field(
        default="http://127.0.0.1:8000/api",
        description="URL gốc API — phải kết thúc bằng /api (hoặc chỉ host:port, client sẽ thêm /api).",
    )

    ui_theme: str = Field(
        default="light",
        description="light hoặc dark — mặc định khi chưa có jobhub_data/ui_theme.json",
    )

    use_mock_data: bool = Field(
        default=False,
        validation_alias=AliasChoices("USE_MOCK_DATA", "JOBHUB_USE_MOCK_DATA"),
        description="True = demo offline: API trả dữ liệu mẫu, không gọi máy chủ.",
    )

    mock_user_role: str = Field(
        default="candidate",
        validation_alias=AliasChoices("MOCK_USER_ROLE", "JOBHUB_MOCK_USER_ROLE"),
        description="Khi use_mock_data: role cho /users/me — candidate | hr | admin.",
    )


@lru_cache(maxsize=1)
def get_settings() -> ClientSettings:
    return ClientSettings()


def _ensure_api_suffix(base: str) -> str:
    """Luôn trả về .../api để path trong jobhub_api là /health, /auth/... → .../api/health, .../api/auth/..."""
    s = base.strip().rstrip("/")
    if s.lower().endswith("/api"):
        return s
    return f"{s}/api"


def load_api_base() -> str:
    return _ensure_api_suffix(get_settings().api_base_url.strip())


def log_client_startup() -> None:
    logger.info("Thư mục client: %s", _CLIENT_ROOT)
    logger.info("File .env: %s | tồn tại=%s", _ENV_FILE.resolve(), _ENV_FILE.is_file())
    s = get_settings()
    raw = s.api_base_url.strip().rstrip("/")
    eff = load_api_base()
    logger.info("API_BASE_URL (trong .env)=%s", raw)
    if raw.rstrip("/") != eff.rstrip("/"):
        logger.info("API gốc dùng cho request (đã thêm /api nếu thiếu)=%s", eff)
    else:
        logger.info("API gốc dùng cho request=%s", eff)
    logger.debug("UI_THEME env default (when ui_theme.json missing)=%s", s.ui_theme)
    if s.use_mock_data:
        logger.info("JOBHUB_USE_MOCK_DATA=1 — chế độ demo, không gọi API thật (role mock=%s)", s.mock_user_role)
