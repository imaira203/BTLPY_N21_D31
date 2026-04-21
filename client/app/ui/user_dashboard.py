"""UserDashboard — pure Python, không dùng .ui file."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QPropertyAnimation, QRect, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor, QIcon, QPainter, QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QDialog, QFileDialog, QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QStackedWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from ..session_store import clear_session
from .. import mock_data as _mock_data

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
# Blue palette (profile page primary)
_BLUE         = "#2563eb"
_BLUE_DARK    = "#1d4ed8"
_BLUE_LIGHT   = "#dbeafe"
_BLUE_BG      = "#eff6ff"

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

# All job listings (shared between home/search and saved views)
_JOBS_DATA = [
    ("Senior Frontend Developer",   "TechCorp Vietnam",    "Toàn thời gian", "$2000 – $3000", "Hà Nội"),
    ("Backend Developer (Node.js)", "StartUp Innovation",  "Toàn thời gian", "$1500 – $2500", "TP. Hồ Chí Minh"),
    ("UI/UX Designer",              "Design Studio",       "Từ xa",           "$1200 – $1800", "Hà Nội / Remote"),
    ("Full Stack Developer",        "Digital Agency",      "Toàn thời gian", "$2500 – $4000", "Đà Nẵng"),
    ("Mobile Engineer (Flutter)",   "Global IT Solutions", "Bán thời gian",  "$1000 – $1500", "Remote"),
    ("DevOps Architect",            "Cloud Systems",       "Toàn thời gian", "$3500 – $5000", "Hà Nội"),
    ("Data Engineer",               "VietAI Lab",          "Toàn thời gian", "$2000 – $3500", "TP. Hồ Chí Minh"),
    ("Product Designer",            "FinTech Pro",         "Từ xa",           "$1500 – $2200", "Remote"),
    ("React Native Developer",      "EduSoft Corp",        "Toàn thời gian", "$1800 – $2800", "Hà Nội"),
]

_STATUS_STYLE = {
    "Đang xử lý": ("#92400e", "#fef3c7", "#d97706", "Đang xử lý", "ic_clock.svg"),
    "Đã xem":     ("#065f46", "#d1fae5", "#10b981", "Đã xem",     "ic_eye2.svg"),
    "Phê duyệt":  ("#1e3a8a", "#dbeafe", "#3b82f6", "Đã duyệt",   "ic_check.svg"),
    "Từ chối":    ("#991b1b", "#fee2e2", "#ef4444", "Từ chối",    "ic_x.svg"),
}

# Ánh xạ trạng thái từ HR (English) sang tiếng Việt cho lịch sử ứng viên
_HR_STATUS_VI: dict[str, str] = {
    "pending":  "Đang xử lý",
    "reviewed": "Đã xem",
    "approved": "Phê duyệt",
    "rejected": "Từ chối",
}

# Toast message khi HR thay đổi trạng thái (icon, accent, tiêu đề)
_STATUS_TOAST: dict[str, tuple[str, str, str]] = {
    "reviewed": ("👀", "#3b82f6", "HR đã xem hồ sơ của bạn"),
    "approved": ("🎉", "#10b981", "Hồ sơ được phê duyệt!"),
    "rejected": ("😔", "#ef4444", "Hồ sơ không được chọn"),
}

# Polling interval (ms) — user dashboard kiểm tra cập nhật từ HR
_POLL_INTERVAL_MS = 5_000

# Bảng màu cho từng danh mục kỹ năng  (bg, fg)
_SKILL_CAT_COLORS: list[tuple[str, str]] = [
    ("#dbeafe", _BLUE),        # blue   – Frontend
    ("#dcfce7", "#16a34a"),    # green  – Backend
    ("#fce7f3", "#db2777"),    # pink   – Cloud/DevOps
    ("#fef3c7", "#d97706"),    # amber  – Mobile
    ("#ede9fe", "#7c3aed"),    # purple – Database
    ("#ccfbf1", "#0d9488"),    # teal   – Tools
    ("#fee2e2", "#dc2626"),    # red    – Other
]


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
        "QFrame{background:white; border:none;"
        "border-radius:12px;}"
    )
    _SS_HOVER = (
        "QFrame{background:#f8fafc; border:none;"
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
#  TOAST NOTIFICATION
# ══════════════════════════════════════════════════════════════
class _Toast(QWidget):
    """Slide-down toast anchored to top-right corner of parent."""

    _W = 360
    _H = 72
    _MARGIN = 20   # from right/top edge

    def __init__(self, parent: QWidget, message: str,
                 accent: str = "#10b981", duration_ms: int = 3500,
                 title_text: str = "Nộp hồ sơ thành công!",
                 icon_char: str = "✓"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFixedSize(self._W, self._H)

        # ── Card styling ──────────────────────────────────────
        self.setStyleSheet(
            "background:white; border-radius:16px;"
            "border:1px solid #e5e7eb;"
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)

        # ── Layout ────────────────────────────────────────────
        lo = QHBoxLayout(self)
        lo.setContentsMargins(16, 0, 16, 0)
        lo.setSpacing(14)

        # Accent circle icon
        ic_bg = QFrame()
        ic_bg.setFixedSize(40, 40)
        ic_bg.setStyleSheet(
            f"background:{accent}20; border-radius:20px; border:none;"
        )
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel(icon_char)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet(
            f"color:{accent}; font-size:18px; font-weight:800;"
            "border:none; background:transparent;"
        )
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        # Text block
        txt_lo = QVBoxLayout()
        txt_lo.setSpacing(2)
        txt_lo.setContentsMargins(0, 0, 0, 0)
        title_lbl = QLabel(title_text)
        title_lbl.setStyleSheet(
            "color:#111827; font-size:14px; font-weight:800;"
            "border:none; background:transparent;"
        )
        sub_lbl = QLabel(message)
        sub_lbl.setWordWrap(True)
        sub_lbl.setStyleSheet(
            "color:#6b7280; font-size:12px; border:none; background:transparent;"
        )
        txt_lo.addWidget(title_lbl)
        txt_lo.addWidget(sub_lbl)

        lo.addWidget(ic_bg)
        lo.addLayout(txt_lo, 1)

        self._place_hidden()
        self._animate_in()
        QTimer.singleShot(duration_ms, self._animate_out)

    def _place_hidden(self):
        p = self.parent()
        x = p.width() - self._W - self._MARGIN
        self.setGeometry(QRect(x, -self._H, self._W, self._H))
        self.show()
        self.raise_()

    def _animate_in(self):
        p = self.parent()
        x = p.width() - self._W - self._MARGIN
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(320)
        self._anim.setStartValue(QRect(x, -self._H, self._W, self._H))
        self._anim.setEndValue(QRect(x, self._MARGIN, self._W, self._H))
        self._anim.start()

    def _animate_out(self):
        p = self.parent()
        x = p.width() - self._W - self._MARGIN
        cur = self.geometry()
        self._anim_out = QPropertyAnimation(self, b"geometry")
        self._anim_out.setDuration(260)
        self._anim_out.setStartValue(cur)
        self._anim_out.setEndValue(QRect(x, -self._H, self._W, self._H))
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()


# ══════════════════════════════════════════════════════════════
#  APPLY DIALOG
# ══════════════════════════════════════════════════════════════
class _ApplyDialog(QDialog):
    """Job application form dialog matching the reference UI."""

    def __init__(self, job_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ứng tuyển")
        self.setModal(True)
        self.setFixedWidth(620)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setStyleSheet(
            "QDialog{background:white; border-radius:16px;}"
        )
        self._selected_cv = 0   # 0 = existing CV, 1 = upload new
        self._build(job_title)

    def _build(self, job_title: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scrollable body ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:white; border:none;")

        body_w = QWidget()
        body_w.setStyleSheet("background:white;")
        body_lo = QVBoxLayout(body_w)
        body_lo.setContentsMargins(32, 28, 32, 20)
        body_lo.setSpacing(20)

        # ── Header ────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(0)
        hdr.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(f"Ứng tuyển cho vị trí {job_title}")
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "color:#111827; font-size:20px; font-weight:800;"
            "background:transparent; border:none;"
        )
        hdr.addWidget(title_lbl, 1)
        body_lo.addLayout(hdr)

        # ── Section label helper ───────────────────────────────
        def _sec(txt):
            l = QLabel(txt)
            l.setStyleSheet(
                "color:#6b7280; font-size:11px; font-weight:700;"
                "letter-spacing:0.6px; background:transparent; border:none;"
            )
            return l

        # ── Name + Email row ──────────────────────────────────
        ne_row = QGridLayout()
        ne_row.setHorizontalSpacing(16)
        ne_row.setVerticalSpacing(6)

        ne_row.addWidget(_sec("HỌ VÀ TÊN"), 0, 0)
        ne_row.addWidget(_sec("EMAIL"), 0, 1)

        self._name_edit = QLineEdit("Nguyễn Văn A")
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("example@email.com")
        for e in (self._name_edit, self._email_edit):
            e.setFixedHeight(44)
            e.setStyleSheet(
                "QLineEdit{background:#f5f3ff; border:none; border-radius:10px;"
                "padding:0 14px; font-size:13px; color:#111827;}"
                "QLineEdit:focus{border:1.5px solid #6366f1; background:white;}"
            )
        ne_row.addWidget(self._name_edit, 1, 0)
        ne_row.addWidget(self._email_edit, 1, 1)
        body_lo.addLayout(ne_row)

        # ── Phone ─────────────────────────────────────────────
        ph_lo = QVBoxLayout()
        ph_lo.setSpacing(6)
        ph_lo.setContentsMargins(0, 0, 0, 0)
        ph_lo.addWidget(_sec("SỐ ĐIỆN THOẠI"))
        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText("+84 000 000 000")
        self._phone_edit.setFixedHeight(44)
        self._phone_edit.setStyleSheet(
            "QLineEdit{background:#f5f3ff; border:none; border-radius:10px;"
            "padding:0 14px; font-size:13px; color:#111827;}"
            "QLineEdit:focus{border:1.5px solid #6366f1; background:white;}"
        )
        ph_lo.addWidget(self._phone_edit)
        body_lo.addLayout(ph_lo)

        # ── CV options ────────────────────────────────────────
        body_lo.addWidget(_sec("HỒ SƠ ỨNG TUYỂN"))

        self._cv_opt1 = self._cv_option(
            selected=True,
            title="SỬ DỤNG CV ĐÃ CÓ",
            subtitle="CV_Nguyen_Van_A.pdf",
            detail="Cập nhật 2 ngày trước",
            icon="ic_doc.svg",
            accent="#6366f1",
        )
        self._cv_opt2 = self._cv_option(
            selected=False,
            title="Tải lên CV khác",
            subtitle="HỖ TRỢ PDF, DOCX TỚI ĐA 10MB",
            detail="",
            icon="ic_doc.svg",
            accent="#94a3b8",
            dashed=True,
        )
        self._cv_opt1.mousePressEvent = lambda e: self._select_cv(0)
        self._cv_opt2.mousePressEvent = lambda e: self._select_cv(1)
        body_lo.addWidget(self._cv_opt1)
        body_lo.addWidget(self._cv_opt2)

        # ── Message ───────────────────────────────────────────
        msg_lo = QVBoxLayout()
        msg_lo.setSpacing(6)
        msg_lo.setContentsMargins(0, 0, 0, 0)
        msg_lo.addWidget(_sec("LỜI NHẮN CHO NHÀ TUYỂN DỤNG"))
        self._msg_edit = QTextEdit()
        self._msg_edit.setPlaceholderText(
            "Chia sẻ thêm về kinh nghiệm và lý do bạn ứng tuyển..."
        )
        self._msg_edit.setFixedHeight(120)
        self._msg_edit.setStyleSheet(
            "QTextEdit{background:#f5f3ff; border:none; border-radius:10px;"
            "padding:12px 14px; font-size:13px; color:#111827;}"
            "QTextEdit:focus{border:1.5px solid #6366f1; background:white;}"
        )
        msg_lo.addWidget(self._msg_edit)
        body_lo.addLayout(msg_lo)

        scroll.setWidget(body_w)
        root.addWidget(scroll)

        # ── Footer ────────────────────────────────────────────
        footer_sep = QFrame()
        footer_sep.setFixedHeight(1)
        footer_sep.setStyleSheet("background:#f1f5f9; border:none;")
        root.addWidget(footer_sep)

        footer = QWidget()
        footer.setStyleSheet("background:white; border:none;")
        footer.setFixedHeight(72)
        f_lo = QHBoxLayout(footer)
        f_lo.setContentsMargins(32, 0, 32, 0)
        f_lo.setSpacing(12)
        f_lo.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.setFixedHeight(44)
        btn_cancel.setMinimumWidth(100)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton{background:transparent; color:#374151; border:none;"
            "font-size:14px; font-weight:600; border-radius:22px; padding:0 20px;}"
            "QPushButton:hover{background:#f1f5f9;}"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_submit = QPushButton("Gửi hồ sơ")
        btn_submit.setFixedHeight(44)
        btn_submit.setMinimumWidth(140)
        btn_submit.setCursor(Qt.PointingHandCursor)
        btn_submit.setStyleSheet(
            "QPushButton{background:#6366f1; color:white; border:none;"
            "border-radius:22px; font-size:14px; font-weight:700; padding:0 24px;}"
            "QPushButton:hover{background:#4f46e5;}"
        )
        eff = QGraphicsDropShadowEffect()
        eff.setBlurRadius(18)
        eff.setOffset(0, 4)
        eff.setColor(QColor("#6366f180"))
        btn_submit.setGraphicsEffect(eff)
        btn_submit.clicked.connect(self.accept)

        f_lo.addWidget(btn_cancel)
        f_lo.addWidget(btn_submit)
        root.addWidget(footer)

    def _cv_option(self, selected: bool, title: str, subtitle: str,
                   detail: str, icon: str, accent: str,
                   dashed: bool = False) -> QFrame:
        f = QFrame()
        f.setCursor(Qt.PointingHandCursor)
        if selected:
            border_style = f"border:2px solid {accent}; border-radius:12px;"
        elif dashed:
            border_style = (
                "border:2px dashed #cbd5e1; border-radius:12px;"
            )
        else:
            border_style = "border:1.5px solid #e2e8f0; border-radius:12px;"
        f.setStyleSheet(f"QFrame{{background:white; {border_style}}}")

        lo = QHBoxLayout(f)
        lo.setContentsMargins(16, 14, 16, 14)
        lo.setSpacing(14)

        # Icon badge
        ic_bg = QFrame()
        ic_bg.setFixedSize(40, 40)
        ic_bg.setStyleSheet(
            f"background:{accent}18; border-radius:10px; border:none;"
        )
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(20, 20)
        ic_lbl.setPixmap(_svg_pm(icon, 20, accent))
        ic_lbl.setStyleSheet("background:transparent; border:none;")
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        # Text col
        txt_lo = QVBoxLayout()
        txt_lo.setSpacing(2)
        txt_lo.setContentsMargins(0, 0, 0, 0)
        t1 = QLabel(title)
        t1.setStyleSheet(
            "color:#6b7280; font-size:10px; font-weight:700;"
            "letter-spacing:0.5px; background:transparent; border:none;"
        )
        t2 = QLabel(subtitle)
        t2.setStyleSheet(
            "color:#111827; font-size:13px; font-weight:700;"
            "background:transparent; border:none;"
        )
        txt_lo.addWidget(t1)
        txt_lo.addWidget(t2)
        if detail:
            t3 = QLabel(detail)
            t3.setStyleSheet(
                "color:#9ca3af; font-size:11px;"
                "background:transparent; border:none;"
            )
            txt_lo.addWidget(t3)

        # Radio indicator
        radio = QLabel()
        radio.setFixedSize(22, 22)
        if selected:
            radio.setStyleSheet(
                f"border:2px solid {accent}; border-radius:11px;"
                f"background:white;"
            )
            dot = QLabel(radio)
            dot.setFixedSize(12, 12)
            dot.move(3, 3)
            dot.setStyleSheet(
                f"background:{accent}; border-radius:6px; border:none;"
            )
        else:
            radio.setStyleSheet(
                "border:2px solid #cbd5e1; border-radius:11px; background:white;"
            )

        lo.addWidget(ic_bg)
        lo.addLayout(txt_lo, 1)
        lo.addWidget(radio, 0, Qt.AlignVCenter)
        return f

    def _select_cv(self, idx: int):
        accent = "#6366f1"

        # If choosing "upload new", open file dialog first
        if idx == 1:
            path, _ = QFileDialog.getOpenFileName(
                self, "Chọn file CV",
                "",
                "CV files (*.pdf *.docx *.doc)"
            )
            if not path:
                return  # user cancelled — keep current selection
            # Update opt2 label to show filename
            fname = Path(path).name
            for lbl in self._cv_opt2.findChildren(QLabel):
                if lbl.styleSheet() and "font-weight:700" in lbl.styleSheet() \
                        and "color:#111827" in lbl.styleSheet():
                    lbl.setText(fname)
                    break

        self._selected_cv = idx
        for i, (frame, sel) in enumerate([
            (self._cv_opt1, idx == 0),
            (self._cv_opt2, idx == 1),
        ]):
            if sel:
                frame.setStyleSheet(
                    f"QFrame{{background:#f5f3ff; border:2px solid {accent};"
                    "border-radius:12px;}}"
                )
                for ch in frame.findChildren(QLabel):
                    if ch.width() == 22 and ch.height() == 22:
                        ch.setStyleSheet(
                            f"border:2px solid {accent}; border-radius:11px;"
                            "background:white;"
                        )
            else:
                frame.setStyleSheet(
                    "QFrame{background:white; border:2px dashed #cbd5e1;"
                    "border-radius:12px;}"
                    if i == 1 else
                    "QFrame{background:white; border:1.5px solid #e2e8f0;"
                    "border-radius:12px;}"
                )


# ══════════════════════════════════════════════════════════════
#  PROFILE EDIT DIALOG
# ══════════════════════════════════════════════════════════════
class _ProfileEditDialog(QDialog):
    """Full-screen modal form for editing personal + professional info."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chỉnh sửa hồ sơ")
        self.setModal(True)
        self.setFixedWidth(640)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.setStyleSheet("QDialog{background:white;}")
        self._data   = dict(data)   # working copy
        self._inputs: dict[str, QLineEdit] = {}
        self._build()

    # ── result ────────────────────────────────────────────────
    def get_data(self) -> dict:
        return self._data

    # ── build ─────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header ─────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0f172a,stop:1 #1e3a8a); border:none;"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(28, 0, 20, 0)
        htitle = QLabel("✏️  Chỉnh sửa hồ sơ")
        htitle.setStyleSheet(
            "color:white; font-size:16px; font-weight:800; border:none; background:transparent;"
        )
        hl.addWidget(htitle)
        hl.addStretch()
        root.addWidget(hdr)

        # ── scroll body ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:white; border:none;}"
            "QScrollBar:vertical{width:6px; background:transparent;}"
            "QScrollBar::handle:vertical{background:#c1c9d6; border-radius:3px;}"
        )
        body = QWidget()
        body.setStyleSheet("background:white;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 24)
        bl.setSpacing(0)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        def _section(icon: str, title: str, accent: str):
            row = QHBoxLayout()
            row.setSpacing(10)
            badge = QLabel(icon)
            badge.setFixedSize(32, 32)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(
                f"background:{accent}20; border-radius:10px; font-size:16px;"
                "border:none;"
            )
            lbl = QLabel(title)
            lbl.setStyleSheet(
                f"color:#111827; font-size:14px; font-weight:800; border:none; background:transparent;"
            )
            row.addWidget(badge)
            row.addWidget(lbl)
            row.addStretch()
            bl.addLayout(row)
            bl.addSpacing(16)

        def _field(label: str, key: str, placeholder: str = ""):
            lbl = QLabel(label)
            lbl.setStyleSheet(
                "color:#6b7280; font-size:10px; font-weight:700; letter-spacing:0.8px;"
                "border:none; background:transparent;"
            )
            inp = QLineEdit(self._data.get(key, ""))
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(42)
            inp.setStyleSheet(
                "QLineEdit{background:#f8fafc; border:1.5px solid #e2e8f0;"
                "border-radius:10px; padding:0 14px; font-size:13px; color:#111827;}"
                "QLineEdit:focus{border:1.5px solid #6366f1; background:white;}"
            )
            self._inputs[key] = inp
            bl.addWidget(lbl)
            bl.addSpacing(4)
            bl.addWidget(inp)
            bl.addSpacing(14)

        def _field_row(pairs: list):
            """Two fields side by side."""
            row = QHBoxLayout()
            row.setSpacing(16)
            for label, key, ph in pairs:
                col = QVBoxLayout()
                col.setSpacing(4)
                lbl = QLabel(label)
                lbl.setStyleSheet(
                    "color:#6b7280; font-size:10px; font-weight:700; letter-spacing:0.8px;"
                    "border:none; background:transparent;"
                )
                inp = QLineEdit(self._data.get(key, ""))
                inp.setPlaceholderText(ph)
                inp.setFixedHeight(42)
                inp.setStyleSheet(
                    "QLineEdit{background:#f8fafc; border:1.5px solid #e2e8f0;"
                    "border-radius:10px; padding:0 14px; font-size:13px; color:#111827;}"
                    "QLineEdit:focus{border:1.5px solid #6366f1; background:white;}"
                )
                self._inputs[key] = inp
                col.addWidget(lbl)
                col.addWidget(inp)
                row.addLayout(col, 1)
            bl.addLayout(row)
            bl.addSpacing(14)

        # Personal section
        _section("👤", "Thông tin cá nhân", "#6366f1")
        _field("HỌ VÀ TÊN", "name", "Nhập họ và tên đầy đủ...")
        _field_row([
            ("EMAIL",          "email",   "example@email.com"),
            ("SỐ ĐIỆN THOẠI",  "phone",   "0912 345 678"),
        ])
        _field("ĐỊA CHỈ HIỆN TẠI", "address", "Thành phố, Tỉnh, Quốc gia...")
        _field("GIỚI THIỆU BẢN THÂN", "tagline", "Tiêu đề hiển thị dưới tên...")

        bl.addSpacing(8)
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background:#f1f5f9; border:none;")
        bl.addWidget(div)
        bl.addSpacing(20)

        # Professional section
        _section("💼", "Thông tin chuyên môn", "#10b981")
        _field_row([
            ("NGÀNH NGHỀ",  "field",  "Vd: Phát triển Phần mềm"),
            ("BẰNG CẤP",    "degree", "Vd: Cử nhân CNTT"),
        ])
        _field_row([
            ("SỐ NĂM KINH NGHIỆM", "exp",  "Vd: 3 năm"),
            ("NGÔN NGỮ",           "lang", "Vd: Tiếng Anh B2"),
        ])

        bl.addSpacing(8)
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background:#f1f5f9; border:none;")
        bl.addWidget(div2)
        bl.addSpacing(20)

        # ── Skills section ─────────────────────────────────────
        _section("🛠️", "Kỹ năng & Vai trò", "#f59e0b")

        # Hint
        hint = QLabel("Nhập các kỹ năng, cách nhau bằng dấu phẩy. Nhấn Enter hoặc nút + để thêm danh mục mới.")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            "color:#9ca3af; font-size:11px; border:none; background:transparent;"
        )
        bl.addWidget(hint)
        bl.addSpacing(14)

        # Container for skill category rows (dynamic)
        self._skill_rows_widget = QWidget()
        self._skill_rows_widget.setStyleSheet("background:transparent;")
        self._skill_rows_lo = QVBoxLayout(self._skill_rows_widget)
        self._skill_rows_lo.setContentsMargins(0, 0, 0, 0)
        self._skill_rows_lo.setSpacing(10)
        bl.addWidget(self._skill_rows_widget)

        # Render existing categories
        init_skills: dict = self._data.get("skills", {})
        self._skill_cat_inputs: dict[str, QLineEdit] = {}  # cat_name → QLineEdit
        for ci, (cat, tags) in enumerate(init_skills.items()):
            self._add_skill_cat_row(cat, ", ".join(tags), ci)

        bl.addSpacing(10)

        # "Thêm danh mục" row
        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._new_cat_inp = QLineEdit()
        self._new_cat_inp.setPlaceholderText("Tên danh mục mới (vd: Mobile, Database...)")
        self._new_cat_inp.setFixedHeight(38)
        self._new_cat_inp.setStyleSheet(
            "QLineEdit{background:#f8fafc; border:1.5px solid #e2e8f0;"
            "border-radius:10px; padding:0 12px; font-size:12px; color:#111827;}"
            "QLineEdit:focus{border:1.5px solid #f59e0b; background:white;}"
        )
        btn_add_cat = QPushButton("＋ Thêm danh mục")
        btn_add_cat.setFixedHeight(38)
        btn_add_cat.setCursor(Qt.PointingHandCursor)
        btn_add_cat.setStyleSheet(
            "QPushButton{background:#fef3c7; color:#d97706; border:none;"
            "border-radius:10px; font-size:12px; font-weight:700; padding:0 14px;}"
            "QPushButton:hover{background:#fde68a;}"
        )
        btn_add_cat.clicked.connect(self._on_add_skill_category)
        self._new_cat_inp.returnPressed.connect(self._on_add_skill_category)
        add_row.addWidget(self._new_cat_inp, 1)
        add_row.addWidget(btn_add_cat)
        bl.addLayout(add_row)
        bl.addSpacing(8)

        # ── footer ─────────────────────────────────────────────
        foot = QWidget()
        foot.setFixedHeight(68)
        foot.setStyleSheet(
            "background:#f8fafc; border-top:1px solid #f1f5f9; border:none;"
        )
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(28, 0, 28, 0)
        fl.setSpacing(12)
        fl.addStretch()

        btn_cancel = QPushButton("Hủy")
        btn_cancel.setFixedSize(100, 42)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(
            "QPushButton{background:white; color:#374151;"
            "border:1.5px solid #d1d5db; border-radius:21px;"
            "font-size:13px; font-weight:600;}"
            "QPushButton:hover{background:#f9fafb;}"
        )
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("💾  Lưu thay đổi")
        btn_save.setFixedSize(160, 42)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            "QPushButton{background:#6366f1; color:white;"
            "border:none; border-radius:21px;"
            "font-size:13px; font-weight:700;}"
            "QPushButton:hover{background:#4f46e5;}"
        )
        btn_save.clicked.connect(self._save)

        fl.addWidget(btn_cancel)
        fl.addWidget(btn_save)
        root.addWidget(foot)

    # ── Skill category helpers ────────────────────────────────
    def _add_skill_cat_row(self, cat_name: str, tags_csv: str, index: int = -1):
        """Thêm một hàng category vào skill_rows_lo."""
        bg, fg = _SKILL_CAT_COLORS[index % len(_SKILL_CAT_COLORS)]

        row_w = QWidget()
        row_w.setStyleSheet("background:transparent;")
        row_lo = QVBoxLayout(row_w)
        row_lo.setContentsMargins(0, 0, 0, 0)
        row_lo.setSpacing(5)

        # Header: category badge + label + remove button
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        badge = QLabel(cat_name)
        badge.setFixedHeight(24)
        badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:12px;"
            "padding:0 10px; font-size:11px; font-weight:700; border:none;"
        )
        hdr.addWidget(badge)
        hdr.addStretch()
        # Remove category button
        btn_del = QPushButton("✕")
        btn_del.setFixedSize(22, 22)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet(
            "QPushButton{background:#fee2e2; color:#dc2626; border:none;"
            "border-radius:11px; font-size:10px; font-weight:800;}"
            "QPushButton:hover{background:#fca5a5;}"
        )
        btn_del.clicked.connect(lambda _, w=row_w, k=cat_name: self._remove_skill_cat(w, k))
        hdr.addWidget(btn_del)
        row_lo.addLayout(hdr)

        # Input line
        inp = QLineEdit(tags_csv)
        inp.setPlaceholderText("Nhập kỹ năng, cách nhau bằng dấu phẩy...")
        inp.setFixedHeight(40)
        inp.setStyleSheet(
            f"QLineEdit{{background:#f8fafc; border:1.5px solid {bg};"
            "border-radius:10px; padding:0 12px; font-size:13px; color:#111827;}"
            f"QLineEdit:focus{{border:1.5px solid {fg}; background:white;}}"
        )
        self._skill_cat_inputs[cat_name] = inp
        row_lo.addWidget(inp)
        self._skill_rows_lo.addWidget(row_w)

    def _remove_skill_cat(self, row_widget: QWidget, cat_name: str):
        self._skill_cat_inputs.pop(cat_name, None)
        row_widget.setParent(None)
        row_widget.deleteLater()

    def _on_add_skill_category(self):
        cat = self._new_cat_inp.text().strip()
        if not cat or cat in self._skill_cat_inputs:
            self._new_cat_inp.clear()
            return
        idx = len(self._skill_cat_inputs)
        self._add_skill_cat_row(cat, "", idx)
        self._new_cat_inp.clear()

    def _save(self):
        # Text fields
        for key, inp in self._inputs.items():
            self._data[key] = inp.text().strip()
        # Skill categories
        skills: dict[str, list[str]] = {}
        for cat_name, inp in self._skill_cat_inputs.items():
            tags = [t.strip() for t in inp.text().split(",") if t.strip()]
            if tags:
                skills[cat_name] = tags
        self._data["skills"] = skills
        self.accept()


