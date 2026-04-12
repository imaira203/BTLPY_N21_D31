"""Lưu chế độ giao diện sáng/tối (áp dụng QSS toàn client)."""

from __future__ import annotations

import json
import logging
from typing import Literal

from .config import get_settings
from .paths import data_dir

logger = logging.getLogger("jobhub.client")

_THEME_FILE = data_dir() / "ui_theme.json"
UiTheme = Literal["light", "dark"]


def get_ui_theme() -> UiTheme:
    if _THEME_FILE.is_file():
        try:
            data = json.loads(_THEME_FILE.read_text(encoding="utf-8"))
            m = str(data.get("mode", "light")).lower().strip()
            if m == "dark":
                return "dark"
        except Exception as e:
            logger.debug("Đọc ui_theme.json lỗi: %s", e)
    s = get_settings()
    raw = str(getattr(s, "ui_theme", "light")).lower().strip()
    return "dark" if raw == "dark" else "light"


def set_ui_theme(mode: UiTheme) -> None:
    _THEME_FILE.write_text(
        json.dumps({"mode": mode}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def chart_facecolor() -> str:
    return "#1e293b" if get_ui_theme() == "dark" else "#fafafa"
