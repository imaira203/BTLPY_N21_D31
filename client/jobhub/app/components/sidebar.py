"""Sidebar navigation — brand, nav items, upgrade card, logout."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget,
)

from app.components.icons import Icon
from app.theme import COLORS


class _NavItem(QPushButton):
    def __init__(self, icon_name: str, label: str, parent=None):
        super().__init__(label, parent)
        self.setObjectName("NavItem")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_name = icon_name
        self._refresh_icon()
        self.setIconSize(self.iconSize() * 0 + self._icon_size())
        self.toggled.connect(self._refresh_icon)

    @staticmethod
    def _icon_size():
        from PyQt6.QtCore import QSize
        return QSize(18, 18)

    def _refresh_icon(self, *_):
        color = COLORS.primary if self.isChecked() else COLORS.text_muted
        self.setIcon(Icon.get(self._icon_name, 18, color))


class Sidebar(QWidget):
    """Emits `navigate(str)` with the nav key when user clicks an item."""

    navigate = pyqtSignal(str)
    logout_requested = pyqtSignal()

    NAV = [
        ("dashboard", "dashboard", "Bảng điều khiển"),
        ("users", "users", "Người dùng"),
        ("recruiters", "building", "Nhà tuyển dụng"),
        ("jobs", "briefcase", "Công việc"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(240)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 20, 16, 20)
        root.setSpacing(6)

        root.addLayout(self._build_brand())
        root.addSpacing(24)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, _NavItem] = {}
        for key, icon, label in self.NAV:
            btn = _NavItem(icon, f"  {label}")
            btn.clicked.connect(lambda _=False, k=key: self.navigate.emit(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            root.addWidget(btn)

        root.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        root.addWidget(self._build_upgrade_card())
        root.addSpacing(8)
        root.addWidget(self._build_logout())

        # default
        self.set_active("dashboard")

    # -- public API --
    def set_active(self, key: str) -> None:
        if key in self._buttons:
            self._buttons[key].setChecked(True)

    # -- builders --
    def _build_brand(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(4, 0, 0, 0)
        row.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(Icon.pixmap("logo", 22, COLORS.primary))
        logo.setFixedSize(32, 32)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            f"background-color: {COLORS.primary_soft}; border-radius: 8px;"
        )

        brand = QLabel("JobHub")
        brand.setObjectName("SidebarBrand")

        row.addWidget(logo)
        row.addWidget(brand)
        row.addStretch(1)
        return row

    def _build_upgrade_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("UpgradeCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        icon = QLabel()
        icon.setPixmap(Icon.pixmap("trend_up", 20, COLORS.primary))

        title = QLabel("Nâng cấp JobHub Pro")
        title.setObjectName("UpgradeTitle")

        body = QLabel("Mở khóa báo cáo nâng cao, quản lý phân quyền và nhiều tính năng hơn.")
        body.setObjectName("UpgradeBody")
        body.setWordWrap(True)

        btn = QPushButton("Nâng cấp ngay")
        btn.setObjectName("PrimaryButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        lay.addWidget(icon)
        lay.addWidget(title)
        lay.addWidget(body)
        lay.addSpacing(4)
        lay.addWidget(btn)
        return card

    def _build_logout(self) -> QPushButton:
        btn = QPushButton("  Đăng xuất")
        btn.setObjectName("LogoutButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIcon(Icon.get("logout", 18, COLORS.text_muted))
        btn.clicked.connect(self.logout_requested.emit)
        return btn