# ══════════════════════════════════════════════════════════════
#  CV PREVIEW DIALOG
# ══════════════════════════════════════════════════════════════
class _CVPreviewDialog(QDialog):
    """Lightweight CV preview / upload modal."""

    def __init__(self, cv_path: str | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Xem CV")
        self.setModal(True)
        self.setFixedSize(580, 480)
        self.setStyleSheet("QDialog{background:white;}")
        self._cv_path  = cv_path
        self._new_path: str | None = None
        self._build()

    def get_cv_path(self) -> str | None:
        return self._new_path or self._cv_path

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header
        hdr = QWidget()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1e3a8a,stop:1 #2563eb); border:none;"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 16, 0)
        ht = QLabel("📄  Xem CV")
        ht.setStyleSheet(
            "color:white; font-size:15px; font-weight:800; border:none; background:transparent;"
        )
        hl.addWidget(ht)
        hl.addStretch()
        root.addWidget(hdr)

        # body
        body = QVBoxLayout()
        body.setContentsMargins(32, 28, 32, 20)
        body.setSpacing(16)

        if self._cv_path:
            from pathlib import Path as _Path
            fname = _Path(self._cv_path).name
            # File info chip
            fchip = QFrame()
            fchip.setStyleSheet(
                "QFrame{background:#eff6ff; border-radius:12px; border:none;}"
            )
            flo = QHBoxLayout(fchip)
            flo.setContentsMargins(16, 12, 16, 12)
            flo.setSpacing(12)
            ficon = QLabel("📄")
            ficon.setStyleSheet("font-size:28px; background:transparent; border:none;")
            ftxt = QVBoxLayout()
            ftxt.setSpacing(2)
            fn_lbl = QLabel(fname)
            fn_lbl.setStyleSheet(
                "color:#1e3a8a; font-size:14px; font-weight:700; border:none; background:transparent;"
            )
            fs_lbl = QLabel("Nhấn 'Mở file' để xem bằng ứng dụng mặc định")
            fs_lbl.setStyleSheet(
                "color:#6b7280; font-size:12px; border:none; background:transparent;"
            )
            ftxt.addWidget(fn_lbl)
            ftxt.addWidget(fs_lbl)
            flo.addWidget(ficon)
            flo.addLayout(ftxt, 1)
            body.addWidget(fchip)

            # Preview placeholder
            prev = QFrame()
            prev.setMinimumHeight(240)
            prev.setStyleSheet(
                "QFrame{background:#f8fafc; border:2px dashed #cbd5e1; border-radius:14px;}"
            )
            prev_lo = QVBoxLayout(prev)
            ph = QLabel("🔍  Xem trực tiếp\n\nNhấn 'Mở file' để xem PDF/Word\nbằng ứng dụng mặc định trên máy bạn")
            ph.setAlignment(Qt.AlignCenter)
            ph.setStyleSheet(
                "color:#94a3b8; font-size:13px; line-height:1.6; border:none; background:transparent;"
            )
            prev_lo.addWidget(ph)
            body.addWidget(prev, 1)
        else:
            # No CV uploaded yet
            empty = QFrame()
            empty.setMinimumHeight(280)
            empty.setStyleSheet(
                "QFrame{background:#f8fafc; border:2px dashed #cbd5e1; border-radius:18px;}"
            )
            el = QVBoxLayout(empty)
            et = QLabel("📋")
            et.setAlignment(Qt.AlignCenter)
            et.setStyleSheet("font-size:48px; background:transparent; border:none;")
            et2 = QLabel("Chưa có CV nào được tải lên")
            et2.setAlignment(Qt.AlignCenter)
            et2.setStyleSheet(
                "color:#374151; font-size:14px; font-weight:700; border:none; background:transparent;"
            )
            et3 = QLabel("Tải lên CV của bạn để bắt đầu ứng tuyển")
            et3.setAlignment(Qt.AlignCenter)
            et3.setStyleSheet(
                "color:#9ca3af; font-size:12px; border:none; background:transparent;"
            )
            el.addStretch()
            el.addWidget(et)
            el.addSpacing(8)
            el.addWidget(et2)
            el.addSpacing(4)
            el.addWidget(et3)
            el.addStretch()
            body.addWidget(empty, 1)

        root.addLayout(body)

        # footer
        foot = QWidget()
        foot.setFixedHeight(62)
        foot.setStyleSheet("background:#f8fafc; border:none;")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(32, 0, 32, 0)
        fl.setSpacing(10)

        btn_upload = QPushButton("⬆️  Tải CV mới lên")
        btn_upload.setFixedHeight(40)
        btn_upload.setCursor(Qt.PointingHandCursor)
        btn_upload.setStyleSheet(
            "QPushButton{background:white; color:#374151;"
            "border:1.5px solid #d1d5db; border-radius:20px;"
            "font-size:12px; font-weight:600; padding:0 16px;}"
            "QPushButton:hover{background:#f9fafb;}"
        )
        btn_upload.clicked.connect(self._upload_cv)
        fl.addWidget(btn_upload)
        fl.addStretch()

        if self._cv_path:
            btn_open = QPushButton("🔗  Mở file")
            btn_open.setFixedHeight(40)
            btn_open.setCursor(Qt.PointingHandCursor)
            btn_open.setStyleSheet(
                "QPushButton{background:#2563eb; color:white;"
                "border:none; border-radius:20px;"
                "font-size:12px; font-weight:700; padding:0 20px;}"
                "QPushButton:hover{background:#1d4ed8;}"
            )
            btn_open.clicked.connect(self._open_file)
            fl.addWidget(btn_open)

        btn_close = QPushButton("Đóng")
        btn_close.setFixedHeight(40)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            "QPushButton{background:#6366f1; color:white;"
            "border:none; border-radius:20px;"
            "font-size:12px; font-weight:700; padding:0 20px;}"
            "QPushButton:hover{background:#4f46e5;}"
        )
        btn_close.clicked.connect(self.accept)
        fl.addWidget(btn_close)

        root.addWidget(foot)

    def _upload_cv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file CV",
            "",
            "CV Files (*.pdf *.doc *.docx);;All Files (*)"
        )
        if path:
            self._new_path = path
            self.accept()

    def _open_file(self):
        if self._cv_path:
            import os as _os, subprocess as _sub, sys as _sys
            path = self._cv_path
            if _sys.platform.startswith("win"):
                _os.startfile(path)
            elif _sys.platform == "darwin":
                _sub.Popen(["open", path])
            else:
                _sub.Popen(["xdg-open", path])


