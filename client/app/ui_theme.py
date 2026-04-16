"""Chốt giao diện sáng cho toàn client."""

from __future__ import annotations

import logging
from typing import Literal

from .config import get_settings

logger = logging.getLogger("jobhub.client")

UiTheme = Literal["light", "dark"]


def get_ui_theme() -> UiTheme:
    return "light"


def set_ui_theme(mode: UiTheme) -> None:
    logger.debug("Bỏ qua set_ui_theme(%s): ứng dụng chỉ dùng light mode.", mode)


def chart_facecolor() -> str:
    return "#fafafa"
