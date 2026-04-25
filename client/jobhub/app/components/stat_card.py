"""Reusable stat card: icon in soft tinted square + value + label + trend."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.components.icons import Icon
from app.theme import COLORS


class StatCard(QFrame):
    """
    Parameters
    ----------
    icon_name : key into `icons.Icon`
    label     : small caption (e.g. "Tổng người dùng")
    value     : big headline number (str — format before passing)
    accent    : hex color used for icon tint + soft background
    trend     : optional (percentage_text, direction) where direction in {"up", "down"}
    trend_hint: optional trailing caption, e.g. "so với tháng trước"
    """

    def __init__(self, icon_name: str, label: str, value: str,
                 accent: str = COLORS.primary,
                 trend: tuple[str, str] | None = None,
                 trend_hint: str = "so với tháng trước",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumHeight(140)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ---- top row: icon badge + label ----
        top = QHBoxLayout()
        top.setSpacing(12)

        icon_badge = QLabel()
        icon_badge.setObjectName("StatIconBg")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setPixmap(Icon.pixmap(icon_name, 20, accent))
        icon_badge.setStyleSheet(
            f"background-color: {self._soften(accent)}; border-radius: 10px;"
        )

        label_w = QLabel(label)
        label_w.setObjectName("StatLabel")

        top.addWidget(icon_badge)
        top.addWidget(label_w)
        top.addStretch(1)

        # ---- value ----
        value_w = QLabel(value)
        value_w.setObjectName("StatValue")

        # ---- trend row ----
        trend_row = QHBoxLayout()
        trend_row.setSpacing(6)
        if trend is not None:
            pct, direction = trend
            up = direction == "up"
            arrow = QLabel()
            arrow.setPixmap(Icon.pixmap(
                "trend_up" if up else "trend_down", 14,
                COLORS.success if up else COLORS.danger,
            ))
            pct_w = QLabel(pct)
            pct_w.setObjectName("StatTrendUp" if up else "StatTrendDown")

            hint = QLabel(trend_hint)
            hint.setObjectName("StatTrendMuted")

            trend_row.addWidget(arrow)
            trend_row.addWidget(pct_w)
            trend_row.addWidget(hint)
            trend_row.addStretch(1)

        root.addLayout(top)
        root.addWidget(value_w)
        root.addLayout(trend_row)
        root.addStretch(1)

    @staticmethod
    def _soften(hex_color: str) -> str:
        """Return a very light tint of the accent color for the icon badge.
        This is a small curated map — keeps visuals predictable vs. runtime math."""
        table = {
            COLORS.primary: "#EEF2FF",
            COLORS.success: "#ECFDF5",
            COLORS.warning: "#FFFBEB",
            COLORS.danger:  "#FEF2F2",
            COLORS.info:    "#EFF6FF",
        }
        return table.get(hex_color, "#F3F4F6")
