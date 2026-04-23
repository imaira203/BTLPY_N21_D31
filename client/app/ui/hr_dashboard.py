"""HR Dashboard — pure Python, không dùng .ui file."""
from __future__ import annotations

import math
from typing import Callable

from PySide6.QtCore import (Qt, QSize, QPropertyAnimation,
                              QEasingCurve, QPoint, QByteArray,
                              QEvent, QObject, QTimer, QRect)
from PySide6.QtGui import (QIcon, QFont, QColor, QPainter, QPixmap,
                            QPainterPath, QLinearGradient, QPen)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFrame, QGraphicsDropShadowEffect,
    QGridLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from pathlib import Path

from ..client import jobhub_api
from ..client.jobhub_api import ApiError
from .. import mock_data
from ..paths import resource_icon
from ..session_store import clear_session
from .charts import make_bar_chart

# ══════════════════════════════════════════════════════════════
#  TOKENS
# ══════════════════════════════════════════════════════════════
SIDEBAR_BG   = "#0f172a"
SIDEBAR_W    = 240
NAV_ACTIVE   = "#6366f1"
NAV_ACTIVE_T = "#ffffff"
NAV_INACT_T  = "#94a3b8"
NAV_INACT_IC = "#94a3b8"
NAV_HOVER_BG = "#1e293b"
CONTENT_BG   = "#f8fafc"
CARD_BG      = "#ffffff"
TOPBAR_BG    = "#ffffff"
TOPBAR_H     = 72
TXT_H        = "#0f172a"
TXT_S        = "#374151"
TXT_M        = "#64748b"
BORDER       = "#e2e8f0"
P            = "#6366f1"
P_DARK       = "#4f46e5"
_CARD_TOP    = "#ffffff"
_CARD_BOT    = "#f8fafc"

_PAGE_SIZE = 5          # rows per table page

_ICONS = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"
_CANDS_PER_PAGE = 5   # số ứng viên mỗi trang


# ══════════════════════════════════════════════════════════════
#  SVG HELPER
# ══════════════════════════════════════════════════════════════
def _svg_pm(name: str, size: int, color: str) -> QPixmap:
    p = _ICONS / name
    if not p.exists():
        return QPixmap()
    raw = p.read_text(encoding="utf-8").replace("currentColor", color)
    data = QByteArray(raw.encode())
    rdr  = QSvgRenderer(data)
    pm   = QPixmap(size, size)
    pm.fill(Qt.transparent)
    pt   = QPainter(pm)
    pt.setRenderHint(QPainter.Antialiasing)
    rdr.render(pt)
    pt.end()
    return pm


def _svg_icon(name: str, size: int = 20, color: str = NAV_INACT_T) -> QIcon:
    return QIcon(_svg_pm(name, size, color))


# ══════════════════════════════════════════════════════════════
#  SHADOW
# ══════════════════════════════════════════════════════════════
def _shadow(w: QWidget, blur: int = 16, dy: int = 4, alpha: int = 18) -> QGraphicsDropShadowEffect:
    fx = QGraphicsDropShadowEffect(w)
    fx.setBlurRadius(blur)
    fx.setOffset(0, dy)
    fx.setColor(QColor(0, 0, 0, alpha))
    w.setGraphicsEffect(fx)
    return fx


# ══════════════════════════════════════════════════════════════
#  SPARKLINE — mini area/line chart drawn with QPainter
# ══════════════════════════════════════════════════════════════
class _Sparkline(QWidget):
    """Small inline trend chart for metric cards."""

    def __init__(self, data: list[int], color: str, parent=None):
        super().__init__(parent)
        self._data  = data
        self._color = QColor(color)
        self.setFixedSize(82, 42)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background:transparent;border:none;")

    def paintEvent(self, _):  # noqa: N802
        if len(self._data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h   = self.width(), self.height()
        pad    = 4
        data   = self._data
        mn, mx = min(data), max(data)
        rng    = max(mx - mn, 1)
        n      = len(data)

        def _pt(i: int) -> tuple[float, float]:
            x = pad + i / (n - 1) * (w - pad * 2)
            y = pad + (1 - (data[i] - mn) / rng) * (h - pad * 2)
            return x, y

        pts = [_pt(i) for i in range(n)]

        # ── Gradient area fill ──────────────────────────────
        path = QPainterPath()
        path.moveTo(pts[0][0], h)
        for x, y in pts:
            path.lineTo(x, y)
        path.lineTo(pts[-1][0], h)
        path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        top_c = QColor(self._color); top_c.setAlpha(90)
        bot_c = QColor(self._color); bot_c.setAlpha(8)
        grad.setColorAt(0, top_c)
        grad.setColorAt(1, bot_c)
        p.fillPath(path, grad)

        # ── Line ────────────────────────────────────────────
        pen = QPen(self._color, 2.0, Qt.SolidLine,
                   Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        for i in range(n - 1):
            p.drawLine(
                int(pts[i][0]),   int(pts[i][1]),
                int(pts[i+1][0]), int(pts[i+1][1]),
            )

        # ── End dot ─────────────────────────────────────────
        ex, ey = pts[-1]
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(int(ex) - 3, int(ey) - 3, 6, 6)

        # Bright white inner highlight on end dot
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(int(ex) - 1, int(ey) - 1, 2, 2)

        p.end()


# ══════════════════════════════════════════════════════════════
#  NAV BUTTON — clean pill, no indicator bar
# ══════════════════════════════════════════════════════════════
class _NavBtn(QWidget):
    """Sidebar nav item: [pill: icon + label]."""

    # Active pill: solid indigo, border-radius matches Cards (12px)
    _SS_ACTIVE = f"background:{NAV_ACTIVE}; border-radius:12px;"
    _SS_INACT  = "background:transparent; border-radius:12px;"
    _SS_HOV    = f"background:{NAV_HOVER_BG}; border-radius:12px;"

    def __init__(self, icon_svg: str, label: str,
                 logout: bool = False, parent=None):
        super().__init__(parent)
        self._icon_svg = icon_svg
        self._active   = False
        self._logout   = logout
        self._cb       = None
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background:transparent;")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Pill (icon + text) ─────────────────────────────
        self._pill = QFrame()
        self._pill.setStyleSheet(self._SS_INACT)
        pill_lo = QHBoxLayout(self._pill)
        pill_lo.setContentsMargins(20, 0, 16, 0)    # 20px left → icon → 12px → text
        pill_lo.setSpacing(12)                       # icon↔text gap
        pill_lo.setAlignment(Qt.AlignVCenter)

        # Icon — 20×20, always centered
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(20, 20)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background:transparent; border:none;")
        inact_ic_col = "#ef9a9a" if logout else NAV_INACT_IC
        self._icon_lbl.setPixmap(_svg_pm(icon_svg, 20, inact_ic_col))
        self._inact_ic_col = inact_ic_col

        # Label
        self._txt = QLabel(label)
        inact_txt = "#fca5a5" if logout else NAV_INACT_T
        self._txt.setStyleSheet(
            f"color:{inact_txt};font-size:14px;font-weight:500;"
            "background:transparent;border:none;"
        )
        self._inact_txt = inact_txt

        pill_lo.addWidget(self._icon_lbl)
        pill_lo.addWidget(self._txt, 1)
        outer.addWidget(self._pill, 1)

    def set_active(self, v: bool) -> None:
        self._active = v
        if v:
            self._pill.setStyleSheet(self._SS_ACTIVE)
            self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 20, "#ffffff"))
            self._txt.setStyleSheet(
                "color:#ffffff;font-size:14px;font-weight:700;"
                "background:transparent;border:none;"
            )
        else:
            self._pill.setStyleSheet(self._SS_INACT)
            self._icon_lbl.setPixmap(
                _svg_pm(self._icon_svg, 20, self._inact_ic_col)
            )
            self._txt.setStyleSheet(
                f"color:{self._inact_txt};font-size:14px;font-weight:500;"
                "background:transparent;border:none;"
            )

    def enterEvent(self, e):
        if not self._active:
            self._pill.setStyleSheet(self._SS_HOV)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._active:
            self._pill.setStyleSheet(self._SS_INACT)   # restore transparent
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._cb:
            self._cb()
        super().mousePressEvent(e)

    def on_click(self, fn) -> None:
        self._cb = fn


