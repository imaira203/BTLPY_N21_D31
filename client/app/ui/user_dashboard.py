"""UserDashboard — pure Python, không dùng .ui file."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import (
    QColor, QIcon, QPainter, QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QGraphicsDropShadowEffect,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..session_store import clear_session

# ══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════
_SIDEBAR_BG   = "#0f172a"
_SIDEBAR_W    = 210
_NAV_ACTIVE   = "#6366f1"
_NAV_HOVER_BG = "#1e293b"
_NAV_INACT_IC = "#94a3b8"
_NAV_INACT_TX = "#94a3b8"
_CONTENT_BG   = "#f8fafc"
_TOPBAR_BG    = "#ffffff"
_TOPBAR_H     = 72
_BORDER       = "#e2e8f0"
_TXT_H        = "#111827"
_TXT_S        = "#374151"
_TXT_M        = "#6b7280"
_CARD_BG      = "#ffffff"
_INDIGO       = "#6366f1"
_INDIGO_DARK  = "#4f46e5"

# Company logo avatar palette
_LOGO_PALETTE = [
    ("#dcfce7", "#16a34a"),   # green
    ("#dbeafe", "#2563eb"),   # blue
    ("#fee2e2", "#dc2626"),   # red
    ("#f3e8ff", "#9333ea"),   # purple
    ("#fef3c7", "#d97706"),   # amber
    ("#ccfbf1", "#0d9488"),   # teal
    ("#fce7f3", "#db2777"),   # pink
    ("#e0e7ff", "#6366f1"),   # indigo
]

_ICONS = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"
_HIST_PAGE_SIZE = 5

_HIST_DATA = [
    ("TechCorp Vietnam",    "Hồ Chí Minh, VN",   "Senior Frontend Engineer",   "Oct 12, 2023", "Đang xử lý"),
    ("StartUp Innovation",  "Hà Nội, VN",         "Fullstack Developer",        "Oct 10, 2023", "Đã xem"),
    ("Creative Studio",     "Remote",             "UI/UX Designer",             "Oct 05, 2023", "Phê duyệt"),
    ("Digital Agency",      "Đà Nẵng, VN",        "Marketing Associate",        "Sep 28, 2023", "Từ chối"),
    ("Global IT Solutions", "Singapore (Remote)", "Project Manager",            "Sep 25, 2023", "Đang xử lý"),
    ("CloudTech Asia",      "Hà Nội, VN",         "DevOps Engineer",            "Sep 20, 2023", "Đã xem"),
    ("Fintech Pro",         "TP. HCM, VN",        "Backend Developer (Python)", "Sep 15, 2023", "Phê duyệt"),
    ("MediaHub VN",         "Remote",             "Content Strategist",         "Sep 10, 2023", "Đang xử lý"),
    ("EduSoft Corp",        "Hà Nội, VN",         "React Native Developer",     "Sep 05, 2023", "Từ chối"),
    ("VietAI Lab",          "TP. HCM, VN",        "ML Engineer",               "Aug 28, 2023", "Đã xem"),
    ("ShipFast Logistics",  "Đà Nẵng, VN",        "System Analyst",            "Aug 20, 2023", "Đang xử lý"),
    ("HealthTech VN",       "Hà Nội, VN",         "QA Engineer",               "Aug 15, 2023", "Phê duyệt"),
    ("DataBridge Corp",     "Hà Nội, VN",         "Data Analyst",              "Aug 08, 2023", "Từ chối"),
    ("ByteWave Studio",     "Remote",             "iOS Developer",             "Jul 30, 2023", "Phê duyệt"),
    ("NexGen AI",           "TP. HCM, VN",        "AI Research Engineer",      "Jul 22, 2023", "Đã xem"),
]

# Gradient palette for company avatars (stops, text-color)
_GRAD_PALETTE = [
    ("stop:0 #6366f1,stop:1 #8b5cf6", "white"),
    ("stop:0 #0ea5e9,stop:1 #2563eb", "white"),
    ("stop:0 #f59e0b,stop:1 #f97316", "white"),
    ("stop:0 #10b981,stop:1 #059669", "white"),
    ("stop:0 #ec4899,stop:1 #db2777", "white"),
    ("stop:0 #14b8a6,stop:1 #0d9488", "white"),
    ("stop:0 #ef4444,stop:1 #dc2626", "white"),
    ("stop:0 #8b5cf6,stop:1 #7c3aed", "white"),
    ("stop:0 #f97316,stop:1 #ea580c", "white"),
    ("stop:0 #06b6d4,stop:1 #0891b2", "white"),
    ("stop:0 #84cc16,stop:1 #65a30d", "white"),
    ("stop:0 #a855f7,stop:1 #9333ea", "white"),
    ("stop:0 #fb7185,stop:1 #f43f5e", "white"),
    ("stop:0 #34d399,stop:1 #10b981", "white"),
    ("stop:0 #60a5fa,stop:1 #3b82f6", "white"),
]

_STATUS_STYLE = {
    "Đang xử lý": ("#92400e", "#fef3c7", "#d97706", "Đang xử lý", "ic_clock.svg"),
    "Đã xem":     ("#065f46", "#d1fae5", "#10b981", "Đã xem",     "ic_eye2.svg"),
    "Phê duyệt":  ("#1e3a8a", "#dbeafe", "#3b82f6", "Phê duyệt",  "ic_check.svg"),
    "Từ chối":    ("#991b1b", "#fee2e2", "#ef4444", "Từ chối",    "ic_x.svg"),
}


# ══════════════════════════════════════════════════════════════
#  SVG HELPERS
# ══════════════════════════════════════════════════════════════
def _svg_pm(name: str, size: int, color: str) -> QPixmap:
    p = _ICONS / name
    if not p.exists():
        return QPixmap()
    raw  = p.read_text(encoding="utf-8").replace("currentColor", color)
    data = QByteArray(raw.encode())
    rdr  = QSvgRenderer(data)
    pm   = QPixmap(size, size)
    pm.fill(Qt.transparent)
    pt   = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing)
    rdr.render(pt)
    pt.end()
    return pm


def _shadow(w: QWidget, blur: int = 14, dy: int = 4,
            alpha: int = 15) -> QGraphicsDropShadowEffect:
    fx = QGraphicsDropShadowEffect(w)
    fx.setBlurRadius(blur)
    fx.setOffset(0, dy)
    fx.setColor(QColor(0, 0, 0, alpha))
    w.setGraphicsEffect(fx)
    return fx


def _btn_shadow(w: QWidget, color_hex: str, alpha: int = 55) -> None:
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    fx = QGraphicsDropShadowEffect(w)
    fx.setBlurRadius(14)
    fx.setOffset(0, 5)
    fx.setColor(QColor(r, g, b, alpha))
    w.setGraphicsEffect(fx)


# ══════════════════════════════════════════════════════════════
#  NAV BUTTON
# ══════════════════════════════════════════════════════════════
class _NavBtn(QWidget):

    _SS_ACTIVE = f"background:{_NAV_ACTIVE}; border-radius:10px;"
    _SS_INACT  = "background:transparent; border-radius:10px;"
    _SS_HOV    = f"background:{_NAV_HOVER_BG}; border-radius:10px;"

    _LOGOUT_IC_INACT = "#fca5a5"
    _LOGOUT_TX_INACT = "#94a3b8"
    _LOGOUT_IC_HOV   = "#ef4444"
    _LOGOUT_TX_HOV   = "#ef4444"

    def __init__(self, icon_svg: str, label: str,
                 logout: bool = False, parent=None):
        super().__init__(parent)
        self._icon_svg = icon_svg
        self._active   = False
        self._logout   = logout
        self._cb: Callable | None = None
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background:transparent;")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._pill = QFrame()
        self._pill.setStyleSheet(self._SS_INACT)
        pill_lo = QHBoxLayout(self._pill)
        pill_lo.setContentsMargins(14, 0, 12, 0)
        pill_lo.setSpacing(10)
        pill_lo.setAlignment(Qt.AlignVCenter)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(18, 18)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background:transparent; border:none;")

        self._txt = QLabel(label)
        self._txt.setStyleSheet(
            f"background:transparent; border:none; "
            f"color:{self._LOGOUT_TX_INACT if logout else _NAV_INACT_TX};"
            "font-size:13px; font-weight:500;"
        )

        pill_lo.addWidget(self._icon_lbl)
        pill_lo.addWidget(self._txt, 1)
        outer.addWidget(self._pill, 1)
        self._set_inactive_style()

    def _set_inactive_style(self):
        ic = self._LOGOUT_IC_INACT if self._logout else _NAV_INACT_IC
        tx = self._LOGOUT_TX_INACT if self._logout else _NAV_INACT_TX
        self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 18, ic))
        self._txt.setStyleSheet(
            f"background:transparent; border:none; color:{tx};"
            "font-size:13px; font-weight:500;"
        )

    def _set_active_style(self):
        self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 18, "#ffffff"))
        self._txt.setStyleSheet(
            "background:transparent; border:none; color:#ffffff;"
            "font-size:13px; font-weight:700;"
        )

    def _set_hover_style(self):
        if self._logout:
            self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 18, self._LOGOUT_IC_HOV))
            self._txt.setStyleSheet(
                f"background:transparent; border:none; color:{self._LOGOUT_TX_HOV};"
                "font-size:13px; font-weight:500;"
            )
        else:
            self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 18, "#cbd5e1"))
            self._txt.setStyleSheet(
                "background:transparent; border:none; color:#cbd5e1;"
                "font-size:13px; font-weight:500;"
            )

    def set_active(self, v: bool) -> None:
        self._active = v
        if v:
            self._pill.setStyleSheet(self._SS_ACTIVE)
            self._set_active_style()
        else:
            self._pill.setStyleSheet(self._SS_INACT)
            self._set_inactive_style()

    def on_click(self, fn: Callable) -> None:
        self._cb = fn

    def enterEvent(self, e):
        if not self._active:
            self._pill.setStyleSheet(self._SS_HOV)
            self._set_hover_style()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._active:
            self._pill.setStyleSheet(self._SS_INACT)
            self._set_inactive_style()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._cb:
            self._cb()
        super().mousePressEvent(e)


# ══════════════════════════════════════════════════════════════
#  HOVER ROW CARD
# ══════════════════════════════════════════════════════════════
class _HoverCard(QFrame):
    """Row card with smooth hover background transition."""

    _SS_NORMAL = (
        "QFrame{background:white; border:1px solid #f1f5f9;"
        "border-radius:12px;}"
    )
    _SS_HOVER = (
        "QFrame{background:#fafbff; border:1px solid #e0e7ff;"
        "border-radius:12px;}"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(self._SS_NORMAL)
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, e):
        self.setStyleSheet(self._SS_HOVER)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet(self._SS_NORMAL)
        super().leaveEvent(e)


# ══════════════════════════════════════════════════════════════
#  USER DASHBOARD
# ══════════════════════════════════════════════════════════════
class UserDashboard:
    """Dashboard cho Ứng viên — pure Python, không .ui file."""

    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout

        self.win = QMainWindow()
        self.win.setWindowTitle("JobHub — Ứng viên")
        self.win.setMinimumSize(1100, 680)

        central = QWidget()
        self.win.setCentralWidget(central)
        root_lo = QHBoxLayout(central)
        root_lo.setContentsMargins(0, 0, 0, 0)
        root_lo.setSpacing(0)

        root_lo.addWidget(self._build_sidebar())

        right = QWidget()
        right.setStyleSheet(f"background:{_CONTENT_BG};")
        right_lo = QVBoxLayout(right)
        right_lo.setContentsMargins(0, 0, 0, 0)
        right_lo.setSpacing(0)

        right_lo.addWidget(self._build_topbar())

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background:{_CONTENT_BG};")
        right_lo.addWidget(self._stack, 1)

        self._stack.addWidget(self._build_home_page())
        self._stack.addWidget(self._build_history_page())
        self._stack.addWidget(self._build_saved_page())
        self._stack.addWidget(self._build_profile_page())

        root_lo.addWidget(right, 1)

        self._nav_btns[0].set_active(True)
        self._stack.setCurrentIndex(0)

    # ══════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════
    def _build_sidebar(self) -> QWidget:
        sb = QWidget()
        sb.setFixedWidth(_SIDEBAR_W)
        sb.setStyleSheet(f"background:{_SIDEBAR_BG};")

        lo = QVBoxLayout(sb)
        lo.setContentsMargins(10, 0, 10, 20)
        lo.setSpacing(2)

        # Brand
        brand = QWidget()
        brand.setFixedHeight(72)
        brand.setStyleSheet("background:transparent;")
        b_lo = QHBoxLayout(brand)
        b_lo.setContentsMargins(6, 0, 0, 0)
        b_lo.setSpacing(10)

        logo_circle = QLabel("J")
        logo_circle.setFixedSize(32, 32)
        logo_circle.setAlignment(Qt.AlignCenter)
        logo_circle.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #6366f1,stop:1 #818cf8);"
            "border-radius:9px; color:white;"
            "font-size:14px; font-weight:800;"
        )
        lbl_brand = QLabel("JobHub")
        lbl_brand.setStyleSheet(
            "color:#f1f5f9; font-size:16px; font-weight:700;"
            "letter-spacing:1.5px; background:transparent;"
        )
        b_lo.addWidget(logo_circle)
        b_lo.addWidget(lbl_brand)
        b_lo.addStretch()
        lo.addWidget(brand)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#1e293b;")
        sep.setFixedHeight(1)
        lo.addWidget(sep)
        lo.addSpacing(10)

        # Section label
        sec_lbl = QLabel("MENU")
        sec_lbl.setStyleSheet(
            "color:#475569; font-size:9px; font-weight:700;"
            "letter-spacing:1.8px; background:transparent;"
        )
        sec_lbl.setContentsMargins(6, 0, 0, 0)
        lo.addWidget(sec_lbl)
        lo.addSpacing(4)

        # Nav items
        nav_defs = [
            ("ic_dashboard.svg",     "Khám phá việc làm", 0),
            ("ic_folder.svg",        "Lịch sử ứng tuyển", 1),
            ("bookmark_outline.svg", "Việc làm đã lưu",   2),
            ("ic_user.svg",          "Hồ sơ cá nhân",     3),
        ]
        self._nav_btns: list[_NavBtn] = []
        for icon, label, idx in nav_defs:
            btn = _NavBtn(icon, label)
            btn.on_click(lambda i=idx: self._go(i))
            self._nav_btns.append(btn)
            lo.addWidget(btn)

        lo.addStretch()

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background:#1e293b;")
        sep2.setFixedHeight(1)
        lo.addWidget(sep2)
        lo.addSpacing(8)

        self._logout_btn = _NavBtn("ic_logout.svg", "Đăng xuất", logout=True)
        self._logout_btn.on_click(self._logout)
        lo.addWidget(self._logout_btn)

        return sb

    # ══════════════════════════════════════════════════════════
    #  TOPBAR — Search bar + Filters + Avatar
    # ══════════════════════════════════════════════════════════
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(_TOPBAR_H)
        bar.setStyleSheet(
            f"background:{_TOPBAR_BG}; border-bottom:1px solid {_BORDER};"
        )
        lo = QHBoxLayout(bar)
        lo.setContentsMargins(24, 0, 24, 0)
        lo.setSpacing(10)

        # ── Search bar ────────────────────────────────────────
        search_wrap = QFrame()
        search_wrap.setFixedHeight(42)
        search_wrap.setMinimumWidth(280)
        search_wrap.setMaximumWidth(380)
        search_wrap.setStyleSheet(
            "QFrame{"
            "background:#f1f5f9; border-radius:21px;"
            f"border:1.5px solid {_BORDER};}}"
            "QFrame:focus-within{"
            f"border:1.5px solid {_INDIGO};}}"
        )
        sw_lo = QHBoxLayout(search_wrap)
        sw_lo.setContentsMargins(14, 0, 14, 0)
        sw_lo.setSpacing(8)

        search_icon = QLabel()
        search_icon.setFixedSize(16, 16)
        search_icon.setPixmap(_svg_pm("ic_search.svg", 16, "#94a3b8"))
        search_icon.setStyleSheet("background:transparent;")

        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Tìm kiếm việc làm, kỹ năng, công ty...")
        search_edit.setStyleSheet(
            "border:none; background:transparent;"
            f"color:{_TXT_S}; font-size:13px;"
            "selection-background-color:#e0e7ff;"
        )

        sw_lo.addWidget(search_icon)
        sw_lo.addWidget(search_edit, 1)
        lo.addWidget(search_wrap)

        # ── Filter pill buttons ───────────────────────────────
        filters = ["Địa điểm", "Mức lương", "Kinh nghiệm", "Cần trả nản"]
        for txt in filters:
            btn = self._filter_pill(txt)
            lo.addWidget(btn)

        lo.addStretch()

        # ── Avatar + name ─────────────────────────────────────
        avatar = QLabel("UV")
        avatar.setFixedSize(38, 38)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"background:{_INDIGO}; color:white; border-radius:19px;"
            "font-size:13px; font-weight:800;"
        )
        name_lbl = QLabel("Ứng viên")
        name_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:13px; font-weight:600;"
        )
        lo.addWidget(avatar)
        lo.addSpacing(8)
        lo.addWidget(name_lbl)

        return bar

    def _filter_pill(self, label: str) -> QPushButton:
        """Rounded pill filter button with chevron-down."""
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(36)

        # Build label + chevron icon inside button via layout
        wrap = QWidget()
        wrap.setAttribute(Qt.WA_TransparentForMouseEvents)
        w_lo = QHBoxLayout(wrap)
        w_lo.setContentsMargins(14, 0, 10, 0)
        w_lo.setSpacing(6)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color:{_TXT_S}; font-size:12px; font-weight:600;"
            "background:transparent;"
        )
        chev = QLabel()
        chev.setFixedSize(14, 14)
        chev.setPixmap(_svg_pm("ic_chevron_down.svg", 14, "#6b7280"))
        chev.setStyleSheet("background:transparent;")
        w_lo.addWidget(lbl)
        w_lo.addWidget(chev)

        # Overlay button on the wrap
        btn.setStyleSheet(
            "QPushButton{"
            f"background:{_CARD_BG}; border:1.5px solid {_BORDER};"
            "border-radius:18px; padding:0 14px;}"
            "QPushButton:hover{"
            f"border:1.5px solid {_INDIGO}; background:#f5f3ff;}}"
        )

        # Since Qt doesn't support child widgets in QPushButton cleanly,
        # we use text + Unicode arrow
        btn.setText(f"{label}  ▾")
        btn.setStyleSheet(
            "QPushButton{"
            f"background:{_CARD_BG}; border:1.5px solid {_BORDER};"
            "border-radius:18px; font-size:12px; font-weight:600;"
            f"color:{_TXT_S}; padding:0 16px;" + "}"
            "QPushButton:hover{"
            f"border:1.5px solid {_INDIGO}; color:{_INDIGO}; background:#f5f3ff;" + "}"
            "QPushButton:pressed{"
            f"background:#ede9fe; border:1.5px solid {_INDIGO};" + "}"
        )
        return btn

    # ══════════════════════════════════════════════════════════
    #  NAVIGATION
    # ══════════════════════════════════════════════════════════
    def _go(self, index: int) -> None:
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == index)
        self._stack.setCurrentIndex(index)

    # ══════════════════════════════════════════════════════════
    #  PAGE BUILDERS
    # ══════════════════════════════════════════════════════════
    def _page_scroll_wrapper(self) -> tuple[QScrollArea, QVBoxLayout]:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea{{background:{_CONTENT_BG}; border:none;}}"
            "QScrollBar:vertical{width:6px; background:#f1f5f9;}"
            "QScrollBar::handle:vertical{background:#cbd5e1; border-radius:3px;}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical{height:0;}"
        )
        inner = QWidget()
        inner.setStyleSheet(f"background:{_CONTENT_BG};")
        lo = QVBoxLayout(inner)
        lo.setContentsMargins(28, 24, 28, 28)
        lo.setSpacing(20)
        scroll.setWidget(inner)
        return scroll, lo

    # ── Home / Khám phá việc làm ──────────────────────────────
    def _build_home_page(self) -> QWidget:
        scroll, lo = self._page_scroll_wrapper()

        # Stats strip
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)
        stats_row.addStretch()
        for label, val, solid_color, icon_svg in [
            ("Tin đang mở", "124", "#10b981", "ic_jobs.svg"),
            ("Lĩnh vực",    "18",  "#3b82f6", "ic_folder.svg"),
            ("Công ty",     "56",  "#ef4444", "ic_building.svg"),
        ]:
            stats_row.addWidget(
                self._stat_card(label, val, solid_color, icon_svg)
            )
        stats_row.addStretch()
        lo.addLayout(stats_row)

        # Section header
        sec_lbl = QLabel("Việc làm nổi bật")
        sec_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:17px; font-weight:700;"
        )
        lo.addWidget(sec_lbl)

        # Jobs grid (2 columns)
        self.jobs_grid = QGridLayout()
        self.jobs_grid.setSpacing(16)
        self._load_jobs_grid(self.jobs_grid, is_saved=False)
        lo.addLayout(self.jobs_grid)
        lo.addStretch()
        return scroll

    def _stat_card(self, label: str, val: str,
                   solid_color: str, icon_svg: str) -> QFrame:
        """Stats card with solid-color icon badge + big number."""
        f = QFrame()
        f.setStyleSheet(
            f"QFrame{{background:{_CARD_BG}; border:1px solid {_BORDER};"
            "border-radius:16px;}}"
        )
        f.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        f.setFixedSize(210, 82)
        _shadow(f, 12, 3, 10)

        lo = QHBoxLayout(f)
        lo.setContentsMargins(18, 0, 18, 0)
        lo.setSpacing(16)

        # Solid-color icon badge with white icon
        badge = QFrame()
        badge.setFixedSize(46, 46)
        badge.setStyleSheet(
            f"background:{solid_color}; border-radius:13px;"
        )
        badge_lo = QHBoxLayout(badge)
        badge_lo.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(22, 22)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent;")
        icon_lbl.setPixmap(_svg_pm(icon_svg, 20, "#ffffff"))
        badge_lo.addWidget(icon_lbl, 0, Qt.AlignCenter)

        # Number + label
        txt_lo = QVBoxLayout()
        txt_lo.setSpacing(1)
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:22px; font-weight:800;"
        )
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px; font-weight:500;"
        )
        txt_lo.addWidget(v_lbl)
        txt_lo.addWidget(l_lbl)

        lo.addWidget(badge)
        lo.addLayout(txt_lo)
        return f

    # ══════════════════════════════════════════════════════════
    #  HISTORY PAGE — card-based rows, search/filter, sort, pagination
    # ══════════════════════════════════════════════════════════
    def _build_history_page(self) -> QWidget:
        # Plain expanding page — no outer scroll, card fills full height
        page = QWidget()
        page.setStyleSheet(f"background:{_CONTENT_BG};")
        lo = QVBoxLayout(page)
        lo.setContentsMargins(28, 20, 28, 20)
        lo.setSpacing(0)

        # ── Outer card shell ───────────────────────────────────
        shell = QFrame()
        shell.setStyleSheet(
            f"QFrame{{background:{_CARD_BG}; border:1px solid {_BORDER};"
            "border-radius:20px;}}"
        )
        _shadow(shell, 14, 4, 12)
        shell_lo = QVBoxLayout(shell)
        shell_lo.setContentsMargins(0, 0, 0, 0)
        shell_lo.setSpacing(0)

        # ── Card header ────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet("background:#f8fafc; border-radius:20px 20px 0 0;")
        hdr_lo = QHBoxLayout(hdr)
        hdr_lo.setContentsMargins(20, 0, 20, 0)
        hdr_lo.setSpacing(12)

        title_lbl = QLabel("Lịch sử ứng tuyển")
        title_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:15px; font-weight:700;"
        )
        hdr_lo.addWidget(title_lbl)
        hdr_lo.addStretch()

        # Search bar inside header
        srch_wrap = QFrame()
        srch_wrap.setFixedSize(220, 36)
        srch_wrap.setStyleSheet(
            "QFrame{background:white; border-radius:18px;"
            f"border:1.5px solid {_BORDER};}}"
        )
        sw_lo = QHBoxLayout(srch_wrap)
        sw_lo.setContentsMargins(10, 0, 10, 0)
        sw_lo.setSpacing(6)
        srch_icon = QLabel()
        srch_icon.setFixedSize(14, 14)
        srch_icon.setPixmap(_svg_pm("ic_search.svg", 14, "#9ca3af"))
        srch_icon.setStyleSheet("background:transparent;")
        self._hist_search = QLineEdit()
        self._hist_search.setPlaceholderText("Tìm công ty, vị trí...")
        self._hist_search.setStyleSheet(
            "border:none; background:transparent;"
            f"color:{_TXT_S}; font-size:12px;"
        )
        self._hist_search.textChanged.connect(self._apply_hist_filters)
        sw_lo.addWidget(srch_icon)
        sw_lo.addWidget(self._hist_search, 1)
        hdr_lo.addWidget(srch_wrap)

        # Status filter dropdown
        from PySide6.QtWidgets import QComboBox
        self._hist_filter = QComboBox()
        self._hist_filter.addItems(
            ["Tất cả", "Đang xử lý", "Đã xem", "Phê duyệt", "Từ chối"]
        )
        self._hist_filter.setFixedSize(140, 36)
        self._hist_filter.setStyleSheet(
            "QComboBox{background:white; border:1.5px solid #e2e8f0;"
            "border-radius:18px; padding:0 14px; font-size:12px;"
            f"color:{_TXT_S}; font-weight:600;" + "}"
            "QComboBox::drop-down{border:none; width:20px;}"
            "QComboBox::down-arrow{image:none;}"
            "QComboBox QAbstractItemView{border:1px solid #e2e8f0;"
            "border-radius:8px; background:white; selection-background-color:#ede9fe;}"
        )
        self._hist_filter.currentTextChanged.connect(self._apply_hist_filters)
        hdr_lo.addWidget(self._hist_filter)
        shell_lo.addWidget(hdr)

        # ── Column header row ──────────────────────────────────
        col_hdr = QWidget()
        col_hdr.setFixedHeight(38)
        col_hdr.setStyleSheet(
            "background:white; border-bottom:1px solid #f1f5f9;"
        )
        ch_lo = QHBoxLayout(col_hdr)
        ch_lo.setContentsMargins(20, 0, 20, 0)
        ch_lo.setSpacing(0)

        def _col_hdr_btn(text: str, sort_key: str,
                         stretch: int = 0, fixed: int = 0) -> QPushButton:
            b = QPushButton(text)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton{background:transparent; border:none;"
                "color:#9ca3af; font-size:10px; font-weight:700;"
                "letter-spacing:1px; text-align:left; padding:0;}"
                "QPushButton:hover{color:#6366f1;}"
            )
            if fixed:
                b.setFixedWidth(fixed)
            b.clicked.connect(lambda _, k=sort_key: self._sort_hist(k))
            return b

        comp_hdr = _col_hdr_btn("CÔNG TY  ↕", "comp", stretch=1)
        pos_hdr  = _col_hdr_btn("VỊ TRÍ  ↕", "pos", stretch=1)
        date_hdr = _col_hdr_btn("NGÀY ỨNG TUYỂN  ↕", "date", fixed=160)
        stat_hdr = _col_hdr_btn("TRẠNG THÁI", "", fixed=130)
        act_hdr  = QPushButton("THAO TÁC")
        act_hdr.setFixedWidth(82)
        act_hdr.setStyleSheet(
            "background:transparent; border:none; color:#9ca3af;"
            "font-size:10px; font-weight:700; letter-spacing:1px;"
            "text-align:left; padding:0;"
        )

        ch_lo.addWidget(comp_hdr, 1)
        ch_lo.addWidget(pos_hdr, 1)
        ch_lo.addWidget(date_hdr)
        ch_lo.addWidget(stat_hdr)
        ch_lo.addWidget(act_hdr)
        shell_lo.addWidget(col_hdr)

        # ── Rows container ─────────────────────────────────────
        self._hist_rows_widget = QWidget()
        self._hist_rows_widget.setStyleSheet("background:white;")
        self._hist_rows_lo = QVBoxLayout(self._hist_rows_widget)
        self._hist_rows_lo.setContentsMargins(12, 8, 12, 8)
        self._hist_rows_lo.setSpacing(6)
        shell_lo.addWidget(self._hist_rows_widget, 1)   # ← expand rows to fill

        # ── Footer: entry count + pagination ───────────────────
        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(
            "background:white; border-top:1px solid #f1f5f9;"
            "border-radius:0 0 20px 20px;"
        )
        foot_lo = QHBoxLayout(footer)
        foot_lo.setContentsMargins(20, 0, 20, 0)
        self._hist_entry_lbl = QLabel()
        self._hist_entry_lbl.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px;"
        )
        foot_lo.addWidget(self._hist_entry_lbl)
        foot_lo.addStretch()
        self._hist_pag_lo = QHBoxLayout()
        self._hist_pag_lo.setSpacing(3)
        foot_lo.addLayout(self._hist_pag_lo)
        shell_lo.addWidget(footer)

        lo.addWidget(shell, 1)   # ← shell fills remaining vertical space

        # ── Init state ─────────────────────────────────────────
        self._hist_page       = 0
        self._hist_sort_key   = "date"
        self._hist_sort_asc   = False
        self._hist_filtered   = list(_HIST_DATA)
        self._render_hist_page()
        return page

    # ── Data helpers ───────────────────────────────────────────
    def _apply_hist_filters(self) -> None:
        q      = self._hist_search.text().lower().strip()
        status = self._hist_filter.currentText()
        data   = _HIST_DATA
        if q:
            data = [r for r in data if q in r[0].lower() or q in r[2].lower()]
        if status != "Tất cả":
            data = [r for r in data if r[4] == status]
        # apply sort
        key_map = {"comp": 0, "pos": 2, "date": 3}
        ki = key_map.get(self._hist_sort_key, 3)
        data = sorted(data, key=lambda r: r[ki],
                      reverse=not self._hist_sort_asc)
        self._hist_filtered = data
        self._hist_page = 0
        self._render_hist_page()

    def _sort_hist(self, key: str) -> None:
        if self._hist_sort_key == key:
            self._hist_sort_asc = not self._hist_sort_asc
        else:
            self._hist_sort_key = key
            self._hist_sort_asc = False
        self._apply_hist_filters()

    def _go_hist_page(self, page: int) -> None:
        self._hist_page = page
        self._render_hist_page()

    # ── Render ─────────────────────────────────────────────────
    def _render_hist_page(self) -> None:
        total   = len(self._hist_filtered)
        n_pages = max(1, (total + _HIST_PAGE_SIZE - 1) // _HIST_PAGE_SIZE)
        self._hist_page = max(0, min(self._hist_page, n_pages - 1))
        start = self._hist_page * _HIST_PAGE_SIZE
        page  = self._hist_filtered[start: start + _HIST_PAGE_SIZE]

        # Clear old row cards
        lo = self._hist_rows_lo
        while lo.count():
            item = lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not page:
            empty = QLabel("Không có kết quả phù hợp")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color:{_TXT_M}; font-size:13px; padding:32px;")
            lo.addWidget(empty)
        else:
            for i, row_data in enumerate(page):
                lo.addWidget(
                    self._hist_row_card(row_data, start + i)
                )

        # Entry label
        end = min(start + _HIST_PAGE_SIZE, total)
        count_txt = f"Hiển thị {start+1}–{end} / {total} kết quả"
        if total == 0:
            count_txt = "Không có kết quả"
        self._hist_entry_lbl.setText(count_txt)

        # Pagination
        pag_lo = self._hist_pag_lo
        while pag_lo.count():
            item = pag_lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        def _pag_btn(label: str, p: int | None,
                     active: bool = False, enabled: bool = True) -> QPushButton:
            b = QPushButton(label)
            b.setFixedSize(32, 32)
            b.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
            if active:
                b.setStyleSheet(
                    f"QPushButton{{background:{_INDIGO}; color:white;"
                    "border-radius:8px; font-size:12px; font-weight:700; border:none;}}"
                )
            else:
                b.setStyleSheet(
                    "QPushButton{background:transparent; color:#6b7280;"
                    "border-radius:8px; font-size:13px; border:none;}"
                    "QPushButton:hover{background:#f3f4f6; color:#111827;}"
                    "QPushButton:disabled{color:#d1d5db;}"
                )
            b.setEnabled(enabled and p is not None)
            if p is not None and enabled:
                b.clicked.connect(lambda _, pg=p: self._go_hist_page(pg))
            return b

        cur = self._hist_page
        pag_lo.addWidget(_pag_btn("«", 0,         enabled=cur > 0))
        pag_lo.addWidget(_pag_btn("‹", cur - 1,   enabled=cur > 0))

        vis = min(n_pages, 3)
        sp  = max(0, min(cur - 1, n_pages - vis))
        for pg in range(sp, sp + vis):
            pag_lo.addWidget(_pag_btn(str(pg + 1), pg, active=(pg == cur)))

        pag_lo.addWidget(_pag_btn("›", cur + 1,       enabled=cur < n_pages - 1))
        pag_lo.addWidget(_pag_btn("»", n_pages - 1,   enabled=cur < n_pages - 1))

    # ── Row card widget (hover effect) ─────────────────────────
    def _hist_row_card(self, row_data: tuple, abs_idx: int) -> QFrame:
        comp, loc, pos, date, status = row_data
        grad_stops, txt_col = _GRAD_PALETTE[abs_idx % len(_GRAD_PALETTE)]

        card = _HoverCard()
        card.setFixedHeight(72)

        lo = QHBoxLayout(card)
        lo.setContentsMargins(12, 0, 12, 0)
        lo.setSpacing(0)

        # ── Gradient avatar ────────────────────────────────────
        avatar = QLabel(comp[0].upper())
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,{grad_stops});"
            f"color:{txt_col}; border-radius:12px;"
            "font-size:15px; font-weight:800;"
        )
        lo.addWidget(avatar)
        lo.addSpacing(12)

        # ── Company + location ─────────────────────────────────
        comp_col = QVBoxLayout()
        comp_col.setSpacing(2)
        comp_lbl = QLabel(comp)
        comp_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:13px; font-weight:700;"
        )

        loc_row = QHBoxLayout()
        loc_row.setSpacing(3)
        loc_row.setContentsMargins(0, 0, 0, 0)
        pin = QLabel()
        pin.setFixedSize(11, 11)
        pin.setPixmap(_svg_pm("ic_pin.svg", 11, "#9ca3af"))
        pin.setStyleSheet("background:transparent;")
        loc_lbl = QLabel(loc)
        loc_lbl.setStyleSheet(f"color:{_TXT_M}; font-size:11px;")
        loc_row.addWidget(pin)
        loc_row.addWidget(loc_lbl)
        loc_row.addStretch()

        comp_col.addWidget(comp_lbl)
        comp_col.addLayout(loc_row)
        lo.addLayout(comp_col, 1)
        lo.addSpacing(8)

        # ── Position ───────────────────────────────────────────
        pos_lbl = QLabel(pos)
        pos_lbl.setStyleSheet(
            f"color:{_TXT_S}; font-size:13px; font-weight:500;"
        )
        pos_lbl.setWordWrap(False)
        lo.addWidget(pos_lbl, 1)

        # ── Date ───────────────────────────────────────────────
        date_lbl = QLabel(date)
        date_lbl.setFixedWidth(160)
        date_lbl.setStyleSheet(f"color:{_TXT_M}; font-size:12px;")
        lo.addWidget(date_lbl)

        # ── Status pill with icon ──────────────────────────────
        sc, sb, ic_color, en_label, icon_svg = _STATUS_STYLE.get(
            status, ("#64748b", "#f1f5f9", "#64748b", "Không rõ", "")
        )
        status_wrap = QFrame()
        status_wrap.setFixedSize(120, 28)
        status_wrap.setStyleSheet(
            f"background:{sb}; border-radius:14px;"
        )
        sw_lo = QHBoxLayout(status_wrap)
        sw_lo.setContentsMargins(10, 0, 12, 0)
        sw_lo.setSpacing(5)

        if icon_svg:
            ic_lbl = QLabel()
            ic_lbl.setFixedSize(12, 12)
            ic_lbl.setPixmap(_svg_pm(icon_svg, 12, ic_color))
            ic_lbl.setStyleSheet("background:transparent;")
            sw_lo.addWidget(ic_lbl)

        st_lbl = QLabel(en_label)
        st_lbl.setStyleSheet(
            f"color:{sc}; font-size:10px; font-weight:800; letter-spacing:0.5px;"
            "background:transparent;"
        )
        sw_lo.addWidget(st_lbl)
        sw_lo.addStretch()
        lo.addWidget(status_wrap)
        lo.addSpacing(8)

        # ── Action buttons ─────────────────────────────────────
        for icon_s, tip, bg_col, ic_col in [
            ("ic_eye2.svg", "Xem chi tiết",  "#f0f9ff", "#0ea5e9"),
            ("ic_edit.svg", "Chỉnh sửa hồ sơ", "#f0fdf4", "#10b981"),
        ]:
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setIcon(QIcon(_svg_pm(icon_s, 15, ic_col)))
            btn.setIconSize(QSize(15, 15))
            btn.setStyleSheet(
                f"QPushButton{{background:{bg_col}; border:none; border-radius:9px;}}"
                f"QPushButton:hover{{background:{_BORDER};}}"
            )
            lo.addWidget(btn)
            lo.addSpacing(4)

        return card

    # ── Saved / Việc làm đã lưu ──────────────────────────────
    def _build_saved_page(self) -> QWidget:
        scroll, lo = self._page_scroll_wrapper()

        sec = QLabel("Việc làm đã lưu")
        sec.setStyleSheet(f"color:{_TXT_H}; font-size:17px; font-weight:700;")
        lo.addWidget(sec)

        self.saved_jobs_grid = QGridLayout()
        self.saved_jobs_grid.setSpacing(16)
        self._load_jobs_grid(self.saved_jobs_grid, is_saved=True)
        lo.addLayout(self.saved_jobs_grid)
        lo.addStretch()
        return scroll

    # ── Profile / Hồ sơ ──────────────────────────────────────
    def _build_profile_page(self) -> QWidget:
        scroll, lo = self._page_scroll_wrapper()

        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{_CARD_BG}; border:1px solid {_BORDER};"
            "border-radius:24px;}}"
        )
        _shadow(card, 18, 6, 14)
        card_lo = QVBoxLayout(card)
        card_lo.setContentsMargins(0, 0, 0, 0)
        card_lo.setSpacing(0)

        # ── Gradient cover banner ──────────────────────────────
        cover = QFrame()
        cover.setFixedHeight(96)
        cover.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #6366f1,stop:0.55 #8b5cf6,stop:1 #a78bfa);"
            "border-radius:24px 24px 0 0;"
        )
        card_lo.addWidget(cover)

        # ── Profile header ─────────────────────────────────────
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{_CARD_BG};")
        hdr_lo = QHBoxLayout(hdr)
        hdr_lo.setContentsMargins(32, 20, 32, 20)
        hdr_lo.setSpacing(20)

        # Avatar with white ring + gradient bg + shadow
        ring = QFrame()
        ring.setFixedSize(86, 86)
        ring.setStyleSheet(
            "background:white; border-radius:43px;"
            "border:3px solid white;"
        )
        _shadow(ring, 20, 6, 30)
        ring_lo = QHBoxLayout(ring)
        ring_lo.setContentsMargins(3, 3, 3, 3)
        av = QLabel("UV")
        av.setFixedSize(76, 76)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #6366f1,stop:1 #8b5cf6);"
            "color:white; border-radius:38px;"
            "font-size:26px; font-weight:800;"
        )
        ring_lo.addWidget(av)

        # Name + email + badges
        info_col = QVBoxLayout()
        info_col.setSpacing(5)

        name_lbl = QLabel("Nguyễn Văn A")
        name_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:22px; font-weight:800;"
        )
        email_row = QHBoxLayout()
        email_row.setSpacing(6)
        email_icon = QLabel()
        email_icon.setFixedSize(14, 14)
        email_icon.setPixmap(_svg_pm("ic_email.svg", 14, "#9ca3af"))
        email_icon.setStyleSheet("background:transparent;")
        email_txt = QLabel("nguyenvana@email.com")
        email_txt.setStyleSheet(f"color:{_TXT_M}; font-size:13px;")
        email_row.addWidget(email_icon)
        email_row.addWidget(email_txt)
        email_row.addStretch()

        badges_row = QHBoxLayout()
        badges_row.setSpacing(8)
        for badge_txt, bg, fg in [
            ("Ứng viên",        "#ede9fe", "#7c3aed"),
            ("Công nghệ TT",    "#e0f2fe", "#0369a1"),
            ("3 năm KN",        "#fef3c7", "#92400e"),
        ]:
            b = QLabel(badge_txt)
            b.setAlignment(Qt.AlignCenter)
            b.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:20px;"
                "padding:3px 12px; font-size:11px; font-weight:700;"
            )
            badges_row.addWidget(b)
        badges_row.addStretch()

        info_col.addWidget(name_lbl)
        info_col.addLayout(email_row)
        info_col.addLayout(badges_row)

        # Stats mini chips
        stats_col = QVBoxLayout()
        stats_col.setAlignment(Qt.AlignTop | Qt.AlignRight)
        stats_col.setSpacing(8)
        for val, lbl_txt, clr in [
            ("15", "Đơn ứng tuyển", _INDIGO),
            ("4",  "Phê duyệt",     "#10b981"),
            ("2",  "Đang chờ",      "#f59e0b"),
        ]:
            chip = QFrame()
            chip.setFixedSize(130, 36)
            chip.setStyleSheet(
                f"background:{clr}10; border-radius:10px;"
            )
            chip_lo = QHBoxLayout(chip)
            chip_lo.setContentsMargins(12, 0, 12, 0)
            chip_lo.setSpacing(6)
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet(
                f"color:{clr}; font-size:16px; font-weight:800;"
            )
            t_lbl = QLabel(lbl_txt)
            t_lbl.setStyleSheet(
                f"color:{_TXT_M}; font-size:11px; font-weight:500;"
            )
            chip_lo.addWidget(v_lbl)
            chip_lo.addWidget(t_lbl)
            chip_lo.addStretch()
            stats_col.addWidget(chip)

        hdr_lo.addWidget(ring)
        hdr_lo.addLayout(info_col, 1)
        hdr_lo.addLayout(stats_col)
        card_lo.addWidget(hdr)

        # ── Divider ────────────────────────────────────────────
        div0 = QFrame()
        div0.setFrameShape(QFrame.HLine)
        div0.setStyleSheet(f"background:{_BORDER};")
        div0.setFixedHeight(1)
        card_lo.addWidget(div0)

        # ── Info sections ──────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background:{_CARD_BG};")
        body_lo = QVBoxLayout(body)
        body_lo.setContentsMargins(32, 24, 32, 28)
        body_lo.setSpacing(24)

        # Section 1 — Thông tin cá nhân
        body_lo.addWidget(self._prof_section_title(
            "ic_user.svg", "#6366f1", "Thông tin cá nhân"
        ))
        grid1 = QGridLayout()
        grid1.setSpacing(12)
        for i, (icon, color, lbl, val) in enumerate([
            ("ic_user.svg",  "#6366f1", "Họ và tên",  "Nguyễn Văn A"),
            ("ic_email.svg", "#0ea5e9", "Email",       "nguyenvana@email.com"),
            ("ic_phone.svg", "#10b981", "Điện thoại",  "0912 345 678"),
            ("ic_pin.svg",   "#f59e0b", "Địa chỉ",    "Hà Nội, Việt Nam"),
        ]):
            grid1.addWidget(self._prof_field(icon, color, lbl, val),
                            i // 2, i % 2)
        body_lo.addLayout(grid1)

        # Thin divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setStyleSheet("background:#f1f5f9;")
        div1.setFixedHeight(1)
        body_lo.addWidget(div1)

        # Section 2 — Thông tin nghề nghiệp
        body_lo.addWidget(self._prof_section_title(
            "ic_jobs.svg", "#8b5cf6", "Thông tin nghề nghiệp"
        ))
        grid2 = QGridLayout()
        grid2.setSpacing(12)
        for i, (icon, color, lbl, val) in enumerate([
            ("ic_jobs.svg",     "#8b5cf6", "Ngành nghề",  "Công nghệ thông tin"),
            ("ic_trend.svg",    "#ef4444", "Kinh nghiệm", "3 năm"),
            ("ic_activity.svg", "#0ea5e9", "Kỹ năng",    "React, Python, Node.js"),
            ("ic_doc.svg",      "#f59e0b", "Bằng cấp",   "Cử nhân CNTT"),
        ]):
            grid2.addWidget(self._prof_field(icon, color, lbl, val),
                            i // 2, i % 2)
        body_lo.addLayout(grid2)

        # ── Action buttons ─────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        # Secondary ghost buttons first, then primary
        for txt, ss in [
            ("Tải CV xuống",
             "QPushButton{background:#f8fafc; color:#374151;"
             "border:1.5px solid #e2e8f0; border-radius:22px;"
             "font-size:13px; font-weight:600; padding:0 20px;}"
             "QPushButton:hover{border:1.5px solid #6366f1; color:#6366f1;}"),
            ("Xem CV",
             f"QPushButton{{background:{_CARD_BG}; color:{_INDIGO};"
             f"border:1.5px solid {_INDIGO}; border-radius:22px;"
             "font-size:13px; font-weight:700; padding:0 20px;}"
             f"QPushButton:hover{{background:#ede9fe;}}"),
            ("Chỉnh sửa hồ sơ",
             f"QPushButton{{background:{_INDIGO}; color:white;"
             "border-radius:22px; font-size:13px; font-weight:700;"
             "padding:0 24px; border:none;}"
             f"QPushButton:hover{{background:{_INDIGO_DARK};}}"),
        ]:
            b = QPushButton(txt)
            b.setFixedHeight(42)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(ss)
            if txt == "Chỉnh sửa hồ sơ":
                _btn_shadow(b, _INDIGO, 45)
            btn_row.addWidget(b)

        body_lo.addLayout(btn_row)
        card_lo.addWidget(body)

        lo.addWidget(card)
        lo.addStretch()
        return scroll

    def _prof_section_title(self, icon_svg: str, color: str,
                            title: str) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(w)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(10)

        ic_bg = QFrame()
        ic_bg.setFixedSize(32, 32)
        ic_bg.setStyleSheet(f"background:{color}18; border-radius:9px;")
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(18, 18)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet("background:transparent;")
        ic_lbl.setPixmap(_svg_pm(icon_svg, 16, color))
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:14px; font-weight:700;"
        )
        lo.addWidget(ic_bg)
        lo.addWidget(title_lbl)
        lo.addStretch()
        return w

    def _prof_field(self, icon_svg: str, icon_color: str,
                    label: str, value: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame{background:#f8fafc; border:1px solid #e2e8f0;"
            "border-radius:14px;}"
            "QFrame:hover{border:1px solid #c7d2fe; background:#f5f3ff;}"
        )
        f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        f.setFixedHeight(74)

        lo = QHBoxLayout(f)
        lo.setContentsMargins(16, 0, 16, 0)
        lo.setSpacing(14)

        # Icon badge
        ic_bg = QFrame()
        ic_bg.setFixedSize(40, 40)
        ic_bg.setStyleSheet(
            f"background:{icon_color}1a; border-radius:12px;"
        )
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(20, 20)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet("background:transparent;")
        ic_lbl.setPixmap(_svg_pm(icon_svg, 18, icon_color))
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        # Label + value stacked
        txt_lo = QVBoxLayout()
        txt_lo.setSpacing(3)
        lbl_w = QLabel(label)
        lbl_w.setStyleSheet(
            "color:#9ca3af; font-size:11px; font-weight:600;"
            "background:transparent;"
        )
        val_w = QLabel(value)
        val_w.setStyleSheet(
            f"color:{_TXT_H}; font-size:14px; font-weight:600;"
            "background:transparent;"
        )

        txt_lo.addWidget(lbl_w)
        txt_lo.addWidget(val_w)

        lo.addWidget(ic_bg)
        lo.addLayout(txt_lo, 1)
        return f

    # ══════════════════════════════════════════════════════════
    #  SHARED HELPERS
    # ══════════════════════════════════════════════════════════
    def _table_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame{{background:{_CARD_BG}; border:1px solid {_BORDER};"
            "border-radius:20px;}}"
        )
        _shadow(card)
        lo = QVBoxLayout(card)
        lo.setContentsMargins(0, 0, 0, 16)
        lo.setSpacing(0)

        hdr = QWidget()
        hdr.setStyleSheet("background:#f8fafc; border-radius:20px 20px 0 0;")
        hdr.setFixedHeight(56)
        hdr_lo = QHBoxLayout(hdr)
        hdr_lo.setContentsMargins(20, 0, 20, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color:{_TXT_H}; font-size:15px; font-weight:700;")
        hdr_lo.addWidget(lbl)
        hdr_lo.addStretch()
        lo.addWidget(hdr)
        return card

    def _style_table(self, tbl: QTableWidget) -> None:
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SingleSelection)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setAlternatingRowColors(True)
        tbl.setStyleSheet(
            "QTableWidget{border:none; background:white;"
            "font-size:13px; outline:none;}"
            f"QTableWidget::item{{padding:0 12px; color:{_TXT_S};}}"
            "QTableWidget::item:selected{background:#ede9fe; color:#1e293b;}"
            "QTableWidget::item:alternate{background:#f8fafc;}"
            f"QHeaderView::section{{background:#f8fafc; color:{_TXT_M};"
            "font-size:12px; font-weight:600; border:none;"
            "border-bottom:1px solid #e2e8f0; padding:0 12px; height:44px;}}"
            "QScrollBar:vertical{width:0px;}"
        )

    # ══════════════════════════════════════════════════════════
    #  JOB CARDS
    # ══════════════════════════════════════════════════════════
    def _load_jobs_grid(self, grid: QGridLayout, is_saved: bool = False) -> None:
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        jobs = [
            ("Senior Frontend Developer",   "TechCorp Vietnam",    "Toàn thời gian", "$2000 – $3000", "Hà Nội"),
            ("Backend Developer (Node.js)", "StartUp Innovation",  "Toàn thời gian", "$1500 – $2500", "TP. Hồ Chí Minh"),
            ("UI/UX Designer",              "Design Studio",       "Từ xa",           "$1200 – $1800", "Hà Nội / Remote"),
        ]
        if not is_saved:
            jobs += [
                ("Full Stack Developer",       "Digital Agency",      "Toàn thời gian", "$2500 – $4000", "Đà Nẵng"),
                ("Mobile Engineer (Flutter)",  "Global IT Solutions", "Bán thời gian",  "$1000 – $1500", "Remote"),
                ("DevOps Architect",           "Cloud Systems",       "Toàn thời gian", "$3500 – $5000", "Hà Nội"),
            ]

        for i, (title, comp, jtype, sal, loc) in enumerate(jobs):
            card = self._job_card(title, comp, jtype, sal, loc, is_saved, i)
            grid.addWidget(card, i // 2, i % 2)

    def _job_card(self, title: str, comp: str, jtype: str,
                  sal: str, loc: str, is_saved: bool, idx: int = 0) -> QFrame:
        bg_col, fg_col = _LOGO_PALETTE[idx % len(_LOGO_PALETTE)]

        card = QFrame()
        card.setObjectName("jobCard")
        card.setStyleSheet(
            "QFrame#jobCard{"
            f"background:{_CARD_BG}; border:1px solid {_BORDER};"
            "border-radius:18px;}"
            "QFrame#jobCard:hover{"
            f"border:1px solid {_INDIGO}; background:#fafbff;}}"
        )
        _shadow(card, 10, 3, 10)

        lo = QVBoxLayout(card)
        lo.setContentsMargins(18, 16, 18, 16)
        lo.setSpacing(0)

        # ── Row 1: logo + title/company + bookmark ─────────────
        top = QHBoxLayout()
        top.setSpacing(12)
        top.setAlignment(Qt.AlignTop)

        # Company logo circle
        logo = QLabel(comp[0].upper())
        logo.setFixedSize(46, 46)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f"background:{bg_col}; color:{fg_col};"
            "border-radius:13px; font-size:17px; font-weight:800;"
        )

        # Title + company
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(
            f"color:{_TXT_H}; font-size:14px; font-weight:700;"
        )
        lbl_title.setWordWrap(True)
        lbl_comp = QLabel(comp)
        lbl_comp.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px; font-weight:500;"
        )
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_comp)

        # Bookmark
        icon_name = "bookmark_filled.svg" if is_saved else "bookmark_outline.svg"
        btn_save = QPushButton()
        btn_save.setFixedSize(26, 26)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet("border:none; background:transparent;")
        btn_save.setIcon(QIcon(_svg_pm(icon_name, 17, "#94a3b8")))
        btn_save.setIconSize(QSize(17, 17))

        top.addWidget(logo)
        top.addLayout(title_col, 1)
        top.addWidget(btn_save, 0, Qt.AlignTop)
        lo.addLayout(top)
        lo.addSpacing(12)

        # ── Divider ────────────────────────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background:{_BORDER};")
        div.setFixedHeight(1)
        lo.addWidget(div)
        lo.addSpacing(10)

        # ── Row 2: badges ──────────────────────────────────────
        h_badges = QHBoxLayout()
        h_badges.setSpacing(8)

        type_badge = QLabel(jtype)
        type_badge.setStyleSheet(
            "background:#eff6ff; color:#2563eb; border-radius:20px;"
            "padding:3px 12px; font-size:11px; font-weight:700;"
        )
        type_badge.setFixedHeight(22)

        sal_badge = QLabel(sal)
        sal_badge.setStyleSheet(
            "background:#f0fdf4; color:#16a34a; border-radius:20px;"
            "padding:3px 12px; font-size:11px; font-weight:700;"
        )
        sal_badge.setFixedHeight(22)

        h_badges.addWidget(type_badge)
        h_badges.addWidget(sal_badge)
        h_badges.addStretch()
        lo.addLayout(h_badges)
        lo.addSpacing(10)

        # ── Row 3: location (left) + apply button (right) ──────
        h_bottom = QHBoxLayout()
        h_bottom.setSpacing(6)

        # Location with pin icon
        pin_lbl = QLabel()
        pin_lbl.setFixedSize(13, 13)
        pin_lbl.setPixmap(_svg_pm("ic_pin.svg", 13, "#9ca3af"))
        loc_lbl = QLabel(loc)
        loc_lbl.setStyleSheet(f"color:{_TXT_M}; font-size:12px;")

        h_bottom.addWidget(pin_lbl)
        h_bottom.addWidget(loc_lbl)
        h_bottom.addStretch()

        # Apply button — compact pill with colored shadow
        btn_apply = QPushButton("Ứng tuyển ngay")
        btn_apply.setFixedSize(138, 34)
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.setStyleSheet(
            f"QPushButton{{background:{_INDIGO}; color:white;"
            "border-radius:17px; font-size:12px; font-weight:700;}}"
            f"QPushButton:hover{{background:{_INDIGO_DARK};}}"
        )
        _btn_shadow(btn_apply, _INDIGO, 50)

        h_bottom.addWidget(btn_apply)
        lo.addLayout(h_bottom)

        return card

    # ══════════════════════════════════════════════════════════
    #  ACTIONS
    # ══════════════════════════════════════════════════════════
    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    def show(self) -> None:
        self.win.show()

    def raise_(self) -> None:
        self.win.raise_()
        self.win.activateWindow()
