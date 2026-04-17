"""Nạp stylesheet từ file `.qss` trong resources (không nhúng QSS trong code Python)."""

from pathlib import Path

from PySide6.QtWidgets import QWidget

from ..paths import resource_ui
from ..ui_theme import get_ui_theme


def apply_qss(widget: QWidget, relative_path: str) -> None:
    path: Path = resource_ui(relative_path)
    if path.is_file():
        widget.setStyleSheet(path.read_text(encoding="utf-8"))


def apply_theme_qss(widget: QWidget, base: str) -> None:
    """Nạp `styles/{base}_light.qss` hoặc `{base}_dark.qss` theo ui_theme."""
    t = get_ui_theme()
    path = resource_ui(f"styles/{base}_{t}.qss")
    if not path.is_file():
        path = resource_ui(f"styles/{base}.qss")
    
    if path.is_file():
        widget.setStyleSheet(path.read_text(encoding="utf-8"))
