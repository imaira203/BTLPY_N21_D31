"""Topbar — page title, search, notifications, user avatar."""
from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from app.components.icons import Icon
from app.theme import COLORS


class _SearchField(QLineEdit):
    """QLineEdit with a leading magnifier icon painted inside the padding."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchInput")
        self.setPlaceholderText("Tìm kiếm nhanh…")
        self.setMinimumWidth(320)
        self.setFixedHeight(38)
        self._icon = Icon.pixmap("search", 16, COLORS.text_subtle)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        y = (self.height() - self._icon.height()) // 2
        p.drawPixmap(14, y, self._icon)
        p.end()


class Topbar(QWidget):
    def __init__(self, title: str = "Bảng điều khiển Admin",
                 subtitle: str = "Tổng quan hệ thống quản lý việc làm",
                 user_name: str = "Admin Sarah",
                 user_role: str = "Quản trị viên cao cấp",
                 parent=None):
        super().__init__(parent)
        self.setObjectName("Topbar")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # ---- left: title + subtitle ----
        titles = QVBoxLayout()
        titles.setSpacing(2)
        titles.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("PageSubtitle")
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)

        root.addLayout(titles)
        root.addStretch(1)

        # ---- search ----
        self.search = _SearchField()
        root.addWidget(self.search)

        # ---- notification bell with badge ----
        root.addWidget(self._build_notification())

        # ---- user chip ----
        root.addWidget(self._build_user_chip(user_name, user_role))

    # -- builders --
    def _build_notification(self) -> QWidget:
        container = QWidget()
        container.setFixedSize(42, 38)

        btn = QPushButton(container)
        btn.setObjectName("IconButton")
        btn.setIcon(Icon.get("bell", 18, COLORS.text_muted))
        btn.setIconSize(QSize(18, 18))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(38, 38)
        btn.setToolTip("Thông báo")

        badge = QLabel("3", container)
        badge.setObjectName("NotificationBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(16, 16)
        badge.move(24, 4)  # top-right corner of the 38x38 button

        return container

    def _build_user_chip(self, name: str, role: str) -> QWidget:
        chip = QWidget()
        row = QHBoxLayout(chip)
        row.setContentsMargins(6, 0, 6, 0)
        row.setSpacing(10)

        avatar = QLabel("AS")
        avatar.setObjectName("Avatar")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setContentsMargins(0, 0, 0, 0)
        n = QLabel(name);  n.setObjectName("UserName")
        r = QLabel(role);  r.setObjectName("UserRole")
        text_col.addWidget(n)
        text_col.addWidget(r)

        chevron = QLabel()
        chevron.setPixmap(Icon.pixmap("chevron_down", 14, COLORS.text_muted))

        row.addWidget(avatar)
        row.addLayout(text_col)
        row.addWidget(chevron)
        return chip