# ══════════════════════════════════════════════════════════════
#  INLINE-EDITABLE FIELD
# ══════════════════════════════════════════════════════════════
_RE_EMAIL = re.compile(r"^[\w.+\-]+@[\w\-]+\.[\w.\-]+$")
_RE_PHONE = re.compile(r"^(0|\+84)[0-9]{8,10}$")

class _EditableField(QWidget):
    """Display field that switches to QLineEdit on click, with validation."""

    _VALIDATORS: dict = {
        "email": (_RE_EMAIL, "Email không đúng định dạng"),
        "phone": (_RE_PHONE, "Số điện thoại không hợp lệ (VD: 0912345678)"),
    }

    def __init__(self, label: str, value: str,
                 validator: str = "",
                 on_save: Callable | None = None,
                 parent=None):
        super().__init__(parent)
        self._label     = label
        self._value     = value
        self._validator = validator
        self._on_save   = on_save
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background:transparent;")
        self._build()

    # ── Build ──────────────────────────────────────────────────
    def _build(self):
        self._lo = QVBoxLayout(self)
        self._lo.setContentsMargins(0, 0, 0, 8)
        self._lo.setSpacing(2)

        # Label row
        lbl_row = QHBoxLayout()
        lbl_row.setContentsMargins(0, 0, 0, 0)
        lbl_row.setSpacing(4)
        self._lbl_w = QLabel(self._label)
        self._lbl_w.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px; font-weight:500;"
        )
        lbl_row.addWidget(self._lbl_w)
        lbl_row.addStretch()
        self._lo.addLayout(lbl_row)

        # Stacked widget: [0] view mode, [1] edit mode
        self._stack = QStackedWidget()
        self._stack.setFixedHeight(36)
        self._lo.addWidget(self._stack)

        # ── View mode ──────────────────────────────────────────
        self._view = QFrame()
        self._view.setStyleSheet(
            "QFrame{background:transparent; border:none;}"
            "QFrame:hover{background:#f8fafc; border-radius:6px;}"
        )
        self._view.setCursor(Qt.PointingHandCursor)
        self._view.setToolTip("Nhấp để chỉnh sửa")
        v_lo = QHBoxLayout(self._view)
        v_lo.setContentsMargins(2, 0, 2, 4)
        v_lo.setSpacing(4)
        self._val_lbl = QLabel(self._value if self._value else "—")
        self._val_lbl.setStyleSheet(
            f"color:{'#9ca3af' if not self._value else _TXT_H};"
            "font-size:13px; font-weight:500; background:transparent;"
            "border:none;"
        )
        edit_ic = QLabel()
        edit_ic.setFixedSize(14, 14)
        edit_ic.setPixmap(_svg_pm("ic_edit.svg", 13, "#c4c9d4"))
        edit_ic.setStyleSheet("background:transparent; border:none;")
        v_lo.addWidget(self._val_lbl, 1)
        v_lo.addWidget(edit_ic)
        self._stack.addWidget(self._view)

        # ── Edit mode ──────────────────────────────────────────
        self._edit_frame = QFrame()
        self._edit_frame.setStyleSheet(
            f"QFrame{{background:#f0f4ff; border:none; border-radius:8px;}}"
        )
        e_lo = QHBoxLayout(self._edit_frame)
        e_lo.setContentsMargins(2, 0, 2, 2)
        e_lo.setSpacing(4)
        self._line = QLineEdit(self._value)
        self._line.setStyleSheet(
            "border:none; background:transparent;"
            f"color:{_TXT_H}; font-size:13px; font-weight:500;"
        )
        self._line.returnPressed.connect(self._save)

        btn_save = QPushButton("✓")
        btn_save.setFixedSize(28, 28)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setToolTip("Lưu (Enter)")
        btn_save.setStyleSheet(
            "QPushButton{background:#dcfce7; color:#16a34a;"
            "border-radius:7px; border:none; font-size:13px; font-weight:800;}"
            "QPushButton:hover{background:#bbf7d0;}"
        )
        btn_save.clicked.connect(self._save)

        btn_cancel = QPushButton("✕")
        btn_cancel.setFixedSize(28, 28)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setToolTip("Hủy (Esc)")
        btn_cancel.setStyleSheet(
            "QPushButton{background:#fee2e2; color:#dc2626;"
            "border-radius:7px; border:none; font-size:11px; font-weight:800;}"
            "QPushButton:hover{background:#fecaca;}"
        )
        btn_cancel.clicked.connect(self._cancel)

        e_lo.addWidget(self._line, 1)
        e_lo.addWidget(btn_save)
        e_lo.addWidget(btn_cancel)
        self._stack.addWidget(self._edit_frame)

        # Error label (hidden by default)
        self._err_lbl = QLabel()
        self._err_lbl.setStyleSheet(
            "color:#ef4444; font-size:11px; font-weight:500;"
            "background:transparent;"
        )
        self._err_lbl.hide()
        self._lo.addWidget(self._err_lbl)

        # Click on view → edit mode
        self._view.mousePressEvent = lambda _e: self._start_edit()

    # ── Edit lifecycle ─────────────────────────────────────────
    def _start_edit(self):
        self._line.setText(self._value)
        self._line.setFocus()
        self._line.selectAll()
        self._err_lbl.hide()
        self._edit_frame.setStyleSheet(
            f"QFrame{{background:white; border:2px solid {_INDIGO};"
            "border-radius:10px;}}"
        )
        self._stack.setCurrentIndex(1)

    def _save(self):
        new_val = self._line.text().strip()
        if self._validator in self._VALIDATORS:
            pattern, msg = self._VALIDATORS[self._validator]
            if new_val and not pattern.match(new_val):
                self._err_lbl.setText(f"⚠  {msg}")
                self._err_lbl.show()
                self._edit_frame.setStyleSheet(
                    "QFrame{background:white; border:2px solid #ef4444;"
                    "border-radius:10px;}"
                )
                return
        self._value = new_val
        self._val_lbl.setText(self._value if self._value else "—")
        self._val_lbl.setStyleSheet(
            f"color:{'#9ca3af' if not self._value else _TXT_H};"
            "font-size:13px; font-weight:500; background:transparent;"
        )
        self._err_lbl.hide()
        self._stack.setCurrentIndex(0)
        if self._on_save:
            self._on_save(self._label, self._value)

    def _cancel(self):
        self._err_lbl.hide()
        self._stack.setCurrentIndex(0)

    def get_value(self) -> str:
        return self._value

    def _set_value(self, new_val: str) -> None:
        """Programmatically update the displayed value (from profile edit dialog)."""
        self._value = new_val
        self._val_lbl.setText(new_val if new_val else "—")
        self._val_lbl.setStyleSheet(
            f"color:{'#9ca3af' if not new_val else _TXT_H};"
            "font-size:14px; font-weight:500; border:none; background:transparent;"
        )
        self._line.setText(new_val)
        self._stack.setCurrentIndex(0)


