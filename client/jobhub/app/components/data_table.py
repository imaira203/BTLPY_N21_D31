"""DataTable — QTableWidget with generous row height, hover highlight,
badge column, and an icon-button action column.

Typical usage:
    columns = [
        Col("user",    "Người dùng",  stretch=True),
        Col("email",   "Email"),
        Col("joined",  "Ngày tham gia"),
        Col("status",  "Trạng thái", kind="badge"),
        Col("actions", "",            kind="actions"),
    ]
    table = DataTable(columns)
    table.set_rows(rows)  # list of dicts keyed by Col.key
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.components.badge import StatusBadge
from app.components.icons import Icon
from app.theme import COLORS


# ------------------------------ config types ------------------------------- #
@dataclass
class Col:
    key: str
    title: str
    kind: str = "text"       # "text" | "badge" | "actions" | "avatar"
    stretch: bool = False
    width: int | None = None


@dataclass
class Action:
    name: str                                 # icon key, e.g. "eye"
    tooltip: str
    color: str = COLORS.text_muted
    handler: Callable[[dict], None] | None = None


# ------------------------------ widgets ------------------------------------ #
class _AvatarCell(QWidget):
    """Compact avatar + two-line text used for the "user" column."""

    _PALETTE = ["#6366F1", "#10B981", "#F59E0B", "#EF4444",
                "#3B82F6", "#8B5CF6", "#EC4899"]

    def __init__(self, name: str, sub: str, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(10)

        avatar = QLabel(self._initials(name))
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background-color: {self._color_for(name)};"
            "color: white; font-weight: 600; font-size: 12px;"
            "border-radius: 16px;"
        )

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        n = QLabel(name)
        n.setStyleSheet(f"color: {COLORS.text}; font-size: 13px; font-weight: 500;")
        s = QLabel(sub)
        s.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 12px;")
        text_col.addWidget(n)
        text_col.addWidget(s)

        row.addWidget(avatar)
        row.addLayout(text_col)
        row.addStretch(1)

    @staticmethod
    def _initials(name: str) -> str:
        parts = [p for p in name.split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def _color_for(self, name: str) -> str:
        return self._PALETTE[sum(ord(c) for c in name) % len(self._PALETTE)]


class _ActionCell(QWidget):
    def __init__(self, actions: list[Action], row_data: dict, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(4)
        row.addStretch(1)

        for a in actions:
            btn = QPushButton()
            btn.setObjectName("RowActionButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(Icon.get(a.name, 16, a.color))
            btn.setIconSize(QSize(16, 16))
            btn.setToolTip(a.tooltip)
            btn.setFixedSize(28, 28)
            if a.handler is not None:
                btn.clicked.connect(lambda _=False, fn=a.handler, d=row_data: fn(d))
            row.addWidget(btn)


# ------------------------------ table -------------------------------------- #
class DataTable(QWidget):
    action_triggered = pyqtSignal(str, dict)  # (action_name, row_data)

    def __init__(self, columns: list[Col], actions: list[Action] | None = None,
                 parent=None):
        super().__init__(parent)
        self._cols = columns
        self._actions = actions or []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels([c.title for c in columns])
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setDefaultSectionSize(56)

        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setHighlightSections(False)
        for i, col in enumerate(columns):
            if col.stretch:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            elif col.width:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(i, col.width)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)

    # -------- public API --------
    def set_rows(self, rows: Iterable[dict]) -> None:
        rows = list(rows)
        self.table.setRowCount(len(rows))
        for r, data in enumerate(rows):
            for c, col in enumerate(self._cols):
                self._write_cell(r, c, col, data)

    # -------- internals --------
    def _write_cell(self, r: int, c: int, col: Col, data: dict) -> None:
        if col.kind == "avatar":
            name = data.get(col.key, "")
            sub  = data.get(f"{col.key}_sub", "")
            self.table.setCellWidget(r, c, _AvatarCell(name, sub))
        elif col.kind == "badge":
            variant, text = _coerce_badge(data.get(col.key))
            cell = QWidget()
            row = QHBoxLayout(cell)
            row.setContentsMargins(12, 0, 12, 0)
            row.addWidget(StatusBadge(text, variant))
            row.addStretch(1)
            self.table.setCellWidget(r, c, cell)
        elif col.kind == "actions":
            handlers = [_wrap(a, self.action_triggered) for a in self._actions]
            self.table.setCellWidget(r, c, _ActionCell(handlers, data))
        else:  # "text"
            value = str(data.get(col.key, ""))
            item = QTableWidgetItem(value)
            item.setForeground(QColor(COLORS.text))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            f = QFont("Inter"); f.setPointSize(10)
            item.setFont(f)
            self.table.setItem(r, c, item)


# ------------------------------ helpers ------------------------------------ #
def _coerce_badge(value) -> tuple[str, str]:
    """Accept either a string (treated as a neutral label) or (variant, label)."""
    if isinstance(value, tuple) and len(value) == 2:
        return value
    return "neutral", str(value or "—")


def _wrap(action: Action, signal) -> Action:
    """Wrap the user's handler so we also fire the widget-level signal."""
    original = action.handler

    def _h(row):
        if original:
            original(row)
        signal.emit(action.name, row)

    return Action(action.name, action.tooltip, action.color, _h)
