"""Status pill — colored badges driven by QSS `badge` dynamic property."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel


class StatusBadge(QLabel):
    VARIANTS = {"success", "warning", "danger", "info", "neutral"}

    def __init__(self, text: str, variant: str = "neutral", parent=None):
        super().__init__(text, parent)
        variant = variant if variant in self.VARIANTS else "neutral"
        self.setProperty("badge", variant)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(22)
        # Ensure pill doesn't stretch to fill a cell.
        self.setMaximumWidth(120)