# ══════════════════════════════════════════════════════════════
#  USER DASHBOARD
# ══════════════════════════════════════════════════════════════
class UserDashboard:
    """Dashboard cho Ứng viên — pure Python, không .ui file."""

    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout

        # ── Shared runtime state (must be first — used by build methods) ──
        self._saved_job_keys: set[str] = set()   # "title||comp" keys of saved jobs
        self._applied_hist:   list     = []      # newly applied entries (prepended)
        self._search_query:   str      = ""      # current topbar search text

        # ── Profile data (persisted in session) ──────────────
        self._profile_data: dict = {
            "name":    "Nguyễn Văn A",
            "tagline": "Mid Developer · 3 năm kinh nghiệm",
            "email":   "nguyenvana@email.com",
            "phone":   "0912 345 678",
            "address": "Hà Nội, Việt Nam",
            "field":   "Phát triển Phần mềm",
            "degree":  "Cử nhân CNTT",
            "exp":     "5 năm kinh nghiệm",
            "lang":    "Tiếng Anh (IELTS 7.5)",
            "cv_path": None,     # path to uploaded CV file
            "skills": {          # danh mục → danh sách kỹ năng
                "Frontend":       ["React", "TypeScript", "HTML/CSS"],
                "Backend":        ["Python", "Node.js", "FastAPI"],
                "Cloud / DevOps": ["Docker", "AWS", "CI/CD"],
            },
        }

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

        self._stack.addWidget(self._build_home_page())      # 0
        self._stack.addWidget(self._build_history_page())   # 1
        self._stack.addWidget(self._build_saved_page())     # 2
        self._stack.addWidget(self._build_profile_page())   # 3
        # page 4: job detail (placeholder, rebuilt on each open)
        self._job_detail_placeholder = QWidget()
        self._job_detail_placeholder.setStyleSheet(
            f"background:{_CONTENT_BG};"
        )
        self._stack.addWidget(self._job_detail_placeholder) # 4
        self._prev_page = 0   # page to return to from detail

        root_lo.addWidget(right, 1)

        self._nav_btns[0].set_active(True)
        self._stack.setCurrentIndex(0)

        # ── Polling timer: kiểm tra cập nhật trạng thái từ HR ──
        self._poll_timer = QTimer(self.win)
        self._poll_timer.setInterval(_POLL_INTERVAL_MS)
        self._poll_timer.timeout.connect(self._poll_application_statuses)
        self._poll_timer.start()

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

        # Brand — logo + JobHub
        brand = QWidget()
        brand.setFixedHeight(68)
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
            "font-size:14px; font-weight:800; border:none;"
        )
        lbl_brand = QLabel("JobHub")
        lbl_brand.setStyleSheet(
            "color:#f1f5f9; font-size:16px; font-weight:700;"
            "letter-spacing:1.5px; background:transparent; border:none;"
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

        lo.addStretch()

        # ── Search bar (centered) ─────────────────────────────
        search_wrap = QFrame()
        search_wrap.setFixedHeight(42)
        search_wrap.setFixedWidth(480)
        search_wrap.setStyleSheet(
            "QFrame{"
            "background:#f1f5f9; border-radius:21px; border:none;}"
            "QFrame:focus-within{"
            f"border:1.5px solid {_INDIGO};}}"
        )
        sw_lo = QHBoxLayout(search_wrap)
        sw_lo.setContentsMargins(14, 0, 14, 0)
        sw_lo.setSpacing(8)

        search_icon = QLabel()
        search_icon.setFixedSize(16, 16)
        search_icon.setPixmap(_svg_pm("ic_search.svg", 16, "#94a3b8"))
        search_icon.setStyleSheet("background:transparent; border:none;")

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Tìm kiếm việc làm, kỹ năng, công ty...")
        self._search_edit.setStyleSheet(
            "border:none; background:transparent;"
            f"color:{_TXT_S}; font-size:13px;"
            "selection-background-color:#e0e7ff;"
        )
        self._search_edit.textChanged.connect(self._on_search_changed)

        sw_lo.addWidget(search_icon)
        sw_lo.addWidget(self._search_edit, 1)
        lo.addWidget(search_wrap)

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

    def _open_job_detail(self, title: str, comp: str, jtype: str,
                         sal: str, loc: str, idx: int = 0) -> None:
        """Replace page-4 widget with fresh job detail and navigate to it."""
        self._prev_page = self._stack.currentIndex()
        new_page = self._build_job_detail_page(title, comp, jtype, sal, loc, idx)
        # swap out placeholder
        old = self._stack.widget(4)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(4, new_page)
        for btn in self._nav_btns:
            btn.set_active(False)
        self._stack.setCurrentIndex(4)

    def _build_job_detail_page(self, title: str, comp: str, jtype: str,
                                sal: str, loc: str, idx: int = 0) -> QWidget:
        """Full job detail page — 2-column layout matching reference UI."""
        bg_col, fg_col = _LOGO_PALETTE[idx % len(_LOGO_PALETTE)]
        scroll, lo = self._page_scroll_wrapper()
        lo.setSpacing(0)

        # ── Back button ──────────────────────────────────────
        back_row = QHBoxLayout()
        back_row.setContentsMargins(0, 0, 0, 16)
        back_btn = QPushButton("← Quay lại danh sách")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet(
            f"QPushButton{{background:transparent; color:{_TXT_M};"
            "border:none; font-size:13px; font-weight:600; padding:0;}}"
            f"QPushButton:hover{{color:{_BLUE};}}"
        )
        back_btn.clicked.connect(lambda: self._go(self._prev_page))
        back_row.addWidget(back_btn)
        back_row.addStretch()
        lo.addLayout(back_row)

        # ── Hero card ────────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet(
            "QFrame{background:white; border-radius:18px; border:1px solid #e5e7eb;}"
        )
        _shadow(hero, 12, 4, 14)
        hero_lo = QHBoxLayout(hero)
        hero_lo.setContentsMargins(28, 24, 28, 24)
        hero_lo.setSpacing(24)

        # Logo
        logo = QLabel(comp[0].upper())
        logo.setFixedSize(72, 72)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(
            f"background:{bg_col}; color:{fg_col}; border-radius:18px;"
            "font-size:28px; font-weight:800; border:none;"
        )

        # Title block
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        h1 = QLabel(title)
        h1.setStyleSheet(
            f"color:{_TXT_H}; font-size:24px; font-weight:800; border:none; background:transparent;"
        )
        h1.setWordWrap(True)
        comp_row = QHBoxLayout()
        comp_row.setSpacing(8)
        comp_lbl = QLabel(comp)
        comp_lbl.setStyleSheet(
            f"color:{_BLUE}; font-size:14px; font-weight:700; border:none; background:transparent;"
        )
        dot_lbl = QLabel("·")
        dot_lbl.setStyleSheet(f"color:{_TXT_M}; border:none; background:transparent;")
        cat_lbl = QLabel("Công nghệ thông tin")
        cat_lbl.setStyleSheet(
            f"color:{_TXT_M}; font-size:13px; border:none; background:transparent;"
        )
        comp_row.addWidget(comp_lbl)
        comp_row.addWidget(dot_lbl)
        comp_row.addWidget(cat_lbl)
        comp_row.addStretch()
        title_col.addWidget(h1)
        title_col.addLayout(comp_row)

        # Info chips (right side of hero)
        chips_col = QVBoxLayout()
        chips_col.setSpacing(10)
        chips_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for chip_title, chip_val, chip_accent in [
            ("Mức lương",      sal,   _BLUE),
            ("Loại hình",      jtype, "#374151"),
            ("Địa điểm",       loc,   "#374151"),
        ]:
            chip = QFrame()
            chip.setStyleSheet(
                f"QFrame{{background:#f8fafc; border:1px solid #e5e7eb;"
                "border-radius:10px;}}"
            )
            chip.setFixedHeight(52)
            chip.setMinimumWidth(170)
            chip_lo = QVBoxLayout(chip)
            chip_lo.setContentsMargins(14, 6, 14, 6)
            chip_lo.setSpacing(1)
            ct = QLabel(chip_title)
            ct.setStyleSheet(
                f"color:{_TXT_M}; font-size:10px; font-weight:600;"
                "letter-spacing:0.5px; border:none; background:transparent;"
            )
            cv = QLabel(chip_val)
            cv.setStyleSheet(
                f"color:{chip_accent}; font-size:13px; font-weight:700;"
                "border:none; background:transparent;"
            )
            chip_lo.addWidget(ct)
            chip_lo.addWidget(cv)
            chips_col.addWidget(chip)

        hero_lo.addWidget(logo, 0, Qt.AlignTop)
        hero_lo.addLayout(title_col, 1)
        hero_lo.addLayout(chips_col)
        lo.addWidget(hero)
        lo.addSpacing(10)

        # Meta bar
        meta = QHBoxLayout()
        meta.setSpacing(24)
        meta.setContentsMargins(4, 0, 0, 0)
        for ic_svg, meta_txt in [
            ("ic_jobs.svg",  "Đăng 2 ngày trước"),
            ("ic_user.svg",  "12 ứng viên"),
            ("ic_check.svg", "Nhà tuyển dụng đã xác minh"),
        ]:
            mr = QHBoxLayout()
            mr.setSpacing(6)
            mi = QLabel()
            mi.setFixedSize(14, 14)
            mi.setPixmap(_svg_pm(ic_svg, 14, "#10b981"))
            mi.setStyleSheet("background:transparent; border:none;")
            mt = QLabel(meta_txt)
            mt.setStyleSheet(
                f"color:{_TXT_M}; font-size:12px; border:none; background:transparent;"
            )
            mr.addWidget(mi)
            mr.addWidget(mt)
            meta.addLayout(mr)
        meta.addStretch()
        lo.addLayout(meta)
        lo.addSpacing(20)

        # ── 2-column body ─────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(20)
        body.setContentsMargins(0, 0, 0, 0)

        # LEFT — main content
        left = QVBoxLayout()
        left.setSpacing(16)
        left.setContentsMargins(0, 0, 0, 0)

        def _content_card(title_txt: str, content_fn) -> QFrame:
            c = QFrame()
            c.setStyleSheet(
                "QFrame{background:white; border-radius:16px; border:1px solid #e5e7eb;}"
            )
            _shadow(c, 8, 3, 10)
            c_lo = QVBoxLayout(c)
            c_lo.setContentsMargins(24, 20, 24, 24)
            c_lo.setSpacing(14)
            h2 = QLabel(title_txt)
            h2.setStyleSheet(
                f"color:{_TXT_H}; font-size:17px; font-weight:800;"
                "border:none; background:transparent;"
            )
            c_lo.addWidget(h2)
            content_fn(c_lo)
            return c

        def _body_lbl(txt: str) -> QLabel:
            l = QLabel(txt)
            l.setWordWrap(True)
            l.setStyleSheet(
                f"color:{_TXT_S}; font-size:13px; line-height:1.6;"
                "border:none; background:transparent;"
            )
            return l

        def _bullet(txt: str) -> QHBoxLayout:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.setContentsMargins(0, 0, 0, 0)
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background:{_BLUE}; border-radius:4px; border:none;"
            )
            dot.setAlignment(Qt.AlignCenter)
            lbl = QLabel(txt)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color:{_TXT_S}; font-size:13px; border:none; background:transparent;"
            )
            row.addWidget(dot, 0, Qt.AlignTop | Qt.AlignHCenter)
            row.addWidget(lbl, 1)
            return row

        # Job description card
        def _desc_content(c_lo):
            c_lo.addWidget(_body_lbl(
                f"{comp} đang tìm kiếm {title} tài năng để gia nhập đội ngũ. "
                "Bạn sẽ chịu trách nhiệm thiết kế và phát triển các tính năng quan trọng, "
                "phối hợp chặt chẽ với các kỹ sư và product manager để xây dựng "
                "trải nghiệm người dùng chất lượng cao."
            ))
            c_lo.addWidget(_body_lbl(
                "Là thành viên cấp cao, bạn sẽ hướng dẫn các thành viên trẻ và đóng góp "
                "vào hệ thống thiết kế tổng thể, đảm bảo tính nhất quán trên toàn bộ nền tảng."
            ))
            kw = QLabel("Nhiệm vụ chính:")
            kw.setStyleSheet(
                f"color:{_TXT_H}; font-size:13px; font-weight:700;"
                "border:none; background:transparent;"
            )
            c_lo.addWidget(kw)
            for b in [
                "Dẫn dắt quy trình thiết kế end-to-end cho các tính năng phức tạp.",
                "Phát triển prototype độ trung thực cao và tài liệu kỹ thuật chi tiết.",
                "Tổ chức nghiên cứu người dùng và chuyển đổi insight thành cải tiến.",
                "Duy trì và mở rộng design system và brand guidelines.",
                "Tham gia code review và đưa ra phản hồi mang tính xây dựng.",
            ]:
                c_lo.addLayout(_bullet(b))

        left.addWidget(_content_card("Mô tả công việc", _desc_content))

        # Requirements card — 2 sub-columns
        def _req_content(c_lo):
            req_row = QHBoxLayout()
            req_row.setSpacing(20)
            for col_title, col_ic, items in [
                ("Kỹ năng kỹ thuật", "ic_jobs.svg", [
                    "5+ năm kinh nghiệm trong lĩnh vực liên quan.",
                    "Thành thạo các công cụ thiết kế / lập trình hiện đại.",
                    "Hiểu biết sâu về HTML/CSS và khả năng làm việc với code.",
                ]),
                ("Kỹ năng mềm", "ic_user.svg", [
                    "Khả năng kể chuyện và trình bày xuất sắc.",
                    "Tư duy chiến lược và giải quyết vấn đề.",
                    "Tinh thần đồng đội và đồng cảm với người dùng.",
                ]),
            ]:
                sub = QVBoxLayout()
                sub.setSpacing(10)
                sub_hdr = QHBoxLayout()
                sub_hdr.setSpacing(8)
                sub_ic = QLabel()
                sub_ic.setFixedSize(16, 16)
                sub_ic.setPixmap(_svg_pm(col_ic, 16, _BLUE))
                sub_ic.setStyleSheet("background:transparent; border:none;")
                sub_ttl = QLabel(col_title)
                sub_ttl.setStyleSheet(
                    f"color:{_TXT_H}; font-size:13px; font-weight:700;"
                    "border:none; background:transparent;"
                )
                sub_hdr.addWidget(sub_ic)
                sub_hdr.addWidget(sub_ttl)
                sub.addLayout(sub_hdr)
                for item in items:
                    row = QHBoxLayout()
                    row.setSpacing(8)
                    chk = QLabel("✓")
                    chk.setFixedWidth(16)
                    chk.setStyleSheet(
                        f"color:#10b981; font-size:13px; font-weight:800;"
                        "border:none; background:transparent;"
                    )
                    t = QLabel(item)
                    t.setWordWrap(True)
                    t.setStyleSheet(
                        f"color:{_TXT_S}; font-size:12px; border:none; background:transparent;"
                    )
                    row.addWidget(chk, 0, Qt.AlignTop)
                    row.addWidget(t, 1)
                    sub.addLayout(row)
                req_row.addLayout(sub, 1)
            c_lo.addLayout(req_row)

        left.addWidget(_content_card("Yêu cầu", _req_content))

        # Perks card — 2x2 grid
        def _perks_content(c_lo):
            perks_grid = QGridLayout()
            perks_grid.setSpacing(12)
            perks_data = [
                ("💰", "Lương cạnh tranh",    "Thưởng hiệu suất hàng năm",   "#dbeafe", _BLUE),
                ("🛡️", "Bảo hiểm toàn diện", "Y tế, nha khoa và thị lực",   "#dcfce7", "#16a34a"),
                ("💻", "Trang bị cao cấp",    "MacBook Pro & workspace stipend", "#f3e8ff", "#9333ea"),
                ("🕐", "Giờ làm linh hoạt",   "Văn hóa remote-first",         "#fef3c7", "#d97706"),
            ]
            for i, (ic, name, desc, bg, fg) in enumerate(perks_data):
                pf = QFrame()
                pf.setStyleSheet(
                    f"QFrame{{background:{bg}; border-radius:12px; border:none;}}"
                )
                pf_lo = QHBoxLayout(pf)
                pf_lo.setContentsMargins(14, 12, 14, 12)
                pf_lo.setSpacing(12)
                ic_lbl = QLabel(ic)
                ic_lbl.setFixedSize(36, 36)
                ic_lbl.setAlignment(Qt.AlignCenter)
                ic_lbl.setStyleSheet(
                    f"background:white; border-radius:9px; font-size:16px; border:none;"
                )
                txt = QVBoxLayout()
                txt.setSpacing(2)
                n = QLabel(name)
                n.setStyleSheet(
                    f"color:{_TXT_H}; font-size:12px; font-weight:700;"
                    "border:none; background:transparent;"
                )
                d = QLabel(desc)
                d.setStyleSheet(
                    f"color:{_TXT_M}; font-size:11px; border:none; background:transparent;"
                )
                txt.addWidget(n)
                txt.addWidget(d)
                pf_lo.addWidget(ic_lbl)
                pf_lo.addLayout(txt, 1)
                perks_grid.addWidget(pf, i // 2, i % 2)
            c_lo.addLayout(perks_grid)

        left.addWidget(_content_card("Quyền lợi & Phúc lợi", _perks_content))
        left.addStretch()

        # RIGHT — sidebar
        right_col = QVBoxLayout()
        right_col.setSpacing(14)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setAlignment(Qt.AlignTop)

        # Action buttons card
        act = QFrame()
        act.setStyleSheet(
            "QFrame{background:white; border-radius:16px; border:1px solid #e5e7eb;}"
        )
        _shadow(act, 8, 3, 10)
        act_lo = QVBoxLayout(act)
        act_lo.setContentsMargins(18, 18, 18, 18)
        act_lo.setSpacing(10)

        def _act_btn(txt, bg, fg, icon_svg):
            b = QPushButton()
            b.setFixedHeight(44)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(QIcon(_svg_pm(icon_svg, 15, fg)))
            b.setIconSize(QSize(15, 15))
            b.setText(f"  {txt}")
            if bg == _BLUE:
                b.setStyleSheet(
                    f"QPushButton{{background:{_BLUE}; color:white; border:none;"
                    "border-radius:22px; font-size:13px; font-weight:700;}}"
                    f"QPushButton:hover{{background:{_BLUE_DARK};}}"
                )
                _btn_shadow(b, _BLUE, 60)
            elif bg == _BLUE_LIGHT:
                b.setStyleSheet(
                    f"QPushButton{{background:{_BLUE_LIGHT}; color:{_BLUE};"
                    "border:none; border-radius:22px; font-size:13px; font-weight:600;}}"
                    f"QPushButton:hover{{background:#bfdbfe;}}"
                )
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:white; color:{_TXT_S};"
                    "border:1.5px solid #d1d5db; border-radius:22px;"
                    "font-size:13px; font-weight:600;}}"
                    "QPushButton:hover{background:#f9fafb;}"
                )
            return b

        btn_apply_now = _act_btn("Ứng tuyển ngay", _BLUE, "white", "ic_edit.svg")

        def _open_apply_from_detail(checked=False, _t=title):
            dlg = _ApplyDialog(_t, self.win)
            if dlg.exec() == QDialog.Accepted:
                _Toast(self.win.centralWidget(),
                       f"Đã gửi hồ sơ cho vị trí {_t} thành công!")

        btn_apply_now.clicked.connect(_open_apply_from_detail)
        act_lo.addWidget(btn_apply_now)
        act_lo.addWidget(_act_btn("Lưu công việc", _BLUE_LIGHT, _BLUE, "bookmark_outline.svg"))
        act_lo.addWidget(_act_btn("Chia sẻ", "white", _TXT_S, "ic_pin.svg"))
        right_col.addWidget(act)

        # About company card
        abt = QFrame()
        abt.setStyleSheet(
            "QFrame{background:white; border-radius:16px; border:1px solid #e5e7eb;}"
        )
        _shadow(abt, 8, 3, 10)
        abt_lo = QVBoxLayout(abt)
        abt_lo.setContentsMargins(18, 18, 18, 18)
        abt_lo.setSpacing(10)
        abt_ttl = QLabel("Về công ty")
        abt_ttl.setStyleSheet(
            f"color:{_TXT_H}; font-size:14px; font-weight:800;"
            "border:none; background:transparent;"
        )
        abt_lo.addWidget(abt_ttl)
        abt_desc = QLabel(
            f"Công ty hàng đầu trong lĩnh vực SaaS với focus vào "
            "thiết kế lấy con người làm trung tâm và hạ tầng mở rộng."
        )
        abt_desc.setWordWrap(True)
        abt_desc.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px; line-height:1.5;"
            "border:none; background:transparent;"
        )
        abt_lo.addWidget(abt_desc)
        for key, val in [
            ("Lĩnh vực",       "Phần mềm & CNTT"),
            ("Quy mô",         "500 – 1000 nhân sự"),
            ("Website",        "techcorp.vn"),
        ]:
            row = QHBoxLayout()
            row.setSpacing(0)
            k = QLabel(key)
            k.setStyleSheet(
                f"color:{_TXT_M}; font-size:12px; border:none; background:transparent;"
            )
            v = QLabel(val)
            v.setAlignment(Qt.AlignRight)
            v.setStyleSheet(
                f"color:{_TXT_H}; font-size:12px; font-weight:600;"
                "border:none; background:transparent;"
            )
            row.addWidget(k, 1)
            row.addWidget(v, 1)
            abt_lo.addLayout(row)
        right_col.addWidget(abt)

        # Related jobs card
        rel = QFrame()
        rel.setStyleSheet(
            "QFrame{background:white; border-radius:16px; border:1px solid #e5e7eb;}"
        )
        _shadow(rel, 8, 3, 10)
        rel_lo = QVBoxLayout(rel)
        rel_lo.setContentsMargins(18, 18, 18, 18)
        rel_lo.setSpacing(10)
        rel_ttl = QLabel("Việc làm liên quan")
        rel_ttl.setStyleSheet(
            f"color:{_TXT_H}; font-size:14px; font-weight:800;"
            "border:none; background:transparent;"
        )
        rel_lo.addWidget(rel_ttl)
        for r_title, r_comp, r_sal in [
            ("Senior Frontend Developer",  "TechViet Corp",  "$2.5k – $4k"),
            ("UX Researcher",              "MetaSystem VN",  "$3k – $5.5k"),
            ("Head of Product",            "Lumine Hub",     "$8k – $12k"),
        ]:
            rf = QFrame()
            rf.setCursor(Qt.PointingHandCursor)
            rf.setStyleSheet(
                "QFrame{background:#f8fafc; border-radius:10px; border:none;}"
                "QFrame:hover{background:#eff6ff;}"
            )
            rf_lo = QVBoxLayout(rf)
            rf_lo.setContentsMargins(12, 10, 12, 10)
            rf_lo.setSpacing(2)
            rn = QLabel(r_title)
            rn.setStyleSheet(
                f"color:{_TXT_H}; font-size:12px; font-weight:700;"
                "border:none; background:transparent;"
            )
            rc = QLabel(f"{r_comp}  •  {r_sal}")
            rc.setStyleSheet(
                f"color:{_TXT_M}; font-size:11px; border:none; background:transparent;"
            )
            rf_lo.addWidget(rn)
            rf_lo.addWidget(rc)
            rel_lo.addWidget(rf)
        right_col.addWidget(rel)
        right_col.addStretch()

        body.addLayout(left, 3)
        body.addLayout(right_col, 1)
        lo.addLayout(body)
        lo.addStretch()
        return scroll

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
            "QScrollBar:vertical{"
            "  width:10px; background:transparent; margin:4px 2px 4px 2px;}"
            "QScrollBar::handle:vertical{"
            "  background:#c1c9d6; border-radius:5px; min-height:40px;}"
            "QScrollBar::handle:vertical:hover{"
            "  background:#94a3b8;}"
            "QScrollBar::handle:vertical:pressed{"
            "  background:#64748b;}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical{height:0;}"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical{background:none;}"
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
            f"QFrame{{background:{_CARD_BG}; border:none;"
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
            "border:none; background:transparent;"
        )
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px; font-weight:500;"
            "border:none; background:transparent;"
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
            f"QFrame{{background:{_CARD_BG}; border:none;"
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
            "background:white; border:none;"
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
            "background:white; border:none;"
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
        # Merge newly applied entries (prepended) with baseline mock data
        data   = self._applied_hist + _HIST_DATA
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
    # ── helper: card section title row ────────────────────────
    def _section_title(self, icon_svg: str, accent: str, title: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)
        ib = QFrame()
        ib.setFixedSize(32, 32)
        ib.setStyleSheet(f"background:{accent}22; border-radius:9px; border:none;")
        il = QHBoxLayout(ib)
        il.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setFixedSize(16, 16)
        ic.setPixmap(_svg_pm(icon_svg, 16, accent))
        ic.setStyleSheet("background:transparent; border:none;")
        il.addWidget(ic, 0, Qt.AlignCenter)
        t = QLabel(title)
        t.setStyleSheet(
            f"color:{_TXT_H}; font-size:15px; font-weight:700;"
            "border:none; background:transparent;"
        )
        row.addWidget(ib)
        row.addWidget(t)
        row.addStretch()
        return row

    # ── helper: skill chip row ─────────────────────────────────
    def _skill_chip_row(self, skills: list[tuple[str, str, str]]) -> QWidget:
        """skills: [(label, bg, fg), ...]"""
        w = QWidget()
        w.setStyleSheet("background:transparent; border:none;")
        lo = QHBoxLayout(w)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(8)
        for lbl, bg, fg in skills:
            c = QLabel(lbl)
            c.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:12px;"
                "padding:4px 11px; font-size:12px; font-weight:600; border:none;"
            )
            lo.addWidget(c)
        lo.addStretch()
        return w

    def _build_profile_page(self) -> QWidget:
        scroll, lo = self._page_scroll_wrapper()
        self._prof_field_refs: list[_EditableField] = []

        # ══════════════════════════════════════════════════════
        #  2-COLUMN LAYOUT: left sidebar | right content
        # ══════════════════════════════════════════════════════
        body = QHBoxLayout()
        body.setSpacing(20)
        body.setContentsMargins(0, 0, 0, 0)

        # ─────────────────────────────────────────────────────
        #  LEFT SIDEBAR (fixed 268px)
        # ─────────────────────────────────────────────────────
        sidebar = QVBoxLayout()
        sidebar.setSpacing(16)
        sidebar.setContentsMargins(0, 0, 0, 0)

        # ── Profile identity card ──────────────────────────────
        id_card = QFrame()
        id_card.setFixedWidth(268)
        id_card.setStyleSheet(
            "QFrame{background:white; border-radius:18px; border:none;}"
        )
        _shadow(id_card, 12, 4, 14)
        id_lo = QVBoxLayout(id_card)
        id_lo.setContentsMargins(24, 28, 24, 24)
        id_lo.setSpacing(0)

        # ── Avatar with camera overlay ─────────────────────────
        av_wrap = QWidget()
        av_wrap.setFixedSize(96, 96)
        av_wrap.setStyleSheet("background:transparent;")

        glow = QLabel(av_wrap)
        glow.setGeometry(0, 0, 96, 96)
        glow.setStyleSheet(
            "border-radius:48px; border:3px solid #10b981; background:transparent;"
        )
        self._av_lbl = QLabel("UV", av_wrap)
        self._av_lbl.setGeometry(6, 6, 84, 84)
        self._av_lbl.setAlignment(Qt.AlignCenter)
        self._av_lbl.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #0f172a,stop:0.5 #1e3a8a,stop:1 #2563eb);"
            "border-radius:42px; color:white; font-size:22px;"
            "font-weight:800; border:none;"
        )
        chk = QLabel("✓", av_wrap)
        chk.setFixedSize(22, 22)
        chk.move(70, 70)
        chk.setAlignment(Qt.AlignCenter)
        chk.setStyleSheet(
            "background:#10b981; color:white; border-radius:11px;"
            "font-size:10px; font-weight:800; border:2px solid white;"
        )
        # Camera button — bottom-left of avatar
        cam_btn = QPushButton("📷", av_wrap)
        cam_btn.setFixedSize(26, 26)
        cam_btn.move(0, 68)
        cam_btn.setCursor(Qt.PointingHandCursor)
        cam_btn.setToolTip("Đổi ảnh đại diện")
        cam_btn.setStyleSheet(
            "QPushButton{background:#6366f1; color:white; border-radius:13px;"
            "font-size:13px; border:2px solid white; padding:0;}"
            "QPushButton:hover{background:#4f46e5;}"
        )
        cam_btn.clicked.connect(self._change_avatar)

        id_lo.addWidget(av_wrap, 0, Qt.AlignHCenter)
        id_lo.addSpacing(14)

        # ── Name — inline edit with double-click ───────────────
        name_stack = QStackedWidget()
        name_stack.setFixedHeight(34)
        name_stack.setStyleSheet("background:transparent;")

        # View mode
        name_view = QWidget()
        name_view.setStyleSheet("background:transparent;")
        nv_lo = QHBoxLayout(name_view)
        nv_lo.setContentsMargins(0, 0, 0, 0)
        nv_lo.setSpacing(6)
        self._prof_name_lbl = QLabel(self._profile_data["name"])
        self._prof_name_lbl.setAlignment(Qt.AlignCenter)
        self._prof_name_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:18px; font-weight:800;"
            "border:none; background:transparent;"
        )
        self._prof_name_lbl.setToolTip("Double-click để đổi tên")
        edit_name_btn = QPushButton("✏")
        edit_name_btn.setFixedSize(20, 20)
        edit_name_btn.setCursor(Qt.PointingHandCursor)
        edit_name_btn.setStyleSheet(
            "QPushButton{background:transparent; color:#94a3b8; border:none;"
            "font-size:11px; padding:0;}"
            "QPushButton:hover{color:#6366f1;}"
        )
        nv_lo.addStretch()
        nv_lo.addWidget(self._prof_name_lbl)
        nv_lo.addWidget(edit_name_btn)
        nv_lo.addStretch()

        # Edit mode
        name_edit_w = QWidget()
        name_edit_w.setStyleSheet("background:transparent;")
        ne_lo = QHBoxLayout(name_edit_w)
        ne_lo.setContentsMargins(0, 0, 0, 0)
        ne_lo.setSpacing(4)
        self._name_inp = QLineEdit(self._profile_data["name"])
        self._name_inp.setFixedHeight(30)
        self._name_inp.setAlignment(Qt.AlignCenter)
        self._name_inp.setStyleSheet(
            "QLineEdit{background:#f1f5f9; border:1.5px solid #6366f1;"
            "border-radius:8px; font-size:13px; font-weight:700;"
            "color:#111827; padding:0 8px;}"
        )
        save_n = QPushButton("✓")
        save_n.setFixedSize(28, 28)
        save_n.setCursor(Qt.PointingHandCursor)
        save_n.setStyleSheet(
            "QPushButton{background:#10b981; color:white; border:none;"
            "border-radius:8px; font-size:14px; font-weight:800;}"
            "QPushButton:hover{background:#059669;}"
        )
        cancel_n = QPushButton("✕")
        cancel_n.setFixedSize(28, 28)
        cancel_n.setCursor(Qt.PointingHandCursor)
        cancel_n.setStyleSheet(
            "QPushButton{background:#f1f5f9; color:#6b7280; border:none;"
            "border-radius:8px; font-size:13px;}"
            "QPushButton:hover{background:#e5e7eb;}"
        )
        ne_lo.addWidget(self._name_inp, 1)
        ne_lo.addWidget(save_n)
        ne_lo.addWidget(cancel_n)

        name_stack.addWidget(name_view)   # index 0
        name_stack.addWidget(name_edit_w) # index 1

        def _enter_name_edit():
            self._name_inp.setText(self._profile_data["name"])
            self._name_inp.selectAll()
            name_stack.setCurrentIndex(1)
            self._name_inp.setFocus()

        def _save_name():
            v = self._name_inp.text().strip()
            if v:
                self._profile_data["name"] = v
                self._prof_name_lbl.setText(v)
                # Update topbar avatar text
                initials = "".join(p[0].upper() for p in v.split()[:2]) or "UV"
                self._av_lbl.setText(initials)
                _Toast(self.win.centralWidget(),
                       f"Tên đã cập nhật: {v}",
                       accent=_INDIGO, duration_ms=2500,
                       title_text="Đã lưu tên mới ✓", icon_char="✓")
            name_stack.setCurrentIndex(0)

        def _cancel_name():
            name_stack.setCurrentIndex(0)

        edit_name_btn.clicked.connect(_enter_name_edit)
        self._prof_name_lbl.mouseDoubleClickEvent = lambda _e: _enter_name_edit()
        save_n.clicked.connect(_save_name)
        cancel_n.clicked.connect(_cancel_name)
        self._name_inp.returnPressed.connect(_save_name)

        id_lo.addWidget(name_stack)
        id_lo.addSpacing(4)

        # tagline
        self._prof_tag_lbl = QLabel(self._profile_data["tagline"])
        self._prof_tag_lbl.setAlignment(Qt.AlignCenter)
        self._prof_tag_lbl.setWordWrap(True)
        self._prof_tag_lbl.setStyleSheet(
            f"color:{_TXT_M}; font-size:12px; border:none; background:transparent;"
        )
        id_lo.addWidget(self._prof_tag_lbl)
        id_lo.addSpacing(20)

        # divider
        div1 = QFrame()
        div1.setFixedHeight(1)
        div1.setStyleSheet("background:#f1f5f9; border:none;")
        id_lo.addWidget(div1)
        id_lo.addSpacing(16)

        # contact items (vertical) — stored for live update
        self._prof_contact_lbls: dict[str, QLabel] = {}
        for icon_svg, key, ctxt in [
            ("ic_email.svg", "email",   self._profile_data["email"]),
            ("ic_phone.svg", "phone",   self._profile_data["phone"]),
            ("ic_pin.svg",   "address", self._profile_data["address"]),
        ]:
            cr = QHBoxLayout()
            cr.setSpacing(10)
            cr.setContentsMargins(0, 0, 0, 0)
            ic_lbl = QLabel()
            ic_lbl.setFixedSize(14, 14)
            ic_lbl.setPixmap(_svg_pm(icon_svg, 14, "#94a3b8"))
            ic_lbl.setStyleSheet("background:transparent; border:none;")
            tx_lbl = QLabel(ctxt)
            tx_lbl.setStyleSheet(
                f"color:{_TXT_S}; font-size:12px;"
                "border:none; background:transparent;"
            )
            self._prof_contact_lbls[key] = tx_lbl
            cr.addWidget(ic_lbl)
            cr.addWidget(tx_lbl, 1)
            id_lo.addLayout(cr)
            id_lo.addSpacing(8)

        id_lo.addSpacing(4)

        # divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background:#f1f5f9; border:none;")
        id_lo.addWidget(div2)
        id_lo.addSpacing(18)

        # ── Progress section ───────────────────────────────────
        prog_hdr = QHBoxLayout()
        prog_hdr.setSpacing(6)
        prog_hdr.setContentsMargins(0, 0, 0, 0)
        prog_ttl = QLabel("Hoàn thiện hồ sơ")
        prog_ttl.setStyleSheet(
            f"color:{_TXT_H}; font-size:13px; font-weight:700;"
            "border:none; background:transparent;"
        )
        self._prog_status_badge = QLabel("Tuyệt vời! 🎉")
        self._prog_status_badge.setFixedHeight(22)
        self._prog_status_badge.setStyleSheet(
            "background:#d1fae5; color:#065f46; border-radius:11px;"
            "padding:0 9px; font-size:11px; font-weight:700; border:none;"
        )
        prog_hdr.addWidget(prog_ttl)
        prog_hdr.addStretch()
        prog_hdr.addWidget(self._prog_status_badge)
        id_lo.addLayout(prog_hdr)
        id_lo.addSpacing(8)

        self._prof_progress = QProgressBar()
        self._prof_progress.setFixedHeight(7)
        self._prof_progress.setTextVisible(False)
        id_lo.addWidget(self._prof_progress)
        id_lo.addSpacing(6)

        prog_foot = QHBoxLayout()
        prog_foot.setSpacing(0)
        prog_foot.setContentsMargins(0, 0, 0, 0)
        self._prog_count_lbl = QLabel("8/8 mục đã hoàn thành")
        self._prog_count_lbl.setStyleSheet(
            f"color:{_TXT_M}; font-size:11px; border:none; background:transparent;"
        )
        self._prof_pct_lbl = QLabel("100%")
        self._prof_pct_lbl.setStyleSheet(
            f"color:{_BLUE}; font-size:13px; font-weight:800;"
            "border:none; background:transparent;"
        )
        prog_foot.addWidget(self._prog_count_lbl)
        prog_foot.addStretch()
        prog_foot.addWidget(self._prof_pct_lbl)
        id_lo.addLayout(prog_foot)
        id_lo.addSpacing(6)

        self._save_status_lbl = QLabel()
        self._save_status_lbl.setAlignment(Qt.AlignRight)
        self._save_status_lbl.setStyleSheet(
            "color:#10b981; font-size:10px; font-weight:600;"
            "border:none; background:transparent;"
        )
        id_lo.addWidget(self._save_status_lbl)
        id_lo.addSpacing(20)

        # ── CTAs ───────────────────────────────────────────────
        btn_edit_prof = QPushButton("  ✏️  Chỉnh sửa hồ sơ")
        btn_edit_prof.setFixedHeight(44)
        btn_edit_prof.setCursor(Qt.PointingHandCursor)
        btn_edit_prof.setStyleSheet(
            "QPushButton{background:#065f46; color:white; border:none;"
            "border-radius:22px; font-size:13px; font-weight:700;}"
            "QPushButton:hover{background:#047857;}"
        )
        _btn_shadow(btn_edit_prof, "#065f46", 60)
        btn_edit_prof.clicked.connect(self._open_profile_edit)
        id_lo.addWidget(btn_edit_prof)
        id_lo.addSpacing(10)

        sec_btns = QHBoxLayout()
        sec_btns.setSpacing(8)
        sec_btns.setContentsMargins(0, 0, 0, 0)

        btn_view_cv = QPushButton("  📄 Xem CV")
        btn_view_cv.setFixedHeight(38)
        btn_view_cv.setCursor(Qt.PointingHandCursor)
        btn_view_cv.setStyleSheet(
            f"QPushButton{{background:white; color:{_BLUE};"
            f"border:1.5px solid {_BLUE}; border-radius:19px;"
            "font-size:12px; font-weight:600;}}"
            f"QPushButton:hover{{background:{_BLUE_BG};}}"
        )
        btn_view_cv.clicked.connect(self._open_cv_preview)

        btn_dl = QPushButton("  ⬇ Tải xuống")
        btn_dl.setFixedHeight(38)
        btn_dl.setCursor(Qt.PointingHandCursor)
        btn_dl.setStyleSheet(
            f"QPushButton{{background:white; color:{_TXT_S};"
            "border:1.5px solid #d1d5db; border-radius:19px;"
            "font-size:12px; font-weight:600;}}"
            "QPushButton:hover{background:#f9fafb;}"
        )
        btn_dl.clicked.connect(self._download_cv)

        sec_btns.addWidget(btn_view_cv, 1)
        sec_btns.addWidget(btn_dl, 1)
        id_lo.addLayout(sec_btns)

        sidebar.addWidget(id_card)
        sidebar.addStretch()

        # ─────────────────────────────────────────────────────
        #  RIGHT CONTENT (flex)
        # ─────────────────────────────────────────────────────
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        right_col.setContentsMargins(0, 0, 0, 0)

        # ── Card 1: Thông tin cá nhân ──────────────────────────
        p_card = QFrame()
        p_card.setStyleSheet(
            "QFrame{background:white; border:none; border-radius:16px;}"
        )
        _shadow(p_card, 8, 3, 10)
        pc_lo = QVBoxLayout(p_card)
        pc_lo.setContentsMargins(24, 20, 24, 24)
        pc_lo.setSpacing(0)

        pc_lo.addLayout(self._section_title("ic_user.svg", _BLUE, "Thông tin cá nhân"))
        pc_lo.addSpacing(16)

        p_grid = QGridLayout()
        p_grid.setHorizontalSpacing(24)
        p_grid.setVerticalSpacing(6)
        for i, (lbl, val, vtype) in enumerate([
            ("HỌ VÀ TÊN",        self._profile_data["name"],    ""),
            ("EMAIL",             self._profile_data["email"],   "email"),
            ("SỐ ĐIỆN THOẠI",     self._profile_data["phone"],   "phone"),
            ("ĐỊA CHỈ HIỆN TẠI",  self._profile_data["address"], ""),
        ]):
            ef = _EditableField(
                label=lbl, value=val, validator=vtype,
                on_save=self._on_profile_field_saved
            )
            self._prof_field_refs.append(ef)
            p_grid.addWidget(ef, i // 2, i % 2)
        pc_lo.addLayout(p_grid)

        right_col.addWidget(p_card)

        # ── Card 2: Chuyên môn ─────────────────────────────────
        s_card = QFrame()
        s_card.setStyleSheet(
            "QFrame{background:white; border:none; border-radius:16px;}"
        )
        _shadow(s_card, 8, 3, 10)
        sc_lo = QVBoxLayout(s_card)
        sc_lo.setContentsMargins(24, 20, 24, 24)
        sc_lo.setSpacing(0)

        sc_lo.addLayout(self._section_title("ic_jobs.svg", "#10b981", "Thông tin chuyên môn"))
        sc_lo.addSpacing(16)

        s_grid = QGridLayout()
        s_grid.setHorizontalSpacing(24)
        s_grid.setVerticalSpacing(6)
        for i, (lbl, val, vtype) in enumerate([
            ("NGÀNH NGHỀ",         self._profile_data["field"],  ""),
            ("BẰNG CẤP",           self._profile_data["degree"], ""),
            ("SỐ NĂM KINH NGHIỆM", self._profile_data["exp"],    ""),
            ("NGÔN NGỮ",           self._profile_data["lang"],   ""),
        ]):
            ef = _EditableField(
                label=lbl, value=val, validator=vtype,
                on_save=self._on_profile_field_saved
            )
            self._prof_field_refs.append(ef)
            s_grid.addWidget(ef, i // 2, i % 2)
        sc_lo.addLayout(s_grid)
        sc_lo.addSpacing(20)

        # ── Skill chips container (dynamic — rebuilt on edit) ─────
        self._skill_chips_widget = QWidget()
        self._skill_chips_widget.setStyleSheet("background:transparent;")
        self._skill_chips_lo = QVBoxLayout(self._skill_chips_widget)
        self._skill_chips_lo.setContentsMargins(0, 0, 0, 0)
        self._skill_chips_lo.setSpacing(0)
        self._rebuild_skill_chips()
        sc_lo.addWidget(self._skill_chips_widget)

        right_col.addWidget(s_card)

        right_col.addStretch()

        body.addLayout(sidebar)
        body.addLayout(right_col, 1)
        lo.addLayout(body)
        lo.addStretch()

        self._update_profile_progress()

        return scroll

    # ── Editable card: icon header + stacked or grid fields ───
    def _prof_editable_card(self, icon_svg: str, accent: str,
                            title: str, fields: list,
                            cols: int = 1) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:white; border:1px solid #e5e7eb;"
            "border-radius:16px;}"
        )
        _shadow(card, 8, 3, 10)
        lo = QVBoxLayout(card)
        lo.setContentsMargins(24, 20, 24, 24)
        lo.setSpacing(16)

        # ── Card title row ─────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.setContentsMargins(0, 0, 0, 0)

        ic_bg = QFrame()
        ic_bg.setFixedSize(36, 36)
        ic_bg.setStyleSheet(
            f"background:{accent}20; border-radius:10px;"
        )
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(20, 20)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet("background:transparent;")
        ic_lbl.setPixmap(_svg_pm(icon_svg, 18, accent))
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:15px; font-weight:700;"
        )
        title_row.addWidget(ic_bg)
        title_row.addWidget(t_lbl)
        title_row.addStretch()
        lo.addLayout(title_row)

        # ── Fields ─────────────────────────────────────────────
        if cols == 1:
            for lbl, val, vtype in fields:
                ef = _EditableField(
                    label=lbl, value=val, validator=vtype,
                    on_save=self._on_profile_field_saved
                )
                self._prof_field_refs.append(ef)
                lo.addWidget(ef)
        else:
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(14)
            for i, (lbl, val, vtype) in enumerate(fields):
                ef = _EditableField(
                    label=lbl, value=val, validator=vtype,
                    on_save=self._on_profile_field_saved
                )
                self._prof_field_refs.append(ef)
                grid.addWidget(ef, i // cols, i % cols)
            lo.addLayout(grid)
        return card

    # ── Callbacks ─────────────────────────────────────────────
    def _on_profile_field_saved(self, label: str, value: str) -> None:
        self._update_profile_progress()
        self._update_profile_save_status()

    def _update_profile_progress(self) -> None:
        if not hasattr(self, "_prof_field_refs"):
            return
        total  = max(len(self._prof_field_refs), 1)
        filled = sum(
            1 for ef in self._prof_field_refs if ef.get_value().strip()
        )
        pct = round(filled / total * 100)

        self._prof_progress.setRange(0, total)
        self._prof_progress.setValue(filled)
        self._prog_count_lbl.setText(f"{filled}/{total} mục đã hoàn thành")

        if hasattr(self, "_prof_pct_lbl"):
            self._prof_pct_lbl.setText(f"{pct}%")

        remaining = total - filled
        if remaining == 0:
            self._prof_progress.setStyleSheet(
                f"QProgressBar{{background:#e5e7eb; border-radius:5px; border:none;}}"
                f"QProgressBar::chunk{{background:{_BLUE}; border-radius:5px;}}"
            )
            if hasattr(self, "_prog_status_badge"):
                self._prog_status_badge.setText("Tuyệt vời! 🎉")
                self._prog_status_badge.setStyleSheet(
                    "background:#d1fae5; color:#065f46; border-radius:12px;"
                    "padding:0 12px; font-size:12px; font-weight:700;"
                )
            if hasattr(self, "_prof_pct_lbl"):
                self._prof_pct_lbl.setStyleSheet(
                    f"color:{_BLUE}; font-size:18px; font-weight:800;"
                )
        elif pct >= 50:
            self._prof_progress.setStyleSheet(
                f"QProgressBar{{background:#e5e7eb; border-radius:5px; border:none;}}"
                f"QProgressBar::chunk{{background:{_BLUE}; border-radius:5px;}}"
            )
            if hasattr(self, "_prog_status_badge"):
                self._prog_status_badge.setText(f"Đang hoàn thiện · {pct}%")
                self._prog_status_badge.setStyleSheet(
                    "background:#fef3c7; color:#92400e; border-radius:12px;"
                    "padding:0 12px; font-size:12px; font-weight:700;"
                )
        else:
            self._prof_progress.setStyleSheet(
                f"QProgressBar{{background:#e5e7eb; border-radius:5px; border:none;}}"
                f"QProgressBar::chunk{{background:#f59e0b; border-radius:5px;}}"
            )
            if hasattr(self, "_prog_status_badge"):
                self._prog_status_badge.setText(f"Cần bổ sung · {pct}%")
                self._prog_status_badge.setStyleSheet(
                    "background:#fee2e2; color:#991b1b; border-radius:12px;"
                    "padding:0 12px; font-size:12px; font-weight:700;"
                )

    def _update_profile_save_status(self) -> None:
        if not hasattr(self, "_save_status_lbl"):
            return
        now = datetime.now().strftime("%H:%M")
        self._save_status_lbl.setText(f"✓ Đã lưu {now}")
        self._save_status_lbl.setStyleSheet(
            "color:#10b981; font-size:10px; font-weight:600;"
        )
        def _fade():
            if hasattr(self, "_save_status_lbl"):
                self._save_status_lbl.setStyleSheet(
                    f"color:{_TXT_M}; font-size:10px;"
                )
        QTimer.singleShot(3000, _fade)

    # ── Stats chip with progress bar ──────────────────────────
    def _prof_stat_chip(self, val: str, label: str,
                        color: str, pct: int) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame{background:white; border:1px solid #eaecf0;"
            "border-radius:14px;}"
        )
        f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        _shadow(f, 6, 2, 8)

        lo = QVBoxLayout(f)
        lo.setContentsMargins(14, 12, 14, 12)
        lo.setSpacing(5)

        # Number + color dot
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 0, 0, 0)
        num = QLabel(val)
        num.setStyleSheet(
            f"color:{color}; font-size:22px; font-weight:800;"
        )
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{color}; border-radius:4px;")
        top.addWidget(num)
        top.addStretch()
        top.addWidget(dot, 0, Qt.AlignVCenter)

        lbl_w = QLabel(label)
        lbl_w.setStyleSheet(
            f"color:{_TXT_M}; font-size:11px; font-weight:500;"
        )

        # Progress bar
        prog = QProgressBar()
        prog.setFixedHeight(4)
        prog.setRange(0, 100)
        prog.setValue(pct)
        prog.setTextVisible(False)
        prog.setStyleSheet(
            "QProgressBar{background:#f1f5f9; border-radius:2px; border:none;}"
            f"QProgressBar::chunk{{background:{color}; border-radius:2px;}}"
        )

        lo.addLayout(top)
        lo.addWidget(lbl_w)
        lo.addWidget(prog)
        return f

    # ── Section card wrapper ───────────────────────────────────
    def _prof_section_card(self, icon_svg: str, color: str,
                           title: str, fields: list) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#f8fafc; border:1px solid #eaecf0;"
            "border-radius:16px;}"
        )

        lo = QVBoxLayout(card)
        lo.setContentsMargins(20, 16, 20, 20)
        lo.setSpacing(14)

        lo.addWidget(self._prof_section_title(icon_svg, color, title))

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#e4e7eb;")
        div.setFixedHeight(1)
        lo.addWidget(div)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        for i, (fi, fc, lbl, fval) in enumerate(fields):
            grid.addWidget(
                self._prof_field(fi, fc, lbl, fval),
                i // 2, i % 2
            )
        lo.addLayout(grid)
        return card

    # ── Editable card: icon header + stacked or grid fields ───
    def _prof_editable_card(self, icon_svg: str, accent: str,
                            title: str, fields: list,
                            cols: int = 1) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:white; border:1px solid #e5e7eb;"
            "border-radius:16px;}"
        )
        _shadow(card, 8, 3, 10)
        lo = QVBoxLayout(card)
        lo.setContentsMargins(24, 20, 24, 24)
        lo.setSpacing(16)

        # ── Card title row ─────────────────────────────────────
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        title_row.setContentsMargins(0, 0, 0, 0)

        ic_bg = QFrame()
        ic_bg.setFixedSize(36, 36)
        ic_bg.setStyleSheet(
            f"background:{accent}20; border-radius:10px;"
        )
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(20, 20)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet("background:transparent;")
        ic_lbl.setPixmap(_svg_pm(icon_svg, 18, accent))
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(
            f"color:{_TXT_H}; font-size:15px; font-weight:700;"
        )
        title_row.addWidget(ic_bg)
        title_row.addWidget(t_lbl)
        title_row.addStretch()
        lo.addLayout(title_row)

        # ── Fields ─────────────────────────────────────────────
        if cols == 1:
            for lbl, val, vtype in fields:
                ef = _EditableField(
                    label=lbl, value=val, validator=vtype,
                    on_save=self._on_profile_field_saved
                )
                self._prof_field_refs.append(ef)
                lo.addWidget(ef)
        else:
            grid = QGridLayout()
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(14)
            for i, (lbl, val, vtype) in enumerate(fields):
                ef = _EditableField(
                    label=lbl, value=val, validator=vtype,
                    on_save=self._on_profile_field_saved
                )
                self._prof_field_refs.append(ef)
                grid.addWidget(ef, i // cols, i % cols)
            lo.addLayout(grid)
        return card

    # ── Callbacks ─────────────────────────────────────────────
    def _on_profile_field_saved(self, label: str, value: str) -> None:
        self._update_profile_progress()
        self._update_profile_save_status()

    def _update_profile_progress(self) -> None:
        if not hasattr(self, "_prof_field_refs"):
            return
        total  = max(len(self._prof_field_refs), 1)
        filled = sum(
            1 for ef in self._prof_field_refs if ef.get_value().strip()
        )
        pct = round(filled / total * 100)

        self._prof_progress.setRange(0, total)
        self._prof_progress.setValue(filled)
        self._prog_count_lbl.setText(f"{filled}/{total} mục đã hoàn thành")

        if hasattr(self, "_prof_pct_lbl"):
            self._prof_pct_lbl.setText(f"{pct}%")

        remaining = total - filled
        if remaining == 0:
            self._prof_progress.setStyleSheet(
                f"QProgressBar{{background:#e5e7eb; border-radius:5px; border:none;}}"
                f"QProgressBar::chunk{{background:{_BLUE}; border-radius:5px;}}"
            )
            if hasattr(self, "_prog_status_badge"):
                self._prog_status_badge.setText("Tuyệt vời! 🎉")
                self._prog_status_badge.setStyleSheet(
                    "background:#d1fae5; color:#065f46; border-radius:12px;"
                    "padding:0 12px; font-size:12px; font-weight:700;"
                )
            if hasattr(self, "_prof_pct_lbl"):
                self._prof_pct_lbl.setStyleSheet(
                    f"color:{_BLUE}; font-size:18px; font-weight:800;"
                )
        elif pct >= 50:
            self._prof_progress.setStyleSheet(
                f"QProgressBar{{background:#e5e7eb; border-radius:5px; border:none;}}"
                f"QProgressBar::chunk{{background:{_BLUE}; border-radius:5px;}}"
            )
            if hasattr(self, "_prog_status_badge"):
                self._prog_status_badge.setText(f"Đang hoàn thiện · {pct}%")
                self._prog_status_badge.setStyleSheet(
                    "background:#fef3c7; color:#92400e; border-radius:12px;"
                    "padding:0 12px; font-size:12px; font-weight:700;"
                )
        else:
            self._prof_progress.setStyleSheet(
                f"QProgressBar{{background:#e5e7eb; border-radius:5px; border:none;}}"
                f"QProgressBar::chunk{{background:#f59e0b; border-radius:5px;}}"
            )
            if hasattr(self, "_prog_status_badge"):
                self._prog_status_badge.setText(f"Cần bổ sung · {pct}%")
                self._prog_status_badge.setStyleSheet(
                    "background:#fee2e2; color:#991b1b; border-radius:12px;"
                    "padding:0 12px; font-size:12px; font-weight:700;"
                )

    def _update_profile_save_status(self) -> None:
        if not hasattr(self, "_save_status_lbl"):
            return
        now = datetime.now().strftime("%H:%M")
        self._save_status_lbl.setText(f"✓ Đã lưu {now}")
        self._save_status_lbl.setStyleSheet(
            "color:#10b981; font-size:10px; font-weight:600;"
        )
        def _fade():
            if hasattr(self, "_save_status_lbl"):
                self._save_status_lbl.setStyleSheet(
                    f"color:{_TXT_M}; font-size:10px;"
                )
        QTimer.singleShot(3000, _fade)

    # ── Stats chip with progress bar ──────────────────────────
    def _prof_stat_chip(self, val: str, label: str,
                        color: str, pct: int) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "QFrame{background:white; border:1px solid #eaecf0;"
            "border-radius:14px;}"
        )
        f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        _shadow(f, 6, 2, 8)

        lo = QVBoxLayout(f)
        lo.setContentsMargins(14, 12, 14, 12)
        lo.setSpacing(5)

        # Number + color dot
        top = QHBoxLayout()
        top.setSpacing(6)
        top.setContentsMargins(0, 0, 0, 0)
        num = QLabel(val)
        num.setStyleSheet(
            f"color:{color}; font-size:22px; font-weight:800;"
        )
        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{color}; border-radius:4px;")
        top.addWidget(num)
        top.addStretch()
        top.addWidget(dot, 0, Qt.AlignVCenter)

        lbl_w = QLabel(label)
        lbl_w.setStyleSheet(
            f"color:{_TXT_M}; font-size:11px; font-weight:500;"
        )

        # Progress bar
        prog = QProgressBar()
        prog.setFixedHeight(4)
        prog.setRange(0, 100)
        prog.setValue(pct)
        prog.setTextVisible(False)
        prog.setStyleSheet(
            "QProgressBar{background:#f1f5f9; border-radius:2px; border:none;}"
            f"QProgressBar::chunk{{background:{color}; border-radius:2px;}}"
        )

        lo.addLayout(top)
        lo.addWidget(lbl_w)
        lo.addWidget(prog)
        return f

    # ── Section card wrapper ───────────────────────────────────
    def _prof_section_card(self, icon_svg: str, color: str,
                           title: str, fields: list) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame{background:#f8fafc; border:1px solid #eaecf0;"
            "border-radius:16px;}"
        )

        lo = QVBoxLayout(card)
        lo.setContentsMargins(20, 16, 20, 20)
        lo.setSpacing(14)

        lo.addWidget(self._prof_section_title(icon_svg, color, title))

        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#e4e7eb;")
        div.setFixedHeight(1)
        lo.addWidget(div)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        for i, (fi, fc, lbl, fval) in enumerate(fields):
            grid.addWidget(
                self._prof_field(fi, fc, lbl, fval),
                i // 2, i % 2
            )
        lo.addLayout(grid)
        return card

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
            "QFrame{background:white; border:1px solid #e8edf2;"
            "border-radius:14px;}"
            "QFrame:hover{border:1px solid #c7d2fe; background:#faf9ff;}"
        )
        f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        f.setFixedHeight(70)

        lo = QHBoxLayout(f)
        lo.setContentsMargins(14, 0, 16, 0)
        lo.setSpacing(12)

        # Icon badge
        ic_bg = QFrame()
        ic_bg.setFixedSize(38, 38)
        ic_bg.setStyleSheet(
            f"background:{icon_color}18; border-radius:11px;"
        )
        ic_lo = QHBoxLayout(ic_bg)
        ic_lo.setContentsMargins(0, 0, 0, 0)
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(20, 20)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet("background:transparent;")
        ic_lbl.setPixmap(_svg_pm(icon_svg, 17, icon_color))
        ic_lo.addWidget(ic_lbl, 0, Qt.AlignCenter)

        # Label + value stacked
        txt_lo = QVBoxLayout()
        txt_lo.setSpacing(4)
        lbl_w = QLabel(label.upper())
        lbl_w.setStyleSheet(
            "color:#b0b8c4; font-size:10px; font-weight:700;"
            "letter-spacing:0.6px; background:transparent;"
        )
        val_w = QLabel(value)
        val_w.setStyleSheet(
            f"color:{_TXT_H}; font-size:13px; font-weight:600;"
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

        if is_saved:
            # Only show jobs the user has saved
            jobs = [
                j for j in _JOBS_DATA
                if self._job_key(j[0], j[1]) in self._saved_job_keys
            ]
        else:
            # Filter by search query (title / company / location)
            q = self._search_query.strip().lower()
            jobs = [
                j for j in _JOBS_DATA
                if not q or q in j[0].lower() or q in j[1].lower() or q in j[4].lower()
            ]

        if not jobs:
            empty = QLabel(
                "Chưa có việc làm đã lưu" if is_saved else "Không tìm thấy việc làm phù hợp"
            )
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{_TXT_M}; font-size:13px; padding:48px;"
            )
            grid.addWidget(empty, 0, 0, 1, 2)
            return

        if not jobs:
            empty = QLabel(
                "Chưa có việc làm đã lưu" if is_saved else "Không tìm thấy việc làm phù hợp"
            )
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{_TXT_M}; font-size:13px; padding:48px;"
            )
            grid.addWidget(empty, 0, 0, 1, 2)
            return

        for i, (title, comp, jtype, sal, loc) in enumerate(jobs):
            saved = self._job_key(title, comp) in self._saved_job_keys
            card = self._job_card(title, comp, jtype, sal, loc, saved, i, is_saved_page=is_saved)
            grid.addWidget(card, i // 2, i % 2)

    @staticmethod
    def _job_key(title: str, comp: str) -> str:
        """Stable string key identifying a job."""
        return f"{title}||{comp}"

    def _job_card(self, title: str, comp: str, jtype: str,
                  sal: str, loc: str, is_saved: bool, idx: int = 0,
                  is_saved_page: bool = False) -> QFrame:
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
        ic_color  = _INDIGO if is_saved else "#94a3b8"
        btn_save.setIcon(QIcon(_svg_pm(icon_name, 17, ic_color)))
        btn_save.setIconSize(QSize(17, 17))

        def _toggle_save(checked=False, _t=title, _c=comp, _b=btn_save,
                         _is_saved_page=is_saved_page):
            key = self._job_key(_t, _c)
            if key in self._saved_job_keys:
                # ── Unsave ────────────────────────────────────
                self._saved_job_keys.discard(key)
                _b.setIcon(QIcon(_svg_pm("bookmark_outline.svg", 17, "#94a3b8")))
                _Toast(
                    self.win.centralWidget(),
                    f"Đã bỏ lưu: {_t}",
                    accent="#f59e0b",
                    duration_ms=2500,
                    title_text="Đã bỏ lưu việc làm",
                    icon_char="🔖",
                )
            else:
                # ── Save ──────────────────────────────────────
                self._saved_job_keys.add(key)
                _b.setIcon(QIcon(_svg_pm("bookmark_filled.svg", 17, _INDIGO)))
                _Toast(
                    self.win.centralWidget(),
                    f"{_t} · {_c}",
                    accent=_INDIGO,
                    duration_ms=2800,
                    title_text="Đã lưu việc làm! 🎉",
                    icon_char="🔖",
                )
            # Sync saved page
            self._refresh_saved_page()

        btn_save.clicked.connect(_toggle_save)

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

        def _open_apply(checked=False, _title=title, _comp=comp, _loc=loc):
            dlg = _ApplyDialog(_title, self.win)
            if dlg.exec() == QDialog.Accepted:
                # Ghi vào shared store (HR sẽ thấy ngay)
                now = datetime.now().strftime("%d/%m/%Y")
                entry = _mock_data.add_candidate_application(
                    title=_title, company=_comp,
                    location=_loc or "Việt Nam",
                    applied_at=now,
                )
                # Lưu vào lịch sử local: tuple 6 phần tử, app_id ở [5]
                self._applied_hist.insert(0, (
                    _comp,
                    _loc or "Việt Nam",
                    _title,
                    datetime.now().strftime("%b %d, %Y"),
                    "Đang xử lý",
                    entry["application_id"],   # ← track để polling
                ))
                self._refresh_history_page()
                _Toast(
                    self.win.centralWidget(),
                    f"{_title} · {_comp}",
                    accent="#10b981",
                    duration_ms=3500,
                    title_text="Nộp hồ sơ thành công! ✅",
                    icon_char="✓",
                )

        btn_apply.clicked.connect(_open_apply)
        h_bottom.addWidget(btn_apply)

        # Double-click card → open job detail page
        card.mouseDoubleClickEvent = (
            lambda e, _t=title, _c=comp, _jt=jtype, _s=sal, _l=loc, _i=idx:
            self._open_job_detail(_t, _c, _jt, _s, _l, _i)
        )
        lo.addLayout(h_bottom)

        return card

    # ══════════════════════════════════════════════════════════
    #  LIVE SYNC HELPERS
    # ══════════════════════════════════════════════════════════
    def _on_search_changed(self, text: str) -> None:
        """Filter home-page job grid as user types in topbar search."""
        self._search_query = text
        # Only update home page if it's currently visible or rebuild on next show
        self._load_jobs_grid(self.jobs_grid, is_saved=False)

    def _refresh_saved_page(self) -> None:
        """Rebuild the saved jobs grid with current saved_job_keys."""
        self._load_jobs_grid(self.saved_jobs_grid, is_saved=True)

    def _refresh_history_page(self) -> None:
        """Prepend newly applied jobs and re-render history table."""
        # _apply_hist_filters reads self._applied_hist + _HIST_DATA
        self._apply_hist_filters()

    def _rebuild_skill_chips(self) -> None:
        """Xóa và vẽ lại toàn bộ skill chips từ _profile_data['skills']."""
        lo = self._skill_chips_lo
        # Xóa widgets cũ
        while lo.count():
            item = lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        skills_dict: dict = self._profile_data.get("skills", {})
        for ci, (cat, tags) in enumerate(skills_dict.items()):
            if not tags:
                continue
            bg, fg = _SKILL_CAT_COLORS[ci % len(_SKILL_CAT_COLORS)]

            # Category label
            cat_lbl = QLabel(cat.upper())
            cat_lbl.setStyleSheet(
                f"color:{_TXT_M}; font-size:10px; font-weight:700;"
                "letter-spacing:0.8px; border:none; background:transparent;"
            )
            lo.addWidget(cat_lbl)
            lo.addSpacing(5)

            # Chip row
            chips = [(t, bg, fg) for t in tags if t.strip()]
            lo.addWidget(self._skill_chip_row(chips))
            lo.addSpacing(12)

    def _poll_application_statuses(self) -> None:
        """Kiểm tra định kỳ xem HR có cập nhật trạng thái nào chưa."""
        changed = False
        for i, entry in enumerate(self._applied_hist):
            if len(entry) < 6:
                continue                         # entry cũ không có app_id
            app_id   = entry[5]
            old_vi   = entry[4]                  # trạng thái tiếng Việt hiện tại
            new_eng  = _mock_data.get_application_status(app_id)
            if new_eng is None:
                continue
            new_vi = _HR_STATUS_VI.get(new_eng, old_vi)
            if new_vi != old_vi:
                # Cập nhật tuple (tạo mới vì tuple bất biến)
                self._applied_hist[i] = (
                    entry[0], entry[1], entry[2], entry[3], new_vi, app_id
                )
                changed = True
                # Hiện toast thông báo
                toast_cfg = _STATUS_TOAST.get(new_eng)
                if toast_cfg:
                    icon_c, accent, title_text = toast_cfg
                    _Toast(
                        self.win.centralWidget(),
                        f"{entry[2]} · {entry[0]}",
                        accent=accent,
                        duration_ms=4000,
                        title_text=title_text,
                        icon_char=icon_c,
                    )
        if changed:
            self._apply_hist_filters()

    # ══════════════════════════════════════════════════════════
    #  PROFILE ACTIONS
    # ══════════════════════════════════════════════════════════
    @staticmethod
    def _make_circle_pixmap(path: str, size: int) -> QPixmap:
        """Load ảnh từ path, scale + crop thành hình tròn hoàn hảo."""
        src = QPixmap(path)
        if src.isNull():
            return QPixmap()
        # Scale ảnh gốc để cạnh ngắn nhất = size (cover)
        src = src.scaled(size, size, Qt.KeepAspectRatioByExpanding,
                         Qt.SmoothTransformation)
        # Crop về đúng size x size (center crop)
        if src.width() > size or src.height() > size:
            x = (src.width()  - size) // 2
            y = (src.height() - size) // 2
            src = src.copy(x, y, size, size)

        # Vẽ lên canvas trong suốt với clip hình tròn
        from PySide6.QtGui import QPainterPath
        result = QPixmap(size, size)
        result.fill(Qt.transparent)
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        path_clip = QPainterPath()
        path_clip.addEllipse(0, 0, size, size)
        painter.setClipPath(path_clip)
        painter.drawPixmap(0, 0, src)
        painter.end()
        return result

    def _change_avatar(self) -> None:
        """Mở file dialog để chọn ảnh đại diện mới, bo tròn tự động."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.win, "Chọn ảnh đại diện",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*)"
        )
        if not file_path:
            return

        circle_pm = self._make_circle_pixmap(file_path, 84)
        if not circle_pm.isNull():
            # Xóa gradient background, chỉ hiện ảnh tròn
            self._av_lbl.setStyleSheet(
                "border-radius:42px; border:none; background:transparent;"
            )
            self._av_lbl.setText("")
            self._av_lbl.setPixmap(circle_pm)
        else:
            # Fallback: dùng initials nếu không load được ảnh
            initials = "".join(
                p[0].upper() for p in self._profile_data["name"].split()[:2]
            ) or "UV"
            self._av_lbl.setText(initials)

        _Toast(
            self.win.centralWidget(),
            "Ảnh đại diện đã được cập nhật",
            accent=_INDIGO, duration_ms=2500,
            title_text="Đổi ảnh thành công 📷", icon_char="📷",
        )

    def _open_profile_edit(self) -> None:
        """Mở dialog chỉnh sửa hồ sơ đầy đủ."""
        dlg = _ProfileEditDialog(self._profile_data, self.win)
        if dlg.exec() != QDialog.Accepted:
            return
        new_data = dlg.get_data()
        self._profile_data.update(new_data)

        # Sync sidebar labels
        self._prof_name_lbl.setText(new_data["name"])
        self._prof_tag_lbl.setText(new_data["tagline"])
        for key, lbl in self._prof_contact_lbls.items():
            lbl.setText(new_data.get(key, ""))
        # Sync avatar initials if no image loaded
        if not self._av_lbl.pixmap() or self._av_lbl.pixmap().isNull():
            initials = "".join(
                p[0].upper() for p in new_data["name"].split()[:2]
            ) or "UV"
            self._av_lbl.setText(initials)

        # Rebuild editable field grids with new values
        for ef in self._prof_field_refs:
            key_map = {
                "HỌ VÀ TÊN":        "name",
                "EMAIL":             "email",
                "SỐ ĐIỆN THOẠI":     "phone",
                "ĐỊA CHỈ HIỆN TẠI":  "address",
                "NGÀNH NGHỀ":        "field",
                "BẰNG CẤP":          "degree",
                "SỐ NĂM KINH NGHIỆM":"exp",
                "NGÔN NGỮ":          "lang",
            }
            if ef._label in key_map:
                ef._set_value(new_data.get(key_map[ef._label], ef._value))

        # Rebuild skill chips with new data
        self._rebuild_skill_chips()

        self._update_profile_progress()
        _Toast(
            self.win.centralWidget(),
            "Thông tin hồ sơ đã được lưu",
            accent="#10b981", duration_ms=3000,
            title_text="Hồ sơ cập nhật thành công ✅", icon_char="✓",
        )

    def _open_cv_preview(self) -> None:
        """Mở dialog xem CV."""
        dlg = _CVPreviewDialog(self._profile_data.get("cv_path"), self.win)
        dlg.exec()
        # If user uploaded a new CV inside the dialog
        new_path = dlg.get_cv_path()
        if new_path and new_path != self._profile_data.get("cv_path"):
            self._profile_data["cv_path"] = new_path
            from pathlib import Path as _Path
            _Toast(
                self.win.centralWidget(),
                f"CV mới: {_Path(new_path).name}",
                accent=_BLUE, duration_ms=3000,
                title_text="Tải CV lên thành công 📄", icon_char="📄",
            )

    def _download_cv(self) -> None:
        """Tải CV về máy."""
        cv_path = self._profile_data.get("cv_path")
        if not cv_path:
            _Toast(
                self.win.centralWidget(),
                "Bạn chưa tải CV lên. Nhấn 'Xem CV' để tải lên trước.",
                accent="#f59e0b", duration_ms=3500,
                title_text="Chưa có CV", icon_char="⚠",
            )
            return
        from pathlib import Path as _Path
        fname = _Path(cv_path).name
        save_path, _ = QFileDialog.getSaveFileName(
            self.win, "Lưu CV về máy",
            fname,
            "All Files (*)"
        )
        if not save_path:
            return
        import shutil as _shutil
        try:
            _shutil.copy2(cv_path, save_path)
            _Toast(
                self.win.centralWidget(),
                f"Đã lưu tại: {save_path}",
                accent="#10b981", duration_ms=3500,
                title_text="Tải xuống thành công ⬇", icon_char="⬇",
            )
        except Exception as exc:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self.win, "Lỗi", f"Không thể lưu file:\n{exc}")

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