# ── helper: hex color → rgba() string (Qt CSS safe) ──────────
def _rgba(hex_color: str, alpha: float = 0.12) -> str:
    """Convert '#rrggbb' → 'rgba(r,g,b,alpha)' for Qt CSS."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ══════════════════════════════════════════════════════════════
#  METRIC CARD — clean, no hover effect, proper rgba backgrounds
# ══════════════════════════════════════════════════════════════
class _MetricCard(QFrame):
    """
    Layout:
    ┌──────────────────────────────────────┐
    │ [icon 40px]              [sparkline] │
    │                          [7 ngày qua]│
    │ 36px bold number                     │
    │ 11px gray label                      │
    │ [subtle badge]                       │
    └──────────────────────────────────────┘
    Background: white  |  Border: very light  |  No hover change
    """

    def __init__(self, icon_svg: str, icon_color: str, icon_bg: str,
                 label: str, value: str, hint: str,
                 hint_color: str = "#10b981", hint_bg: str = "#d1fae5",
                 glow_color: str = "#6366f1",
                 sparkline_data: list | None = None,
                 sparkline_color: str = "#818cf8",
                 parent=None):
        super().__init__(parent)

        # Card: white bg, very light border, soft shadow — static (no hover)
        self.setStyleSheet(
            f"QFrame{{background:#ffffff;border:1px solid #f1f5f9;"
            "border-radius:18px;}}"
        )
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(164)

        fx = QGraphicsDropShadowEffect(self)
        fx.setBlurRadius(16)
        fx.setOffset(0, 3)
        fx.setColor(QColor(0, 0, 0, 12))
        self.setGraphicsEffect(fx)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(0)

        # ── Top row: icon badge  |  sparkline ─────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(0)
        top_row.setContentsMargins(0, 0, 0, 0)

        # Icon badge — rgba background (correct alpha, no ARGB confusion)
        badge = QFrame()
        badge.setFixedSize(40, 40)
        badge.setStyleSheet(
            f"background:{_rgba(icon_color, 0.10)};border-radius:12px;border:none;"
        )
        b_lo = QHBoxLayout(badge)
        b_lo.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setAlignment(Qt.AlignCenter)
        ic.setPixmap(_svg_pm(icon_svg, 18, icon_color))
        ic.setStyleSheet("background:transparent;border:none;")
        b_lo.addWidget(ic)
        top_row.addWidget(badge, 0, Qt.AlignVCenter | Qt.AlignLeft)
        top_row.addStretch()

        # Sparkline + "7 ngày qua" label
        if sparkline_data and len(sparkline_data) >= 2:
            sp_col = QVBoxLayout()
            sp_col.setSpacing(2)
            sp_col.setContentsMargins(0, 0, 0, 0)
            sp = _Sparkline(sparkline_data, sparkline_color)
            sp.setFixedSize(78, 36)
            period_lbl = QLabel("7 ngày qua")
            period_lbl.setAlignment(Qt.AlignRight)
            period_lbl.setStyleSheet(
                "color:#cbd5e1;font-size:9px;font-weight:500;"
                "background:transparent;border:none;letter-spacing:0.3px;"
            )
            sp_col.addWidget(sp, 0, Qt.AlignRight)
            sp_col.addWidget(period_lbl, 0, Qt.AlignRight)
            top_row.addLayout(sp_col)

        root.addLayout(top_row)
        root.addSpacing(10)

        # ── Number — dominant ──────────────────────────────────
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:36px;font-weight:800;"
            "background:transparent;border:none;letter-spacing:-1px;"
        )
        root.addWidget(val_lbl)
        root.addSpacing(3)

        # ── Label — quiet ──────────────────────────────────────
        lab_lbl = QLabel(label)
        lab_lbl.setStyleSheet(
            "color:#94a3b8;font-size:11px;font-weight:400;"
            "background:transparent;border:none;letter-spacing:0.2px;"
        )
        root.addWidget(lab_lbl)
        root.addSpacing(10)

        # ── Trend badge — subtle rgba tint ─────────────────────
        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(0, 0, 0, 0)
        pill_row.setSpacing(0)
        hint_pill = QLabel(hint)
        hint_pill.setStyleSheet(
            f"background:{_rgba(icon_color, 0.10)};color:{icon_color};"
            "font-size:11px;font-weight:600;"
            "border-radius:6px;padding:3px 10px;border:none;"
        )
        pill_row.addWidget(hint_pill, 0, Qt.AlignLeft)
        pill_row.addStretch()
        root.addLayout(pill_row)


# ══════════════════════════════════════════════════════════════
#  SECTION FRAME
# ══════════════════════════════════════════════════════════════
def _card_frame(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame{{background:{CARD_BG};border:1px solid {BORDER};"
        "border-radius:16px;}}"
    )
    _shadow(frame, blur=12, dy=3, alpha=10)
    lo = QVBoxLayout(frame)
    lo.setContentsMargins(24, 20, 24, 20)
    lo.setSpacing(16)
    if title:
        t = QLabel(title)
        t.setStyleSheet(
            f"color:{TXT_H};font-size:16px;font-weight:700;"
            "background:transparent;border:none;"
        )
        lo.addWidget(t)
    return frame, lo


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def _lbl(text: str, size: int = 13, bold: bool = False,
         color: str = TXT_S) -> QLabel:
    w = QLabel(text)
    w.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'700' if bold else '500'};"
        "background:transparent;border:none;"
    )
    return w


def _input(ph: str = "", h: int = 42) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(ph)
    e.setMinimumHeight(h)
    e.setStyleSheet(
        f"background:#f8fafc;border:1.5px solid {BORDER};"
        "border-radius:10px;padding:0 12px;font-size:14px;"
        f"color:{TXT_H};"
    )
    return e


def _btn_primary(text: str, h: int = 42) -> QPushButton:
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        f"QPushButton{{background:{P};color:#fff;border:none;"
        "border-radius:10px;font-size:14px;font-weight:700;padding:0 20px;}}"
        f"QPushButton:hover{{background:{P_DARK};}}"
        "QPushButton:pressed{background:#4338ca;}"
    )
    return b


def _combo(options: list[str]) -> QComboBox:
    c = QComboBox()
    for opt in options:
        c.addItem(opt)
    c.setMinimumHeight(44)
    c.setCursor(Qt.PointingHandCursor)
    c.setStyleSheet(f"""
        QComboBox {{
            background:#f8fafc; border:1.5px solid {BORDER};
            border-radius:10px; padding:0 14px;
            font-size:14px; color:{TXT_H};
        }}
        QComboBox:hover {{ border-color:#a5b4fc; }}
        QComboBox::drop-down {{
            border:none; width:30px;
        }}
        QComboBox::down-arrow {{
            width:12px; height:12px;
            image:none;
        }}
        QComboBox QAbstractItemView {{
            background:{CARD_BG}; border:1.5px solid {BORDER};
            border-radius:10px; selection-background-color:#ede9fe;
            selection-color:{P_DARK}; font-size:14px; padding:4px;
        }}
    """)
    return c


def _section_header(icon_svg: str, title: str,
                    icon_color: str = P, icon_bg: str = "#ede9fe") -> QWidget:
    """Icon badge + bold section title, used inside card sections."""
    row = QWidget()
    row.setStyleSheet("background:transparent;")
    lo = QHBoxLayout(row)
    lo.setContentsMargins(0, 0, 0, 0)
    lo.setSpacing(12)

    badge = QFrame()
    badge.setFixedSize(36, 36)
    badge.setStyleSheet(f"background:{icon_bg};border-radius:10px;")
    b_lo = QHBoxLayout(badge)
    b_lo.setContentsMargins(0, 0, 0, 0)
    ic = QLabel()
    ic.setAlignment(Qt.AlignCenter)
    ic.setPixmap(_svg_pm(icon_svg, 18, icon_color))
    ic.setStyleSheet("background:transparent;")
    b_lo.addWidget(ic)

    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"color:{TXT_H};font-size:17px;font-weight:700;"
        "background:transparent;border:none;"
    )

    lo.addWidget(badge)
    lo.addWidget(lbl)
    lo.addStretch()
    return row


def _pag_btn(text: str, active: bool = False,
             enabled: bool = True) -> QPushButton:
    """Pagination button — active = indigo pill, else ghost."""
    btn = QPushButton(text)
    btn.setFixedSize(32, 32)
    btn.setEnabled(enabled)
    btn.setCursor(
        Qt.PointingHandCursor if (enabled and not active) else Qt.ArrowCursor
    )
    if active:
        btn.setStyleSheet(
            f"QPushButton{{background:{P};color:#fff;"
            "border:none;border-radius:8px;"
            "font-size:13px;font-weight:700;}}"
        )
    else:
        btn.setStyleSheet(
            f"QPushButton{{background:#f1f5f9;color:{TXT_S};"
            "border:none;border-radius:8px;"
            "font-size:13px;font-weight:500;}}"
            "QPushButton:hover{background:#e2e8f0;}"
            f"QPushButton:disabled{{color:#cbd5e1;background:#f8fafc;}}"
        )
    return btn


def _btn_secondary(text: str, h: int = 42) -> QPushButton:
    b = QPushButton(text)
    b.setMinimumHeight(h)
    b.setCursor(Qt.PointingHandCursor)
    b.setStyleSheet(
        "QPushButton{background:#f1f5f9;color:#475569;border:none;"
        "border-radius:10px;font-size:14px;font-weight:600;padding:0 20px;}"
        "QPushButton:hover{background:#e2e8f0;}"
    )
    return b


def _style_table(tbl: QTableWidget) -> None:
    tbl.setStyleSheet(f"""
        QTableWidget {{
            background:{CARD_BG}; border:none;
            gridline-color:{BORDER}; font-size:13px;
            outline:none; selection-background-color:#ede9fe;
        }}
        QTableWidget::item {{ padding:10px 12px; border:none; color:{TXT_S}; }}
        QTableWidget::item:selected {{ background:#ede9fe; color:{P_DARK}; }}
        QHeaderView::section {{
            background:#f8fafc; border:none;
            border-bottom:1.5px solid {BORDER};
            padding:10px 12px; font-size:12px;
            font-weight:700; color:{TXT_M};
            text-transform:uppercase; letter-spacing:0.5px;
        }}
    """)
    tbl.setAlternatingRowColors(False)
    tbl.setShowGrid(False)
    tbl.verticalHeader().setVisible(False)
    tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tbl.horizontalHeader().setStretchLastSection(False)
    tbl.setFrameShape(QFrame.NoFrame)
    tbl.verticalHeader().setDefaultSectionSize(48)


# ══════════════════════════════════════════════════════════════
#  PROPORTIONAL COLUMN RESIZER
# ══════════════════════════════════════════════════════════════
class _ColResizeFilter(QObject):
    """Keeps two 'flex' columns at a fixed ratio whenever the table resizes.

    Install on the table's viewport so every window-resize fires _apply().
    col_a gets  ratio   × available_width
    col_b gets (1-ratio) × available_width
    """

    def __init__(self, tbl: "QTableWidget",
                 col_a: int, col_b: int,
                 ratio: float,
                 fixed_total: int,
                 parent=None):
        super().__init__(parent or tbl)
        self._tbl       = tbl
        self._ca        = col_a
        self._cb        = col_b
        self._ratio     = ratio
        self._fixed     = fixed_total
        tbl.viewport().installEventFilter(self)

    def _apply(self) -> None:
        avail = max(self._tbl.viewport().width() - self._fixed - 2, 220)
        hh = self._tbl.horizontalHeader()
        hh.blockSignals(True)
        self._tbl.setColumnWidth(self._ca, int(avail * self._ratio))
        self._tbl.setColumnWidth(self._cb, int(avail * (1 - self._ratio)))
        hh.blockSignals(False)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Resize:
            self._apply()
        return False


# ══════════════════════════════════════════════════════════════
#  HR DASHBOARD
# ══════════════════════════════════════════════════════════════
class HRDashboard:
    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout  = on_logout
        self._nav_btns: list[_NavBtn] = []
        self._build()
        self._go(0)

    # ── build window ──────────────────────────────────────────
    def _build(self) -> None:
        win = QMainWindow()
        win.setWindowTitle("JobHub HR - Bảng điều khiển")
        win.setMinimumSize(1100, 680)
        win.resize(1280, 820)
        win.setStyleSheet(
            f"QMainWindow{{background:{CONTENT_BG};}}"
            "QToolTip{"
            "background:#1e293b;color:#f8fafc;"
            "border:none;border-radius:6px;"
            "padding:5px 10px;font-size:12px;"
            "}"
        )
        self.win = win

        root = QWidget()
        root.setStyleSheet(f"background:{CONTENT_BG};")
        rlo = QHBoxLayout(root)
        rlo.setSpacing(0)
        rlo.setContentsMargins(0, 0, 0, 0)
        rlo.addWidget(self._build_sidebar())
        rlo.addWidget(self._build_main(), 1)
        win.setCentralWidget(root)

    # ── toast notification ────────────────────────────────────
    def _show_toast(self, text: str, icon: str = "✅",
                    color: str = "#10b981", duration: int = 3000) -> None:
        """Hiện thông báo nổi góc phải-dưới, tự động tắt sau `duration` ms."""
        toast = QWidget(self.win)
        toast.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        toast.setAttribute(Qt.WA_TranslucentBackground, False)
        toast.setFixedWidth(320)

        lo = QHBoxLayout(toast)
        lo.setContentsMargins(14, 12, 14, 12)
        lo.setSpacing(10)

        # Icon badge
        ic_lbl = QLabel(icon)
        ic_lbl.setFixedSize(32, 32)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet(
            f"background:{color}22;border-radius:16px;"
            f"color:{color};font-size:16px;border:none;"
        )

        # Message
        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:13px;font-weight:500;"
            "background:transparent;border:none;"
        )

        # Close btn
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TXT_M};"
            "border:none;font-size:16px;font-weight:700;border-radius:10px;}}"
            f"QPushButton:hover{{background:#f1f5f9;color:{TXT_H};}}"
        )
        close_btn.clicked.connect(toast.hide)

        lo.addWidget(ic_lbl)
        lo.addWidget(msg_lbl, 1)
        lo.addWidget(close_btn, 0, Qt.AlignTop)

        toast.setStyleSheet(
            "QWidget{"
            f"background:#ffffff;border:1.5px solid {color}55;"
            "border-radius:12px;"
            "}"
        )

        # Drop shadow
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(24)
        sh.setXOffset(0)
        sh.setYOffset(4)
        sh.setColor(QColor(0, 0, 0, 40))
        toast.setGraphicsEffect(sh)

        toast.adjustSize()
        toast.setFixedHeight(toast.sizeHint().height())

        # Position: bottom-right of window
        pw = self.win.width()
        ph = self.win.height()
        tx = pw - toast.width() - 24
        ty_end = ph - toast.height() - 24
        ty_start = ph  # slide up from below

        toast.move(tx, ty_start)
        toast.show()
        toast.raise_()

        # Slide-in animation
        anim_in = QPropertyAnimation(toast, b"pos")
        anim_in.setDuration(280)
        anim_in.setStartValue(QPoint(tx, ty_start))
        anim_in.setEndValue(QPoint(tx, ty_end))
        anim_in.setEasingCurve(QEasingCurve.OutCubic)
        anim_in.start()
        toast._anim_in = anim_in  # keep reference

        # Auto-dismiss
        def _dismiss():
            anim_out = QPropertyAnimation(toast, b"pos")
            anim_out.setDuration(220)
            anim_out.setStartValue(QPoint(tx, ty_end))
            anim_out.setEndValue(QPoint(tx, ty_start))
            anim_out.setEasingCurve(QEasingCurve.InCubic)
            anim_out.finished.connect(toast.deleteLater)
            anim_out.start()
            toast._anim_out = anim_out

        QTimer.singleShot(duration, _dismiss)

    # ── global search popup ───────────────────────────────────
    def _show_global_search_popup(self) -> None:
        kw = self.search_input.text().strip().lower()
        if not kw:
            self._hide_global_search_popup()
            return

        # Search jobs
        job_hits = [j for j in mock_data.JOB_STORE
                    if kw in j.get("title", "").lower()
                    or kw in j.get("department", "").lower()
                    or kw in j.get("location", "").lower()
                    or kw in j.get("job_type", "").lower()
                    or kw in j.get("company_name", "").lower()][:5]

        # Search candidates
        all_apps = list(mock_data.CANDIDATE_APPLICATIONS) + list(mock_data.MOCK_HR_APPLICATIONS)
        cand_hits = [a for a in all_apps
                     if kw in a.get("candidate_name",  "").lower()
                     or kw in a.get("candidate_email", "").lower()
                     or kw in a.get("job_title",       "").lower()][:5]

        if not job_hits and not cand_hits:
            self._hide_global_search_popup()
            return

        # Build popup
        if self._global_popup:
            self._global_popup.deleteLater()
        popup = QFrame(self.win)
        popup.setWindowFlags(Qt.SubWindow)
        popup.setStyleSheet(
            f"QFrame{{background:#ffffff;border:1.5px solid {BORDER};"
            "border-radius:12px;}}"
            f"QLabel{{color:{TXT_H};background:transparent;border:none;}}"
        )
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(20); sh.setXOffset(0); sh.setYOffset(6)
        sh.setColor(QColor(0, 0, 0, 35))
        popup.setGraphicsEffect(sh)

        vlo = QVBoxLayout(popup)
        vlo.setContentsMargins(0, 8, 0, 8)
        vlo.setSpacing(0)

        def _section_hdr(txt):
            l = QLabel(f"  {txt}")
            l.setFixedHeight(28)
            l.setStyleSheet(
                f"color:{TXT_M};font-size:10px;font-weight:700;"
                "letter-spacing:1.2px;background:#f8fafc;"
                f"border-bottom:1px solid {BORDER};border:none;"
                "padding-left:14px;"
            )
            return l

        def _result_row(icon, title, sub, on_click):
            row = QWidget()
            row.setCursor(Qt.PointingHandCursor)
            row.setFixedHeight(48)
            row.setStyleSheet("QWidget{background:transparent;border-radius:0px;}")
            row_lo = QHBoxLayout(row)
            row_lo.setContentsMargins(14, 0, 14, 0)
            row_lo.setSpacing(10)

            ic = QLabel(icon)
            ic.setFixedSize(30, 30)
            ic.setAlignment(Qt.AlignCenter)
            ic.setStyleSheet(
                "background:#f1f5f9;border-radius:15px;"
                f"font-size:14px;color:{TXT_M};border:none;"
            )
            txt_col = QVBoxLayout()
            txt_col.setSpacing(1)
            t_lbl = QLabel(title[:50] + ("…" if len(title) > 50 else ""))
            t_lbl.setStyleSheet(
                f"color:{TXT_H};font-size:13px;font-weight:600;"
                "background:transparent;border:none;"
            )
            s_lbl = QLabel(sub[:60] + ("…" if len(sub) > 60 else ""))
            s_lbl.setStyleSheet(
                f"color:{TXT_M};font-size:11px;"
                "background:transparent;border:none;"
            )
            txt_col.addWidget(t_lbl)
            txt_col.addWidget(s_lbl)
            row_lo.addWidget(ic)
            row_lo.addLayout(txt_col, 1)

            def _on_enter(e, w=row):
                w.setStyleSheet("QWidget{background:#f8fafc;border-radius:0;}")
            def _on_leave(e, w=row):
                w.setStyleSheet("QWidget{background:transparent;border-radius:0;}")
            row.enterEvent = _on_enter
            row.leaveEvent = _on_leave
            row.mousePressEvent = lambda e, fn=on_click: fn()
            return row

        if job_hits:
            vlo.addWidget(_section_hdr(f"TIN ĐĂNG  ({len(job_hits)})"))
            for j in job_hits:
                sub = f"{j.get('company_name','')}  ·  {j.get('location','')}  ·  {j.get('job_type','')}"
                def _go_job(jid=j["id"], title=j["title"]):
                    self._hide_global_search_popup()
                    self._go(2)
                    self._jobs_search.setText(title)
                vlo.addWidget(_result_row("💼", j.get("title",""), sub, _go_job))

        if cand_hits:
            vlo.addWidget(_section_hdr(f"ỨNG VIÊN  ({len(cand_hits)})"))
            for a in cand_hits:
                sub = f"{a.get('job_title','')}  ·  {a.get('candidate_email','')}"
                def _go_cand(name=a.get("candidate_name","")):
                    self._hide_global_search_popup()
                    self._go(3)
                    self._cands_search.setText(name)
                vlo.addWidget(_result_row("👤", a.get("candidate_name",""), sub, _go_cand))

        # Footer "Tìm tất cả"
        footer = QWidget()
        footer.setFixedHeight(38)
        footer.setCursor(Qt.PointingHandCursor)
        footer.setStyleSheet(
            f"QWidget{{background:transparent;border-top:1px solid {BORDER};}}"
        )
        f_lo = QHBoxLayout(footer)
        f_lo.setContentsMargins(14, 0, 14, 0)
        f_all = QLabel(f"🔍  Tìm tất cả kết quả cho  \"{self.search_input.text().strip()}\"")
        f_all.setStyleSheet(
            f"color:{P};font-size:12px;font-weight:600;"
            "background:transparent;border:none;"
        )
        f_lo.addWidget(f_all)
        f_lo.addStretch()
        footer.enterEvent = lambda e: footer.setStyleSheet(
            f"QWidget{{background:#f5f3ff;border-top:1px solid {BORDER};}}"
        )
        footer.leaveEvent = lambda e: footer.setStyleSheet(
            f"QWidget{{background:transparent;border-top:1px solid {BORDER};}}"
        )
        footer.mousePressEvent = lambda e: self._global_search_enter()
        vlo.addWidget(footer)

        # Position popup below search bar
        popup.adjustSize()
        ref = self._search_outer_ref
        pos = ref.mapTo(self.win, QPoint(0, ref.height() + 4))
        popup.setFixedWidth(max(ref.width(), 460))
        popup.move(pos)
        popup.show()
        popup.raise_()
        self._global_popup = popup

    def _hide_global_search_popup(self) -> None:
        if self._global_popup:
            self._global_popup.hide()
            self._global_popup.deleteLater()
            self._global_popup = None

    def _global_search_enter(self) -> None:
        """Navigate to best matching tab and apply search term."""
        kw = self.search_input.text().strip()
        self._hide_global_search_popup()
        if not kw:
            return
        # Decide which tab to land on based on results
        job_hits = [j for j in mock_data.JOB_STORE
                    if kw.lower() in j.get("title","").lower()
                    or kw.lower() in j.get("company_name","").lower()]
        if job_hits:
            self._go(2)
            self._jobs_search.setText(kw)
        else:
            self._go(3)
            self._cands_search.setText(kw)
        self.search_input.clear()

    # ── sidebar ───────────────────────────────────────────────
    def _build_sidebar(self) -> QFrame:
        sb = QFrame()
        sb.setFixedWidth(SIDEBAR_W)
        sb.setStyleSheet(f"QFrame{{background:{SIDEBAR_BG};border:none;}}")

        lo = QVBoxLayout(sb)
        lo.setContentsMargins(12, 0, 12, 0)
        lo.setSpacing(2)

        # ── Brand area — transparent, blends into sidebar ──────
        brand_area = QWidget()
        brand_area.setFixedHeight(76)
        # Force transparent so no white box appears on any platform
        brand_area.setStyleSheet("background:transparent;")
        brand_lo = QHBoxLayout(brand_area)
        brand_lo.setContentsMargins(16, 0, 0, 0)   # 16px left breathing room
        brand_lo.setSpacing(10)

        # ⚡ Lightning bolt accent icon
        brand_bolt = QLabel("⚡")
        brand_bolt.setStyleSheet(
            "color:#818cf8;font-size:20px;background:transparent;border:none;"
        )
        # "JobHub" wordmark — white on dark, no container
        brand_t = QLabel("JobHub")
        brand_t.setStyleSheet(
            "color:#ffffff;font-size:21px;font-weight:800;"
            "letter-spacing:-0.4px;background:transparent;border:none;"
        )
        # HR badge pill
        brand_badge = QLabel("HR")
        brand_badge.setFixedHeight(20)
        brand_badge.setStyleSheet(
            "background:#312e81;color:#a5b4fc;font-size:10px;"
            "font-weight:700;border-radius:5px;padding:0 6px;"
        )
        brand_lo.addWidget(brand_bolt)
        brand_lo.addWidget(brand_t)
        brand_lo.addSpacing(4)
        brand_lo.addWidget(brand_badge, alignment=Qt.AlignVCenter)
        brand_lo.addStretch()
        lo.addWidget(brand_area)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("background:#1e293b; max-height:1px; border:none;")
        lo.addWidget(div)
        lo.addSpacing(10)

        # ── Nav section label — visible but not distracting ─────
        sec = QLabel("ĐIỀU HƯỚNG")
        sec.setStyleSheet(
            "color:#475569;"          # clearly readable on #0f172a
            "font-size:11px;font-weight:700;"
            "letter-spacing:2.4px;padding-left:20px;"
            "background:transparent;"
        )
        lo.addWidget(sec)
        lo.addSpacing(6)

        nav_items = [
            ("ic_dashboard.svg", "Bảng điều khiển"),
            ("ic_edit.svg",      "Đăng tin mới"),
            ("ic_jobs.svg",      "Quản lý tin đăng"),
            ("ic_users.svg",     "Danh sách ứng viên"),
        ]
        for i, (icon, label) in enumerate(nav_items):
            btn = _NavBtn(icon, label)
            btn.on_click(lambda idx=i: self._go(idx))
            lo.addWidget(btn)
            self._nav_btns.append(btn)

        lo.addStretch()

        # Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet("background:#1e293b; max-height:1px; border:none;")
        lo.addWidget(div2)
        lo.addSpacing(8)

        # ── Logout — uses logout=True for built-in pastel-red colors ──
        self._btn_logout = _NavBtn("ic_logout.svg", "Đăng xuất",
                                   logout=True)
        self._btn_logout.on_click(self._logout)
        lo.addWidget(self._btn_logout)
        lo.addSpacing(16)

        return sb

    # ── main area ─────────────────────────────────────────────
    def _build_main(self) -> QWidget:
        main = QWidget()
        main.setStyleSheet(f"background:{CONTENT_BG};")
        lo = QVBoxLayout(main)
        lo.setSpacing(0)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.addWidget(self._build_topbar())
        lo.addWidget(self._build_content(), 1)
        return main

    # ── topbar ────────────────────────────────────────────────
    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(TOPBAR_H)
        bar.setStyleSheet(
            f"QFrame{{background:{TOPBAR_BG};border-bottom:1px solid {BORDER};}}"
        )

        # 3-column layout: [title | search | profile]
        lo = QHBoxLayout(bar)
        lo.setContentsMargins(24, 0, 24, 0)
        lo.setSpacing(16)

        # ── LEFT: title + subtitle (fixed-width column) ───────
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_col.setAlignment(Qt.AlignVCenter)
        self.lbl_page_title = QLabel("Bảng điều khiển")
        self.lbl_page_title.setStyleSheet(
            f"color:{TXT_H};font-size:18px;font-weight:700;"
            "background:transparent;border:none;"
        )
        self.lbl_page_sub = QLabel("Theo dõi hiệu quả tuyển dụng của bạn")
        self.lbl_page_sub.setStyleSheet(
            f"color:{TXT_M};font-size:12px;font-weight:400;"
            "background:transparent;border:none;"
        )
        title_col.addWidget(self.lbl_page_title)
        title_col.addWidget(self.lbl_page_sub)

        title_wrap = QWidget()
        title_wrap.setFixedWidth(230)
        title_wrap.setStyleSheet("background:transparent;")
        tw_lo = QVBoxLayout(title_wrap)
        tw_lo.setContentsMargins(0, 0, 0, 0)
        tw_lo.setSpacing(0)
        tw_lo.setAlignment(Qt.AlignVCenter)
        tw_lo.addLayout(title_col)
        lo.addWidget(title_wrap)

        # ── CENTER: dominant search bar ───────────────────────
        search_outer = QFrame()
        search_outer.setFixedHeight(42)
        search_outer.setStyleSheet(
            f"QFrame{{background:#f8fafc;border:1.5px solid {BORDER};"
            "border-radius:21px;}}"
            f"QFrame:focus-within{{border-color:{P};}}"
        )

        s_lo = QHBoxLayout(search_outer)
        s_lo.setContentsMargins(14, 0, 14, 0)
        s_lo.setSpacing(8)

        search_ic = QLabel()
        search_ic.setPixmap(_svg_pm("ic_search.svg", 16, "#94a3b8"))
        search_ic.setStyleSheet("background:transparent;border:none;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm ứng viên, tin đăng...")
        self.search_input.setFrame(False)
        self.search_input.setStyleSheet(
            f"background:transparent;border:none;font-size:14px;"
            f"color:{TXT_H};"
        )

        s_lo.addWidget(search_ic)
        s_lo.addWidget(self.search_input, 1)
        lo.addWidget(search_outer, 1)   # stretch to fill center

        # Debounce timer for global search
        self._global_search_timer = QTimer()
        self._global_search_timer.setSingleShot(True)
        self._global_search_timer.timeout.connect(self._show_global_search_popup)
        self.search_input.textChanged.connect(
            lambda t: (
                self._global_search_timer.stop(),
                self._global_search_timer.start(250) if t.strip() else self._hide_global_search_popup()
            )
        )
        self.search_input.returnPressed.connect(self._global_search_enter)
        # Store reference for popup positioning
        self._search_outer_ref = search_outer
        # Popup widget (created lazily)
        self._global_popup: QWidget | None = None

        # ── RIGHT: profile section ────────────────────────────
        profile_wrap = QWidget()
        profile_wrap.setFixedWidth(220)
        profile_wrap.setStyleSheet("background:transparent;")
        p_lo = QHBoxLayout(profile_wrap)
        p_lo.setContentsMargins(0, 0, 0, 0)
        p_lo.setSpacing(10)
        p_lo.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setAlignment(Qt.AlignVCenter)
        self.lbl_hr_name = QLabel("TechCorp HR")
        self.lbl_hr_name.setAlignment(Qt.AlignRight)
        self.lbl_hr_name.setStyleSheet(
            f"color:{TXT_H};font-size:14px;font-weight:600;"
            "background:transparent;border:none;"
        )
        lbl_role = QLabel("Nhà tuyển dụng xác thực")
        lbl_role.setAlignment(Qt.AlignRight)
        lbl_role.setStyleSheet(
            f"color:{TXT_M};font-size:11px;font-weight:400;"
            "background:transparent;border:none;"
        )
        info_col.addWidget(self.lbl_hr_name)
        info_col.addWidget(lbl_role)
        p_lo.addLayout(info_col)

        ava_btn = QPushButton("HR")
        ava_btn.setFixedSize(40, 40)
        ava_btn.setCursor(Qt.PointingHandCursor)
        ava_btn.setStyleSheet(
            f"QPushButton{{background:{P};color:#fff;border-radius:20px;"
            "font-size:13px;font-weight:800;border:none;}}"
            f"QPushButton:hover{{background:{P_DARK};}}"
        )
        p_lo.addWidget(ava_btn)

        arrow = QLabel("▾")
        arrow.setStyleSheet(
            f"color:{TXT_M};font-size:13px;"
            "background:transparent;border:none;"
        )
        p_lo.addWidget(arrow)
        lo.addWidget(profile_wrap)

        return bar

    # ── stacked content ───────────────────────────────────────
    def _build_content(self) -> QWidget:
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background:{CONTENT_BG};")
        self._stack.addWidget(self._build_dash_page())    # 0
        self._stack.addWidget(self._build_post_page())    # 1
        self._stack.addWidget(self._build_jobs_page())    # 2
        self._stack.addWidget(self._build_cands_page())   # 3
        return self._stack

    # ── PAGE 0: DASHBOARD ─────────────────────────────────────
    def _build_dash_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:8px;background:transparent;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#cbd5e1;border-radius:4px;min-height:32px;}"
            "QScrollBar::handle:vertical:hover{background:#94a3b8;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        pg = QWidget()
        pg.setStyleSheet(f"background:{CONTENT_BG};")
        lo = QVBoxLayout(pg)
        lo.setContentsMargins(28, 28, 28, 28)
        lo.setSpacing(20)

        # ── Metric cards row ────────────────────────────────
        self._cards_row = QHBoxLayout()
        self._cards_row.setSpacing(18)
        lo.addLayout(self._cards_row)

        # ── Quick stats divider bar ──────────────────────────
        stats_bar = QFrame()
        stats_bar.setFixedHeight(52)
        stats_bar.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:1px solid {BORDER};"
            "border-radius:12px;}}"
        )
        stats_lo = QHBoxLayout(stats_bar)
        stats_lo.setContentsMargins(20, 0, 20, 0)
        stats_lo.setSpacing(0)

        for i, (val, lbl, col) in enumerate([
            ("3",   "Ứng viên mới hôm nay",    "#6366f1"),
            ("1",   "Tin chờ Admin duyệt",      "#f59e0b"),
            ("86%", "Tỷ lệ trả lời ứng viên",  "#10b981"),
            ("2",   "Phỏng vấn sắp tới",        "#0ea5e9"),
        ]):
            if i > 0:
                sep = QFrame()
                sep.setFixedSize(1, 30)
                sep.setStyleSheet(f"background:{BORDER};border:none;")
                stats_lo.addWidget(sep)
                stats_lo.addSpacing(0)

            stat_w = QWidget()
            stat_w.setStyleSheet("background:transparent;")
            stat_inner = QHBoxLayout(stat_w)
            stat_inner.setContentsMargins(20, 0, 20, 0)
            stat_inner.setSpacing(8)
            stat_inner.setAlignment(Qt.AlignCenter)

            v_lbl = QLabel(val)
            v_lbl.setStyleSheet(
                f"color:{col};font-size:20px;font-weight:800;"
                "background:transparent;border:none;"
            )
            t_lbl = QLabel(lbl)
            t_lbl.setStyleSheet(
                f"color:{TXT_M};font-size:12px;font-weight:500;"
                "background:transparent;border:none;"
            )
            stat_inner.addWidget(v_lbl)
            stat_inner.addWidget(t_lbl)
            stats_lo.addWidget(stat_w, 1)

        lo.addWidget(stats_bar)

        # ── Bottom: chart (left) + activity (right) ─────────
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # ── Chart card with period filter tabs ───────────────
        chart_frame, chart_lo = _card_frame()
        chart_frame.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:none;border-radius:16px;}}"
        )
        chart_lo.setSpacing(12)

        chart_header_row = QHBoxLayout()
        chart_header_row.setSpacing(0)

        chart_left = QHBoxLayout()
        chart_left.setSpacing(8)
        chart_ic = QLabel()
        chart_ic.setPixmap(_svg_pm("ic_trend.svg", 18, P))
        chart_ic.setStyleSheet("background:transparent;border:none;")
        chart_title_lbl = QLabel("Xu hướng tuyển dụng")
        chart_title_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:16px;font-weight:700;"
            "background:transparent;border:none;"
        )
        chart_left.addWidget(chart_ic)
        chart_left.addWidget(chart_title_lbl)
        chart_header_row.addLayout(chart_left, 1)

        # Period filter pill-tabs
        self._chart_period = "week"
        self._chart_period_btns: list[QPushButton] = []
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        for period, label in [("week", "Tuần"), ("month", "Tháng"), ("quarter", "Quý")]:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setMinimumWidth(56)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(period == "week")
            btn.setStyleSheet(
                f"QPushButton{{background:#f1f5f9;color:{TXT_M};"
                "border:none;border-radius:6px;"
                "font-size:12px;font-weight:600;padding:0 12px;}}"
                f"QPushButton:checked{{background:{P};color:white;}}"
                "QPushButton:hover:!checked{background:#e2e8f0;}"
            )
            btn.clicked.connect(
                lambda checked, p=period: self._switch_chart_period(p)
            )
            self._chart_period_btns.append(btn)
            filter_row.addWidget(btn)

        chart_header_row.addLayout(filter_row)
        chart_lo.addLayout(chart_header_row)

        self._chart_holder = QWidget()
        self._chart_holder.setStyleSheet("background:transparent;")
        chart_h_lo = QVBoxLayout(self._chart_holder)
        chart_h_lo.setContentsMargins(0, 0, 0, 0)
        chart_lo.addWidget(self._chart_holder)
        bottom_row.addWidget(chart_frame, 6)

        # ── Activity feed card ───────────────────────────────
        act_frame, act_lo = _card_frame()
        act_frame.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:none;border-radius:16px;}}"
        )
        act_lo.setSpacing(0)

        act_header = QHBoxLayout()
        act_header.setSpacing(8)
        act_ic = QLabel()
        act_ic.setPixmap(_svg_pm("ic_activity.svg", 18, "#10b981"))
        act_ic.setStyleSheet("background:transparent;")
        act_title_lbl = QLabel("Hoạt động gần đây")
        act_title_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:16px;font-weight:700;"
            "background:transparent;border:none;"
        )
        act_count = QLabel(f"  {len(mock_data.MOCK_HR_ACTIVITY)} sự kiện  ")
        act_count.setStyleSheet(
            f"background:#ede9fe;color:{P};font-size:11px;font-weight:700;"
            "border-radius:10px;padding:2px 0;"
        )
        act_header.addWidget(act_ic)
        act_header.addWidget(act_title_lbl, 1)
        act_header.addWidget(act_count)
        act_lo.addLayout(act_header)
        act_lo.addSpacing(12)

        # Scrollable activity list inside the card
        act_scroll = QScrollArea()
        act_scroll.setWidgetResizable(True)
        act_scroll.setFrameShape(QFrame.NoFrame)
        act_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        act_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:6px;background:transparent;}"
            "QScrollBar::handle:vertical{background:#e2e8f0;border-radius:3px;min-height:20px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        act_inner = QWidget()
        act_inner.setStyleSheet("background:transparent;")
        self._act_list_lo = QVBoxLayout(act_inner)
        self._act_list_lo.setSpacing(0)
        self._act_list_lo.setContentsMargins(0, 0, 0, 0)
        act_scroll.setWidget(act_inner)
        act_scroll.setMinimumHeight(320)
        act_lo.addWidget(act_scroll, 1)
        bottom_row.addWidget(act_frame, 4)

        lo.addLayout(bottom_row)
        lo.addStretch()

        scroll.setWidget(pg)
        return scroll

    # Type → (emoji, bg_color, fg_color)
    _ACT_TYPE_STYLE: dict = {
        "apply":     ("📋", "#ede9fe", "#6366f1"),
        "interview": ("📅", "#dbeafe", "#2563eb"),
        "approved":  ("✅", "#d1fae5", "#059669"),
        "update":    ("🔄", "#fef3c7", "#d97706"),
        "view":      ("👁️",  "#f1f5f9", "#64748b"),
    }
    _ACT_GROUP_LABEL: dict = {
        "today":     "Hôm nay",
        "yesterday": "Hôm qua",
        "week":      "Tuần này",
    }

    def _load_dash(self) -> None:
        data  = mock_data.MOCK_HR_DASHBOARD
        cards = data.get("cards") or {}

        # ── Metric cards ─────────────────────────────────────
        while self._cards_row.count():
            it = self._cards_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        sp = {
            "jobs":      [7, 8, 9, 10, 11, 12],
            "candidates":[30, 35, 39, 43, 46, 48],
            "views":     [1900, 2200, 2600, 2900, 3050, 3200],
            "response":  [34, 36, 38, 40, 41, 42],
        }
        # (icon, accent_color, label, value, hint_text, sp_data, sp_color)
        card_defs = [
            ("ic_jobs.svg",
             "#6366f1",           # indigo — thay đỏ
             "Tin đang đăng",
             str(cards.get("jobs", 0)),
             "↑ +2 tuần này",
             sp["jobs"],   "#818cf8"),

            ("ic_users.svg",
             "#f97316",           # orange — thay vàng đậm
             "Tổng ứng viên",
             str(cards.get("candidates", 0)),
             "↑ +15 mới",
             sp["candidates"], "#fb923c"),

            ("ic_view.svg",
             "#0ea5e9",           # sky — giữ nguyên
             "Lượt xem tin",
             f"{cards.get('views', 0):,}",
             "↑ +12% xu hướng",
             sp["views"],  "#38bdf8"),

            ("ic_chat.svg",
             "#10b981",           # emerald — giữ nguyên
             "Tỷ lệ phản hồi",
             f"{cards.get('response_rate', 0)}%",
             "● Tối ưu",
             sp["response"], "#34d399"),
        ]
        for (icon, accent, label, val, hint, sp_data, sp_col) in card_defs:
            c = _MetricCard(
                icon_svg=icon,
                icon_color=accent,
                icon_bg=accent + "20",   # unused in new design but kept for compat
                label=label,
                value=val,
                hint=hint,
                hint_color=accent,
                hint_bg=accent + "18",
                glow_color=accent,
                sparkline_data=sp_data,
                sparkline_color=sp_col,
            )
            self._cards_row.addWidget(c)

        # ── Chart (initial period = week) ─────────────────────
        self._rebuild_chart("week")

        # ── Activity feed (grouped) ───────────────────────────
        self._rebuild_activity_feed()

    def _switch_chart_period(self, period: str) -> None:
        """Called when user clicks a chart period tab."""
        self._chart_period = period
        for btn in self._chart_period_btns:
            btn.setChecked(btn.text() in {"Tuần": "week", "Tháng": "month", "Quý": "quarter"}
                           and {"Tuần": "week", "Tháng": "month", "Quý": "quarter"}[btn.text()] == period)
        self._rebuild_chart(period)

    def _rebuild_chart(self, period: str) -> None:
        """Rebuild the bar chart for the given period."""
        chart_data = mock_data.MOCK_HR_CHART_DATA.get(period, {})
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])

        lay = self._chart_holder.layout()
        while lay.count():
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        canvas = make_bar_chart(
            [str(x) for x in labels],
            [int(x) for x in values],
            "#6366f1", dark=False,
        )
        canvas.setMinimumHeight(240)
        lay.addWidget(canvas)

    def _rebuild_activity_feed(self) -> None:
        """Rebuild activity feed with grouping by day + icons."""
        while self._act_list_lo.count():
            it = self._act_list_lo.takeAt(0)
            if w := it.widget():
                w.deleteLater()

        # Merge runtime events (from User/Admin actions) + static mock data
        runtime = list(mock_data.HR_ACTIVITY_STORE)
        activities = runtime + mock_data.MOCK_HR_ACTIVITY
        current_group = None
        for act in activities:
            group = act.get("group", "week")
            # Group header when group changes
            if group != current_group:
                current_group = group
                grp_lbl = QLabel(self._ACT_GROUP_LABEL.get(group, group))
                grp_lbl.setStyleSheet(
                    f"color:{TXT_M};font-size:10px;font-weight:700;"
                    "letter-spacing:1.5px;background:transparent;border:none;"
                    "padding:12px 0 6px 0;"
                )
                self._act_list_lo.addWidget(grp_lbl)

            item = self._make_activity_item(act)
            self._act_list_lo.addWidget(item)

            # Thin divider
            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER};border:none;margin:0 4px;")
            self._act_list_lo.addWidget(div)

        self._act_list_lo.addStretch()

    def _make_activity_item(self, act: dict) -> QWidget:
        """Redesigned activity row: type icon | text + time | quick-action button."""
        act_type  = act.get("type", "view")
        dot_color = act.get("dot_color", TXT_M)
        text      = act.get("text", "")
        time_str  = act.get("time", "")
        bold      = act.get("bold", False)
        act_label = act.get("action_label", "")
        act_page  = act.get("action_page", 0)

        emoji, type_bg, type_fg = self._ACT_TYPE_STYLE.get(
            act_type, ("●", "#f1f5f9", "#64748b")
        )

        row = QWidget()
        row.setMinimumHeight(52)
        row.setStyleSheet("QWidget{background:transparent;border-radius:8px;}")
        row.setCursor(Qt.PointingHandCursor)

        def _on_enter(e, w=row):
            w.setStyleSheet("QWidget{background:#f8fafc;border-radius:8px;}")
            super(QWidget, w).enterEvent(e)  # noqa

        def _on_leave(e, w=row):
            w.setStyleSheet("QWidget{background:transparent;border-radius:8px;}")
            super(QWidget, w).leaveEvent(e)  # noqa

        row.enterEvent = _on_enter
        row.leaveEvent = _on_leave

        lo = QHBoxLayout(row)
        lo.setContentsMargins(4, 6, 4, 6)
        lo.setSpacing(10)

        # Type icon badge
        badge = QLabel(emoji)
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background:{type_bg};border-radius:8px;"
            "font-size:14px;border:none;"
        )

        # Text column
        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        txt_col.setContentsMargins(0, 0, 0, 0)

        main_lbl = QLabel(text)
        main_lbl.setWordWrap(True)
        weight = "600" if bold else "400"
        main_lbl.setStyleSheet(
            f"color:{TXT_S};font-size:12px;font-weight:{weight};"
            "background:transparent;border:none;"
        )
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(
            f"color:{TXT_M};font-size:10px;font-weight:400;"
            "background:transparent;border:none;"
        )
        txt_col.addWidget(main_lbl)
        txt_col.addWidget(time_lbl)

        lo.addWidget(badge, 0, Qt.AlignVCenter)
        lo.addLayout(txt_col, 1)

        # Quick-action button
        if act_label:
            qa_btn = QPushButton(act_label)
            qa_btn.setFixedHeight(24)
            qa_btn.setMinimumWidth(64)
            qa_btn.setCursor(Qt.PointingHandCursor)
            qa_btn.setStyleSheet(
                f"QPushButton{{background:{type_bg};color:{type_fg};"
                "border:none;border-radius:6px;"
                "font-size:10px;font-weight:700;padding:0 8px;}}"
                f"QPushButton:hover{{background:{dot_color};color:white;}}"
            )
            qa_btn.clicked.connect(lambda _, p=act_page: self._go(p))
            lo.addWidget(qa_btn, 0, Qt.AlignVCenter)

        return row

    # ── PAGE 1: POST JOB ──────────────────────────────────────
    def _build_post_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")

        pg = QWidget()
        pg.setStyleSheet(f"background:{CONTENT_BG};")
        outer = QVBoxLayout(pg)
        outer.setContentsMargins(48, 32, 48, 32)
        outer.setSpacing(20)

        # ── Page header ─────────────────────────────────────────
        page_title = QLabel("Đăng tin tuyển dụng mới")
        page_title.setAlignment(Qt.AlignCenter)
        page_title.setStyleSheet(
            f"color:{TXT_H};font-size:26px;font-weight:800;"
            "background:transparent;border:none;letter-spacing:-0.3px;"
        )
        page_sub = QLabel(
            "Kiến tạo đội ngũ mơ ước của bạn với quy trình tuyển dụng "
            "chuẩn mực và hiện đại."
        )
        page_sub.setAlignment(Qt.AlignCenter)
        page_sub.setWordWrap(True)
        page_sub.setStyleSheet(
            f"color:{TXT_M};font-size:14px;background:transparent;border:none;"
        )
        outer.addWidget(page_title)
        outer.addWidget(page_sub)
        outer.addSpacing(4)

        # ── Info banner ─────────────────────────────────────────
        banner = QLabel(
            "✅  Tài khoản HR của bạn đã được xác thực. "
            "Tin đăng sẽ được ưu tiên hiển thị trên trang chủ."
        )
        banner.setWordWrap(True)
        banner.setStyleSheet(
            "background:#eff6ff;border:1.5px solid #bfdbfe;border-radius:10px;"
            "color:#1d4ed8;font-size:13px;padding:12px 16px;"
        )
        outer.addWidget(banner)

        # ── SECTION 1: Thông tin cơ bản ─────────────────────────
        s1, s1lo = _card_frame()
        s1lo.setSpacing(16)
        s1lo.addWidget(_section_header("ic_edit.svg", "Thông tin cơ bản"))

        s1lo.addWidget(_lbl("Tiêu đề tin đăng", 13, bold=True))
        self.line_title = _input("Ví dụ: Senior Frontend Developer (ReactJS)")
        self.line_title.setMinimumHeight(46)
        s1lo.addWidget(self.line_title)

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        col_a = QVBoxLayout(); col_a.setSpacing(8)
        col_a.addWidget(_lbl("Cấp bậc", 13, bold=True))
        self.combo_level = _combo(
            ["Nhân viên", "Trưởng nhóm", "Quản lý", "Giám đốc", "Thực tập sinh"]
        )
        col_a.addWidget(self.combo_level)
        col_b = QVBoxLayout(); col_b.setSpacing(8)
        col_b.addWidget(_lbl("Loại hình làm việc", 13, bold=True))
        self.combo_type = _combo(
            ["Toàn thời gian", "Bán thời gian", "Remote", "Hybrid", "Hợp đồng"]
        )
        col_b.addWidget(self.combo_type)
        row1.addLayout(col_a)
        row1.addLayout(col_b)
        s1lo.addLayout(row1)
        outer.addWidget(s1)

        # ── SECTION 2: Chi tiết & Đãi ngộ ───────────────────────
        s2, s2lo = _card_frame()
        s2lo.setSpacing(16)
        s2lo.addWidget(
            _section_header("ic_jobs.svg", "Chi tiết & Đãi ngộ",
                            "#f59e0b", "#fef3c7")
        )

        row2 = QHBoxLayout(); row2.setSpacing(16)
        col_c = QVBoxLayout(); col_c.setSpacing(8)
        col_c.addWidget(_lbl("Mức lương (VNĐ)", 13, bold=True))
        self.line_salary = _input("Ví dụ: 15 – 25 triệu VNĐ")
        self.line_salary.setMinimumHeight(46)
        col_c.addWidget(self.line_salary)
        col_d = QVBoxLayout(); col_d.setSpacing(8)
        col_d.addWidget(_lbl("Địa điểm làm việc", 13, bold=True))
        self.line_location = _input("Thành phố Hồ Chí Minh, Quận 1")
        self.line_location.setMinimumHeight(46)
        col_d.addWidget(self.line_location)
        row2.addLayout(col_c)
        row2.addLayout(col_d)
        s2lo.addLayout(row2)

        row3 = QHBoxLayout(); row3.setSpacing(16)
        col_e = QVBoxLayout(); col_e.setSpacing(8)
        col_e.addWidget(_lbl("Số lượng tuyển", 13, bold=True))
        self.line_count = _input("01")
        self.line_count.setMinimumHeight(46)
        col_e.addWidget(self.line_count)
        col_f = QVBoxLayout(); col_f.setSpacing(8)
        col_f.addWidget(_lbl("Hạn nộp hồ sơ", 13, bold=True))
        self.line_deadline = _input("Ví dụ: 31/12/2025")
        self.line_deadline.setMinimumHeight(46)
        col_f.addWidget(self.line_deadline)
        row3.addLayout(col_e)
        row3.addLayout(col_f)
        s2lo.addLayout(row3)
        outer.addWidget(s2)

        # ── SECTION 3: Mô tả công việc ──────────────────────────
        s3, s3lo = _card_frame()
        s3lo.setSpacing(14)
        s3lo.addWidget(
            _section_header("ic_doc.svg", "Mô tả công việc",
                            "#0ea5e9", "#e0f2fe")
        )
        s3lo.addWidget(_lbl("Nội dung chi tiết", 13, bold=True))

        self.plain_desc = QPlainTextEdit()
        self.plain_desc.setPlaceholderText(
            "Mô tả các nhiệm vụ, yêu cầu kỹ năng và các phúc lợi đặc thù..."
        )
        self.plain_desc.setMinimumHeight(200)
        self.plain_desc.setStyleSheet(
            f"QPlainTextEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
            "border-radius:10px;padding:10px 14px;font-size:14px;"
            f"color:{TXT_H};}}"
            f"QPlainTextEdit:focus{{border-color:{P};}}"
        )
        s3lo.addWidget(self.plain_desc)

        # Expert tip box
        tip_row = QHBoxLayout()
        tip_row.setSpacing(12)
        tip_icon = QLabel("💡")
        tip_icon.setStyleSheet(
            "font-size:18px;background:transparent;border:none;"
        )
        tip_icon.setFixedWidth(28)
        tip_text = QLabel(
            "<b style='color:#92400e;'>Mẹo nhỏ từ chuyên gia</b><br>"
            "<span style='color:#92400e;font-size:12px;'>"
            "Tin tuyển dụng có mô tả rõ ràng về văn hóa công ty thường nhận được "
            "lượng ứng viên chất lượng cao hơn 40%.</span>"
        )
        tip_text.setTextFormat(Qt.RichText)
        tip_text.setWordWrap(True)
        tip_text.setStyleSheet("background:transparent;border:none;")
        tip_row.addWidget(tip_icon, 0, Qt.AlignTop)
        tip_row.addWidget(tip_text, 1)

        tip_box = QFrame()
        tip_box.setStyleSheet(
            "QFrame{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;}"
        )
        tip_box_lo = QHBoxLayout(tip_box)
        tip_box_lo.setContentsMargins(14, 12, 14, 12)
        tip_box_lo.addLayout(tip_row)
        s3lo.addWidget(tip_box)
        outer.addWidget(s3)

        # ── Action bar ──────────────────────────────────────────
        btn_lo = QHBoxLayout()
        btn_lo.setSpacing(12)
        self.btn_draft  = _btn_secondary("💾  Lưu nháp")
        self.btn_submit = _btn_primary("🚀  Đăng tin ngay")
        self.btn_draft.setFixedHeight(50)
        self.btn_submit.setFixedHeight(50)
        self.btn_draft.setMinimumWidth(160)
        self.btn_submit.setMinimumWidth(190)
        self.btn_draft.clicked.connect(lambda: self._create_job(draft=True))
        self.btn_submit.clicked.connect(lambda: self._create_job(draft=False))
        btn_lo.addStretch()
        btn_lo.addWidget(self.btn_draft)
        btn_lo.addWidget(self.btn_submit)
        outer.addLayout(btn_lo)
        outer.addStretch()

        scroll.setWidget(pg)
        return scroll

    # ── PAGE 2: MANAGE JOBS ───────────────────────────────────
    def _build_jobs_page(self) -> QWidget:
        pg = QWidget()
        pg.setStyleSheet(f"background:{CONTENT_BG};")
        outer = QVBoxLayout(pg)
        outer.setContentsMargins(28, 24, 28, 28)
        outer.setSpacing(20)

        # ── Local toolbar: search + action button ────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        # Search bar (with inline clear button)
        search_wrap = QFrame()
        search_wrap.setFixedHeight(42)
        search_wrap.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:1.5px solid {BORDER};"
            "border-radius:21px;}}"
            f"QFrame:focus-within{{border-color:{P};}}"
        )
        sw_lo = QHBoxLayout(search_wrap)
        sw_lo.setContentsMargins(14, 0, 8, 0)
        sw_lo.setSpacing(8)
        s_ic = QLabel()
        s_ic.setPixmap(_svg_pm("ic_search.svg", 16, "#94a3b8"))
        s_ic.setStyleSheet("background:transparent;border:none;")
        self._jobs_search = QLineEdit()
        self._jobs_search.setPlaceholderText(
            "Tìm tiêu đề, vị trí, địa điểm, lương..."
        )
        self._jobs_search.setFrame(False)
        self._jobs_search.setStyleSheet(
            f"background:transparent;border:none;"
            f"font-size:13px;color:{TXT_H};"
        )
        # Clear button inside search bar
        self._jobs_search_clear = QPushButton("×")
        self._jobs_search_clear.setFixedSize(22, 22)
        self._jobs_search_clear.setCursor(Qt.PointingHandCursor)
        self._jobs_search_clear.setVisible(False)
        self._jobs_search_clear.setStyleSheet(
            f"QPushButton{{background:#e2e8f0;color:{TXT_M};"
            "border:none;border-radius:11px;font-size:14px;font-weight:700;}}"
            f"QPushButton:hover{{background:#cbd5e1;color:{TXT_H};}}"
        )
        self._jobs_search_clear.clicked.connect(
            lambda: self._jobs_search.clear()
        )
        self._jobs_search.textChanged.connect(self._on_jobs_search_changed)
        sw_lo.addWidget(s_ic)
        sw_lo.addWidget(self._jobs_search, 1)
        sw_lo.addWidget(self._jobs_search_clear)
        toolbar.addWidget(search_wrap, 1)

        # Status filter combo
        self._jobs_status_filter = _combo(
            ["Tất cả TT", "Hiển thị", "Chờ duyệt", "Nháp", "Từ chối"]
        )
        self._jobs_status_filter.setFixedHeight(42)
        self._jobs_status_filter.setFixedWidth(148)
        self._jobs_status_filter.currentIndexChanged.connect(
            lambda: self._filter_jobs(self._jobs_search.text())
        )
        toolbar.addWidget(self._jobs_status_filter)

        # Job type filter combo
        self._jobs_type_filter = _combo(
            ["Tất cả loại", "Full-time", "Part-time", "Remote", "Hybrid", "Contract"]
        )
        self._jobs_type_filter.setFixedHeight(42)
        self._jobs_type_filter.setFixedWidth(148)
        self._jobs_type_filter.currentIndexChanged.connect(
            lambda: self._filter_jobs(self._jobs_search.text())
        )
        toolbar.addWidget(self._jobs_type_filter)

        # "+ Đăng tin mới" button
        btn_new = _btn_primary("+ Đăng tin mới")
        btn_new.setFixedHeight(42)
        btn_new.setMinimumWidth(150)
        btn_new.clicked.connect(lambda: self._go(1))
        toolbar.addWidget(btn_new)
        outer.addLayout(toolbar)
        outer.addStretch(1)        # đẩy card xuống một chút

        # ── Table card ────────────────────────────────────────
        frame, flo = _card_frame()
        flo.setSpacing(16)

        # Card header
        hdr_row = QHBoxLayout()
        hdr_ic  = QLabel()
        hdr_ic.setPixmap(_svg_pm("ic_doc.svg", 18, P))
        hdr_ic.setStyleSheet("background:transparent;")
        hdr_lbl = QLabel("Tin đăng của bạn")
        hdr_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:16px;font-weight:700;"
            "background:transparent;border:none;"
        )
        self._lbl_job_count = QLabel()
        self._lbl_job_count.setStyleSheet(
            f"background:#ede9fe;color:{P};font-size:11px;"
            "font-weight:700;border-radius:10px;padding:2px 10px;"
        )
        hdr_row.addWidget(hdr_ic)
        hdr_row.addSpacing(8)
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addSpacing(10)
        hdr_row.addWidget(self._lbl_job_count, 0, Qt.AlignVCenter)
        hdr_row.addStretch()
        flo.addLayout(hdr_row)

        # Table
        self.table_jobs = QTableWidget()
        _style_table(self.table_jobs)
        self.table_jobs.verticalHeader().setDefaultSectionSize(54)
        self.table_jobs.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        flo.addWidget(self.table_jobs)

        # "No results" placeholder
        self._jobs_no_result_lbl = QLabel(
            "🔍  Không tìm thấy tin đăng nào khớp với bộ lọc."
        )
        self._jobs_no_result_lbl.setAlignment(Qt.AlignCenter)
        self._jobs_no_result_lbl.setFixedHeight(56)
        self._jobs_no_result_lbl.setStyleSheet(
            f"color:{TXT_M};font-size:13px;background:transparent;border:none;"
        )
        self._jobs_no_result_lbl.setVisible(False)
        flo.addWidget(self._jobs_no_result_lbl)

        # ── Pagination ────────────────────────────────────────
        pag_div = QFrame()
        pag_div.setFrameShape(QFrame.HLine)
        pag_div.setStyleSheet(
            f"background:{BORDER};max-height:1px;border:none;"
        )
        flo.addWidget(pag_div)

        self._jobs_pag_wrap = QWidget()
        self._jobs_pag_wrap.setFixedHeight(44)
        self._jobs_pag_wrap.setStyleSheet("background:transparent;")
        self._jobs_pag_lo = QHBoxLayout(self._jobs_pag_wrap)
        self._jobs_pag_lo.setContentsMargins(4, 4, 4, 4)
        self._jobs_pag_lo.setSpacing(4)
        flo.addWidget(self._jobs_pag_wrap)

        # Pagination state
        self._jobs_page: int = 0
        self._jobs_data: list = []

        # Proportional resizer: Title 58% — Dept 42% of flexible space
        # Fixed cols: ID(60)+Date(112)+Count(90)+Status(136)+Actions(118) = 516
        self._jobs_resizer = _ColResizeFilter(
            self.table_jobs, 1, 2, 0.58, 516
        )

        # Card wraps content — space distributed 1:2 above:below
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        outer.addWidget(frame)
        outer.addStretch(2)
        return pg

    # ── PAGE 3: CANDIDATES ────────────────────────────────────
    def _build_cands_page(self) -> QWidget:
        pg = QWidget()
        pg.setStyleSheet(f"background:{CONTENT_BG};")
        outer = QVBoxLayout(pg)
        outer.setContentsMargins(28, 24, 28, 28)
        outer.setSpacing(20)

        # ── Toolbar: search + status filter ───────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        search_wrap = QFrame()
        search_wrap.setFixedHeight(42)
        search_wrap.setStyleSheet(
            f"QFrame{{background:{CARD_BG};border:1.5px solid {BORDER};"
            "border-radius:21px;}}"
            f"QFrame:focus-within{{border-color:{P};}}"
        )
        sw_lo = QHBoxLayout(search_wrap)
        sw_lo.setContentsMargins(14, 0, 14, 0)
        sw_lo.setSpacing(8)
        s_ic = QLabel()
        s_ic.setPixmap(_svg_pm("ic_search.svg", 16, "#94a3b8"))
        s_ic.setStyleSheet("background:transparent;border:none;")
        self._cands_search = QLineEdit()
        self._cands_search.setPlaceholderText(
            "Tìm kiếm ứng viên, email, vị trí ứng tuyển..."
        )
        self._cands_search.setFrame(False)
        self._cands_search.setStyleSheet(
            f"background:transparent;border:none;"
            f"font-size:13px;color:{TXT_H};"
        )
        self._cands_search.textChanged.connect(self._on_cands_search_changed)

        # Clear button inside cands search bar
        self._cands_search_clear = QPushButton("×")
        self._cands_search_clear.setFixedSize(22, 22)
        self._cands_search_clear.setCursor(Qt.PointingHandCursor)
        self._cands_search_clear.setVisible(False)
        self._cands_search_clear.setStyleSheet(
            f"QPushButton{{background:#e2e8f0;color:{TXT_M};"
            "border:none;border-radius:11px;font-size:14px;font-weight:700;}}"
            f"QPushButton:hover{{background:#cbd5e1;color:{TXT_H};}}"
        )
        self._cands_search_clear.clicked.connect(
            lambda: self._cands_search.clear()
        )
        sw_lo.addWidget(s_ic)
        sw_lo.addWidget(self._cands_search, 1)
        sw_lo.addWidget(self._cands_search_clear)
        toolbar.addWidget(search_wrap, 1)

        # Status filter
        self._cands_status_filter = _combo(
            ["Tất cả trạng thái", "Chờ xét duyệt",
             "Đã xem xét", "Phê duyệt", "Từ chối"]
        )
        self._cands_status_filter.setFixedHeight(42)
        self._cands_status_filter.setFixedWidth(175)
        self._cands_status_filter.currentIndexChanged.connect(
            lambda: self._filter_cands(self._cands_search.text())
        )
        toolbar.addWidget(self._cands_status_filter)

        # Sort combo
        self._cands_sort = _combo(
            ["Mới nhất trước", "Cũ nhất trước", "Tên A→Z", "Tên Z→A"]
        )
        self._cands_sort.setFixedHeight(42)
        self._cands_sort.setFixedWidth(160)
        self._cands_sort.currentIndexChanged.connect(
            lambda: self._filter_cands(self._cands_search.text())
        )
        toolbar.addWidget(self._cands_sort)

        # Reset all filters button
        btn_reset = QPushButton("↺ Xoá bộ lọc")
        btn_reset.setFixedHeight(42)
        btn_reset.setCursor(Qt.PointingHandCursor)
        btn_reset.setStyleSheet(
            f"QPushButton{{background:#f1f5f9;color:{TXT_S};"
            "border:none;border-radius:10px;padding:0 14px;font-size:13px;}}"
            "QPushButton:hover{background:#e2e8f0;}"
        )
        def _reset_cands():
            self._cands_search.clear()
            self._cands_status_filter.setCurrentIndex(0)
            self._cands_sort.setCurrentIndex(0)
        btn_reset.clicked.connect(_reset_cands)
        toolbar.addWidget(btn_reset)

        outer.addLayout(toolbar)
        outer.addStretch(1)        # đẩy card xuống một chút

        # ── Table card ────────────────────────────────────────
        frame, flo = _card_frame()
        flo.setSpacing(16)

        hdr_row = QHBoxLayout()
        hdr_ic = QLabel()
        hdr_ic.setPixmap(_svg_pm("ic_users.svg", 18, "#f59e0b"))
        hdr_ic.setStyleSheet("background:transparent;")
        hdr_lbl = QLabel("Danh sách ứng viên")
        hdr_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:16px;font-weight:700;"
            "background:transparent;border:none;"
        )
        self._lbl_cand_count = QLabel()
        self._lbl_cand_count.setStyleSheet(
            "background:#fef3c7;color:#d97706;font-size:11px;"
            "font-weight:700;border-radius:10px;padding:2px 10px;"
        )
        hdr_row.addWidget(hdr_ic)
        hdr_row.addSpacing(8)
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addSpacing(10)
        hdr_row.addWidget(self._lbl_cand_count, 0, Qt.AlignVCenter)
        hdr_row.addStretch()
        flo.addLayout(hdr_row)

        self.table_cands = QTableWidget()
        _style_table(self.table_cands)
        self.table_cands.verticalHeader().setDefaultSectionSize(62)
        self.table_cands.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        flo.addWidget(self.table_cands)

        # "No results" placeholder
        self._cands_no_result_lbl = QLabel(
            "🔍  Không tìm thấy ứng viên nào khớp với bộ lọc."
        )
        self._cands_no_result_lbl.setAlignment(Qt.AlignCenter)
        self._cands_no_result_lbl.setFixedHeight(56)
        self._cands_no_result_lbl.setStyleSheet(
            f"color:{TXT_M};font-size:13px;background:transparent;border:none;"
        )
        self._cands_no_result_lbl.setVisible(False)
        flo.addWidget(self._cands_no_result_lbl)

        # Proportional resizer: Ứng viên 36% — Vị trí 64% of flexible space
        # Fixed cols: Date(140)+Status(136)+Actions(120) = 396
        self._cands_resizer = _ColResizeFilter(
            self.table_cands, 0, 1, 0.36, 396
        )

        # ── Pagination bar ─────────────────────────────────────
        self._cands_page_wrap = QWidget()
        self._cands_page_wrap.setStyleSheet("background:transparent;")
        self._pg_lo = QHBoxLayout(self._cands_page_wrap)
        self._pg_lo.setContentsMargins(0, 4, 0, 0)
        self._pg_lo.setSpacing(6)
        self._cands_page_wrap.setVisible(False)
        flo.addWidget(self._cands_page_wrap)

        # Pagination state
        self._cands_page: int = 0
        self._cands_data: list = []

        # Card wraps content — space distributed 1:2 above:below
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        outer.addWidget(frame)
        outer.addStretch(2)
        return pg

    # ── navigation ────────────────────────────────────────────
    def _go(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == idx)

        titles = [
            "Bảng điều khiển",
            "Đăng tin mới",
            "Quản lý tin đăng",
            "Đơn ứng tuyển",
        ]
        subs = [
            "Theo dõi hiệu quả tuyển dụng của bạn",
            "Tạo tin tuyển dụng mới cho ứng viên",
            "Xem và chỉnh sửa các tin tuyển dụng đang hoạt động",
            "Quản lý các ứng viên đã ứng tuyển",
        ]
        self.lbl_page_title.setText(titles[idx])
        self.lbl_page_sub.setText(subs[idx])

        if idx == 0:
            self._load_dash()
        elif idx == 2:
            self._fill_jobs_table()
        elif idx == 3:
            self._fill_cands_table()

    # ── job actions ───────────────────────────────────────────
    def _create_job(self, draft: bool) -> None:
        title = self.line_title.text().strip()
        if not title:
            QMessageBox.warning(self.win, "Cảnh báo",
                                "Vui lòng nhập tiêu đề công việc.")
            return

        # Collect all form fields
        level    = self.combo_level.currentText()
        job_type = self.combo_type.currentText()
        salary   = self.line_salary.text().strip()
        location = self.line_location.text().strip()
        count    = self.line_count.text().strip() or "1"
        deadline = self.line_deadline.text().strip()
        desc     = self.plain_desc.toPlainText().strip()

        mock_data.add_job(
            title=title,
            company_name="TechCorp Vietnam",   # current HR company
            department="Kỹ thuật & Công nghệ",
            location=location or "Hà Nội",
            salary_text=salary or "Thương lượng",
            job_type=job_type,
            level=level,
            count=count,
            deadline=deadline,
            description=desc,
            hr_id=1,
            draft=draft,
        )

        # Clear form
        self.line_title.clear()
        self.line_salary.clear()
        self.line_location.clear()
        self.line_count.clear()
        self.line_deadline.clear()
        self.plain_desc.clear()

        msg = ("Đã lưu bản nháp thành công!" if draft
               else "Tin đã gửi Admin duyệt thành công!")
        QMessageBox.information(self.win, "Thành công", msg)
        self._go(2)

    # ── fill tables ───────────────────────────────────────────
    _JOB_STATUS = {
        "published":        ("Đang tuyển",  "#059669", "#d1fae5"),
        "draft":            ("Bản nháp",    "#d97706", "#fef3c7"),
        "closed":           ("Đã đóng",     "#dc2626", "#fee2e2"),
        "pending_approval": ("Chờ duyệt",   "#2563eb", "#dbeafe"),
        "rejected":         ("Vi phạm",     "#ef4444", "#fee2e2"),
    }

    _CAND_STATUS = {
        "pending":  ("Chờ xét duyệt", "#d97706", "#fef3c7"),
        "reviewed": ("Đã xem xét",    "#2563eb", "#dbeafe"),
        "approved": ("Phê duyệt",     "#059669", "#d1fae5"),
        "rejected": ("Từ chối",       "#dc2626", "#fee2e2"),
    }

    def _fill_jobs_table(self) -> None:
        self._jobs_data = mock_data.get_hr_jobs()
        self._jobs_page = 0
        self._render_jobs_page()

    def _on_jobs_search_changed(self, text: str) -> None:
        """Show/hide clear button + trigger filter."""
        self._jobs_search_clear.setVisible(bool(text))
        self._filter_jobs(text)

    def _filter_jobs(self, text: str) -> None:
        kw = text.strip().lower()
        all_jobs = mock_data.get_hr_jobs()

        # ── Status filter ────────────────────────────────────
        _STATUS_MAP = {
            0: None,
            1: "published",
            2: "pending_approval",
            3: "draft",
            4: "rejected",
        }
        status_filter = _STATUS_MAP.get(
            self._jobs_status_filter.currentIndex()
        )

        # ── Job type filter ──────────────────────────────────
        type_idx = self._jobs_type_filter.currentIndex()
        type_options = [None, "Full-time", "Part-time", "Remote", "Hybrid", "Contract"]
        type_filter = type_options[type_idx] if type_idx < len(type_options) else None

        # ── Text search (broad: title, dept, company, location,
        #    job_type, level, salary, description) ─────────────
        if kw:
            all_jobs = [j for j in all_jobs
                        if kw in j.get("title",        "").lower()
                        or kw in j.get("department",   "").lower()
                        or kw in j.get("company_name", "").lower()
                        or kw in j.get("location",     "").lower()
                        or kw in j.get("job_type",     "").lower()
                        or kw in j.get("level",        "").lower()
                        or kw in j.get("salary_text",  "").lower()
                        or kw in j.get("description",  "").lower()]

        if status_filter:
            all_jobs = [j for j in all_jobs
                        if j.get("status") == status_filter]

        if type_filter:
            all_jobs = [j for j in all_jobs
                        if j.get("job_type") == type_filter]

        self._jobs_data = all_jobs
        self._jobs_page = 0
        self._render_jobs_page()

        # Show "no results" hint if empty
        self._jobs_no_result_lbl.setVisible(len(all_jobs) == 0)

    def _render_jobs_page(self) -> None:
        """Slice data by current page and render table + pagination bar."""
        total   = len(self._jobs_data)
        n_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        self._jobs_page = max(0, min(self._jobs_page, n_pages - 1))
        start   = self._jobs_page * _PAGE_SIZE
        self._render_jobs(self._jobs_data[start: start + _PAGE_SIZE])
        # Badge shows TOTAL filtered count
        self._lbl_job_count.setText(f"  {total} tin  ")
        self._update_jobs_pag(n_pages, total)

    def _go_jobs_page(self, n: int) -> None:
        self._jobs_page = n
        self._render_jobs_page()

    def _update_jobs_pag(self, n_pages: int, total: int) -> None:
        """Rebuild pagination bar below the jobs table."""
        lo = self._jobs_pag_lo
        while lo.count():
            it = lo.takeAt(0)
            if w := it.widget():
                w.deleteLater()

        if n_pages <= 1:
            self._jobs_pag_wrap.setVisible(False)
            return
        self._jobs_pag_wrap.setVisible(True)

        s = self._jobs_page * _PAGE_SIZE + 1
        e = min((self._jobs_page + 1) * _PAGE_SIZE, total)
        info = QLabel(f"Hiển thị {s}–{e} trong {total} tin")
        info.setStyleSheet(
            f"color:{TXT_M};font-size:12px;"
            "background:transparent;border:none;"
        )
        lo.addWidget(info)
        lo.addStretch()

        btn_prev = _pag_btn("‹", enabled=(self._jobs_page > 0))
        if self._jobs_page > 0:
            btn_prev.clicked.connect(
                lambda: self._go_jobs_page(self._jobs_page - 1)
            )
        lo.addWidget(btn_prev)

        for i in range(n_pages):
            pb = _pag_btn(str(i + 1), active=(i == self._jobs_page))
            if i != self._jobs_page:
                pb.clicked.connect(
                    lambda _=False, idx=i: self._go_jobs_page(idx)
                )
            lo.addWidget(pb)

        btn_next = _pag_btn("›", enabled=(self._jobs_page < n_pages - 1))
        if self._jobs_page < n_pages - 1:
            btn_next.clicked.connect(
                lambda: self._go_jobs_page(self._jobs_page + 1)
            )
        lo.addWidget(btn_next)

    def _render_jobs(self, jobs: list) -> None:
        COLS = ["ID", "Tiêu đề công việc", "Phòng ban",
                "Ngày đăng", "Ứng tuyển", "Trạng thái", "Thao tác"]
        tbl  = self.table_jobs
        tbl.setColumnCount(len(COLS))
        tbl.setHorizontalHeaderLabels(COLS)
        tbl.setRowCount(len(jobs))

        for row, j in enumerate(jobs):
            # ── ID ───────────────────────────────────────────
            id_item = QTableWidgetItem(f"#{j['id']}")
            id_item.setTextAlignment(Qt.AlignCenter)
            id_item.setForeground(QColor(TXT_M))
            tbl.setItem(row, 0, id_item)

            # ── Title ────────────────────────────────────────
            t = QTableWidgetItem(j.get("title", ""))
            t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            t.setForeground(QColor(TXT_H))
            tbl.setItem(row, 1, t)

            # ── Department ───────────────────────────────────
            dept = QTableWidgetItem(j.get("department", "—"))
            dept.setForeground(QColor(TXT_S))
            tbl.setItem(row, 2, dept)

            # ── Date ─────────────────────────────────────────
            dt = QTableWidgetItem(j.get("created_at", "—"))
            dt.setTextAlignment(Qt.AlignCenter)
            dt.setForeground(QColor(TXT_M))
            tbl.setItem(row, 3, dt)

            # ── Applicants count ─────────────────────────────
            cnt = j.get("applicants_count", 0)
            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            cnt_item.setForeground(
                QColor(P) if cnt > 0 else QColor(TXT_M)
            )
            if cnt > 0:
                cnt_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tbl.setItem(row, 4, cnt_item)

            # ── Status badge ─────────────────────────────────
            st = j.get("status", "draft")
            txt, fg, bg_c = self._JOB_STATUS.get(
                st, (st, "#64748b", "#f1f5f9")
            )
            badge_wrap = QWidget()
            badge_wrap.setStyleSheet("background:transparent;")
            bw_lo = QHBoxLayout(badge_wrap)
            bw_lo.setContentsMargins(8, 0, 8, 0)
            bw_lo.setAlignment(Qt.AlignCenter)
            badge = QLabel(txt)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedHeight(26)
            badge.setMinimumWidth(90)
            badge.setStyleSheet(
                f"background:{bg_c};color:{fg};"
                "font-size:12px;font-weight:700;"
                "border-radius:13px;padding:0 12px;"
            )
            bw_lo.addWidget(badge)
            tbl.setCellWidget(row, 5, badge_wrap)

            # ── Action buttons ───────────────────────────────
            tbl.setCellWidget(row, 6, self._make_job_actions(j["id"]))

        hh = tbl.horizontalHeader()
        # Cols 1+2 managed proportionally by _jobs_resizer (58 : 42)
        hh.setSectionResizeMode(0, QHeaderView.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Interactive)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        hh.setSectionResizeMode(6, QHeaderView.Fixed)
        tbl.setColumnWidth(0, 60)
        tbl.setColumnWidth(3, 112)
        tbl.setColumnWidth(4, 90)
        tbl.setColumnWidth(5, 136)
        tbl.setColumnWidth(6, 118)
        # Fix height to exactly fit rows — no empty space
        tbl.setFixedHeight(44 + len(jobs) * 54 + 2)
        self._jobs_resizer._apply()   # set proportional widths immediately

    def _make_job_actions(self, job_id: int) -> QWidget:
        """Three icon-only action buttons per row with tooltip labels + toasts."""
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(wrap)
        lo.setContentsMargins(8, 0, 8, 0)
        lo.setSpacing(6)
        lo.setAlignment(Qt.AlignVCenter)

        def _ic_btn(svg: str, color: str, hover_bg: str,
                    tooltip: str) -> QPushButton:
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setIcon(QIcon(_svg_pm(svg, 16, color)))
            btn.setIconSize(QSize(16, 16))
            btn.setStyleSheet(
                "QPushButton{"
                f"background:transparent;border:1.5px solid {BORDER};"
                "border-radius:8px;}"
                f"QPushButton:hover{{background:{hover_bg};"
                f"border-color:{color};}}"
                "QPushButton:pressed{"
                "opacity:0.7;}"
            )
            return btn

        btn_edit = _ic_btn("ic_edit.svg",   "#6366f1", "#ede9fe", "✏️ Chỉnh sửa tin")
        btn_view = _ic_btn("ic_view.svg",   "#0ea5e9", "#e0f2fe", "👁️ Xem chi tiết")
        btn_del  = _ic_btn("ic_delete.svg", "#ef4444", "#fee2e2", "🗑️ Xoá tin")

        # ── Edit dialog ──────────────────────────────────────────
        def _do_edit(_jid=job_id):
            job = next((j for j in mock_data.JOB_STORE if j["id"] == _jid), None)
            if not job:
                self._show_toast("Không tìm thấy tin đăng!", "❌", "#ef4444")
                return

            dlg = QDialog(self.win)
            dlg.setWindowTitle(f"✏️ Chỉnh sửa tin — #{_jid}")
            dlg.setMinimumWidth(540)
            dlg.setStyleSheet(
                f"QDialog{{background:{CONTENT_BG};border-radius:12px;}}"
                f"QLabel{{color:{TXT_H};background:transparent;border:none;}}"
                "QLineEdit,QComboBox,QPlainTextEdit{"
                f"background:#ffffff;border:1.5px solid {BORDER};"
                "border-radius:8px;padding:6px 10px;"
                f"color:{TXT_H};font-size:13px;}}"
                "QLineEdit:focus,QComboBox:focus,QPlainTextEdit:focus{"
                f"border-color:{P};}}"
            )
            vlo = QVBoxLayout(dlg)
            vlo.setContentsMargins(24, 20, 24, 20)
            vlo.setSpacing(16)

            # Header
            h_lbl = QLabel(f"✏️  Chỉnh sửa tin đăng  #{_jid}")
            h_lbl.setStyleSheet(
                f"color:{TXT_H};font-size:16px;font-weight:700;"
                f"background:transparent;border:none;padding-bottom:8px;"
            )
            vlo.addWidget(h_lbl)

            # Divider
            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER};border:none;")
            vlo.addWidget(div)

            # Form grid
            grid = QGridLayout()
            grid.setHorizontalSpacing(16)
            grid.setVerticalSpacing(10)

            def _lbl(t):
                l = QLabel(t)
                l.setStyleSheet(
                    f"color:{TXT_S};font-size:12px;font-weight:600;"
                    "background:transparent;border:none;"
                )
                return l

            # Row 0: title
            grid.addWidget(_lbl("Tiêu đề *"), 0, 0, 1, 2)
            e_title = QLineEdit(job.get("title", ""))
            e_title.setPlaceholderText("Tiêu đề vị trí tuyển dụng")
            grid.addWidget(e_title, 1, 0, 1, 2)

            # Row 2: level | job_type
            grid.addWidget(_lbl("Cấp độ"), 2, 0)
            grid.addWidget(_lbl("Loại hình"), 2, 1)
            c_level = QComboBox()
            c_level.addItems(["Intern", "Junior", "Mid", "Senior", "Lead", "Manager"])
            cur_lv = job.get("level", "")
            idx = c_level.findText(cur_lv)
            if idx >= 0: c_level.setCurrentIndex(idx)
            c_type = QComboBox()
            c_type.addItems(["Full-time", "Part-time", "Remote", "Hybrid", "Contract"])
            cur_jt = job.get("job_type", "")
            idx2 = c_type.findText(cur_jt)
            if idx2 >= 0: c_type.setCurrentIndex(idx2)
            grid.addWidget(c_level, 3, 0)
            grid.addWidget(c_type, 3, 1)

            # Row 4: salary | location
            grid.addWidget(_lbl("Mức lương"), 4, 0)
            grid.addWidget(_lbl("Địa điểm"), 4, 1)
            e_sal = QLineEdit(job.get("salary_text", ""))
            e_sal.setPlaceholderText("VD: 15–25 triệu")
            e_loc = QLineEdit(job.get("location", ""))
            e_loc.setPlaceholderText("Hà Nội, TP.HCM…")
            grid.addWidget(e_sal, 5, 0)
            grid.addWidget(e_loc, 5, 1)

            # Row 6: count | deadline
            grid.addWidget(_lbl("Số lượng"), 6, 0)
            grid.addWidget(_lbl("Hạn nộp"), 6, 1)
            e_count = QLineEdit(str(job.get("count", 1)))
            e_count.setPlaceholderText("1")
            e_dead = QLineEdit(job.get("deadline", ""))
            e_dead.setPlaceholderText("DD/MM/YYYY")
            grid.addWidget(e_count, 7, 0)
            grid.addWidget(e_dead, 7, 1)

            # Row 8: description
            grid.addWidget(_lbl("Mô tả công việc"), 8, 0, 1, 2)
            e_desc = QPlainTextEdit(job.get("description", ""))
            e_desc.setFixedHeight(100)
            e_desc.setPlaceholderText("Mô tả chi tiết vị trí tuyển dụng…")
            grid.addWidget(e_desc, 9, 0, 1, 2)

            vlo.addLayout(grid)

            # Button row
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_cancel = QPushButton("Huỷ")
            btn_cancel.setFixedHeight(36)
            btn_cancel.setStyleSheet(
                f"QPushButton{{background:#f1f5f9;color:{TXT_S};"
                "border:none;border-radius:8px;padding:0 20px;font-size:13px;}}"
                "QPushButton:hover{background:#e2e8f0;}"
            )
            btn_save = QPushButton("💾  Lưu thay đổi")
            btn_save.setFixedHeight(36)
            btn_save.setStyleSheet(
                f"QPushButton{{background:{P};color:#ffffff;"
                "border:none;border-radius:8px;padding:0 20px;font-size:13px;font-weight:600;}}"
                f"QPushButton:hover{{background:{P_DARK};}}"
            )
            btn_cancel.clicked.connect(dlg.reject)
            btn_row.addWidget(btn_cancel)
            btn_row.addSpacing(8)
            btn_row.addWidget(btn_save)
            vlo.addLayout(btn_row)

            def _save():
                # Apply changes back to JOB_STORE
                for j in mock_data.JOB_STORE:
                    if j["id"] == _jid:
                        j["title"]       = e_title.text().strip() or j["title"]
                        j["level"]       = c_level.currentText()
                        j["job_type"]    = c_type.currentText()
                        j["salary_text"] = e_sal.text().strip() or j["salary_text"]
                        j["location"]    = e_loc.text().strip() or j["location"]
                        try:   j["count"] = int(e_count.text())
                        except ValueError: pass
                        j["deadline"]    = e_dead.text().strip() or j["deadline"]
                        j["description"] = e_desc.toPlainText().strip() or j["description"]
                        break
                dlg.accept()
                self._fill_jobs_table()
                _saved_title = e_title.text().strip()
                self._show_toast(
                    f'Đã lưu thay đổi tin \u201c{_saved_title}\u201d',
                    "✅", "#10b981"
                )

            btn_save.clicked.connect(_save)
            dlg.exec()

        # ── View dialog ──────────────────────────────────────────
        def _do_view(_jid=job_id):
            job = next((j for j in mock_data.JOB_STORE if j["id"] == _jid), None)
            if not job:
                self._show_toast("Không tìm thấy tin đăng!", "❌", "#ef4444")
                return

            dlg = QDialog(self.win)
            dlg.setWindowTitle(f"👁️ Chi tiết tin — #{_jid}")
            dlg.setMinimumWidth(480)
            dlg.setStyleSheet(
                f"QDialog{{background:{CONTENT_BG};}}"
                f"QLabel{{color:{TXT_H};background:transparent;border:none;}}"
            )
            vlo = QVBoxLayout(dlg)
            vlo.setContentsMargins(24, 20, 24, 20)
            vlo.setSpacing(12)

            # Title
            t = QLabel(job.get("title", "—"))
            t.setStyleSheet(
                f"color:{TXT_H};font-size:18px;font-weight:700;"
                "background:transparent;border:none;"
            )
            vlo.addWidget(t)

            c = QLabel(f"🏢  {job.get('company_name','—')}  ·  {job.get('department','—')}")
            c.setStyleSheet(f"color:{TXT_M};font-size:13px;background:transparent;border:none;")
            vlo.addWidget(c)

            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER};border:none;margin:4px 0;")
            vlo.addWidget(div)

            STATUS_COLORS = {
                "published":        ("#d1fae5", "#059669"),
                "pending_approval": ("#fef3c7", "#d97706"),
                "draft":            ("#f1f5f9", "#64748b"),
                "rejected":         ("#fee2e2", "#dc2626"),
            }
            st = job.get("status", "")
            st_bg, st_fg = STATUS_COLORS.get(st, ("#f1f5f9", "#64748b"))
            st_lbl = QLabel(st.replace("_", " ").title())
            st_lbl.setFixedHeight(24)
            st_lbl.setStyleSheet(
                f"background:{st_bg};color:{st_fg};"
                "border-radius:10px;padding:0 10px;"
                "font-size:11px;font-weight:700;border:none;"
            )

            # Info chips row
            chips_row = QHBoxLayout()
            chips_row.setSpacing(8)
            chips_row.addWidget(st_lbl)
            chips_row.addStretch()
            vlo.addLayout(chips_row)

            # Details grid
            fields = [
                ("📍 Địa điểm",   job.get("location",    "—")),
                ("💰 Lương",       job.get("salary_text", "—")),
                ("🧑‍💼 Cấp độ",     job.get("level",       "—")),
                ("🕐 Loại hình",   job.get("job_type",    "—")),
                ("👥 Số lượng",    str(job.get("count",   "—"))),
                ("📅 Hạn nộp",     job.get("deadline",    "—")),
                ("📊 Ứng viên",    str(job.get("applicants_count", 0))),
                ("🗓️ Đăng ngày",   job.get("created_at",  "—")),
            ]
            grid = QGridLayout()
            grid.setHorizontalSpacing(20)
            grid.setVerticalSpacing(6)
            for i, (k, v) in enumerate(fields):
                r, c2 = divmod(i, 2)
                key_l = QLabel(k)
                key_l.setStyleSheet(
                    f"color:{TXT_M};font-size:12px;background:transparent;border:none;"
                )
                val_l = QLabel(f"<b>{v}</b>")
                val_l.setTextFormat(Qt.RichText)
                val_l.setStyleSheet(
                    f"color:{TXT_H};font-size:13px;background:transparent;border:none;"
                )
                sub = QVBoxLayout()
                sub.setSpacing(2)
                sub.addWidget(key_l)
                sub.addWidget(val_l)
                grid.addLayout(sub, r, c2)
            vlo.addLayout(grid)

            # Description
            desc_hdr = QLabel("📄  Mô tả")
            desc_hdr.setStyleSheet(
                f"color:{TXT_S};font-size:12px;font-weight:700;"
                "background:transparent;border:none;margin-top:8px;"
            )
            vlo.addWidget(desc_hdr)
            desc_txt = QLabel(job.get("description", "—")[:400] + ("…" if len(job.get("description","")) > 400 else ""))
            desc_txt.setWordWrap(True)
            desc_txt.setStyleSheet(
                f"color:{TXT_S};font-size:12px;background:#f8fafc;"
                "border-radius:8px;padding:10px;border:none;"
            )
            vlo.addWidget(desc_txt)

            # Close btn
            close_btn = QPushButton("Đóng")
            close_btn.setFixedHeight(36)
            close_btn.setStyleSheet(
                f"QPushButton{{background:{P};color:#ffffff;"
                "border:none;border-radius:8px;padding:0 24px;"
                "font-size:13px;font-weight:600;}}"
                f"QPushButton:hover{{background:{P_DARK};}}"
            )
            close_btn.clicked.connect(dlg.accept)
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_row.addWidget(close_btn)
            vlo.addLayout(btn_row)

            dlg.exec()
            _vt = job.get('title', '')
            self._show_toast(
                f'\u201c{_vt}\u201d \u2014 \u0111\u00e3 xem chi ti\u1ebft',
                "👁️", "#0ea5e9"
            )

        # ── Delete ───────────────────────────────────────────────
        def _do_delete(_jid=job_id):
            job = next((j for j in mock_data.JOB_STORE if j["id"] == _jid), None)
            job_title = job.get("title", f"#{_jid}") if job else f"#{_jid}"
            ret = QMessageBox.question(
                self.win, "🗑️  Xác nhận xoá",
                f"Bạn có chắc muốn xoá tin:\n\"{job_title}\"?\n\nThao tác này không thể hoàn tác.",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.Yes:
                mock_data.delete_job(_jid)
                self._fill_jobs_table()
                self._show_toast(
                    f'Đã xo\u00e1 tin \u201c{job_title}\u201d',
                    "🗑️", "#ef4444"
                )

        btn_edit.clicked.connect(_do_edit)
        btn_view.clicked.connect(_do_view)
        btn_del.clicked.connect(_do_delete)

        lo.addWidget(btn_edit)
        lo.addWidget(btn_view)
        lo.addWidget(btn_del)
        lo.addStretch()
        return wrap

    def _all_applications(self) -> list:
        """Kết hợp đơn mới từ candidate + mock cũ (mới nhất lên đầu)."""
        return list(mock_data.CANDIDATE_APPLICATIONS) + list(mock_data.MOCK_HR_APPLICATIONS)

    def _fill_cands_table(self) -> None:
        self._cands_page = 0
        self._render_cands(self._all_applications())

    def _on_cands_search_changed(self, text: str) -> None:
        """Show/hide clear button + trigger filter."""
        self._cands_search_clear.setVisible(bool(text))
        self._filter_cands(text)

    def _filter_cands(self, text: str) -> None:
        kw = text.strip().lower()
        st_map = {
            0: None, 1: "pending", 2: "reviewed",
            3: "approved", 4: "rejected",
        }
        status_filter = st_map.get(
            self._cands_status_filter.currentIndex()
        )
        data = self._all_applications()

        # ── Text search (name, email, job title, company) ─────
        if kw:
            data = [a for a in data
                    if kw in a.get("candidate_name",  "").lower()
                    or kw in a.get("candidate_email", "").lower()
                    or kw in a.get("job_title",       "").lower()
                    or kw in a.get("company",         "").lower()
                    or kw in a.get("location",        "").lower()]

        # ── Status filter ─────────────────────────────────────
        if status_filter:
            data = [a for a in data
                    if a.get("status") == status_filter]

        # ── Sort ──────────────────────────────────────────────
        sort_idx = self._cands_sort.currentIndex()
        if sort_idx == 0:   # Mới nhất trước (default order, already newest first)
            pass
        elif sort_idx == 1: # Cũ nhất trước
            data = list(reversed(data))
        elif sort_idx == 2: # Tên A→Z
            data = sorted(data, key=lambda a: a.get("candidate_name", "").lower())
        elif sort_idx == 3: # Tên Z→A
            data = sorted(data, key=lambda a: a.get("candidate_name", "").lower(),
                          reverse=True)

        self._cands_page = 0
        self._render_cands(data)

        # Show "no results" hint if empty
        self._cands_no_result_lbl.setVisible(len(data) == 0)

    def _render_cands(self, apps: list) -> None:
        # ── Store full data + paginate ────────────────────────
        self._cands_data = apps
        total   = len(apps)
        n_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        self._cands_page = max(0, min(self._cands_page, n_pages - 1))
        start   = self._cands_page * _PAGE_SIZE
        page_apps = apps[start: start + _PAGE_SIZE]

        COLS = ["Ứng viên", "Vị trí ứng tuyển",
                "Ngày ứng tuyển", "Trạng thái", "Thao tác"]
        tbl = self.table_cands
        tbl.setColumnCount(len(COLS))
        tbl.setHorizontalHeaderLabels(COLS)
        tbl.setRowCount(len(page_apps))

        self._lbl_cand_count.setText(f"  {total} ứng viên  ")

        for row, a in enumerate(page_apps):
            # Col 0: Avatar + name + email
            tbl.setCellWidget(
                row, 0,
                self._make_cand_info(
                    a.get("candidate_name", ""),
                    a.get("candidate_email", ""),
                )
            )

            # Col 1: Job title
            jt = QTableWidgetItem(a.get("job_title", ""))
            jt.setForeground(QColor(TXT_S))
            tbl.setItem(row, 1, jt)

            # Col 2: Applied date
            dt = QTableWidgetItem(a.get("applied_at", "—"))
            dt.setTextAlignment(Qt.AlignCenter)
            dt.setForeground(QColor(TXT_M))
            tbl.setItem(row, 2, dt)

            # Col 3: Status pill
            st = a.get("status", "pending")
            txt, fg, bg_c = self._CAND_STATUS.get(
                st, (st, "#64748b", "#f1f5f9")
            )
            badge_wrap = QWidget()
            badge_wrap.setStyleSheet("background:transparent;")
            bw_lo = QHBoxLayout(badge_wrap)
            bw_lo.setContentsMargins(8, 0, 8, 0)
            bw_lo.setAlignment(Qt.AlignCenter)
            badge = QLabel(txt)
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedHeight(26)
            badge.setMinimumWidth(100)
            badge.setStyleSheet(
                f"background:{bg_c};color:{fg};"
                "font-size:12px;font-weight:700;"
                "border-radius:13px;padding:0 12px;"
            )
            bw_lo.addWidget(badge)
            tbl.setCellWidget(row, 3, badge_wrap)

            # Col 4: Action buttons
            tbl.setCellWidget(
                row, 4,
                self._make_cand_actions(
                    a["application_id"],
                    a.get("cv_name", ""),
                )
            )

        hh = tbl.horizontalHeader()
        # Cols 0+1 managed proportionally by _cands_resizer (36 : 64)
        hh.setSectionResizeMode(0, QHeaderView.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        tbl.setColumnWidth(2, 140)
        tbl.setColumnWidth(3, 136)
        tbl.setColumnWidth(4, 120)
        # Fix height to exactly fit rows — no empty space
        tbl.setFixedHeight(44 + len(page_apps) * 62 + 2)
        self._cands_resizer._apply()

        self._update_cands_pagination(n_pages, total)

    def _make_cand_info(self, name: str, email: str) -> QWidget:
        """Colored avatar circle + name + email stacked."""
        _PALETTE = [
            ("#6366f1", "#fff"), ("#f59e0b", "#fff"), ("#10b981", "#fff"),
            ("#0ea5e9", "#fff"), ("#ec4899", "#fff"), ("#8b5cf6", "#fff"),
            ("#ef4444", "#fff"), ("#14b8a6", "#fff"),
        ]
        idx = sum(ord(c) for c in name) % len(_PALETTE)
        av_bg, av_fg = _PALETTE[idx]
        initials = "".join(p[0].upper() for p in name.split()[:2]) if name else "?"

        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(wrap)
        lo.setContentsMargins(12, 6, 8, 6)
        lo.setSpacing(12)
        lo.setAlignment(Qt.AlignVCenter)

        ava = QLabel(initials)
        ava.setFixedSize(38, 38)
        ava.setAlignment(Qt.AlignCenter)
        ava.setStyleSheet(
            f"background:{av_bg};color:{av_fg};"
            "border-radius:19px;font-size:13px;font-weight:700;"
            "border:none;"
        )

        txt_col = QVBoxLayout()
        txt_col.setSpacing(2)
        txt_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:13px;font-weight:700;"
            "background:transparent;border:none;"
        )
        email_lbl = QLabel(email)
        email_lbl.setStyleSheet(
            f"color:{TXT_M};font-size:11px;font-weight:400;"
            "background:transparent;border:none;"
        )
        txt_col.addWidget(name_lbl)
        txt_col.addWidget(email_lbl)

        lo.addWidget(ava)
        lo.addLayout(txt_col, 1)
        return wrap

    def _make_cand_actions(self, app_id: int, cv_name: str) -> QWidget:
        """Three icon-only action buttons: view CV / approve / reject."""
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(wrap)
        lo.setContentsMargins(8, 0, 8, 0)
        lo.setSpacing(6)
        lo.setAlignment(Qt.AlignVCenter)

        def _ic_btn(svg: str, color: str,
                    hover_bg: str, tooltip: str) -> QPushButton:
            btn = QPushButton()
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setIcon(QIcon(_svg_pm(svg, 16, color)))
            btn.setIconSize(QSize(16, 16))
            btn.setStyleSheet(
                "QPushButton{"
                f"background:transparent;border:1.5px solid {BORDER};"
                "border-radius:8px;}"
                f"QPushButton:hover{{background:{hover_bg};"
                f"border-color:{color};}}"
            )
            return btn

        btn_cv  = _ic_btn("ic_view.svg",   "#0ea5e9", "#e0f2fe", f"Xem CV: {cv_name}")
        btn_ok  = _ic_btn("ic_edit.svg",   "#10b981", "#d1fae5", "Phê duyệt")
        btn_rej = _ic_btn("ic_delete.svg", "#ef4444", "#fee2e2", "Từ chối")

        btn_cv.clicked.connect(
            lambda _=False, _aid=app_id: self._hr_set_status(_aid, "reviewed")
        )
        btn_ok.clicked.connect(
            lambda _=False, _aid=app_id: self._hr_set_status(_aid, "approved")
        )
        btn_rej.clicked.connect(
            lambda _=False, _aid=app_id: self._hr_set_status(_aid, "rejected")
        )

        lo.addWidget(btn_cv)
        lo.addWidget(btn_ok)
        lo.addWidget(btn_rej)
        lo.addStretch()
        return wrap

    # ── Status update (approve / reject / review) ─────────────
    _STATUS_LABEL_VI: dict[str, str] = {
        "reviewed": "Đã xem",
        "approved": "Phê duyệt",
        "rejected": "Từ chối",
    }
    _STATUS_CONFIRM: dict[str, str] = {
        "reviewed": "Đánh dấu đã xem xét đơn #{id}?",
        "approved": "Phê duyệt đơn ứng tuyển #{id}?",
        "rejected": "Từ chối đơn ứng tuyển #{id}?",
    }

    def _hr_set_status(self, app_id: int, new_status: str) -> None:
        """Cập nhật trạng thái đơn, refresh bảng, hiện thông báo."""
        label_vi = self._STATUS_LABEL_VI.get(new_status, new_status)
        confirm_msg = self._STATUS_CONFIRM.get(
            new_status, "Xác nhận thay đổi trạng thái?"
        ).replace("{id}", str(app_id))

        reply = QMessageBox.question(
            self.win, "Xác nhận", confirm_msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok = mock_data.update_application_status(app_id, new_status)
        if ok:
            _TOAST = {
                "reviewed": ("👁️",  "#0ea5e9", f"Đã đánh dấu xem xét đơn #{app_id}"),
                "approved": ("✅",  "#10b981", f"Đã phê duyệt đơn ứng tuyển #{app_id}"),
                "rejected": ("❌",  "#ef4444", f"Đã từ chối đơn ứng tuyển #{app_id}"),
            }
            ic, col, msg = _TOAST.get(new_status, ("ℹ️", "#6366f1", f"Cập nhật → {label_vi}"))
            self._show_toast(msg, ic, col)
        else:
            self._show_toast(f"Không tìm thấy đơn #{app_id}", "❌", "#ef4444")
        # Refresh table với dữ liệu mới nhất
        self._fill_cands_table()

    # ── pagination ────────────────────────────────────────────
    def _update_cands_pagination(self, n_pages: int, total: int) -> None:
        """Rebuild the pagination bar below the candidates table."""
        # Clear old widgets
        while self._pg_lo.count():
            it = self._pg_lo.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        if n_pages <= 1:
            self._cands_page_wrap.setVisible(False)
            return

        self._cands_page_wrap.setVisible(True)

        # ── Info label (left) ─────────────────────────────────
        s = self._cands_page * _PAGE_SIZE + 1
        e = min((self._cands_page + 1) * _PAGE_SIZE, total)
        info = QLabel(f"Hiển thị {s}–{e} trong {total} ứng viên")
        info.setStyleSheet(
            f"color:{TXT_M};font-size:12px;"
            "background:transparent;border:none;"
        )
        self._pg_lo.addWidget(info)
        self._pg_lo.addStretch()

        # ── Helper ────────────────────────────────────────────
        def _pg_btn(label: str, active: bool = False,
                    enabled: bool = True) -> QPushButton:
            b = QPushButton(label)
            b.setFixedSize(34, 34)
            b.setCursor(Qt.PointingHandCursor if enabled
                        else Qt.ArrowCursor)
            b.setEnabled(enabled)
            if active:
                b.setStyleSheet(
                    f"QPushButton{{background:{P};color:#fff;"
                    "border:none;border-radius:8px;"
                    "font-size:13px;font-weight:700;}}"
                )
            elif not enabled:
                b.setStyleSheet(
                    f"QPushButton{{background:transparent;"
                    f"color:{BORDER};border:1.5px solid {BORDER};"
                    "border-radius:8px;font-size:14px;}}"
                )
            else:
                b.setStyleSheet(
                    f"QPushButton{{background:transparent;"
                    f"color:{TXT_M};border:1.5px solid {BORDER};"
                    "border-radius:8px;font-size:13px;font-weight:500;}}"
                    f"QPushButton:hover{{background:#ede9fe;"
                    f"color:{P};border-color:{P};}}"
                )
            return b

        # ← Prev
        btn_prev = _pg_btn("‹", enabled=self._cands_page > 0)
        if self._cands_page > 0:
            btn_prev.clicked.connect(
                lambda: self._cands_go_page(self._cands_page - 1)
            )
        self._pg_lo.addWidget(btn_prev)

        # Page number buttons
        for i in range(n_pages):
            is_active = (i == self._cands_page)
            b = _pg_btn(str(i + 1), active=is_active)
            if not is_active:
                b.clicked.connect(
                    lambda _=False, idx=i: self._cands_go_page(idx)
                )
            self._pg_lo.addWidget(b)

        # → Next
        btn_next = _pg_btn("›", enabled=self._cands_page < n_pages - 1)
        if self._cands_page < n_pages - 1:
            btn_next.clicked.connect(
                lambda: self._cands_go_page(self._cands_page + 1)
            )
        self._pg_lo.addWidget(btn_next)

    def _cands_go_page(self, n: int) -> None:
        self._cands_page = n
        self._render_cands(self._cands_data)

    # ── logout ────────────────────────────────────────────────
    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    # ── public ────────────────────────────────────────────────
    def show(self) -> None:
        self.win.show()

    def raise_(self) -> None:
        self.win.raise_()
        self.win.activateWindow()
