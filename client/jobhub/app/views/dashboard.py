"""Dashboard view — stats row, revenue chart, three recent-lists."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from app.components.badge import StatusBadge
from app.components.chart import RevenueChart
from app.components.icons import Icon
from app.components.stat_card import StatCard
from app.theme import COLORS


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        page = QWidget()
        scroll.setWidget(page)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(24)

        layout.addLayout(self._build_stats())
        layout.addWidget(self._build_chart_card())
        layout.addLayout(self._build_recent_row())
        layout.addStretch(1)

    # -------- stat cards --------
    def _build_stats(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setContentsMargins(0, 0, 0, 0)

        cards = [
            StatCard("users",      "Tổng người dùng",  "1,240",
                     accent=COLORS.primary, trend=("12.5%", "up")),
            StatCard("building",   "Tổng nhà tuyển dụng", "86",
                     accent=COLORS.info,    trend=("8.3%",  "up")),
            StatCard("briefcase",  "Tổng công việc",   "320",
                     accent=COLORS.success, trend=("15.2%", "up")),
            StatCard("activity",   "Hoạt động hôm nay", "45",
                     accent=COLORS.warning, trend=("3.1%",  "down"),
                     trend_hint="so với hôm qua"),
        ]
        for i, c in enumerate(cards):
            grid.addWidget(c, 0, i)
        for i in range(len(cards)):
            grid.setColumnStretch(i, 1)
        return grid

    # -------- revenue chart --------
    def _build_chart_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")

        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Báo cáo tổng thu nhập")
        title.setObjectName("SectionTitle")
        sub = QLabel("12 tháng qua")
        sub.setObjectName("StatLabel")

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(sub)

        months = ["Th1","Th2","Th3","Th4","Th5","Th6","Th7","Th8","Th9","Th10","Th11","Th12"]
        values = [15, 19, 17, 21, 22.35, 19, 16, 18, 20, 23, 29, 25]

        chart = RevenueChart(months, values)

        lay.addLayout(header)
        lay.addWidget(chart)
        return card

    # -------- three recent lists --------
    def _build_recent_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)

        row.addWidget(self._list_card(
            "Người dùng mới nhất",
            [
                ("NV", "Nguyễn Văn An",   "an.nguyen@email.com",   "15/03/2026", ("success", "Hoạt động")),
                ("TT", "Trần Thị Bình",    "binh.tran@email.com",   "20/03/2026", ("success", "Hoạt động")),
                ("LH", "Lê Hoàng Cường",  "cuong.le@email.com",    "22/03/2026", ("success", "Hoạt động")),
                ("PM", "Phạm Minh Đức",   "duc.pham@email.com",    "25/03/2026", ("warning", "Chờ duyệt")),
                ("VT", "Võ Thị Em",        "em.vo@email.com",       "01/04/2026", ("success", "Hoạt động")),
            ]
        ), 1)

        row.addWidget(self._list_card(
            "Nhà tuyển dụng nổi bật",
            [
                ("TC", "TechCorp Vietnam",     "hr@techcorp.vn",       "12 việc làm", ("info", "Đã xác minh")),
                ("SI", "StartUp Innovation",   "recruit@startup.vn",   "8 việc làm",  ("info", "Đã xác minh")),
                ("DS", "Design Studio",        "jobs@designstudio.vn", "5 việc làm",  ("neutral", "Mới")),
                ("DA", "Digital Agency",       "hr@digital.vn",        "3 việc làm",  ("neutral", "Mới")),
                ("CS", "Cloud Solutions",      "recruit@cloud.vn",     "9 việc làm",  ("info", "Đã xác minh")),
            ]
        ), 1)

        row.addWidget(self._list_card(
            "Công việc mới nhất",
            [
                ("FE", "Frontend Developer (React)", "TechCorp Vietnam",    "18 phút trước", ("info", "Remote")),
                ("UX", "UI/UX Designer",              "Design Studio",       "45 phút trước", ("neutral", "Toàn thời gian")),
                ("MK", "Marketing Manager",           "StartUp Innovation",  "1 giờ trước",   ("neutral", "Toàn thời gian")),
                ("BE", "Backend Engineer (Python)",   "Digital Agency",      "2 giờ trước",   ("warning", "Hybrid")),
                ("DO", "DevOps Engineer",             "Cloud Solutions",     "3 giờ trước",   ("info", "Remote")),
            ]
        ), 1)

        return row

    def _list_card(self, title: str, rows: list[tuple]) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 8)
        lay.setSpacing(8)

        header = QHBoxLayout()
        t = QLabel(title); t.setObjectName("SectionTitle")
        link = QLabel("Xem tất cả"); link.setObjectName("SectionLink")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(t); header.addStretch(1); header.addWidget(link)
        lay.addLayout(header)
        lay.addSpacing(4)

        for initials, name, sub, meta, badge in rows:
            lay.addWidget(self._list_item(initials, name, sub, meta, badge))

        return card

    def _list_item(self, initials, name, sub, meta, badge):
        row_w = QWidget()
        row = QHBoxLayout(row_w)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(12)

        avatar = QLabel(initials)
        avatar.setFixedSize(34, 34)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            f"background-color: {_deterministic_color(initials)};"
            "color: white; font-weight: 600; font-size: 12px; border-radius: 17px;"
        )

        col = QVBoxLayout(); col.setSpacing(2)
        n = QLabel(name);  n.setStyleSheet(f"color: {COLORS.text}; font-size: 13px; font-weight: 500;")
        s = QLabel(sub);   s.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 12px;")
        col.addWidget(n); col.addWidget(s)

        right = QVBoxLayout(); right.setSpacing(2); right.setAlignment(Qt.AlignmentFlag.AlignRight)
        m = QLabel(meta);  m.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 12px;")
        m.setAlignment(Qt.AlignmentFlag.AlignRight)
        b = StatusBadge(badge[1], badge[0])
        right_row = QHBoxLayout(); right_row.addStretch(1); right_row.addWidget(b)
        right.addLayout(right_row)
        right.addWidget(m)

        row.addWidget(avatar)
        row.addLayout(col, 1)
        row.addLayout(right)
        return row_w


_PALETTE = ["#6366F1", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#8B5CF6", "#EC4899"]

def _deterministic_color(seed: str) -> str:
    return _PALETTE[sum(ord(c) for c in seed) % len(_PALETTE)]
