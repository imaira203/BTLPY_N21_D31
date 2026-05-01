"""HR Dashboard — pure Python, không dùng .ui file."""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Callable

from PySide6.QtCore import (Qt, QSize, QPropertyAnimation,
                              QEasingCurve, QPoint, QByteArray,
                              QEvent, QObject, QTimer, QRect, QDate)
from PySide6.QtGui import (QIcon, QFont, QColor, QPainter, QPixmap,
                            QPainterPath, QLinearGradient, QPen)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFrame, QGraphicsDropShadowEffect,
    QDateEdit, QGridLayout, QGroupBox,
    QFileDialog,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSizePolicy, QSpacerItem, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from pathlib import Path

from ..client import jobhub_api
from ..client.jobhub_api import ApiError
from ..paths import resource_icon
from ..session_store import clear_session
from .charts import make_bar_chart

_DESC_MARKER = "__JH_V1__"


def _encode_desc(desc: str, duties: str, requirements: str,
                 soft_skills: str, benefits: str = "") -> str:
    """Pack all job-detail sections into a single JSON blob stored as description."""
    def _lines(txt: str) -> list[str]:
        return [l.strip() for l in txt.splitlines() if l.strip()]
    return _DESC_MARKER + json.dumps({
        "desc":         desc,
        "duties":       _lines(duties),
        "requirements": _lines(requirements),
        "soft_skills":  _lines(soft_skills),
        "benefits":     _lines(benefits),
    }, ensure_ascii=False)


def _decode_desc(raw: str | None) -> dict:
    """Return structured dict; falls back gracefully for old plain-text descriptions."""
    raw = (raw or "").strip()
    if raw.startswith(_DESC_MARKER):
        try:
            return json.loads(raw[len(_DESC_MARKER):])
        except Exception:
            pass
    return {"desc": raw, "duties": [], "requirements": [], "soft_skills": [], "benefits": []}

# ══════════════════════════════════════════════════════════════
#  TOKENS
# ══════════════════════════════════════════════════════════════
SIDEBAR_BG      = "#ffffff"       # Light sidebar
SIDEBAR_BORDER  = "#e5e7eb"       # Right divider
SIDEBAR_W       = 240
NAV_ACTIVE      = "#eef2ff"       # Light indigo pill bg
NAV_ACTIVE_T    = "#6366f1"       # Indigo text when active
NAV_ACTIVE_IC   = "#6366f1"       # Indigo icon when active
NAV_INACT_T     = "#374151"       # Dark gray text (readable on white)
NAV_INACT_IC    = "#9ca3af"       # Mid-gray icon
NAV_HOVER_BG    = "#f3f4f6"       # Very light hover
CONTENT_BG      = "#f8fafc"
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
_HR_ACCEPT_FEE_RATE = 0.02

_ICONS = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"
_CANDS_PER_PAGE = 5   # số ứng viên mỗi trang


# ══════════════════════════════════════════════════════════════
#  SVG HELPER
# ══════════════════════════════════════════════════════════════
def _lighten(hex_color: str, mix: float = 0.72) -> str:
    """Mix hex_color with white by `mix` ratio → lighter shade for duotone."""
    try:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r2 = int(r * (1 - mix) + 255 * mix)
        g2 = int(g * (1 - mix) + 255 * mix)
        b2 = int(b * (1 - mix) + 255 * mix)
        return f"#{r2:02x}{g2:02x}{b2:02x}"
    except Exception:
        return hex_color


def _svg_pm(name: str, size: int, color: str,
            color2: str = "") -> QPixmap:
    """
    Render SVG icon at `size` px, replacing:
      - currentColor  → color  (main stroke/fill)
      - softColor     → color2 (duotone fill; auto-lightened if not given)
    """
    p = _ICONS / name
    if not p.exists():
        return QPixmap()
    raw = p.read_text(encoding="utf-8")
    raw = raw.replace("currentColor", color)
    soft = color2 if color2 else _lighten(color, 0.78)
    raw = raw.replace("softColor", soft)
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


def _circular_fill_pixmap(src: QPixmap, size: QSize) -> QPixmap:
    if src.isNull():
        return QPixmap()
    side = min(size.width(), size.height())
    scaled = src.scaled(side, side, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    out = QPixmap(side, side)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, side, side)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return out


def _fmt_vnd(amount: int | float) -> str:
    return f"{int(amount):,}".replace(",", ".") + " đ"


def _to_int(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return int(digits) if digits else 0


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
    """Sidebar nav item — light sidebar style.
    Active:   light indigo pill (#eef2ff) + indigo text/icon
    Hover:    very light gray (#f3f4f6)
    Inactive: transparent bg + dark gray text
    """

    def __init__(self, icon_svg: str, label: str,
                 logout: bool = False, parent=None):
        super().__init__(parent)
        self._icon_svg  = icon_svg
        self._active    = False
        self._logout    = logout
        self._cb        = None

        # Colors depending on type
        if logout:
            self._ic_inact  = "#f87171"   # red-400
            self._ic_active = "#ef4444"
            self._tx_inact  = "#f87171"
            self._tx_active = "#ef4444"
            self._bg_active = "#fef2f2"
            self._bg_hover  = "#fff5f5"
        else:
            self._ic_inact  = NAV_INACT_IC
            self._ic_active = NAV_ACTIVE_IC
            self._tx_inact  = NAV_INACT_T
            self._tx_active = NAV_ACTIVE_T
            self._bg_active = NAV_ACTIVE
            self._bg_hover  = NAV_HOVER_BG

        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background:transparent;")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Left accent bar (3px, visible only when active)
        self._accent_bar = QFrame()
        self._accent_bar.setFixedWidth(3)
        self._accent_bar.setStyleSheet(
            "background:transparent;border:none;border-radius:2px;"
        )
        outer.addWidget(self._accent_bar)
        outer.addSpacing(4)

        # Pill (icon + text)
        self._pill = QFrame()
        self._pill.setStyleSheet(
            "background:transparent;border-radius:10px;"
        )
        pill_lo = QHBoxLayout(self._pill)
        pill_lo.setContentsMargins(14, 0, 14, 0)
        pill_lo.setSpacing(10)
        pill_lo.setAlignment(Qt.AlignVCenter)

        # Icon
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(18, 18)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background:transparent;border:none;")
        self._icon_lbl.setPixmap(_svg_pm(icon_svg, 18, self._ic_inact))

        # Text
        self._txt = QLabel(label)
        self._txt.setStyleSheet(
            f"color:{self._tx_inact};font-size:13px;font-weight:400;"
            "background:transparent;border:none;"
        )

        pill_lo.addWidget(self._icon_lbl)
        pill_lo.addWidget(self._txt, 1)
        outer.addWidget(self._pill, 1)

    def set_active(self, v: bool) -> None:
        self._active = v
        if v:
            self._pill.setStyleSheet(
                f"background:{self._bg_active};border-radius:10px;"
            )
            self._accent_bar.setStyleSheet(
                f"background:{self._ic_active};border:none;border-radius:2px;"
            )
            self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 18, self._ic_active))
            self._txt.setStyleSheet(
                f"color:{self._tx_active};font-size:13px;font-weight:600;"
                "background:transparent;border:none;"
            )
        else:
            self._pill.setStyleSheet(
                "background:transparent;border-radius:10px;"
            )
            self._accent_bar.setStyleSheet(
                "background:transparent;border:none;border-radius:2px;"
            )
            self._icon_lbl.setPixmap(_svg_pm(self._icon_svg, 18, self._ic_inact))
            self._txt.setStyleSheet(
                f"color:{self._tx_inact};font-size:13px;font-weight:500;"
                "background:transparent;border:none;"
            )

    def enterEvent(self, e):
        if not self._active:
            self._pill.setStyleSheet(
                f"background:{self._bg_hover};border-radius:10px;"
            )
            self._icon_lbl.setPixmap(
                _svg_pm(self._icon_svg, 18, self._ic_active)
            )
            self._txt.setStyleSheet(
                f"color:{self._tx_active};font-size:13px;font-weight:500;"
                "background:transparent;border:none;"
            )
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._active:
            self._pill.setStyleSheet("background:transparent;border-radius:10px;")
            self._icon_lbl.setPixmap(
                _svg_pm(self._icon_svg, 18, self._ic_inact)
            )
            self._txt.setStyleSheet(
                f"color:{self._tx_inact};font-size:13px;font-weight:400;"
                "background:transparent;border:none;"
            )
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
    │ [icon 40px]                          │
    │                                      │
    │ 38px bold number                     │
    │ 12px gray label                      │
    │ [colored trend badge]                │
    └──────────────────────────────────────┘
    Each card has its own semantic accent color.
    Hover: lift + colored shadow + accent border.
    """

    _NUM_COLOR   = "#111827"   # near-black — dominant
    _LABEL_COLOR = "#6B7280"   # neutral gray — secondary

    def __init__(self, icon_svg: str, accent: str = "#6366f1",
                 label: str = "", value: str = "", hint: str = "",
                 sparkline_data: list | None = None,
                 parent=None):
        super().__init__(parent)

        # Store accent for hover events
        self._accent = accent
        h = accent.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        self._ar, self._ag, self._ab = r, g, b
        icon_bg  = f"rgba({r},{g},{b},0.10)"
        badge_bg = f"rgba({r},{g},{b},0.08)"

        # Card base style
        self.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #f1f5f9;border-radius:18px;}"
        )
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(162)

        # Shadow
        self._fx = QGraphicsDropShadowEffect(self)
        self._fx.setBlurRadius(18)
        self._fx.setOffset(0, 4)
        self._fx.setColor(QColor(r, g, b, 14))
        self.setGraphicsEffect(self._fx)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(0)

        # ── Icon badge ────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(0)
        top_row.setContentsMargins(0, 0, 0, 0)

        badge = QFrame()
        badge.setFixedSize(42, 42)
        badge.setStyleSheet(
            f"background:{icon_bg};border-radius:13px;border:none;"
        )
        b_lo = QHBoxLayout(badge)
        b_lo.setContentsMargins(0, 0, 0, 0)
        ic = QLabel()
        ic.setAlignment(Qt.AlignCenter)
        ic.setPixmap(_svg_pm(icon_svg, 20, accent, _lighten(accent, 0.65)))
        ic.setStyleSheet("background:transparent;border:none;")
        b_lo.addWidget(ic)
        top_row.addWidget(badge, 0, Qt.AlignVCenter | Qt.AlignLeft)
        top_row.addStretch()

        root.addLayout(top_row)
        root.addSpacing(10)

        # ── Number ────────────────────────────────────────────
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(
            f"color:{self._NUM_COLOR};font-size:36px;font-weight:800;"
            "background:transparent;border:none;letter-spacing:-1px;"
        )
        root.addWidget(val_lbl)
        root.addSpacing(3)

        # ── Label ─────────────────────────────────────────────
        lab_lbl = QLabel(label)
        lab_lbl.setStyleSheet(
            f"color:{self._LABEL_COLOR};font-size:12px;font-weight:500;"
            "background:transparent;border:none;"
        )
        root.addWidget(lab_lbl)
        root.addSpacing(10)

        # ── Trend badge (semantic color) ───────────────────────
        pill_row = QHBoxLayout()
        pill_row.setContentsMargins(0, 0, 0, 0)
        pill_row.setSpacing(0)
        hint_pill = QLabel(hint)
        hint_pill.setStyleSheet(
            f"background:{badge_bg};color:{accent};"
            "font-size:11px;font-weight:500;"
            "border-radius:5px;padding:2px 9px;border:none;"
        )
        pill_row.addWidget(hint_pill, 0, Qt.AlignLeft)
        pill_row.addStretch()
        root.addLayout(pill_row)

    def enterEvent(self, e):
        r, g, b = self._ar, self._ag, self._ab
        self._fx.setBlurRadius(28)
        self._fx.setOffset(0, 8)
        self._fx.setColor(QColor(r, g, b, 35))
        self.setStyleSheet(
            f"QFrame{{background:#ffffff;border:1.5px solid rgba({r},{g},{b},0.35);"
            "border-radius:18px;}"
        )
        super().enterEvent(e)

    def leaveEvent(self, e):
        r, g, b = self._ar, self._ag, self._ab
        self._fx.setBlurRadius(18)
        self._fx.setOffset(0, 4)
        self._fx.setColor(QColor(r, g, b, 14))
        self.setStyleSheet(
            "QFrame{background:#ffffff;border:1px solid #f1f5f9;"
            "border-radius:18px;}"
        )
        super().leaveEvent(e)


# ══════════════════════════════════════════════════════════════
#  SECTION FRAME
# ══════════════════════════════════════════════════════════════
def _card_frame(title: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame{{background:{CARD_BG};border:none;"
        "border-radius:16px;}}"
    )
    _shadow(frame, blur=16, dy=4, alpha=12)
    lo = QVBoxLayout(frame)
    lo.setContentsMargins(24, 20, 24, 20)
    lo.setSpacing(16)
    if title:
        t = QLabel(title)
        t.setStyleSheet(
            f"color:{TXT_H};font-size:15px;font-weight:600;"
            "background:transparent;border:none;letter-spacing:-0.2px;"
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
        "border-radius:10px;font-size:13px;font-weight:600;padding:0 20px;}}"
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
        f"color:{TXT_H};font-size:16px;font-weight:600;"
        "background:transparent;border:none;letter-spacing:-0.3px;"
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
        "border-radius:10px;font-size:13px;font-weight:500;padding:0 20px;}"
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
            padding:10px 8px; font-size:12px;
            font-weight:700; color:{TXT_M};
            letter-spacing:0.3px;
        }}
    """)
    tbl.setAlternatingRowColors(False)
    tbl.setShowGrid(False)
    tbl.verticalHeader().setVisible(False)
    tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
    tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
    tbl.horizontalHeader().setStretchLastSection(False)
    tbl.setFrameShape(QFrame.NoFrame)
    tbl.verticalHeader().setDefaultSectionSize(52)


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
        self._hr_profile_data: dict = {}
        self._hr_me_data: dict = {}
        self._hr_avatar_pixmap: QPixmap | None = None
        self._billing_poll_timer: QTimer | None = None
        self._billing_poll_invoice_code: str = ""
        self._billing_detail_invoice_code: str = ""
        self._billing_detail_refresh_cb = None
        self._build()
        self._load_hr_identity()
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
    def _show_toast(self, text: str, icon: str = "ic_check.svg",
                    color: str = "#10b981", duration: int = 3000) -> None:
        """Hiện thông báo nổi góc phải-dưới, tự động tắt sau `duration` ms.
        icon: tên file SVG (vd: 'ic_check.svg', 'ic_x.svg', 'ic_alert.svg')
        """
        toast = QWidget(self.win)
        toast.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        toast.setAttribute(Qt.WA_TranslucentBackground, False)
        # Responsive width: adapt to current window size, keep sensible limits.
        parent_w = max(320, int(self.win.width() or 0))
        toast_w = max(300, min(460, int(parent_w * 0.42)))
        toast.setFixedWidth(toast_w)

        lo = QHBoxLayout(toast)
        lo.setContentsMargins(14, 12, 14, 12)
        lo.setSpacing(10)
        lo.setAlignment(Qt.AlignTop)

        # Icon badge — SVG rendered into circular tinted badge
        ic_lbl = QLabel()
        ic_lbl.setFixedSize(32, 32)
        ic_lbl.setAlignment(Qt.AlignCenter)
        ic_lbl.setStyleSheet(
            f"background:{_rgba(color, 0.12)};border-radius:16px;border:none;"
        )
        ic_lbl.setPixmap(_svg_pm(icon, 16, color))

        # Message
        msg_lbl = QLabel(text)
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        msg_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        msg_lbl.setMaximumWidth(max(180, toast_w - 14 - 14 - 32 - 20 - (10 * 2)))
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
        toast.setFixedHeight(max(56, toast.sizeHint().height()))

        # Position: bottom-right of window
        pw = self.win.width()
        ph = self.win.height()
        tx = max(12, pw - toast.width() - 24)
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
        job_hits = [j for j in self._jobs_data
                    if kw in j.get("title", "").lower()
                    or kw in j.get("department", "").lower()
                    or kw in j.get("location", "").lower()
                    or kw in j.get("job_type", "").lower()
                    or kw in j.get("company_name", "").lower()][:5]

        # Search candidates
        all_apps = self._all_applications()
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

            ic = QLabel()
            ic.setFixedSize(30, 30)
            ic.setAlignment(Qt.AlignCenter)
            ic.setPixmap(_svg_pm(icon, 14, TXT_M))
            ic.setStyleSheet(
                "background:#f1f5f9;border-radius:15px;border:none;"
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
                vlo.addWidget(_result_row("ic_jobs.svg", j.get("title",""), sub, _go_job))

        if cand_hits:
            vlo.addWidget(_section_hdr(f"ỨNG VIÊN  ({len(cand_hits)})"))
            for a in cand_hits:
                sub = f"{a.get('job_title','')}  ·  {a.get('candidate_email','')}"
                def _go_cand(name=a.get("candidate_name","")):
                    self._hide_global_search_popup()
                    self._go(3)
                    self._cands_search.setText(name)
                vlo.addWidget(_result_row("ic_user.svg", a.get("candidate_name",""), sub, _go_cand))

        # Footer "Tìm tất cả"
        footer = QWidget()
        footer.setFixedHeight(38)
        footer.setCursor(Qt.PointingHandCursor)
        footer.setStyleSheet(
            f"QWidget{{background:transparent;border-top:1px solid {BORDER};}}"
        )
        f_lo = QHBoxLayout(footer)
        f_lo.setContentsMargins(14, 0, 14, 0)
        f_lo.setSpacing(8)
        f_ic = QLabel()
        f_ic.setPixmap(_svg_pm("ic_search.svg", 13, P))
        f_ic.setStyleSheet("background:transparent;border:none;")
        f_all = QLabel(f"Tìm tất cả kết quả cho  \"{self.search_input.text().strip()}\"")
        f_all.setStyleSheet(
            f"color:{P};font-size:12px;font-weight:600;"
            "background:transparent;border:none;"
        )
        f_lo.addWidget(f_ic)
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
        job_hits = [j for j in self._jobs_data
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
        # Light bg + right border for separation
        sb.setStyleSheet(
            f"QFrame{{background:{SIDEBAR_BG};"
            f"border-right:1px solid {SIDEBAR_BORDER};"
            "border-top:none;border-left:none;border-bottom:none;}}"
        )
        # Soft right shadow for depth
        sb_sh = QGraphicsDropShadowEffect()
        sb_sh.setBlurRadius(20)
        sb_sh.setXOffset(4)
        sb_sh.setYOffset(0)
        sb_sh.setColor(QColor(0, 0, 0, 18))
        sb.setGraphicsEffect(sb_sh)

        lo = QVBoxLayout(sb)
        lo.setContentsMargins(12, 0, 12, 0)
        lo.setSpacing(2)

        # ── Brand area ─────────────────────────────────────────
        brand_area = QWidget()
        brand_area.setFixedHeight(72)
        brand_area.setStyleSheet("background:transparent;")
        brand_lo = QHBoxLayout(brand_area)
        brand_lo.setContentsMargins(8, 0, 8, 0)
        brand_lo.setSpacing(9)

        # Brand icon container — indigo tint
        bolt_frame = QFrame()
        bolt_frame.setFixedSize(34, 34)
        bolt_frame.setStyleSheet(
            f"background:{_rgba(P, 0.10)};border-radius:10px;border:none;"
        )
        bolt_lo = QHBoxLayout(bolt_frame)
        bolt_lo.setContentsMargins(0, 0, 0, 0)
        bolt_ic = QLabel("⚡")
        bolt_ic.setAlignment(Qt.AlignCenter)
        bolt_ic.setStyleSheet(
            f"color:{P};font-size:16px;background:transparent;border:none;"
        )
        bolt_lo.addWidget(bolt_ic)

        # "JobHub" wordmark — dark on white
        brand_t = QLabel("JobHub")
        brand_t.setStyleSheet(
            f"color:{TXT_H};font-size:18px;font-weight:700;"
            "letter-spacing:-0.3px;background:transparent;border:none;"
        )
        # HR role badge
        brand_badge = QLabel("HR")
        brand_badge.setFixedHeight(20)
        brand_badge.setStyleSheet(
            f"background:{_rgba(P, 0.10)};color:{P};"
            "font-size:10px;font-weight:600;border-radius:5px;padding:0 7px;border:none;"
            "letter-spacing:1px;"
        )
        brand_lo.addWidget(bolt_frame, 0, Qt.AlignVCenter)
        brand_lo.addWidget(brand_t, 0, Qt.AlignVCenter)
        brand_lo.addSpacing(2)
        brand_lo.addWidget(brand_badge, 0, Qt.AlignVCenter)
        brand_lo.addStretch()
        lo.addWidget(brand_area)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet(f"background:{SIDEBAR_BORDER};max-height:1px;border:none;")
        lo.addWidget(div)
        lo.addSpacing(12)

        # ── Nav section label ──────────────────────────────────
        sec = QLabel("ĐIỀU HƯỚNG")
        sec.setStyleSheet(
            "color:#9ca3af;font-size:10px;font-weight:600;"
            "letter-spacing:2.5px;padding-left:20px;"
            "background:transparent;border:none;"
        )
        lo.addWidget(sec)
        lo.addSpacing(4)

        nav_items = [
            ("ic_dashboard.svg", "Bảng điều khiển"),
            ("ic_edit.svg",      "Đăng tin mới"),
            ("ic_jobs.svg",      "Quản lý tin đăng"),
            ("ic_users.svg",     "Danh sách ứng viên"),
            ("ic_card.svg",      "Hóa đơn"),
            ("ic_user.svg",      "Hồ sơ"),
        ]
        for i, (icon, label) in enumerate(nav_items):
            btn = _NavBtn(icon, label)
            btn.on_click(lambda idx=i: self._go(idx))
            lo.addWidget(btn)
            self._nav_btns.append(btn)

        lo.addStretch()

        # Bottom divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet(f"background:{SIDEBAR_BORDER};max-height:1px;border:none;")
        lo.addWidget(div2)
        lo.addSpacing(8)

        # Logout button
        self._btn_logout = _NavBtn("ic_logout.svg", "Đăng xuất", logout=True)
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
            f"color:{TXT_H};font-size:17px;font-weight:700;"
            "background:transparent;border:none;letter-spacing:-0.3px;"
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
        self.lbl_hr_role = QLabel("Nhà tuyển dụng")
        self.lbl_hr_role.setAlignment(Qt.AlignRight)
        self.lbl_hr_role.setStyleSheet(
            f"color:{TXT_M};font-size:11px;font-weight:400;"
            "background:transparent;border:none;"
        )
        info_col.addWidget(self.lbl_hr_name)
        info_col.addWidget(self.lbl_hr_role)
        p_lo.addLayout(info_col)

        self._btn_hr_avatar = QPushButton("HR")
        self._btn_hr_avatar.setFixedSize(40, 40)
        self._btn_hr_avatar.setCursor(Qt.PointingHandCursor)
        self._btn_hr_avatar.setStyleSheet(
            f"QPushButton{{background:{P};color:#fff;border-radius:20px;"
            "font-size:13px;font-weight:800;border:none;}}"
            f"QPushButton:hover{{background:{P_DARK};}}"
        )
        self._btn_hr_avatar.clicked.connect(lambda _=False: self._go(5))
        p_lo.addWidget(self._btn_hr_avatar)

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
        self._stack.addWidget(self._build_billing_page()) # 4
        self._stack.addWidget(self._build_hr_profile_page())  # 5
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
            f"QFrame{{background:{CARD_BG};border:none;"
            "border-radius:12px;}"
        )
        stats_lo = QHBoxLayout(stats_bar)
        stats_lo.setContentsMargins(20, 0, 20, 0)
        stats_lo.setSpacing(0)
        self._quick_stats_values: dict[str, QLabel] = {}
        quick_defs = [
            ("new_today", "0",  "Ứng viên mới hôm nay",   "#6366f1"),
            ("pending_jobs", "0", "Tin chờ Admin duyệt",  "#f59e0b"),
            ("response_rate", "0%", "Tỷ lệ trả lời ứng viên", "#10b981"),
        ]
        for i, (key, val, lbl, col) in enumerate(quick_defs):
            if i > 0:
                sep = QFrame()
                sep.setFixedSize(1, 28)
                sep.setStyleSheet(f"background:{BORDER};border:none;")
                stats_lo.addWidget(sep)

            stat_w = QWidget()
            stat_w.setCursor(Qt.PointingHandCursor)
            stat_w.setStyleSheet("QWidget{background:transparent;border-radius:8px;}")
            stat_inner = QHBoxLayout(stat_w)
            stat_inner.setContentsMargins(18, 0, 18, 0)
            stat_inner.setSpacing(8)
            stat_inner.setAlignment(Qt.AlignCenter)

            v_lbl = QLabel(val)
            v_lbl.setStyleSheet(
                f"color:{col};font-size:20px;font-weight:700;"
                "background:transparent;border:none;letter-spacing:-0.5px;"
            )
            self._quick_stats_values[key] = v_lbl
            t_lbl = QLabel(lbl)
            t_lbl.setStyleSheet(
                f"color:{TXT_M};font-size:12px;font-weight:500;"
                "background:transparent;border:none;"
            )
            stat_inner.addWidget(v_lbl)
            stat_inner.addWidget(t_lbl)

            # Micro-interaction: hover tint
            _col = col
            def _enter(e, w=stat_w, c=_col):
                w.setStyleSheet(
                    f"QWidget{{background:{_rgba(c, 0.06)};border-radius:8px;}}"
                )
            def _leave(e, w=stat_w):
                w.setStyleSheet("QWidget{background:transparent;border-radius:8px;}")
            stat_w.enterEvent = _enter
            stat_w.leaveEvent = _leave

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
            f"color:{TXT_H};font-size:15px;font-weight:600;"
            "background:transparent;border:none;letter-spacing:-0.2px;"
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
            f"color:{TXT_H};font-size:15px;font-weight:600;"
            "background:transparent;border:none;letter-spacing:-0.2px;"
        )
        self._act_count = QLabel("  0 sự kiện  ")
        self._act_count.setStyleSheet(
            f"background:#ede9fe;color:{P};font-size:11px;font-weight:600;"
            "border-radius:10px;padding:2px 0;"
        )
        act_header.addWidget(act_ic)
        act_header.addWidget(act_title_lbl, 1)
        act_header.addWidget(self._act_count)
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

    # Type → (svg_icon, bg_color, fg_color)
    _ACT_TYPE_STYLE: dict = {
        "apply":     ("ic_doc.svg",      "#ede9fe", "#6366f1"),
        "interview": ("ic_clock.svg",    "#dbeafe", "#2563eb"),
        "approved":  ("ic_check.svg",    "#d1fae5", "#059669"),
        "update":    ("ic_edit.svg",     "#fef3c7", "#d97706"),
        "view":      ("ic_view.svg",     "#f1f5f9", "#64748b"),
        "rejected":  ("ic_x.svg",        "#fee2e2", "#dc2626"),
    }
    _ACT_GROUP_LABEL: dict = {
        "today":     "Hôm nay",
        "yesterday": "Hôm qua",
        "week":      "Tuần này",
        "older":     "Trước đó",
    }

    def _load_dash(self) -> None:
        try:
            data = jobhub_api.hr_dashboard()
        except ApiError:
            data = {
                "cards": {"jobs": 0, "candidates": 0, "views": 0, "response_rate": 0},
                "labels": [],
                "values": [],
                "recent_pending_applications": [],
            }
        cards = data.get("cards") or {}
        pending_apps = list(data.get("recent_pending_applications") or [])
        self._refresh_quick_stats(cards)
        try:
            views_count = int(cards.get("views", 0) or 0)
        except (TypeError, ValueError):
            views_count = 0

        # ── Metric cards ─────────────────────────────────────
        while self._cards_row.count():
            it = self._cards_row.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        # All cards use real values from backend dashboard API.
        card_defs = [
            # (icon,          accent,      label,             value,                         hint)
            ("ic_jobs.svg",  "#3b82f6",  "Tin đang đăng",   str(cards.get("jobs", 0)),      "Số tin đã đăng tải"),
            ("ic_users.svg", "#8b5cf6",  "Tổng ứng viên",   str(cards.get("candidates", 0)), f"{len(pending_apps)} hồ sơ chờ duyệt"),
            ("ic_view.svg",  "#f97316",  "Lượt xem tin",    f"{views_count:,}",              "Số lượt xem tin đăng"),
            ("ic_chat.svg",  "#10b981",  "Tỷ lệ phản hồi",  f"{cards.get('response_rate', 0)}%", "Tỷ lệ phản hồi ứng viên"),
        ]
        for (icon, accent, label, val, hint) in card_defs:
            c = _MetricCard(
                icon_svg=icon,
                accent=accent,
                label=label,
                value=val,
                hint=hint,
            )
            self._cards_row.addWidget(c)

        # ── Chart (initial period = week) ─────────────────────
        self._rebuild_chart("week")

        # ── Activity feed (grouped) ───────────────────────────
        self._rebuild_activity_feed()

    def _load_hr_identity(self) -> None:
        profile = {}
        me_data = {}
        try:
            me_data = jobhub_api.me() or {}
            full_name = str(me_data.get("full_name") or "").strip()
            if full_name:
                self.lbl_hr_name.setText(full_name)
        except ApiError:
            me_data = {}
        self._hr_me_data = dict(me_data)

        try:
            profile = jobhub_api.hr_profile() or {}
        except ApiError:
            profile = {}
        self._hr_profile_data = dict(profile)
        try:
            avatar_bytes, _ = jobhub_api.hr_avatar_view()
            pm = QPixmap()
            if pm.loadFromData(avatar_bytes):
                self._hr_avatar_pixmap = pm
            else:
                self._hr_avatar_pixmap = None
        except Exception:
            self._hr_avatar_pixmap = None
        self._apply_hr_identity(profile)

    def _apply_hr_identity(self, profile: dict | None = None) -> None:
        profile = profile or {}
        company_name = str(profile.get("company_name") or "").strip()
        status = str(profile.get("approval_status") or "").strip().lower()
        if company_name:
            self.lbl_hr_name.setText(company_name)

        status_text = self._hr_status_label(status)
        self.lbl_hr_role.setText(status_text)

        display = company_name or self.lbl_hr_name.text()
        initials = "".join(part[:1].upper() for part in display.split()[:2]) or "HR"
        if self._hr_avatar_pixmap and not self._hr_avatar_pixmap.isNull():
            top_pm = _circular_fill_pixmap(self._hr_avatar_pixmap, self._btn_hr_avatar.size())
            self._btn_hr_avatar.setIcon(QIcon(top_pm))
            self._btn_hr_avatar.setIconSize(self._btn_hr_avatar.size())
            self._btn_hr_avatar.setText("")
            self._btn_hr_avatar.setStyleSheet(
                "QPushButton{background:#ffffff;border-radius:20px;border:1px solid #e2e8f0;}"
                "QPushButton:hover{background:#f8fafc;}"
            )
        else:
            self._btn_hr_avatar.setIcon(QIcon())
            self._btn_hr_avatar.setText(initials)
            self._btn_hr_avatar.setStyleSheet(
                f"QPushButton{{background:{P};color:#fff;border-radius:20px;"
                "font-size:13px;font-weight:800;border:none;}}"
                f"QPushButton:hover{{background:{P_DARK};}}"
            )
        self._refresh_hr_profile_form()

    def _hr_status_label(self, status: str) -> str:
        status = str(status or "").strip().lower()
        if status == "approved":
            return "Nhà tuyển dụng xác thực"
        if status == "pending":
            return "Nhà tuyển dụng chờ duyệt"
        if status == "rejected":
            return "Nhà tuyển dụng bị từ chối"
        return "Nhà tuyển dụng"

    def _open_hr_profile_dialog(self) -> None:
        profile = dict(self._hr_profile_data or {})
        dlg = QDialog(self.win)
        dlg.setWindowTitle("Hồ sơ nhà tuyển dụng")
        dlg.resize(640, 560)
        dlg.setModal(True)
        dlg.setStyleSheet(
            f"QDialog{{background:{CONTENT_BG};}}"
            "QLabel{background:transparent;border:none;}"
        )
        root = QVBoxLayout(dlg)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        title = QLabel("Cập nhật hồ sơ công ty")
        title.setStyleSheet(f"color:{TXT_H};font-size:20px;font-weight:800;")
        root.addWidget(title)

        status_raw = str(profile.get("approval_status") or "").strip().lower()
        status_text = "Chưa xác định"
        if status_raw == "approved":
            status_text = "Đã duyệt"
        elif status_raw == "pending":
            status_text = "Chờ duyệt"
        elif status_raw == "rejected":
            status_text = "Từ chối"
        st = QLabel(f"Trạng thái xác thực: {status_text}")
        st.setStyleSheet(f"color:{TXT_M};font-size:12px;font-weight:600;")
        root.addWidget(st)

        card, clo = _card_frame()
        clo.setSpacing(10)
        clo.addWidget(_lbl("Tên công ty", 12, bold=True))
        e_company = _input("Tên công ty")
        e_company.setText(str(profile.get("company_name") or ""))
        e_company.setMinimumHeight(44)
        clo.addWidget(e_company)

        clo.addWidget(_lbl("Số điện thoại liên hệ", 12, bold=True))
        e_phone = _input("Ví dụ: 090xxxxxxx")
        e_phone.setText(str(profile.get("contact_phone") or ""))
        e_phone.setMinimumHeight(44)
        clo.addWidget(e_phone)

        clo.addWidget(_lbl("Mô tả công ty", 12, bold=True))
        e_desc = QPlainTextEdit(str(profile.get("company_description") or ""))
        e_desc.setMinimumHeight(150)
        e_desc.setStyleSheet(
            f"QPlainTextEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
            "border-radius:10px;padding:10px 12px;font-size:13px;"
            f"color:{TXT_H};}}"
            f"QPlainTextEdit:focus{{border-color:{P};}}"
        )
        clo.addWidget(e_desc)
        root.addWidget(card, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_avatar = QPushButton("Cập nhật ảnh đại diện")
        btn_avatar.setFixedHeight(36)
        btn_avatar.setCursor(Qt.PointingHandCursor)
        btn_avatar.setStyleSheet(
            f"QPushButton{{background:#eef2ff;color:{P_DARK};border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}}"
            "QPushButton:hover{background:#e0e7ff;}"
        )

        def _do_update_avatar() -> None:
            path, _ = QFileDialog.getOpenFileName(
                dlg,
                "Chọn ảnh đại diện công ty",
                "",
                "Image Files (*.png *.jpg *.jpeg *.webp *.gif)",
            )
            if not path:
                return
            try:
                new_profile = jobhub_api.upload_hr_avatar(path)
            except ApiError as e:
                QMessageBox.warning(dlg, "Lỗi", str(e))
                return
            self._hr_profile_data = dict(new_profile or {})
            self._apply_hr_identity(self._hr_profile_data)
            self._show_toast("Đã cập nhật ảnh đại diện", "ic_check.svg", "#10b981")

        btn_avatar.clicked.connect(_do_update_avatar)
        btn_row.addWidget(btn_avatar)
        btn_row.addSpacing(8)

        btn_save = QPushButton("Lưu thông tin công ty")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            f"QPushButton{{background:{P};color:#fff;border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}}"
            f"QPushButton:hover{{background:{P_DARK};}}"
        )

        def _do_save_company_profile() -> None:
            company_name = e_company.text().strip()
            if not company_name:
                QMessageBox.warning(dlg, "Thiếu thông tin", "Vui lòng nhập tên công ty.")
                return
            try:
                updated = jobhub_api.update_my_hr_profile(
                    company_name=company_name,
                    contact_phone=e_phone.text().strip() or None,
                    company_description=e_desc.toPlainText().strip() or None,
                )
            except ApiError as e:
                QMessageBox.warning(dlg, "Lỗi", str(e))
                return
            self._hr_profile_data = dict(updated or {})
            self._apply_hr_identity(self._hr_profile_data)
            self._show_toast(
                "Đã cập nhật hồ sơ công ty. Tài khoản được chuyển về trạng thái chờ duyệt.",
                "ic_check.svg",
                "#f59e0b",
            )
            dlg.accept()

        btn_save.clicked.connect(_do_save_company_profile)
        btn_row.addWidget(btn_save)
        root.addLayout(btn_row)
        dlg.exec()

    def _build_hr_profile_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:8px;background:transparent;margin:4px 2px;}"
            "QScrollBar::handle:vertical{background:#cbd5e1;border-radius:4px;min-height:32px;}"
        )

        pg = QWidget()
        pg.setStyleSheet(f"background:{CONTENT_BG};")
        lo = QVBoxLayout(pg)
        lo.setContentsMargins(28, 24, 28, 28)
        lo.setSpacing(20)

        body = QHBoxLayout()
        body.setSpacing(18)

        # Left identity card
        left_card = QFrame()
        left_card.setFixedWidth(290)
        left_card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:16px;}")
        _shadow(left_card, 12, 4, 12)
        left_lo = QVBoxLayout(left_card)
        left_lo.setContentsMargins(22, 24, 22, 20)
        left_lo.setSpacing(10)

        # Avatar block (same interaction style as candidate profile)
        av_wrap = QWidget()
        av_wrap.setFixedSize(96, 96)
        av_wrap.setStyleSheet("background:transparent;")
        glow = QLabel(av_wrap)
        glow.setGeometry(0, 0, 96, 96)
        glow.setStyleSheet(
            f"border-radius:48px;border:3px solid {_rgba(P, 0.30)};background:transparent;"
        )
        self._hr_prof_avatar_lbl = QLabel("HR", av_wrap)
        self._hr_prof_avatar_lbl.setGeometry(6, 6, 84, 84)
        self._hr_prof_avatar_lbl.setAlignment(Qt.AlignCenter)
        self._hr_prof_avatar_lbl.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {P_DARK},stop:1 {P});"
            "color:white;border-radius:42px;font-size:24px;font-weight:800;border:none;"
        )
        cam_btn = QPushButton("", av_wrap)
        cam_btn.setFixedSize(26, 26)
        cam_btn.move(0, 68)
        cam_btn.setCursor(Qt.PointingHandCursor)
        cam_btn.setToolTip("Đổi ảnh đại diện")
        cam_btn.setIcon(QIcon(_svg_pm("ic_edit.svg", 14, "#ffffff")))
        cam_btn.setIconSize(QSize(14, 14))
        cam_btn.setStyleSheet(
            f"QPushButton{{background:{P};color:white;border-radius:13px;border:2px solid white;padding:0;}}"
            f"QPushButton:hover{{background:{P_DARK};}}"
        )
        cam_btn.clicked.connect(self._upload_hr_avatar_from_profile_page)
        left_lo.addWidget(av_wrap, 0, Qt.AlignHCenter)

        self._hr_prof_company_lbl = QLabel("Công ty")
        self._hr_prof_company_lbl.setWordWrap(True)
        self._hr_prof_company_lbl.setAlignment(Qt.AlignCenter)
        self._hr_prof_company_lbl.setStyleSheet(f"color:{TXT_H};font-size:19px;font-weight:800;")
        left_lo.addWidget(self._hr_prof_company_lbl)

        self._hr_prof_status_lbl = QLabel("Nhà tuyển dụng")
        self._hr_prof_status_lbl.setAlignment(Qt.AlignCenter)
        self._hr_prof_status_lbl.setStyleSheet(f"color:{TXT_M};font-size:12px;font-weight:600;")
        left_lo.addWidget(self._hr_prof_status_lbl)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{BORDER};border:none;")
        left_lo.addSpacing(6)
        left_lo.addWidget(div)
        left_lo.addSpacing(6)

        self._hr_prof_phone_lbl = QLabel("SĐT liên hệ: —")
        self._hr_prof_phone_lbl.setWordWrap(True)
        self._hr_prof_phone_lbl.setStyleSheet(f"color:{TXT_S};font-size:12px;")
        left_lo.addWidget(self._hr_prof_phone_lbl)
        self._hr_prof_email_lbl = QLabel("Email liên hệ: —")
        self._hr_prof_email_lbl.setWordWrap(True)
        self._hr_prof_email_lbl.setStyleSheet(f"color:{TXT_S};font-size:12px;")
        left_lo.addWidget(self._hr_prof_email_lbl)
        left_lo.addStretch()
        body.addWidget(left_card)

        # Right editable form
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        form_card, form_lo = _card_frame()
        form_lo.setSpacing(10)
        form_lo.addWidget(_section_header("ic_user.svg", "Thông tin công ty", "#0ea5e9", "#e0f2fe"))

        form_lo.addWidget(_lbl("Tên công ty", 12, bold=True))
        self._hr_prof_company_inp = _input("Nhập tên công ty")
        self._hr_prof_company_inp.setMinimumHeight(44)
        form_lo.addWidget(self._hr_prof_company_inp)

        form_lo.addWidget(_lbl("Số điện thoại liên hệ", 12, bold=True))
        self._hr_prof_phone_inp = _input("Ví dụ: 090xxxxxxx")
        self._hr_prof_phone_inp.setMinimumHeight(44)
        form_lo.addWidget(self._hr_prof_phone_inp)

        form_lo.addWidget(_lbl("Email liên hệ", 12, bold=True))
        self._hr_prof_email_inp = _input("contact@company.com")
        self._hr_prof_email_inp.setMinimumHeight(44)
        form_lo.addWidget(self._hr_prof_email_inp)

        form_lo.addWidget(_lbl("Mô tả công ty", 12, bold=True))
        self._hr_prof_desc_inp = QPlainTextEdit()
        self._hr_prof_desc_inp.setMinimumHeight(170)
        self._hr_prof_desc_inp.setStyleSheet(
            f"QPlainTextEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
            "border-radius:10px;padding:10px 12px;font-size:13px;"
            f"color:{TXT_H};}}"
            f"QPlainTextEdit:focus{{border-color:{P};}}"
        )
        form_lo.addWidget(self._hr_prof_desc_inp)

        self._hr_prof_hint_lbl = QLabel(
            "Lưu thông tin công ty sẽ đưa tài khoản về trạng thái chờ duyệt lại. Cập nhật avatar không ảnh hưởng trạng thái."
        )
        self._hr_prof_hint_lbl.setWordWrap(True)
        self._hr_prof_hint_lbl.setStyleSheet(f"color:{TXT_M};font-size:12px;")
        form_lo.addWidget(self._hr_prof_hint_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_save = QPushButton("Lưu thông tin công ty")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            f"QPushButton{{background:{P};color:#fff;border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}}"
            f"QPushButton:hover{{background:{P_DARK};}}"
        )
        btn_save.clicked.connect(self._save_hr_profile_from_page)
        btn_row.addWidget(btn_save)
        form_lo.addLayout(btn_row)

        right_col.addWidget(form_card, 1)
        body.addLayout(right_col, 1)
        lo.addLayout(body)
        lo.addStretch()
        scroll.setWidget(pg)
        self._refresh_hr_profile_form()
        return scroll

    def _refresh_hr_profile_form(self) -> None:
        if not hasattr(self, "_hr_prof_company_inp"):
            return
        profile = dict(self._hr_profile_data or {})
        company = str(profile.get("company_name") or "").strip()
        phone = str(profile.get("contact_phone") or "").strip()
        desc = str(profile.get("company_description") or "").strip()
        status = str(profile.get("approval_status") or "").strip().lower()
        email = str((self._hr_me_data or {}).get("email") or "").strip()

        self._hr_prof_company_lbl.setText(company or "Công ty")
        self._hr_prof_status_lbl.setText(self._hr_status_label(status))
        self._hr_prof_phone_lbl.setText(f"SĐT liên hệ: {phone or '—'}")
        self._hr_prof_email_lbl.setText(f"Email liên hệ: {email or '—'}")
        initials = "".join(part[:1].upper() for part in (company or "HR").split()[:2]) or "HR"
        if self._hr_avatar_pixmap and not self._hr_avatar_pixmap.isNull():
            self._hr_prof_avatar_lbl.setPixmap(_circular_fill_pixmap(self._hr_avatar_pixmap, self._hr_prof_avatar_lbl.size()))
            self._hr_prof_avatar_lbl.setText("")
            self._hr_prof_avatar_lbl.setStyleSheet("background:transparent;border:none;")
        else:
            self._hr_prof_avatar_lbl.setPixmap(QPixmap())
            self._hr_prof_avatar_lbl.setText(initials)
            self._hr_prof_avatar_lbl.setStyleSheet(
                f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {P_DARK},stop:1 {P});"
                "color:white;border-radius:42px;font-size:24px;font-weight:800;border:none;"
            )

        self._hr_prof_company_inp.blockSignals(True)
        self._hr_prof_phone_inp.blockSignals(True)
        self._hr_prof_email_inp.blockSignals(True)
        self._hr_prof_desc_inp.blockSignals(True)
        self._hr_prof_company_inp.setText(company)
        self._hr_prof_phone_inp.setText(phone)
        self._hr_prof_email_inp.setText(email)
        self._hr_prof_desc_inp.setPlainText(desc)
        self._hr_prof_company_inp.blockSignals(False)
        self._hr_prof_phone_inp.blockSignals(False)
        self._hr_prof_email_inp.blockSignals(False)
        self._hr_prof_desc_inp.blockSignals(False)

    def _upload_hr_avatar_from_profile_page(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.win,
            "Chọn ảnh đại diện công ty",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.gif)",
        )
        if not path:
            return
        try:
            updated = jobhub_api.upload_hr_avatar(path)
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return
        pm = QPixmap(path)
        self._hr_avatar_pixmap = pm if not pm.isNull() else None
        self._hr_profile_data = dict(updated or {})
        self._apply_hr_identity(self._hr_profile_data)
        self._show_toast("Đã cập nhật ảnh đại diện", "ic_check.svg", "#10b981")

    def _save_hr_profile_from_page(self) -> None:
        company_name = self._hr_prof_company_inp.text().strip()
        if not company_name:
            QMessageBox.warning(self.win, "Thiếu thông tin", "Vui lòng nhập tên công ty.")
            return
        email = self._hr_prof_email_inp.text().strip().lower()
        if not email:
            QMessageBox.warning(self.win, "Thiếu thông tin", "Vui lòng nhập email liên hệ.")
            return
        try:
            # Update account email first (if changed)
            current_email = str((self._hr_me_data or {}).get("email") or "").strip().lower()
            if email != current_email:
                me_updated = jobhub_api.update_my_basic_profile(email=email)
                self._hr_me_data = dict(me_updated or self._hr_me_data)
            updated = jobhub_api.update_my_hr_profile(
                company_name=company_name,
                contact_phone=self._hr_prof_phone_inp.text().strip() or None,
                company_description=self._hr_prof_desc_inp.toPlainText().strip() or None,
            )
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return
        self._hr_profile_data = dict(updated or {})
        self._apply_hr_identity(self._hr_profile_data)
        self._show_toast(
            "Đã cập nhật hồ sơ công ty. Tài khoản chuyển về trạng thái chờ duyệt.",
            "ic_check.svg",
            "#f59e0b",
        )

    def _refresh_quick_stats(self, cards: dict) -> None:
        if not hasattr(self, "_quick_stats_values"):
            return
        # Response rate: use backend-computed real metric
        response_rate = int(cards.get("response_rate", 0) or 0)
        # New candidates today + upcoming interviews: derived from applications API
        new_today = 0
        try:
            apps = list(jobhub_api.hr_applications())
        except ApiError:
            apps = []
        today_s = datetime.now().strftime("%d/%m/%Y")
        for app in apps:
            applied_at = str(app.get("applied_at", "")).strip()
            if applied_at == today_s:
                new_today += 1
        # Pending jobs for admin approval: derived from HR jobs API
        pending_jobs = 0
        try:
            jobs = list(jobhub_api.hr_my_jobs())
        except ApiError:
            jobs = []
        pending_jobs = sum(1 for j in jobs if str(j.get("status", "")).lower() == "pending_approval")

        self._quick_stats_values["new_today"].setText(str(new_today))
        self._quick_stats_values["pending_jobs"].setText(str(pending_jobs))
        self._quick_stats_values["response_rate"].setText(f"{response_rate}%")

    def _switch_chart_period(self, period: str) -> None:
        """Called when user clicks a chart period tab."""
        self._chart_period = period
        for btn in self._chart_period_btns:
            btn.setChecked(btn.text() in {"Tuần": "week", "Tháng": "month", "Quý": "quarter"}
                           and {"Tuần": "week", "Tháng": "month", "Quý": "quarter"}[btn.text()] == period)
        self._rebuild_chart(period)

    def _rebuild_chart(self, period: str) -> None:
        """Rebuild the bar chart for the given period."""
        try:
            dash = jobhub_api.hr_dashboard()
        except ApiError:
            dash = {"labels": [], "values": []}
        labels = list(dash.get("labels", []))
        values = list(dash.get("values", []))

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
        """Rebuild activity feed from latest applications + jobs, sorted by time."""
        while self._act_list_lo.count():
            it = self._act_list_lo.takeAt(0)
            if w := it.widget():
                w.deleteLater()

        now = datetime.now()
        activities: list[dict] = []

        def _group_of(dt: datetime) -> str:
            if dt.date() == now.date():
                return "today"
            if dt.date() == (now - timedelta(days=1)).date():
                return "yesterday"
            if (now - dt).days < 7:
                return "week"
            return "older"

        # Latest candidate applications
        try:
            apps_payload = jobhub_api.hr_applications(sort_by="newest")
            apps = list(apps_payload.get("items") or []) if isinstance(apps_payload, dict) else list(apps_payload)
        except ApiError:
            apps = []
        for app in apps[:60]:
            applied_at = str(app.get("applied_at", "")).strip()
            dt: datetime | None = None
            if applied_at:
                try:
                    dt = datetime.strptime(applied_at, "%d/%m/%Y")
                except Exception:
                    dt = None
            if dt is None:
                dt = now
            activities.append(
                {
                    "type": "apply",
                    "dot_color": "#6366f1",
                    "text": f"{app.get('candidate_name', 'Ứng viên')} ứng tuyển {app.get('job_title', '')}",
                    "time": dt.strftime("%d/%m/%Y"),
                    "group": _group_of(dt),
                    "bold": True,
                    "action_label": "Ứng viên",
                    "action_page": 3,
                    "_dt": dt,
                }
            )

        # Latest posted/approved jobs
        try:
            jobs = list(jobhub_api.hr_my_jobs())
        except ApiError:
            jobs = []
        for job in jobs[:80]:
            created_raw = str(job.get("created_at") or "").strip()
            if not created_raw:
                continue
            try:
                dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
            except Exception:
                continue
            j_status = str(job.get("status") or "").lower()
            if j_status == "published":
                text = f"Tin '{job.get('title', '—')}' đã được duyệt và đang tuyển"
                act_type = "approved"
            else:
                text = f"Đăng tin mới: '{job.get('title', '—')}'"
                act_type = "update"
            activities.append(
                {
                    "type": act_type,
                    "dot_color": "#10b981" if act_type == "approved" else "#f59e0b",
                    "text": text,
                    "time": dt.strftime("%d/%m/%Y %H:%M"),
                    "group": _group_of(dt),
                    "bold": False,
                    "action_label": "Tin đăng",
                    "action_page": 2,
                    "_dt": dt,
                }
            )

        activities.sort(key=lambda x: x.get("_dt") or now, reverse=True)
        activities = activities[:40]
        if hasattr(self, "_act_count"):
            self._act_count.setText(f"  {len(activities)} sự kiện  ")
        current_group = None
        for act in activities:
            group = act.get("group", "week")
            # Group header when group changes
            if group != current_group:
                current_group = group
                grp_lbl = QLabel(self._ACT_GROUP_LABEL.get(group, "Trước đó"))
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

        act_svg, type_bg, type_fg = self._ACT_TYPE_STYLE.get(
            act_type, ("ic_activity.svg", "#f1f5f9", "#64748b")
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

        # Type icon badge — SVG rendered into tinted rounded square
        badge = QLabel()
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignCenter)
        badge.setPixmap(_svg_pm(act_svg, 14, type_fg))
        badge.setStyleSheet(
            f"background:{type_bg};border-radius:8px;border:none;"
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

        s1lo.addWidget(_lbl("Phòng ban / Bộ phận", 13, bold=True))
        self.line_dept = _input("Ví dụ: Kỹ thuật & Công nghệ, Marketing, Kinh doanh…")
        self.line_dept.setMinimumHeight(46)
        s1lo.addWidget(self.line_dept)

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
        col_c.addWidget(_lbl("Lương tối thiểu (VNĐ)", 13, bold=True))
        self.line_min_salary = _input("Ví dụ: 15000000")
        self.line_min_salary.setMinimumHeight(46)
        col_c.addWidget(self.line_min_salary)
        col_d = QVBoxLayout(); col_d.setSpacing(8)
        col_d.addWidget(_lbl("Lương tối đa (VNĐ)", 13, bold=True))
        self.line_max_salary = _input("Ví dụ: 25000000")
        self.line_max_salary.setMinimumHeight(46)
        col_d.addWidget(self.line_max_salary)
        row2.addLayout(col_c)
        row2.addLayout(col_d)
        s2lo.addLayout(row2)

        row3 = QHBoxLayout(); row3.setSpacing(16)
        col_loc = QVBoxLayout(); col_loc.setSpacing(8)
        col_loc.addWidget(_lbl("Địa điểm làm việc", 13, bold=True))
        self.line_location = _input("Thành phố Hồ Chí Minh, Quận 1")
        self.line_location.setMinimumHeight(46)
        col_loc.addWidget(self.line_location)
        col_e = QVBoxLayout(); col_e.setSpacing(8)
        col_e.addWidget(_lbl("Số lượng tuyển", 13, bold=True))
        self.line_count = _input("01")
        self.line_count.setMinimumHeight(46)
        col_e.addWidget(self.line_count)
        col_f = QVBoxLayout(); col_f.setSpacing(8)
        col_f.addWidget(_lbl("Hạn nộp hồ sơ", 13, bold=True))
        self.line_deadline = QDateEdit()
        self.line_deadline.setDisplayFormat("dd/MM/yyyy")
        self.line_deadline.setCalendarPopup(True)
        self.line_deadline.setDate(QDate.currentDate().addMonths(1))
        self.line_deadline.setMinimumHeight(46)
        self.line_deadline.setStyleSheet(
            "QDateEdit{border:1.5px solid #e5e7eb; border-radius:10px; padding:0 12px;"
            " font-size:13px; background:#fff;}"
            "QDateEdit::drop-down{border:none; width:28px;}"
        )
        col_f.addWidget(self.line_deadline)
        row3.addLayout(col_loc)
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

        # ── SECTION 4: Nhiệm vụ & Yêu cầu ──────────────────────
        s4, s4lo = _card_frame()
        s4lo.setSpacing(16)
        s4lo.addWidget(
            _section_header("ic_user.svg", "Nhiệm vụ & Yêu cầu",
                            "#10b981", "#d1fae5")
        )

        def _ta(ph: str, h: int = 110) -> QPlainTextEdit:
            e = QPlainTextEdit()
            e.setPlaceholderText(ph)
            e.setFixedHeight(h)
            e.setStyleSheet(
                f"QPlainTextEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
                "border-radius:10px;padding:8px 12px;font-size:13px;"
                f"color:{TXT_H};}}"
                f"QPlainTextEdit:focus{{border-color:{P};}}"
            )
            return e

        s4lo.addWidget(_lbl("Nhiệm vụ chính", 13, bold=True))
        s4lo.addWidget(_lbl(
            "Mỗi dòng = 1 nhiệm vụ. Ví dụ:\n"
            "Phát triển tính năng mới theo yêu cầu sản phẩm.\n"
            "Review code và hỗ trợ đồng đội.",
            11, color="#9ca3af"
        ))
        self.plain_duties = _ta(
            "Mỗi dòng là một nhiệm vụ chính...\n"
            "Ví dụ: Phát triển và duy trì hệ thống backend.\n"
            "Ví dụ: Phối hợp với team frontend và QA.",
            110
        )
        s4lo.addWidget(self.plain_duties)

        row_reqs = QHBoxLayout()
        row_reqs.setSpacing(16)

        col_req = QVBoxLayout(); col_req.setSpacing(6)
        col_req.addWidget(_lbl("Yêu cầu chuyên môn", 13, bold=True))
        self.plain_requirements = _ta(
            "Mỗi dòng là một yêu cầu...\n"
            "Ví dụ: Tốt nghiệp CNTT hoặc liên quan.\n"
            "Ví dụ: Có kinh nghiệm với Python / Java.",
            110
        )
        col_req.addWidget(self.plain_requirements)

        col_soft = QVBoxLayout(); col_soft.setSpacing(6)
        col_soft.addWidget(_lbl("Kỹ năng mềm", 13, bold=True))
        self.plain_soft_skills = _ta(
            "Mỗi dòng là một kỹ năng...\n"
            "Ví dụ: Giao tiếp và làm việc nhóm tốt.\n"
            "Ví dụ: Tư duy phân tích và giải quyết vấn đề.",
            110
        )
        col_soft.addWidget(self.plain_soft_skills)

        row_reqs.addLayout(col_req, 1)
        row_reqs.addLayout(col_soft, 1)
        s4lo.addLayout(row_reqs)

        s4lo.addWidget(_lbl("Quyền lợi & Phúc lợi", 13, bold=True))
        s4lo.addWidget(_lbl(
            "Mỗi dòng = 1 quyền lợi. Ví dụ: Bảo hiểm sức khỏe toàn diện.",
            11, color="#9ca3af"
        ))
        self.plain_benefits = _ta(
            "Mỗi dòng là một quyền lợi...\n"
            "Ví dụ: Bảo hiểm y tế, nha khoa và thị lực.\n"
            "Ví dụ: Thưởng hiệu suất hàng quý.\n"
            "Ví dụ: Giờ làm việc linh hoạt.",
            110
        )
        s4lo.addWidget(self.plain_benefits)
        outer.addWidget(s4)

        # ── Action bar ──────────────────────────────────────────
        btn_lo = QHBoxLayout()
        btn_lo.setSpacing(12)
        self.btn_draft  = _btn_secondary("Lưu nháp")
        self.btn_submit = _btn_primary("Đăng tin ngay")
        self.btn_draft.setIcon(QIcon(_svg_pm("ic_doc.svg", 16, P)))
        self.btn_draft.setIconSize(QSize(16, 16))
        self.btn_submit.setIcon(QIcon(_svg_pm("ic_edit.svg", 16, "#ffffff")))
        self.btn_submit.setIconSize(QSize(16, 16))
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

        btn_jobs_reset = QPushButton("Xóa lọc")
        btn_jobs_reset.setFixedHeight(42)
        btn_jobs_reset.setCursor(Qt.PointingHandCursor)
        btn_jobs_reset.setIcon(QIcon(_svg_pm("ic_x.svg", 14, TXT_M)))
        btn_jobs_reset.setIconSize(QSize(14, 14))
        btn_jobs_reset.setStyleSheet(
            f"QPushButton{{background:#f1f5f9;color:{TXT_S};"
            "border:none;border-radius:10px;padding:0 14px;font-size:13px;}}"
            "QPushButton:hover{background:#e2e8f0;}"
        )
        def _reset_jobs():
            self._jobs_search.clear()
            self._jobs_status_filter.setCurrentIndex(0)
            self._jobs_type_filter.setCurrentIndex(0)
            self._filter_jobs("")
        btn_jobs_reset.clicked.connect(_reset_jobs)
        toolbar.addWidget(btn_jobs_reset)

        # "+ Đăng tin mới" button
        btn_new = _btn_primary("+ Đăng tin mới")
        btn_new.setIcon(QIcon(_svg_pm("ic_edit.svg", 16, "#ffffff")))
        btn_new.setIconSize(QSize(16, 16))
        btn_new.setFixedHeight(42)
        btn_new.setMinimumWidth(150)
        btn_new.clicked.connect(lambda: self._go(1))
        toolbar.addWidget(btn_new)
        outer.addLayout(toolbar)

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
            f"color:{TXT_H};font-size:15px;font-weight:600;"
            "background:transparent;border:none;letter-spacing:-0.2px;"
        )
        self._lbl_job_count = QLabel()
        self._lbl_job_count.setStyleSheet(
            f"background:#ede9fe;color:{P};font-size:11px;"
            "font-weight:600;border-radius:10px;padding:2px 10px;"
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
        _nr_jobs = QWidget()
        _nr_jobs.setFixedHeight(56)
        _nr_jobs.setStyleSheet("background:transparent;")
        _nr_lo = QHBoxLayout(_nr_jobs)
        _nr_lo.setContentsMargins(0, 0, 0, 0)
        _nr_lo.setSpacing(8)
        _nr_lo.setAlignment(Qt.AlignCenter)
        _nr_ic = QLabel(); _nr_ic.setPixmap(_svg_pm("ic_search.svg", 14, TXT_M))
        _nr_ic.setStyleSheet("background:transparent;border:none;")
        _nr_txt = QLabel("Không tìm thấy tin đăng nào khớp với bộ lọc.")
        _nr_txt.setStyleSheet(f"color:{TXT_M};font-size:13px;background:transparent;border:none;")
        _nr_lo.addWidget(_nr_ic); _nr_lo.addWidget(_nr_txt)
        self._jobs_no_result_lbl = _nr_jobs
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

        # Proportional resizer: Title 62% — Dept 38% of flexible space
        # Fixed cols: Date(120)+Applied(108)+Status(146)+Actions(168) = 542
        self._jobs_resizer = _ColResizeFilter(
            self.table_jobs, 0, 1, 0.62, 542
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
        btn_reset = QPushButton("Xóa lọc")
        btn_reset.setIcon(QIcon(_svg_pm("ic_x.svg", 14, TXT_M)))
        btn_reset.setIconSize(QSize(14, 14))
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

        # ── Table card ────────────────────────────────────────
        frame, flo = _card_frame()
        flo.setSpacing(16)

        hdr_row = QHBoxLayout()
        hdr_ic = QLabel()
        hdr_ic.setPixmap(_svg_pm("ic_users.svg", 18, "#f59e0b"))
        hdr_ic.setStyleSheet("background:transparent;")
        hdr_lbl = QLabel("Danh sách ứng viên")
        hdr_lbl.setStyleSheet(
            f"color:{TXT_H};font-size:15px;font-weight:600;"
            "background:transparent;border:none;letter-spacing:-0.2px;"
        )
        self._lbl_cand_count = QLabel()
        self._lbl_cand_count.setStyleSheet(
            "background:#fef3c7;color:#d97706;font-size:11px;"
            "font-weight:600;border-radius:10px;padding:2px 10px;"
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
        _nr_cands = QWidget()
        _nr_cands.setFixedHeight(56)
        _nr_cands.setStyleSheet("background:transparent;")
        _nc_lo = QHBoxLayout(_nr_cands)
        _nc_lo.setContentsMargins(0, 0, 0, 0)
        _nc_lo.setSpacing(8)
        _nc_lo.setAlignment(Qt.AlignCenter)
        _nc_ic = QLabel(); _nc_ic.setPixmap(_svg_pm("ic_search.svg", 14, TXT_M))
        _nc_ic.setStyleSheet("background:transparent;border:none;")
        _nc_txt = QLabel("Không tìm thấy ứng viên nào khớp với bộ lọc.")
        _nc_txt.setStyleSheet(f"color:{TXT_M};font-size:13px;background:transparent;border:none;")
        _nc_lo.addWidget(_nc_ic); _nc_lo.addWidget(_nc_txt)
        self._cands_no_result_lbl = _nr_cands
        self._cands_no_result_lbl.setVisible(False)
        flo.addWidget(self._cands_no_result_lbl)

        # Proportional resizer: Ứng viên 36% — Vị trí 64% of flexible space
        # Fixed cols: Date(140)+Status(136)+Actions(168) = 444
        self._cands_resizer = _ColResizeFilter(
            self.table_cands, 0, 1, 0.36, 444
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
        self._cands_keyword: str = ""
        self._cands_status_value: str | None = None
        self._cands_sort_value: str = "newest"

        # Card wraps content — space distributed 1:2 above:below
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(frame, 1)
        return pg

    # ── navigation ────────────────────────────────────────────
    def _build_billing_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        pg = QWidget()
        pg.setStyleSheet(f"background:{CONTENT_BG};")
        outer = QVBoxLayout(pg)
        outer.setContentsMargins(40, 34, 40, 34)
        outer.setSpacing(24)

        summary_grid = QGridLayout()
        summary_grid.setHorizontalSpacing(16)
        summary_grid.setVerticalSpacing(16)
        self._billing_labels: dict[str, QLabel] = {}

        def _summary_card(key: str, title: str, icon: str, color: str, soft: str) -> QFrame:
            card = QFrame()
            card.setMinimumHeight(118)
            card.setStyleSheet(f"QFrame{{background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;}}")
            _shadow(card, blur=16, dy=4, alpha=14)
            lo = QHBoxLayout(card)
            lo.setContentsMargins(18, 14, 18, 14)
            lo.setSpacing(14)
            ic = QLabel()
            ic.setFixedSize(52, 52)
            ic.setAlignment(Qt.AlignCenter)
            ic.setPixmap(_svg_pm(icon, 24, color))
            ic.setStyleSheet(f"background:{soft};border-radius:26px;border:none;")
            copy = QVBoxLayout()
            copy.setSpacing(4)
            ttl = QLabel(title)
            ttl.setStyleSheet(f"color:#1f2942;font-size:12px;font-weight:800;letter-spacing:0.5px;background:transparent;border:none;")
            val = QLabel("0")
            if key == "period_range":
                val.setWordWrap(True)
                val.setStyleSheet(
                    f"color:{TXT_H};font-size:16px;font-weight:800;background:transparent;border:none;"
                )
            else:
                val.setStyleSheet(
                    f"color:{TXT_H};font-size:24px;font-weight:900;background:transparent;border:none;"
                )
            self._billing_labels[key] = val
            copy.addWidget(ttl)
            copy.addWidget(val)
            lo.addWidget(ic)
            lo.addLayout(copy, 1)
            return card

        summary_grid.addWidget(_summary_card("total", "TỔNG CHI PHÍ", "ic_card.svg", "#4f46e5", "#ddd6fe"), 0, 0)
        summary_grid.addWidget(_summary_card("approved", "ỨNG VIÊN ĐÃ NHẬN", "ic_users.svg", "#16a34a", "#dcfce7"), 0, 1)
        summary_grid.addWidget(_summary_card("period_range", "KỲ THANH TOÁN", "ic_calendar.svg", "#6366f1", "#e0e7ff"), 1, 0, 1, 2)
        summary_grid.setColumnStretch(0, 1)
        summary_grid.setColumnStretch(1, 1)
        outer.addLayout(summary_grid)

        table_card = QFrame()
        table_card.setStyleSheet(f"QFrame{{background:{CARD_BG};border:1px solid {BORDER};border-radius:14px;}}")
        _shadow(table_card, blur=16, dy=4, alpha=12)
        table_lo = QVBoxLayout(table_card)
        table_lo.setContentsMargins(0, 0, 0, 0)
        table_lo.setSpacing(0)

        filter_bar = QHBoxLayout()
        filter_bar.setContentsMargins(30, 30, 30, 24)
        filter_bar.setSpacing(16)
        self._billing_status_filter = _combo(["Trạng thái hóa đơn: Tất cả", "Đã thanh toán", "Đang chờ thanh toán", "Quá hạn"])
        self._billing_status_filter.setFixedSize(250, 48)
        self._billing_period_filter = _combo(["Thời gian: 30 ngày gần nhất", "Tháng này", "Quý này", "Tất cả thời gian"])
        self._billing_period_filter.setFixedSize(280, 48)
        self._billing_status_filter.currentIndexChanged.connect(self._refresh_billing_page)
        self._billing_period_filter.currentIndexChanged.connect(self._refresh_billing_page)
        self._billing_period_filter.setCurrentIndex(3)  # default: tất cả thời gian
        filter_bar.addWidget(self._billing_status_filter)
        filter_bar.addWidget(self._billing_period_filter)
        filter_bar.addStretch()
        filter_btn = QPushButton()
        filter_btn.setFixedSize(52, 52)
        filter_btn.setCursor(Qt.PointingHandCursor)
        filter_btn.setIcon(QIcon(_svg_pm("ic_search.svg", 18, TXT_M)))
        filter_btn.setIconSize(QSize(18, 18))
        filter_btn.setToolTip("Lọc hóa đơn")
        filter_btn.setStyleSheet(
            f"QPushButton{{background:#f8fafc;border:1px solid {BORDER};border-radius:10px;}}"
            "QPushButton:hover{background:#eef2ff;}"
        )
        filter_bar.addWidget(filter_btn)
        table_lo.addLayout(filter_bar)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background:{BORDER};border:none;")
        table_lo.addWidget(divider)

        self.table_billing = QTableWidget(0, 8)
        self.table_billing.setHorizontalHeaderLabels(
            ["Mã hóa đơn", "Công ty", "Ngày", "Kỳ thanh toán", "Hạn thanh toán", "Số tiền", "Trạng thái", "Thao tác"]
        )
        self.table_billing.verticalHeader().setVisible(False)
        self.table_billing.verticalHeader().setDefaultSectionSize(58)
        self.table_billing.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_billing.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_billing.setAlternatingRowColors(False)
        self.table_billing.setFocusPolicy(Qt.NoFocus)
        self.table_billing.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table_billing.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_billing.horizontalHeader().setStretchLastSection(False)
        _bh = self.table_billing.horizontalHeader()
        # Responsive: cột dài co giãn theo chiều ngang cửa sổ
        _bh.setSectionResizeMode(0, QHeaderView.Stretch)  # Mã hóa đơn
        _bh.setSectionResizeMode(1, QHeaderView.Stretch)  # Công ty
        _bh.setSectionResizeMode(2, QHeaderView.Fixed)
        _bh.setSectionResizeMode(3, QHeaderView.Fixed)
        _bh.setSectionResizeMode(4, QHeaderView.Stretch)  # Hạn thanh toán
        _bh.setSectionResizeMode(5, QHeaderView.Fixed)
        _bh.setSectionResizeMode(6, QHeaderView.Fixed)
        _bh.setSectionResizeMode(7, QHeaderView.Fixed)
        _bh.setMinimumSectionSize(88)
        _bh.setFixedHeight(44)
        self.table_billing.setColumnWidth(2, 110)  # Ngày
        self.table_billing.setColumnWidth(3, 120)  # Kỳ thanh toán
        self.table_billing.setColumnWidth(5, 130)  # Số tiền
        self.table_billing.setColumnWidth(6, 170)  # Trạng thái
        self.table_billing.setColumnWidth(7, 120)  # Thao tác
        self.table_billing.setMinimumHeight(560)
        self.table_billing.setStyleSheet(
            "QTableWidget{background:#ffffff;border:none;gridline-color:#eef2f7;font-size:14px;color:#0f172a;}"
            "QHeaderView::section{background:#ffffff;color:#1f2942;font-size:13px;font-weight:800;border:none;border-bottom:1px solid #e2e8f0;padding:10px 10px;}"
            "QTableWidget::item{padding:12px 10px;border:none;border-bottom:1px solid #eef2f7;}"
            "QTableWidget::item:focus{outline:none;border:none;}"
            "QTableWidget::item:selected{background:#eef2ff;color:#1e1b4b;}"
        )
        table_lo.addWidget(self.table_billing)

        self._billing_page_label = QLabel("")
        self._billing_page_label.setStyleSheet(f"color:{TXT_M};font-size:13px;background:transparent;border:none;padding:18px 30px;")
        table_lo.addWidget(self._billing_page_label)
        outer.addWidget(table_card)
        outer.addStretch()
        scroll.setWidget(pg)
        return scroll

    def _billing_rows(self) -> tuple[list[dict], int, str]:
        try:
            invoices = list(jobhub_api.hr_invoices())
        except ApiError:
            invoices = []
        rows: list[dict] = []
        total = 0
        current_period = datetime.now().strftime("%m/%Y")
        period_ranges: list[tuple[datetime, datetime]] = []
        for inv in invoices:
            amt = _to_int(inv.get("amount_vnd") or inv.get("amount") or 0)
            total += amt
            created_raw = str(inv.get("created_at") or "")
            due_raw = str(inv.get("due_at") or "")
            try:
                created_dt = datetime.fromisoformat(created_raw.replace("Z", "+00:00")) if created_raw else datetime.now()
            except Exception:
                created_dt = datetime.now()
            try:
                due_dt = datetime.fromisoformat(due_raw.replace("Z", "+00:00")) if due_raw else None
            except Exception:
                due_dt = None
            status_key = str(inv.get("status") or "pending").lower()
            if status_key == "paid":
                status_text = "Đã thanh toán"
            elif status_key == "overdue":
                status_text = "Quá hạn"
            elif status_key == "due":
                status_text = "Đến hạn thanh toán"
            elif status_key == "cancelled":
                status_text = "Đã hủy"
            else:
                status_text = "Đang chờ thanh toán"
            period_text = str(inv.get("period") or (due_dt.strftime("%m/%Y") if due_dt else current_period))
            period_start_raw = str(inv.get("period_start") or "").strip()
            period_end_raw = str(inv.get("period_end") or "").strip()
            period_start_dt: datetime | None = None
            period_end_dt: datetime | None = None
            try:
                if period_start_raw:
                    period_start_dt = datetime.strptime(period_start_raw, "%d/%m/%Y")
            except Exception:
                period_start_dt = None
            try:
                if period_end_raw:
                    period_end_dt = datetime.strptime(period_end_raw, "%d/%m/%Y")
            except Exception:
                period_end_dt = None
            if period_start_dt and period_end_dt:
                period_ranges.append((period_start_dt, period_end_dt))

            rows.append({
                "invoice_id": f"#{str(inv.get('invoice_code') or f'HD-{_to_int(inv.get('id')):05d}')}",
                "candidate": "—",
                "job": "Hóa đơn tuyển dụng theo kỳ",
                "date": created_dt.strftime("%d/%m/%Y"),
                "created_dt": created_dt,
                "period": period_text,
                "avg_salary": 0,
                "fee": amt,
                "status": status_text,
                "due_date": due_dt.strftime("%d/%m/%Y") if due_dt else "—",
                "note": str(inv.get("note") or ""),
                "period_start": period_start_raw,
                "period_end": period_end_raw,
                "period_start_dt": period_start_dt,
                "period_end_dt": period_end_dt,
                "payment_window_start": str(inv.get("payment_window_start") or ""),
                "payment_window_end": str(inv.get("payment_window_end") or ""),
                "payment_window": (
                    f"{str(inv.get('payment_window_start') or '—')} - {str(inv.get('payment_window_end') or '—')}"
                ),
                "can_pay_now": bool(inv.get("can_pay_now")),
                "payment_url": str(inv.get("sepay_payment_url") or ""),
            })
        if period_ranges:
            earliest_start = min(x[0] for x in period_ranges)
            latest_end = max(x[1] for x in period_ranges)
            period_range_label = f"{earliest_start.strftime('%d/%m/%Y')} - {latest_end.strftime('%d/%m/%Y')}"
        else:
            period_range_label = "—"
        return rows, total, period_range_label

    def _refresh_billing_page(self) -> None:
        rows, total, period_range = self._billing_rows()
        period_idx = getattr(self, "_billing_period_filter", None).currentIndex() if hasattr(self, "_billing_period_filter") else 0
        now = datetime.now()
        def _row_in_selected_cycle(r: dict) -> bool:
            p_start = r.get("period_start_dt")
            p_end = r.get("period_end_dt")
            if not isinstance(p_start, datetime) or not isinstance(p_end, datetime):
                return period_idx == 3
            if period_idx == 0:  # 30 ngày gần nhất theo chu kỳ
                threshold = now - timedelta(days=30)
                return p_end >= threshold
            if period_idx == 1:  # Tháng này theo chu kỳ hóa đơn
                return p_end.month == now.month and p_end.year == now.year
            if period_idx == 2:  # Quý này theo chu kỳ hóa đơn
                q_now = (now.month - 1) // 3 + 1
                q_end = (p_end.month - 1) // 3 + 1
                return p_end.year == now.year and q_end == q_now
            return True

        status_idx = getattr(self, "_billing_status_filter", None).currentIndex() if hasattr(self, "_billing_status_filter") else 0
        if status_idx == 1:
            rows = [r for r in rows if r["status"] == "Đã thanh toán"]
        elif status_idx == 2:
            rows = [r for r in rows if r["status"] in {"Đang chờ thanh toán", "Đến hạn thanh toán"}]
        elif status_idx == 3:
            rows = [r for r in rows if r["status"] == "Quá hạn"]
        rows = [r for r in rows if _row_in_selected_cycle(r)]

        try:
            approved_apps_payload = jobhub_api.hr_applications(status_filter="approved")
            approved_apps = list(approved_apps_payload.get("items") or []) if isinstance(approved_apps_payload, dict) else list(approved_apps_payload)
        except ApiError:
            approved_apps = []
        cycle_ranges: list[tuple[datetime, datetime]] = []
        for r in rows:
            p_start = r.get("period_start_dt")
            p_end = r.get("period_end_dt")
            if isinstance(p_start, datetime) and isinstance(p_end, datetime):
                cycle_ranges.append((p_start, p_end))

        def _in_any_cycle(dt: datetime) -> bool:
            if not cycle_ranges:
                return False
            return any(start <= dt <= end for start, end in cycle_ranges)

        approved_count = 0
        for app in approved_apps:
            accepted_raw = str(app.get("accepted_at") or "").strip()
            applied_raw = str(app.get("applied_at") or "").strip()
            dt: datetime | None = None
            try:
                if accepted_raw:
                    dt = datetime.fromisoformat(accepted_raw.replace("Z", "+00:00"))
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                elif applied_raw:
                    dt = datetime.strptime(applied_raw, "%d/%m/%Y")
            except Exception:
                dt = None
            if dt and _in_any_cycle(dt):
                approved_count += 1

        filtered_total = sum(_to_int(r.get("fee") or 0) for r in rows)
        self._billing_labels["approved"].setText(str(approved_count))
        self._billing_labels["total"].setText(_fmt_vnd(filtered_total))
        self._billing_labels["period_range"].setText(period_range)

        self.table_billing.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self.table_billing.setRowHeight(r, 58)
            values = [
                row["invoice_id"],
                "TechCorp HR",
                row["date"],
                row["period"],
                row.get("payment_window", "—"),
                _fmt_vnd(row["fee"]),
                row["status"],
                "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(str(value))
                if c == 5:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                elif c in (6, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table_billing.setItem(r, c, item)
            status_item = self.table_billing.item(r, 6)
            if status_item:
                _status_color = "#b45309"
                if row["status"] == "Đã thanh toán":
                    _status_color = "#059669"
                elif row["status"] == "Quá hạn":
                    _status_color = "#dc2626"
                status_item.setForeground(QColor(_status_color))
                status_item.setTextAlignment(Qt.AlignCenter)
            action = QPushButton()
            action.setText("Chi tiết")
            action.setFixedSize(90, 34)
            action.setCursor(Qt.PointingHandCursor)
            action.setToolTip("Xem chi tiết hóa đơn")
            action.setStyleSheet(
                f"QPushButton{{background:#eef2ff;color:{P_DARK};border:none;border-radius:8px;font-size:11px;font-weight:700;}}"
                f"QPushButton:hover{{background:#e0e7ff;}}"
            )
            action.clicked.connect(lambda _=False, _row=row: self._show_invoice_detail(_row))
            action_wrap = QWidget()
            action_lo = QHBoxLayout(action_wrap)
            action_lo.setContentsMargins(0, 0, 0, 0)
            action_lo.setAlignment(Qt.AlignCenter)
            action_lo.addWidget(action)
            self.table_billing.setCellWidget(r, 7, action_wrap)
        self.table_billing.setFixedHeight(max(520, 58 + len(rows) * 64))
        if hasattr(self, "_billing_page_label"):
            shown = len(rows)
            self._billing_page_label.setText(f"Hiển thị {shown} trong {shown} hóa đơn")

    def _show_invoice_detail(self, row: dict) -> None:
        import webbrowser

        dlg = QDialog(self.win)
        dlg.setWindowTitle(f"Chi tiết hóa đơn {row.get('invoice_id', '')}")
        dlg.setMinimumWidth(560)
        dlg.setStyleSheet(
            f"QDialog{{background:{CONTENT_BG};}}"
            f"QLabel{{color:{TXT_H};background:transparent;border:none;}}"
        )
        lo = QVBoxLayout(dlg)
        lo.setContentsMargins(20, 18, 20, 18)
        lo.setSpacing(14)

        header_card = QFrame()
        header_card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:14px;}")
        _shadow(header_card, 12, 2, 10)
        hlo = QVBoxLayout(header_card)
        hlo.setContentsMargins(16, 14, 16, 14)
        hlo.setSpacing(8)

        title = QLabel(f"Hóa đơn {row.get('invoice_id', '')}")
        title.setStyleSheet(f"color:{TXT_H};font-size:21px;font-weight:900;background:transparent;border:none;")
        amount_lbl = QLabel(_fmt_vnd(row.get("fee", 0)))
        amount_lbl.setStyleSheet(f"color:{P_DARK};font-size:28px;font-weight:900;background:transparent;border:none;")
        period_lbl = QLabel(
            f"Kỳ thanh toán: {row.get('period_start', '—')} - {row.get('period_end', '—')}"
        )
        period_lbl.setStyleSheet(f"color:{TXT_S};font-size:13px;font-weight:600;background:transparent;border:none;")
        hlo.addWidget(title)
        hlo.addWidget(amount_lbl)
        hlo.addWidget(period_lbl)
        lo.addWidget(header_card)

        info_card = QFrame()
        info_card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:14px;}")
        _shadow(info_card, 10, 2, 8)
        info_lo = QGridLayout(info_card)
        info_lo.setContentsMargins(16, 14, 16, 14)
        info_lo.setHorizontalSpacing(18)
        info_lo.setVerticalSpacing(10)

        def _meta(label: str, value: str) -> tuple[QLabel, QLabel]:
            l = QLabel(label)
            l.setStyleSheet(f"color:{TXT_M};font-size:11px;font-weight:800;border:none;background:transparent;")
            v = QLabel(value)
            v.setStyleSheet(f"color:{TXT_H};font-size:13px;font-weight:700;border:none;background:transparent;")
            return l, v

        company_l, company_v = _meta("CÔNG TY", "TechCorp HR")
        created_l, created_v = _meta("NGÀY PHÁT SINH", row.get("date", "—"))
        period_l, period_v = _meta(
            "KỲ THANH TOÁN",
            f"{row.get('period_start', '—')} - {row.get('period_end', '—')}",
        )
        paywin_l, paywin_v = _meta(
            "HẠN THANH TOÁN",
            f"{row.get('payment_window_start', '—')} - {row.get('payment_window_end', '—')}",
        )
        status_l, status_v = _meta("TRẠNG THÁI", row.get("status", "—"))
        info_lo.addWidget(company_l, 0, 0); info_lo.addWidget(company_v, 1, 0)
        info_lo.addWidget(created_l, 0, 1); info_lo.addWidget(created_v, 1, 1)
        info_lo.addWidget(period_l, 2, 0); info_lo.addWidget(period_v, 3, 0)
        info_lo.addWidget(status_l, 2, 1); info_lo.addWidget(status_v, 3, 1)
        info_lo.addWidget(paywin_l, 4, 0); info_lo.addWidget(paywin_v, 5, 0, 1, 2)
        lo.addWidget(info_card)

        note_card = QFrame()
        note_card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:12px;}")
        note_lo = QVBoxLayout(note_card)
        note_lo.setContentsMargins(14, 12, 14, 12)
        note_lo.setSpacing(6)
        note_title = QLabel("Ghi chú hóa đơn")
        note_title.setStyleSheet(f"color:{TXT_M};font-size:11px;font-weight:800;")
        note_text = QLabel(row.get("note", "—") or "—")
        note_text.setWordWrap(True)
        note_text.setStyleSheet(f"color:{TXT_S};font-size:13px;font-weight:600;")
        note_lo.addWidget(note_title)
        note_lo.addWidget(note_text)
        lo.addWidget(note_card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        pay_wrap = QWidget()
        pay_lo = QHBoxLayout(pay_wrap)
        pay_lo.setContentsMargins(0, 0, 0, 0)
        pay_lo.setSpacing(0)
        btn_row.addWidget(pay_wrap)
        btn_row.addSpacing(8)
        btn = QPushButton("Đóng")
        btn.setFixedHeight(38)
        btn.setStyleSheet(
            "QPushButton{background:#e2e8f0;color:#0f172a;border:none;border-radius:10px;font-weight:700;padding:0 14px;}"
            "QPushButton:hover{background:#cbd5e1;}"
        )
        btn.clicked.connect(dlg.accept)
        btn_row.addWidget(btn)
        lo.addLayout(btn_row)

        current_row: dict = dict(row)

        def _render_pay_action() -> None:
            while pay_lo.count():
                it = pay_lo.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            if current_row.get("can_pay_now") and current_row.get("payment_url"):
                btn_pay = QPushButton("Thanh toán")
                btn_pay.setFixedHeight(38)
                btn_pay.setCursor(Qt.PointingHandCursor)
                btn_pay.setStyleSheet(
                    f"QPushButton{{background:{P};color:#fff;border:none;border-radius:10px;font-weight:800;padding:0 14px;}}"
                    f"QPushButton:hover{{background:{P_DARK};}}"
                )

                def _pay_and_poll(_checked=False) -> None:
                    url = str(current_row.get("payment_url") or "").strip()
                    if url:
                        try:
                            webbrowser.open(url)
                        except Exception:
                            pass
                    inv_code = str(current_row.get("invoice_id") or "").lstrip("#").strip()
                    if inv_code:
                        self._start_billing_refresh_poll(inv_code)
                        self._show_toast(
                            "Đã mở cổng SePay. Hệ thống sẽ tự đồng bộ ngay khi thanh toán thành công.",
                            "ic_view.svg",
                            "#6366f1",
                        )

                btn_pay.clicked.connect(_pay_and_poll)
                pay_lo.addWidget(btn_pay)

        def _apply_invoice_row(new_row: dict) -> None:
            incoming = dict(new_row or {})
            # Defensive merge: keep previous non-empty values if incoming payload is partial.
            for k in [
                "invoice_id", "fee", "period_start", "period_end", "date",
                "payment_window_start", "payment_window_end", "status",
                "note", "payment_url", "can_pay_now",
            ]:
                v = incoming.get(k)
                if v is None or (isinstance(v, str) and not v.strip()):
                    incoming[k] = current_row.get(k)
            if (incoming.get("fee") in (None, 0, "0", "0.0")) and current_row.get("fee"):
                incoming["fee"] = current_row.get("fee")
            current_row.update(incoming)
            amount_lbl.setText(_fmt_vnd(current_row.get("fee") or 0))
            period_lbl.setText(
                f"Kỳ thanh toán: {current_row.get('period_start', '—')} - {current_row.get('period_end', '—')}"
            )
            created_v.setText(str(current_row.get("date") or "—"))
            period_v.setText(f"{current_row.get('period_start', '—')} - {current_row.get('period_end', '—')}")
            paywin_v.setText(
                f"{current_row.get('payment_window_start', '—')} - {current_row.get('payment_window_end', '—')}"
            )
            status_v.setText(str(current_row.get("status") or "—"))
            note_text.setText(str(current_row.get("note") or "—"))
            _render_pay_action()

        _apply_invoice_row(current_row)
        inv_code = str(current_row.get("invoice_id") or "").lstrip("#").strip()
        self._billing_detail_invoice_code = inv_code
        self._billing_detail_refresh_cb = _apply_invoice_row

        def _clear_detail_binding() -> None:
            if self._billing_detail_invoice_code == inv_code:
                self._billing_detail_invoice_code = ""
                self._billing_detail_refresh_cb = None

        dlg.finished.connect(lambda _res=0: _clear_detail_binding())
        dlg.exec()

    def _start_billing_refresh_poll(self, invoice_code: str) -> None:
        self._billing_poll_invoice_code = str(invoice_code or "").strip()
        if not self._billing_poll_invoice_code:
            return
        if self._billing_poll_timer is None:
            self._billing_poll_timer = QTimer(self.win)
            self._billing_poll_timer.setInterval(4000)
            self._billing_poll_timer.timeout.connect(self._poll_billing_after_payment)
        if self._billing_poll_timer.isActive():
            self._billing_poll_timer.stop()
        self._billing_poll_timer.start()

    def _poll_billing_after_payment(self) -> None:
        invoice_code = str(self._billing_poll_invoice_code or "").strip()
        if not invoice_code:
            if self._billing_poll_timer and self._billing_poll_timer.isActive():
                self._billing_poll_timer.stop()
            return
        try:
            invoices = list(jobhub_api.hr_invoices() or [])
        except Exception:
            return
        for inv in invoices:
            code = str(inv.get("invoice_code") or "").strip()
            if code != invoice_code:
                continue
            status_key = str(inv.get("status") or "").strip().lower()
            if status_key == "paid":
                if self._billing_poll_timer and self._billing_poll_timer.isActive():
                    self._billing_poll_timer.stop()
                self._refresh_billing_page()
                if self._billing_detail_invoice_code and self._billing_detail_invoice_code == invoice_code:
                    rows, _total, _period = self._billing_rows()
                    matched = next(
                        (
                            r for r in rows
                            if str(r.get("invoice_id") or "").lstrip("#").strip() == invoice_code
                        ),
                        None,
                    )
                    if matched and callable(self._billing_detail_refresh_cb):
                        try:
                            self._billing_detail_refresh_cb(matched)
                        except Exception:
                            pass
                self._show_toast("Thanh toán thành công. Hóa đơn đã được cập nhật.", "ic_check.svg", "#10b981")
            return

    def _go(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_btns):
            btn.set_active(i == idx)

        titles = [
            "Bảng điều khiển",
            "Đăng tin mới",
            "Quản lý tin đăng",
            "Đơn ứng tuyển",
            "Hóa đơn",
            "Hồ sơ nhà tuyển dụng",
        ]
        subs = [
            "Theo dõi hiệu quả tuyển dụng của bạn",
            "Tạo tin tuyển dụng mới cho ứng viên",
            "Xem và chỉnh sửa các tin tuyển dụng đang hoạt động",
            "Quản lý các ứng viên đã ứng tuyển",
            "Quản lý và theo dõi các khoản phí tuyển dụng phát sinh",
            "Cập nhật thông tin công ty và ảnh đại diện",
        ]
        self.lbl_page_title.setText(titles[idx])
        self.lbl_page_sub.setText(subs[idx])

        if idx == 0:
            self._load_dash()
        elif idx == 2:
            self._fill_jobs_table()
        elif idx == 3:
            self._fill_cands_table()
        elif idx == 4:
            self._refresh_billing_page()
        elif idx == 5:
            self._load_hr_identity()

    def _validate_salary_pair(self, min_text: str, max_text: str, parent=None) -> tuple[int, int] | None:
        parent = parent or self.win
        min_text = min_text.strip()
        max_text = max_text.strip()
        if not min_text.isdigit() or not max_text.isdigit():
            QMessageBox.warning(parent, "Lương không hợp lệ", "Vui lòng nhập lương tối thiểu và tối đa bằng số.")
            return None
        min_salary = int(min_text)
        max_salary = int(max_text)
        if min_salary <= 0 or max_salary <= 0:
            QMessageBox.warning(parent, "Lương không hợp lệ", "Lương tối thiểu và tối đa phải lớn hơn 0.")
            return None
        if max_salary <= min_salary:
            QMessageBox.warning(parent, "Lương không hợp lệ", "Lương tối đa phải lớn hơn lương tối thiểu.")
            return None
        return min_salary, max_salary

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
        dept     = self.line_dept.text().strip() or "Kỹ thuật & Công nghệ"
        min_salary_txt = self.line_min_salary.text().strip()
        max_salary_txt = self.line_max_salary.text().strip()
        location = self.line_location.text().strip()
        count    = self.line_count.text().strip() or "1"
        deadline = self.line_deadline.text().strip()
        desc         = self.plain_desc.toPlainText().strip()
        duties       = self.plain_duties.toPlainText().strip()
        requirements = self.plain_requirements.toPlainText().strip()
        soft_skills  = self.plain_soft_skills.toPlainText().strip()
        benefits     = self.plain_benefits.toPlainText().strip()

        salary_pair = self._validate_salary_pair(min_salary_txt, max_salary_txt)
        if not salary_pair:
            return
        min_salary, max_salary = salary_pair
        encoded_desc = _encode_desc(desc, duties, requirements, soft_skills, benefits)
        try:
            jobhub_api.hr_create_job(
                {
                    "title": title,
                    "description": encoded_desc,
                    "department": dept,
                    "level": level,
                    "min_salary": min_salary,
                    "max_salary": max_salary,
                    "location": location or "Hà Nội",
                    "job_type": job_type,
                    "count": int(count) if str(count).isdigit() else 1,
                    "deadline": deadline,
                    "as_draft": draft,
                }
            )
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return

        # Clear form
        self.line_title.clear()
        self.line_dept.clear()
        self.line_min_salary.clear()
        self.line_max_salary.clear()
        self.line_location.clear()
        self.line_count.clear()
        self.line_deadline.clear()
        self.plain_desc.clear()
        self.plain_duties.clear()
        self.plain_requirements.clear()
        self.plain_soft_skills.clear()
        self.plain_benefits.clear()

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
        try:
            self._jobs_all_data = list(jobhub_api.hr_my_jobs())
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            self._jobs_all_data = []
        self._jobs_data = list(self._jobs_all_data)
        self._jobs_page = 0
        self._render_jobs_page()

    def _on_jobs_search_changed(self, text: str) -> None:
        """Show/hide clear button + trigger filter."""
        self._jobs_search_clear.setVisible(bool(text))
        self._filter_jobs(text)

    def _filter_jobs(self, text: str) -> None:
        kw = text.strip().lower()
        all_jobs = list(getattr(self, "_jobs_all_data", self._jobs_data))

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
        self._jobs_no_result_lbl.setVisible(total == 0)
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
        COLS = ["Tiêu đề công việc", "Phòng ban",
                "Ngày đăng", "Ứng tuyển", "Trạng thái", "Thao tác"]
        tbl  = self.table_jobs
        tbl.setColumnCount(len(COLS))
        tbl.setHorizontalHeaderLabels(COLS)
        tbl.setRowCount(len(jobs))

        for row, j in enumerate(jobs):
            # ── Title ────────────────────────────────────────
            t = QTableWidgetItem(j.get("title", ""))
            t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            t.setForeground(QColor(TXT_H))
            tbl.setItem(row, 0, t)

            # ── Department ───────────────────────────────────
            dept = QTableWidgetItem(j.get("department", "—"))
            dept.setForeground(QColor(TXT_S))
            tbl.setItem(row, 1, dept)

            # ── Date ─────────────────────────────────────────
            dt = QTableWidgetItem(j.get("created_at", "—"))
            dt.setTextAlignment(Qt.AlignCenter)
            dt.setForeground(QColor(TXT_M))
            tbl.setItem(row, 2, dt)

            # ── Applicants count ─────────────────────────────
            cnt = j.get("applicants_count", 0)
            cnt_item = QTableWidgetItem(str(cnt))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            cnt_item.setForeground(
                QColor(P) if cnt > 0 else QColor(TXT_M)
            )
            if cnt > 0:
                cnt_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            tbl.setItem(row, 3, cnt_item)

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
            tbl.setCellWidget(row, 4, badge_wrap)

            # ── Action buttons ───────────────────────────────
            tbl.setCellWidget(row, 5, self._make_job_actions(_to_int(j.get("id")), j.get("status", ""), j.get("title", "")))

        hh = tbl.horizontalHeader()
        # Cols 0+1 managed proportionally by _jobs_resizer (62 : 38)
        hh.setSectionResizeMode(0, QHeaderView.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.Fixed)
        hh.setSectionResizeMode(5, QHeaderView.Fixed)
        tbl.setColumnWidth(2, 120)
        tbl.setColumnWidth(3, 108)
        tbl.setColumnWidth(4, 146)
        tbl.setColumnWidth(5, 168)
        # Keep table visually stable and aligned on wide screens
        tbl.setMinimumHeight(360)
        tbl.setMaximumHeight(16777215)
        self._jobs_resizer._apply()   # set proportional widths immediately

    def _make_job_actions(self, job_id: int, status: str = "", job_title: str = "") -> QWidget:
        """Three icon-only action buttons per row with tooltip labels + toasts."""
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(wrap)
        lo.setContentsMargins(8, 0, 8, 0)
        lo.setSpacing(6)
        lo.setAlignment(Qt.AlignVCenter)

        def _ic_btn(svg: str, color: str, tint: str,
                    tooltip: str) -> QPushButton:
            """Glassmorphism + Duotone icon button."""
            h = color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            # Render icon with duotone (auto-lightened softColor)
            btn.setIcon(QIcon(_svg_pm(svg, 18, color)))
            btn.setIconSize(QSize(18, 18))
            btn.setStyleSheet(
                "QPushButton{"
                "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #ffffff,stop:1 #f5f7ff);"
                f"border:1px solid {BORDER};"
                "border-radius:11px;}"
                "QPushButton:hover{"
                f"background:rgba({r},{g},{b},0.09);"
                f"border:1.5px solid rgba({r},{g},{b},0.38);}}"
                "QPushButton:pressed{"
                f"background:rgba({r},{g},{b},0.16);"
                f"border:1.5px solid rgba({r},{g},{b},0.55);}}"
            )
            return btn

        def _center_dialog(d: QDialog) -> None:
            try:
                p = self.win.frameGeometry().center()
                r = d.frameGeometry()
                r.moveCenter(p)
                d.move(r.topLeft())
            except Exception:
                pass

        btn_edit = _ic_btn("ic_edit.svg",   "#6366f1", "#ede9fe", "Chỉnh sửa tin")
        btn_view = _ic_btn("ic_view.svg",   "#0ea5e9", "#e0f2fe", "Xem chi tiết")
        btn_submit = _ic_btn("ic_check.svg", "#10b981", "#d1fae5", "Gửi Admin duyệt")
        btn_del  = _ic_btn("ic_delete.svg", "#ef4444", "#fee2e2", "Xoá tin")

        # ── Edit dialog ──────────────────────────────────────────
        def _do_edit(_jid=job_id):
            try:
                job = jobhub_api.hr_get_job(_jid)
            except ApiError as e:
                self._show_toast(str(e), "ic_x.svg", "#ef4444")
                return
            if not job:
                self._show_toast("Không tìm thấy tin đăng!", "ic_x.svg", "#ef4444")
                return

            dlg = QDialog(self.win)
            _ttl = (job_title or str(job.get("title") or "")).strip() or f"#{_jid}"
            dlg.setWindowTitle(f"Chỉnh sửa tin - {_ttl}")
            dlg.resize(980, 760)
            dlg.setStyleSheet(
                f"QDialog{{background:{CONTENT_BG};}}"
                f"QLabel{{color:{TXT_H};background:transparent;border:none;}}"
            )
            root = QVBoxLayout(dlg)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            scroll = QScrollArea(dlg)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setStyleSheet(
                f"QScrollArea{{background:{CONTENT_BG}; border:none;}}"
                "QScrollBar:vertical{width:8px; background:transparent;}"
                "QScrollBar::handle:vertical{background:#cbd5e1; border-radius:4px;}"
            )
            body = QWidget()
            body.setStyleSheet(f"background:{CONTENT_BG};")
            vlo = QVBoxLayout(body)
            vlo.setContentsMargins(34, 24, 34, 24)
            vlo.setSpacing(18)

            # Header
            h_lbl = QLabel(f"Chỉnh sửa tin đăng: {_ttl}")
            h_lbl.setStyleSheet(
                f"color:{TXT_H};font-size:24px;font-weight:800;"
                "background:transparent;border:none;"
            )
            h_lbl.setAlignment(Qt.AlignCenter)
            h_sub = QLabel("Cập nhật nội dung tin tuyển dụng.")
            h_sub.setAlignment(Qt.AlignCenter)
            h_sub.setStyleSheet(
                f"color:{TXT_M};font-size:13px;background:transparent;border:none;"
            )
            vlo.addWidget(h_lbl)
            vlo.addWidget(h_sub)

            banner = QLabel(
                "ℹ️  Sau khi lưu chỉnh sửa, tin sẽ được chuyển về trạng thái chờ Admin duyệt lại."
            )
            banner.setWordWrap(True)
            banner.setStyleSheet(
                "background:#eff6ff;border:1.5px solid #bfdbfe;border-radius:10px;"
                "color:#1d4ed8;font-size:13px;padding:10px 14px;"
            )
            vlo.addWidget(banner)

            # SECTION 1: Thông tin cơ bản
            s1, s1lo = _card_frame()
            s1lo.setSpacing(14)
            s1lo.addWidget(_section_header("ic_edit.svg", "Thông tin cơ bản"))

            def _lbl(t):
                l = QLabel(t)
                l.setStyleSheet(
                    f"color:{TXT_S};font-size:12px;font-weight:600;"
                    "background:transparent;border:none;"
                )
                return l

            def _style_line_input(w: QLineEdit) -> None:
                w.setStyleSheet(
                    f"QLineEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
                    "border-radius:10px;padding:0 12px;font-size:13px;"
                    f"color:{TXT_H};}}"
                    f"QLineEdit:focus{{border-color:{P};}}"
                )

            def _style_combo_input(w: QComboBox) -> None:
                w.setStyleSheet(
                    f"QComboBox{{background:#f8fafc;border:1.5px solid {BORDER};"
                    "border-radius:10px;padding:0 12px;font-size:13px;"
                    f"color:{TXT_H};}}"
                    f"QComboBox:focus{{border-color:{P};}}"
                    "QComboBox::drop-down{border:none;width:26px;}"
                )

            _LEVELS = ["Nhân viên", "Trưởng nhóm", "Quản lý", "Giám đốc", "Thực tập sinh"]
            _TYPES  = ["Toàn thời gian", "Bán thời gian", "Remote", "Hybrid", "Hợp đồng"]

            s1lo.addWidget(_lbl("Tiêu đề *"))
            e_title = QLineEdit(str(job.get("title") or ""))
            e_title.setMinimumHeight(46)
            e_title.setPlaceholderText("Tiêu đề vị trí tuyển dụng")
            _style_line_input(e_title)
            s1lo.addWidget(e_title)

            s1lo.addWidget(_lbl("Phòng ban / Bộ phận"))
            e_dept = QLineEdit(str(job.get("department") or ""))
            e_dept.setMinimumHeight(46)
            e_dept.setPlaceholderText("Ví dụ: Kỹ thuật & Công nghệ, Marketing…")
            _style_line_input(e_dept)
            s1lo.addWidget(e_dept)

            row_top = QHBoxLayout(); row_top.setSpacing(16)
            col_lv = QVBoxLayout(); col_lv.setSpacing(8)
            col_tp = QVBoxLayout(); col_tp.setSpacing(8)
            col_lv.addWidget(_lbl("Cấp bậc"))
            col_tp.addWidget(_lbl("Loại hình làm việc"))
            c_level = QComboBox()
            c_level.addItems(_LEVELS)
            cur_lv = str(job.get("level") or "")
            idx = c_level.findText(cur_lv)
            if idx >= 0:
                c_level.setCurrentIndex(idx)
            elif cur_lv:
                c_level.insertItem(0, cur_lv)
                c_level.setCurrentIndex(0)
            c_type = QComboBox()
            c_type.addItems(_TYPES)
            cur_jt = str(job.get("job_type") or "")
            idx2 = c_type.findText(cur_jt)
            if idx2 >= 0:
                c_type.setCurrentIndex(idx2)
            elif cur_jt:
                c_type.insertItem(0, cur_jt)
                c_type.setCurrentIndex(0)
            c_level.setMinimumHeight(44)
            c_type.setMinimumHeight(44)
            _style_combo_input(c_level)
            _style_combo_input(c_type)
            col_lv.addWidget(c_level)
            col_tp.addWidget(c_type)
            row_top.addLayout(col_lv, 1)
            row_top.addLayout(col_tp, 1)
            s1lo.addLayout(row_top)
            vlo.addWidget(s1)

            # SECTION 2: Chi tiết & Đãi ngộ
            s2, s2lo = _card_frame()
            s2lo.setSpacing(14)
            s2lo.addWidget(_section_header("ic_jobs.svg", "Chi tiết & Đãi ngộ", "#f59e0b", "#fef3c7"))

            row_salary = QHBoxLayout(); row_salary.setSpacing(16)
            col_min = QVBoxLayout(); col_min.setSpacing(8)
            col_max = QVBoxLayout(); col_max.setSpacing(8)
            col_min.addWidget(_lbl("Lương tối thiểu (VNĐ)"))
            col_max.addWidget(_lbl("Lương tối đa (VNĐ)"))
            e_min_sal = QLineEdit(str(job.get("min_salary") or ""))
            e_min_sal.setPlaceholderText("VD: 15000000")
            e_min_sal.setMinimumHeight(46)
            _style_line_input(e_min_sal)
            e_max_sal = QLineEdit(str(job.get("max_salary") or ""))
            e_max_sal.setPlaceholderText("VD: 25000000")
            e_max_sal.setMinimumHeight(46)
            _style_line_input(e_max_sal)
            col_min.addWidget(e_min_sal)
            col_max.addWidget(e_max_sal)
            row_salary.addLayout(col_min, 1)
            row_salary.addLayout(col_max, 1)
            s2lo.addLayout(row_salary)

            row_mid = QHBoxLayout(); row_mid.setSpacing(16)
            col_loc = QVBoxLayout(); col_loc.setSpacing(8)
            col_cnt = QVBoxLayout(); col_cnt.setSpacing(8)
            col_loc.addWidget(_lbl("Địa điểm làm việc"))
            col_cnt.addWidget(_lbl("Số lượng tuyển"))
            e_loc = QLineEdit(str(job.get("location") or ""))
            e_loc.setPlaceholderText("Hà Nội, TP.HCM…")
            e_loc.setMinimumHeight(46)
            _style_line_input(e_loc)
            e_count = QLineEdit(str(job.get("count") or 1))
            e_count.setPlaceholderText("1")
            e_count.setMinimumHeight(46)
            _style_line_input(e_count)
            col_loc.addWidget(e_loc)
            col_cnt.addWidget(e_count)
            row_mid.addLayout(col_loc, 1)
            row_mid.addLayout(col_cnt, 1)
            s2lo.addLayout(row_mid)

            s2lo.addWidget(_lbl("Hạn nộp hồ sơ"))
            e_dead = QDateEdit()
            e_dead.setDisplayFormat("dd/MM/yyyy")
            e_dead.setCalendarPopup(True)
            e_dead.setMinimumHeight(46)
            e_dead.setStyleSheet(
                f"QDateEdit{{background:#f8fafc;border:1.5px solid {BORDER}; border-radius:10px; padding:0 12px;"
                f" font-size:13px; color:{TXT_H};}}"
                f"QDateEdit:focus{{border-color:{P};}}"
                "QDateEdit::drop-down{border:none; width:28px;}"
            )
            raw_deadline = str(job.get("deadline") or "").strip()
            parsed_deadline = QDate.fromString(raw_deadline, "dd/MM/yyyy")
            if not parsed_deadline.isValid():
                parsed_deadline = QDate.fromString(raw_deadline[:10], "yyyy-MM-dd")
            if not parsed_deadline.isValid():
                parsed_deadline = QDate.currentDate().addMonths(1)
            e_dead.setDate(parsed_deadline)
            s2lo.addWidget(e_dead)
            vlo.addWidget(s2)

            # SECTION 3: Mô tả công việc
            _sd = _decode_desc(job.get("description", ""))
            s3, s3lo = _card_frame()
            s3lo.setSpacing(12)
            s3lo.addWidget(_section_header("ic_doc.svg", "Mô tả công việc", "#0ea5e9", "#e0f2fe"))
            s3lo.addWidget(_lbl("Mô tả chung"))
            e_desc = QPlainTextEdit(_sd.get("desc", ""))
            e_desc.setMinimumHeight(180)
            e_desc.setPlaceholderText("Mô tả tổng quan vị trí tuyển dụng…")
            e_desc.setStyleSheet(
                f"QPlainTextEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
                "border-radius:10px;padding:10px 14px;font-size:14px;"
                f"color:{TXT_H};}}"
                f"QPlainTextEdit:focus{{border-color:{P};}}"
            )
            s3lo.addWidget(e_desc)
            vlo.addWidget(s3)

            # SECTION 4: Nhiệm vụ & Yêu cầu
            s4, s4lo = _card_frame()
            s4lo.setSpacing(12)
            s4lo.addWidget(_section_header("ic_user.svg", "Nhiệm vụ & Yêu cầu", "#10b981", "#d1fae5"))
            def _style_task_input(w: QPlainTextEdit) -> None:
                w.setStyleSheet(
                    f"QPlainTextEdit{{background:#f8fafc;border:1.5px solid {BORDER};"
                    "border-radius:10px;padding:10px 12px;font-size:13px;"
                    f"color:{TXT_H};}}"
                    f"QPlainTextEdit:focus{{border-color:{P};}}"
                )
            s4lo.addWidget(_lbl("Nhiệm vụ chính (mỗi dòng = 1 nhiệm vụ)"))
            e_duties = QPlainTextEdit("\n".join(_sd.get("duties", [])))
            e_duties.setMinimumHeight(120)
            e_duties.setPlaceholderText("Mỗi dòng là một nhiệm vụ chính…")
            _style_task_input(e_duties)
            s4lo.addWidget(e_duties)

            row_req = QHBoxLayout(); row_req.setSpacing(16)
            col_req = QVBoxLayout(); col_req.setSpacing(6)
            col_soft = QVBoxLayout(); col_soft.setSpacing(6)
            col_req.addWidget(_lbl("Yêu cầu chuyên môn"))
            col_soft.addWidget(_lbl("Kỹ năng mềm"))
            e_reqs = QPlainTextEdit("\n".join(_sd.get("requirements", [])))
            e_reqs.setMinimumHeight(120)
            e_reqs.setPlaceholderText("Mỗi dòng là một yêu cầu…")
            _style_task_input(e_reqs)
            e_soft = QPlainTextEdit("\n".join(_sd.get("soft_skills", [])))
            e_soft.setMinimumHeight(120)
            e_soft.setPlaceholderText("Mỗi dòng là một kỹ năng…")
            _style_task_input(e_soft)
            col_req.addWidget(e_reqs)
            col_soft.addWidget(e_soft)
            row_req.addLayout(col_req, 1)
            row_req.addLayout(col_soft, 1)
            s4lo.addLayout(row_req)

            s4lo.addWidget(_lbl("Quyền lợi & Phúc lợi (mỗi dòng = 1 quyền lợi)"))
            e_benefits = QPlainTextEdit("\n".join(_sd.get("benefits", [])))
            e_benefits.setMinimumHeight(120)
            e_benefits.setPlaceholderText("Mỗi dòng là một quyền lợi…")
            _style_task_input(e_benefits)
            s4lo.addWidget(e_benefits)
            vlo.addWidget(s4)

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
            btn_save = QPushButton("Lưu thay đổi")
            btn_save.setIcon(QIcon(_svg_pm("ic_check.svg", 15, "#ffffff")))
            btn_save.setIconSize(QSize(15, 15))
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
                salary_pair = self._validate_salary_pair(e_min_sal.text(), e_max_sal.text(), dlg)
                if not salary_pair:
                    return
                min_salary, max_salary = salary_pair
                encoded = _encode_desc(
                    e_desc.toPlainText().strip(),
                    e_duties.toPlainText().strip(),
                    e_reqs.toPlainText().strip(),
                    e_soft.toPlainText().strip(),
                    e_benefits.toPlainText().strip(),
                )
                payload = {
                    "title": e_title.text().strip() or job.get("title", ""),
                    "description": encoded,
                    "department": e_dept.text().strip() or job.get("department") or "Kỹ thuật & Công nghệ",
                    "level": c_level.currentText(),
                    "min_salary": min_salary,
                    "max_salary": max_salary,
                    "location": e_loc.text().strip() or job.get("location"),
                    "job_type": c_type.currentText(),
                    "count": int(e_count.text()) if e_count.text().isdigit() else int(job.get("count") or 1),
                    "deadline": e_dead.date().toString("dd/MM/yyyy"),
                    "as_draft": job.get("status") == "draft",
                }
                try:
                    jobhub_api.hr_update_job(_jid, payload)
                except ApiError as e:
                    self._show_toast(str(e), "ic_x.svg", "#ef4444")
                    return
                dlg.accept()
                self._fill_jobs_table()
                _saved_title = e_title.text().strip()
                self._show_toast(
                    f'Đã lưu thay đổi tin "{_saved_title}"',
                    "ic_check.svg", "#10b981"
                )

            btn_save.clicked.connect(_save)
            scroll.setWidget(body)
            root.addWidget(scroll, 1)
            _center_dialog(dlg)
            dlg.exec()

        # ── View dialog ──────────────────────────────────────────
        def _do_view(_jid=job_id):
            try:
                job = jobhub_api.hr_get_job(_jid)
            except ApiError as e:
                self._show_toast(str(e), "ic_x.svg", "#ef4444")
                return
            if not job:
                self._show_toast("Không tìm thấy tin đăng!", "ic_x.svg", "#ef4444")
                return

            created_at_raw = str(job.get("created_at") or "").strip()
            created_at_text = created_at_raw
            if created_at_raw:
                try:
                    _dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                    created_at_text = _dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    created_at_text = created_at_raw.replace("T", " ")[:16]
            _sd = _decode_desc(job.get("description", ""))

            dlg = QDialog(self.win)
            _ttl = (job_title or str(job.get("title") or "")).strip() or f"#{_jid}"
            dlg.setWindowTitle(f"Chi tiết tin tuyển dụng — {_ttl}")
            dlg.resize(980, 720)
            dlg.setStyleSheet(
                f"QDialog{{background:{CONTENT_BG};}}"
                "QLabel{background:transparent;border:none;}"
                f"QScrollArea{{background:{CONTENT_BG};border:none;}}"
            )

            scroll = QScrollArea(dlg)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            inner = QWidget()
            inner.setStyleSheet(f"background:{CONTENT_BG};")
            vlo = QVBoxLayout(inner)
            vlo.setContentsMargins(24, 20, 24, 24)
            vlo.setSpacing(14)
            scroll.setWidget(inner)
            outer_lo = QVBoxLayout(dlg)
            outer_lo.setContentsMargins(0, 0, 0, 0)
            outer_lo.addWidget(scroll)

            _ST_MAP = {
                "published":        ("Đang tuyển", "#d1fae5", "#059669"),
                "pending_approval": ("Chờ duyệt",  "#fef3c7", "#d97706"),
                "draft":            ("Bản nháp",    "#f1f5f9", "#64748b"),
                "rejected":         ("Vi phạm",     "#fee2e2", "#dc2626"),
                "closed":           ("Đã đóng",     "#f1f5f9", "#374151"),
            }
            st = job.get("status", "")
            st_txt, st_bg, st_fg = _ST_MAP.get(st, (st, "#f1f5f9", "#64748b"))

            # ── HERO CARD ────────────────────────────────────────
            hero = QFrame()
            hero.setStyleSheet(
                f"QFrame{{background:#ffffff;border-radius:16px;"
                f"border:1.5px solid {BORDER};}}"
            )
            _shadow(hero, 12, 4, 12)
            hero_lo = QHBoxLayout(hero)
            hero_lo.setContentsMargins(20, 18, 20, 18)
            hero_lo.setSpacing(18)

            comp_name = job.get("company_name", "?")
            logo_lbl = QLabel((comp_name[0] if comp_name else "?").upper())
            logo_lbl.setFixedSize(60, 60)
            logo_lbl.setAlignment(Qt.AlignCenter)
            logo_lbl.setStyleSheet(
                f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                f"stop:0 {P},stop:1 {P_DARK});"
                "color:#ffffff;border-radius:14px;"
                "font-size:24px;font-weight:800;border:none;"
            )
            title_col = QVBoxLayout()
            title_col.setSpacing(4)
            h1 = QLabel(job.get("title", "—"))
            h1.setWordWrap(True)
            h1.setStyleSheet(
                f"color:{TXT_H};font-size:20px;font-weight:800;"
                "background:transparent;border:none;"
            )
            comp_row_h = QHBoxLayout()
            comp_row_h.setSpacing(6)
            comp_l = QLabel(comp_name)
            comp_l.setStyleSheet(
                f"color:{P};font-size:13px;font-weight:700;"
                "background:transparent;border:none;"
            )
            comp_row_h.addWidget(comp_l)
            dept_str = job.get("department", "")
            if dept_str:
                dot = QLabel("·")
                dot.setStyleSheet(f"color:{TXT_M};background:transparent;border:none;")
                dept_l = QLabel(dept_str)
                dept_l.setStyleSheet(
                    f"color:{TXT_M};font-size:13px;background:transparent;border:none;"
                )
                comp_row_h.addWidget(dot)
                comp_row_h.addWidget(dept_l)
            comp_row_h.addStretch()
            st_badge = QLabel(st_txt)
            st_badge.setFixedHeight(22)
            st_badge.setStyleSheet(
                f"background:{st_bg};color:{st_fg};"
                "border-radius:11px;padding:0 10px;"
                "font-size:11px;font-weight:700;border:none;"
            )
            title_col.addWidget(h1)
            title_col.addLayout(comp_row_h)
            title_col.addWidget(st_badge)
            hero_lo.addWidget(logo_lbl, 0, Qt.AlignTop)
            hero_lo.addLayout(title_col, 1)
            vlo.addWidget(hero)

            # ── META BAR ─────────────────────────────────────────
            meta_row = QHBoxLayout()
            meta_row.setSpacing(20)
            meta_row.setContentsMargins(4, 0, 0, 0)
            created_at = job.get("created_at", "")
            applicants = job.get("applicants_count", 0)
            for icon_svg, meta_txt, meta_color in [
                ("ic_jobs.svg",  f"Đăng ngày {created_at_text}" if created_at_text else "Mới đăng", TXT_M),
                ("ic_user.svg",  f"{applicants} ứng viên đã ứng tuyển", P if applicants > 0 else TXT_M),
                ("ic_check.svg", "Nhà tuyển dụng đã xác minh", "#059669"),
            ]:
                mr = QHBoxLayout()
                mr.setSpacing(5)
                mi = QLabel()
                mi.setFixedSize(13, 13)
                mi.setPixmap(_svg_pm(icon_svg, 13, meta_color))
                mi.setStyleSheet("background:transparent;border:none;")
                mt = QLabel(meta_txt)
                mt.setStyleSheet(
                    f"color:{meta_color};font-size:12px;"
                    "background:transparent;border:none;"
                )
                mr.addWidget(mi)
                mr.addWidget(mt)
                meta_row.addLayout(mr)
            meta_row.addStretch()
            vlo.addLayout(meta_row)

            # ── Candidate-style two-column detail body ──────────
            body_row = QHBoxLayout()
            body_row.setSpacing(14)

            left_col = QVBoxLayout()
            left_col.setSpacing(12)

            def _content_card(title_text: str, content_text: str) -> QFrame:
                card = QFrame()
                card.setStyleSheet(
                    f"QFrame{{background:#ffffff;border-radius:14px;border:1.5px solid {BORDER};}}"
                )
                _shadow(card, 8, 2, 8)
                c_lo = QVBoxLayout(card)
                c_lo.setContentsMargins(16, 14, 16, 14)
                c_lo.setSpacing(8)
                ttl = QLabel(title_text)
                ttl.setStyleSheet(
                    f"color:{TXT_H};font-size:15px;font-weight:800;background:transparent;border:none;"
                )
                txt = QLabel(content_text if content_text else "Chưa cập nhật.")
                txt.setWordWrap(True)
                txt.setTextFormat(Qt.PlainText)
                txt.setStyleSheet(
                    f"color:{TXT_S};font-size:13px;background:transparent;border:none;"
                )
                c_lo.addWidget(ttl)
                c_lo.addWidget(txt)
                return card

            def _list_block(items: list[str]) -> str:
                clean = [str(x).strip() for x in (items or []) if str(x).strip()]
                return "\n".join(f"• {x}" for x in clean)

            desc_text = str(_sd.get("desc") or "").strip()
            if not desc_text:
                desc_text = _list_block(_sd.get("duties", []))
            left_col.addWidget(_content_card("Mô tả công việc", desc_text))
            left_col.addWidget(_content_card("Yêu cầu công việc", _list_block(_sd.get("requirements", []))))
            left_col.addWidget(_content_card("Kỹ năng mềm", _list_block(_sd.get("soft_skills", []))))
            left_col.addWidget(_content_card("Quyền lợi & Phúc lợi", _list_block(_sd.get("benefits", []))))
            left_col.addStretch()

            right_card = QFrame()
            right_card.setFixedWidth(320)
            right_card.setStyleSheet(
                f"QFrame{{background:#ffffff;border-radius:14px;border:1.5px solid {BORDER};}}"
            )
            _shadow(right_card, 8, 2, 8)
            right_lo = QVBoxLayout(right_card)
            right_lo.setContentsMargins(14, 14, 14, 14)
            right_lo.setSpacing(8)

            right_title = QLabel("Tổng quan công việc")
            right_title.setStyleSheet(
                f"color:{TXT_H};font-size:14px;font-weight:800;background:transparent;border:none;"
            )
            right_lo.addWidget(right_title)

            def _info_row(k: str, v: str, color: str = TXT_H) -> None:
                r = QHBoxLayout()
                r.setSpacing(6)
                lk = QLabel(k)
                lk.setStyleSheet(f"color:{TXT_M};font-size:12px;font-weight:600;background:transparent;border:none;")
                lv = QLabel(v if v else "—")
                lv.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                lv.setStyleSheet(f"color:{color};font-size:12px;font-weight:700;background:transparent;border:none;")
                r.addWidget(lk, 1)
                r.addWidget(lv, 1)
                right_lo.addLayout(r)

            _info_row("Mức lương", str(job.get("salary_text", "—")), P)
            _info_row("Loại hình", str(job.get("job_type", "—")))
            _info_row("Địa điểm", str(job.get("location", "—")))
            _info_row("Cấp bậc", str(job.get("level", "—")), "#4f46e5")
            _info_row("Số lượng", f"{job.get('count', '—')} vị trí", "#059669")
            _info_row("Hạn nộp", str(job.get("deadline", "—")), "#d97706")
            _info_row("Ngày đăng", created_at_text or "—")
            _info_row("Ứng viên", f"{applicants}")
            right_lo.addStretch()

            body_row.addLayout(left_col, 1)
            body_row.addWidget(right_card)
            vlo.addLayout(body_row)

            # ── CLOSE BUTTON ─────────────────────────────────────
            close_btn = QPushButton("Đóng")
            close_btn.setFixedHeight(40)
            close_btn.setCursor(Qt.PointingHandCursor)
            close_btn.setStyleSheet(
                f"QPushButton{{background:{P};color:#ffffff;"
                "border:none;border-radius:10px;padding:0 28px;"
                "font-size:14px;font-weight:600;}}"
                f"QPushButton:hover{{background:{P_DARK};}}"
            )
            close_btn.clicked.connect(dlg.accept)
            close_row = QHBoxLayout()
            close_row.addStretch()
            close_row.addWidget(close_btn)
            vlo.addLayout(close_row)

            _center_dialog(dlg)
            dlg.exec()
            _vt = job.get("title", "")
            self._show_toast(
                f'"{_vt}" — đã xem chi tiết',
                "ic_view.svg", "#0ea5e9"
            )
        # ── Delete ───────────────────────────────────────────────
        def _do_delete(_jid=job_id):
            job = next((j for j in self._jobs_data if j.get("id") == _jid), None)
            job_title = job.get("title", f"#{_jid}") if job else f"#{_jid}"
            ret = QMessageBox.question(
                self.win, "Xác nhận dừng tuyển",
                f"Bạn có chắc muốn dừng tuyển tin:\n\"{job_title}\"?\n\nTin bị sẽ ẩn khỏi bảng tin công khai",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret == QMessageBox.Yes:
                try:
                    jobhub_api.hr_delete_job(_jid)
                except ApiError as e:
                    self._show_toast(str(e), "ic_x.svg", "#ef4444")
                    return
                self._fill_jobs_table()
                self._show_toast(
                    f'Đã dừng tuyển tin “{job_title}”',
                    "ic_delete.svg", "#ef4444"
                )

        def _do_submit(_jid=job_id):
            try:
                job = jobhub_api.hr_get_job(_jid)
            except ApiError as e:
                self._show_toast(str(e), "ic_x.svg", "#ef4444")
                return
            if not self._validate_salary_pair(str(job.get("min_salary") or ""), str(job.get("max_salary") or "")):
                return
            ret = QMessageBox.question(
                self.win, "Gửi duyệt tin",
                f"Gửi tin #{_jid} cho Admin phê duyệt?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
            try:
                jobhub_api.hr_submit_job(_jid)
            except ApiError as e:
                self._show_toast(str(e), "ic_x.svg", "#ef4444")
                return
            self._fill_jobs_table()
            self._show_toast("Đã gửi tin cho Admin duyệt", "ic_check.svg", "#10b981")

        btn_edit.clicked.connect(lambda _=False: _do_edit())
        btn_view.clicked.connect(lambda _=False: _do_view())
        btn_submit.clicked.connect(lambda _=False: _do_submit())
        btn_del.clicked.connect(lambda _=False: _do_delete())

        lo.addWidget(btn_edit)
        lo.addWidget(btn_view)
        if status in {"draft", "rejected"}:
            lo.addWidget(btn_submit)
        lo.addWidget(btn_del)
        lo.addStretch()
        return wrap

    def _all_applications(self) -> list:
        try:
            return list(jobhub_api.hr_applications())
        except ApiError:
            return []

    def _fill_cands_table(self) -> None:
        self._cands_page = 0
        self._fetch_cands_page()

    def _on_cands_search_changed(self, text: str) -> None:
        """Show/hide clear button + trigger filter."""
        self._cands_search_clear.setVisible(bool(text))
        self._filter_cands(text)

    def _filter_cands(self, text: str) -> None:
        st_map = {
            0: None, 1: "pending", 2: "reviewed",
            3: "approved", 4: "rejected",
        }
        self._cands_status_value = st_map.get(self._cands_status_filter.currentIndex())
        sort_map = {
            0: "newest",
            1: "oldest",
            2: "name_asc",
            3: "name_desc",
        }
        self._cands_sort_value = sort_map.get(self._cands_sort.currentIndex(), "newest")
        self._cands_keyword = (text or "").strip()
        self._cands_page = 0
        self._fetch_cands_page()

    def _fetch_cands_page(self) -> None:
        try:
            payload = jobhub_api.hr_applications(
                page=self._cands_page + 1,
                page_size=_PAGE_SIZE,
                keyword=self._cands_keyword or None,
                status_filter=self._cands_status_value or None,
                sort_by=self._cands_sort_value or "newest",
            )
        except ApiError:
            self._render_cands([], total=0, page_size=_PAGE_SIZE)
            return

        if isinstance(payload, dict):
            items = list(payload.get("items") or [])
            total = int(payload.get("total") or 0)
            page_size = int(payload.get("page_size") or _PAGE_SIZE)
        else:
            items = list(payload)
            total = len(items)
            page_size = _PAGE_SIZE
        self._render_cands(items, total=total, page_size=page_size)

    def _render_cands(self, apps: list, *, total: int, page_size: int) -> None:
        # ── Store current page data ───────────────────────────
        self._cands_data = apps
        n_pages = max(1, (total + max(1, page_size) - 1) // max(1, page_size))
        self._cands_page = max(0, min(self._cands_page, n_pages - 1))
        page_apps = apps

        COLS = ["Ứng viên", "Vị trí ứng tuyển",
                "Ngày ứng tuyển", "Trạng thái", "Thao tác"]
        tbl = self.table_cands
        tbl.setColumnCount(len(COLS))
        tbl.setHorizontalHeaderLabels(COLS)
        tbl.setRowCount(len(page_apps))

        self._lbl_cand_count.setText(f"  {total} ứng viên  ")
        self._cands_no_result_lbl.setVisible(total == 0)

        for row, a in enumerate(page_apps):
            # Col 0: Avatar + name + email
            tbl.setCellWidget(
                row, 0,
                self._make_cand_info(
                    a.get("candidate_name", ""),
                    a.get("candidate_email", ""),
                    bool(a.get("is_pro_active")),
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
                    a.get("status", ""),
                    a,
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
        tbl.setColumnWidth(4, 168)
        # Fix height to exactly fit rows — no empty space
        tbl.setMinimumHeight(320)
        tbl.setMaximumHeight(16777215)
        tbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._cands_resizer._apply()

        self._update_cands_pagination(n_pages, total, page_size)

    def _make_cand_info(self, name: str, email: str, is_pro_active: bool = False) -> QWidget:
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
        name_row = QHBoxLayout()
        name_row.setSpacing(4)
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.addWidget(name_lbl)
        if is_pro_active:
            badge = QLabel()
            badge.setFixedSize(16, 16)
            badge.setPixmap(_svg_pm("ic_pro_badge.svg", 16, "#2563eb", "#dbeafe"))
            badge.setStyleSheet("background:transparent; border:none;")
            name_row.addWidget(badge)
        name_row.addStretch()
        txt_col.addLayout(name_row)
        txt_col.addWidget(email_lbl)

        lo.addWidget(ava)
        lo.addLayout(txt_col, 1)
        return wrap

    def _make_cand_actions(self, app_id: int, cv_name: str, status: str = "", app_data: dict | None = None) -> QWidget:
        """Action buttons: view profile / approve / reject."""
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(wrap)
        lo.setContentsMargins(8, 0, 8, 0)
        lo.setSpacing(6)
        lo.setAlignment(Qt.AlignVCenter)

        def _ic_btn(svg: str, color: str,
                    tint: str, tooltip: str) -> QPushButton:
            """Glassmorphism + Duotone icon button."""
            h = color.lstrip("#")
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setIcon(QIcon(_svg_pm(svg, 18, color)))
            btn.setIconSize(QSize(18, 18))
            btn.setStyleSheet(
                "QPushButton{"
                "background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
                "stop:0 #ffffff,stop:1 #f5f7ff);"
                f"border:1px solid {BORDER};"
                "border-radius:11px;}"
                "QPushButton:hover{"
                f"background:rgba({r},{g},{b},0.09);"
                f"border:1.5px solid rgba({r},{g},{b},0.38);}}"
                "QPushButton:pressed{"
                f"background:rgba({r},{g},{b},0.16);"
                f"border:1.5px solid rgba({r},{g},{b},0.55);}}"
            )
            return btn

        btn_profile = _ic_btn("ic_view.svg",   "#0ea5e9", "#e0f2fe", "Xem hồ sơ ứng viên")
        btn_ok  = _ic_btn("ic_check.svg",  "#10b981", "#d1fae5", "Phê duyệt")
        btn_rej = _ic_btn("ic_x.svg", "#ef4444", "#fee2e2", "Từ chối")

        btn_profile.clicked.connect(
            lambda _=False, _app=(app_data or {}), _aid=app_id, _cv=cv_name: self._open_candidate_profile_dialog(_app, _aid, _cv)
        )
        btn_ok.clicked.connect(
            lambda _=False, _aid=app_id: self._hr_set_status(_aid, "approved")
        )
        btn_rej.clicked.connect(
            lambda _=False, _aid=app_id: self._hr_set_status(_aid, "rejected")
        )
        is_final = status in {"approved", "rejected"}
        if status == "approved":
            btn_ok.setEnabled(False)
            btn_ok.setToolTip("Đơn đã được phê duyệt")
        elif status == "rejected":
            btn_rej.setEnabled(False)
            btn_rej.setToolTip("Đơn đã bị từ chối")
        if is_final:
            btn_ok.setEnabled(False)
            btn_rej.setEnabled(False)

        lo.addWidget(btn_profile)
        lo.addWidget(btn_ok)
        lo.addWidget(btn_rej)
        lo.addStretch()
        return wrap

    def _open_candidate_profile_dialog(self, app_data: dict, app_id: int, cv_name: str = "") -> None:
        # Detail view is considered an action: backend may lock it when overdue invoice.
        try:
            view_result = jobhub_api.hr_view_candidate_profile(app_id)
            new_status = str(view_result.get("status") or "").strip().lower()
            if new_status:
                app_data["status"] = new_status
            self._fill_cands_table()
        except ApiError as e:
            detail = str(e).strip() or "Không thể mở hồ sơ ứng viên."
            if getattr(e, "status", None) == 403:
                detail = "Tài khoản đang bị tạm khóa thao tác do hóa đơn quá hạn. Vui lòng thanh toán để tiếp tục."
            elif getattr(e, "status", None) == 404:
                detail = f"Không tìm thấy đơn ứng tuyển #{app_id}."
            self._show_toast(detail, "ic_x.svg", "#ef4444")
            return

        can_full = bool(app_data.get("can_view_full_profile"))
        is_pro = bool(app_data.get("is_pro_active"))
        profile = app_data.get("candidate_profile") or {}
        dlg = QDialog(self.win)
        dlg.setWindowTitle(f"Hồ sơ ứng viên #{app_id}")
        dlg.resize(960, 640)
        dlg.setModal(True)
        dlg.setStyleSheet(
            f"QDialog{{background:{CONTENT_BG};}}"
            "QLabel{border:none;background:transparent;}"
        )
        root = QVBoxLayout(dlg)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)

        name = str(app_data.get("candidate_name") or "Ứng viên")
        status_raw = str(app_data.get("status") or "pending")
        status_vi = self._CAND_STATUS.get(status_raw, (status_raw, "#64748b", "#f1f5f9"))[0]
        status_badge = QLabel(status_vi)
        _st_fg = self._CAND_STATUS.get(status_raw, (status_vi, "#64748b", "#f1f5f9"))[1]
        _st_bg = self._CAND_STATUS.get(status_raw, (status_vi, "#64748b", "#f1f5f9"))[2]
        status_badge.setStyleSheet(
            f"background:{_st_bg}; color:{_st_fg}; border-radius:11px; "
            "font-size:11px; font-weight:700; padding:3px 10px;"
        )
        header = QHBoxLayout()
        title = QLabel("Hồ sơ ứng viên")
        title.setStyleSheet(f"color:{TXT_H}; font-size:18px; font-weight:800;")
        header.addWidget(title)
        header.addSpacing(8)
        header.addWidget(status_badge, 0, Qt.AlignVCenter)
        header.addStretch()
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(14)

        # Left identity card (candidate profile style)
        left_card = QFrame()
        left_card.setFixedWidth(285)
        left_card.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:14px;}")
        _shadow(left_card, 10, 3, 10)
        left_lo = QVBoxLayout(left_card)
        left_lo.setContentsMargins(18, 20, 18, 18)
        left_lo.setSpacing(8)

        initials = "".join(part[:1].upper() for part in name.split()[:2]) or "UV"
        avatar = QLabel(initials)
        avatar.setFixedSize(88, 88)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1e3a8a,stop:1 #2563eb);"
            "border-radius:44px; color:white; font-size:28px; font-weight:800;"
            "border:3px solid #10b981;"
        )
        left_lo.addWidget(avatar, 0, Qt.AlignHCenter)

        nm = QLabel(name)
        nm.setAlignment(Qt.AlignCenter)
        nm.setStyleSheet(f"color:{TXT_H}; font-size:22px; font-weight:800;")
        if is_pro:
            pro_lbl = QLabel("PRO")
            pro_lbl.setAlignment(Qt.AlignCenter)
            pro_lbl.setFixedWidth(58)
            pro_lbl.setStyleSheet(
                "background:#fef3c7;color:#b45309;border:none;border-radius:10px;"
                "font-size:11px;font-weight:800;padding:3px 10px;"
            )
            left_lo.addWidget(pro_lbl, 0, Qt.AlignHCenter)
        tg = QLabel(str(profile.get("tagline") or "Chưa cập nhật tagline"))
        tg.setAlignment(Qt.AlignCenter)
        tg.setWordWrap(True)
        tg.setStyleSheet(f"color:{TXT_M}; font-size:12px;")
        left_lo.addWidget(nm)
        left_lo.addWidget(tg)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        left_lo.addWidget(sep)

        def _contact_line(icon: str, text_val: str) -> None:
            row = QHBoxLayout()
            row.setSpacing(6)
            ic = QLabel()
            ic.setFixedSize(14, 14)
            ic.setPixmap(_svg_pm(icon, 14, TXT_M))
            tx = QLabel(text_val or "—")
            tx.setStyleSheet(f"color:{TXT_S}; font-size:12px;")
            row.addWidget(ic)
            row.addWidget(tx, 1)
            left_lo.addLayout(row)

        _contact_line("ic_email.svg", str(app_data.get("candidate_email") or ("Ẩn cho đến khi phê duyệt" if not can_full else "—")))
        _contact_line("ic_phone.svg", str(profile.get("phone") or ("Ẩn cho đến khi phê duyệt" if not can_full else "—")))
        _contact_line("ic_pin.svg", str(profile.get("address") or ("Ẩn cho đến khi phê duyệt" if not can_full else "—")))

        left_lo.addStretch()

        body.addWidget(left_card)

        # Right detail cards
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        def _field_block(label: str, val: str) -> QWidget:
            w = QWidget()
            v = QVBoxLayout(w)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(2)
            l = QLabel(label)
            l.setStyleSheet(f"color:{TXT_M}; font-size:10px; font-weight:700; text-transform:uppercase;")
            t = QLabel(val or "—")
            t.setWordWrap(True)
            t.setStyleSheet(f"color:{TXT_H}; font-size:12px; font-weight:600;")
            v.addWidget(l)
            v.addWidget(t)
            return w

        personal = QFrame()
        personal.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:14px;}")
        _shadow(personal, 8, 2, 8)
        plo = QVBoxLayout(personal)
        plo.setContentsMargins(16, 14, 16, 14)
        plo.setSpacing(10)
        pttl = QLabel("Thông tin cá nhân")
        pttl.setStyleSheet(f"color:{TXT_H}; font-size:15px; font-weight:800;")
        plo.addWidget(pttl)
        pgrid = QGridLayout()
        pgrid.setHorizontalSpacing(24)
        pgrid.setVerticalSpacing(8)
        pgrid.addWidget(_field_block("Họ và tên", name), 0, 0)
        pgrid.addWidget(_field_block("Email", str(app_data.get("candidate_email") or ("Ẩn thông tin" if not can_full else "—"))), 0, 1)
        pgrid.addWidget(_field_block("Số điện thoại", str(profile.get("phone") or ("Ẩn thông tin" if not can_full else "—"))), 1, 0)
        pgrid.addWidget(_field_block("Địa chỉ hiện tại", str(profile.get("address") or ("Ẩn thông tin" if not can_full else "—"))), 1, 1)
        plo.addLayout(pgrid)
        right_col.addWidget(personal)

        prof = QFrame()
        prof.setStyleSheet("QFrame{background:#ffffff;border:none;border-radius:14px;}")
        _shadow(prof, 8, 2, 8)
        clo = QVBoxLayout(prof)
        clo.setContentsMargins(16, 14, 16, 14)
        clo.setSpacing(10)
        cttl = QLabel("Thông tin chuyên môn")
        cttl.setStyleSheet(f"color:{TXT_H}; font-size:15px; font-weight:800;")
        clo.addWidget(cttl)
        cgrid = QGridLayout()
        cgrid.setHorizontalSpacing(24)
        cgrid.setVerticalSpacing(8)
        cgrid.addWidget(_field_block("Ngành nghề", str(profile.get("professional_field") or "")), 0, 0)
        cgrid.addWidget(_field_block("Bằng cấp", str(profile.get("degree") or "")), 0, 1)
        cgrid.addWidget(_field_block("Số năm kinh nghiệm", str(profile.get("experience_text") or "")), 1, 0)
        cgrid.addWidget(_field_block("Ngôn ngữ", str(profile.get("language") or "")), 1, 1)
        clo.addLayout(cgrid)

        skills_raw = profile.get("skills_json")
        skills_map: dict[str, list[str]] = {}
        if isinstance(skills_raw, str) and skills_raw.strip():
            try:
                parsed = json.loads(skills_raw)
                if isinstance(parsed, dict):
                    skills_raw = parsed
            except Exception:
                skills_raw = {}
        if isinstance(skills_raw, dict):
            for cat, vals in skills_raw.items():
                cat_name = str(cat or "Khác").strip() or "Khác"
                if isinstance(vals, list):
                    norm_vals = [str(v).strip() for v in vals if str(v).strip()]
                elif vals is None:
                    norm_vals = []
                else:
                    norm_vals = [str(vals).strip()] if str(vals).strip() else []
                if norm_vals:
                    skills_map[cat_name] = norm_vals

        if skills_map:
            skills_card = QFrame()
            skills_card.setStyleSheet("QFrame{background:#f8fafc;border:none;border-radius:12px;}")
            skl = QVBoxLayout(skills_card)
            skl.setContentsMargins(12, 10, 12, 10)
            skl.setSpacing(10)

            skill_title = QLabel("Kỹ năng")
            skill_title.setStyleSheet(f"color:{TXT_H}; font-size:12px; font-weight:800;")
            skl.addWidget(skill_title)

            for cat, vals in skills_map.items():
                cat_lbl = QLabel(cat)
                cat_lbl.setStyleSheet(f"color:{TXT_M}; font-size:11px; font-weight:800;")
                skl.addWidget(cat_lbl)

                chip_grid_wrap = QWidget()
                chip_grid = QGridLayout(chip_grid_wrap)
                chip_grid.setContentsMargins(0, 0, 0, 0)
                chip_grid.setHorizontalSpacing(8)
                chip_grid.setVerticalSpacing(8)
                for idx, val in enumerate(vals):
                    chip = QLabel(val)
                    chip.setFixedHeight(28)
                    chip.setStyleSheet(
                        f"background:#e0e7ff; color:{P_DARK}; border:none; border-radius:14px;"
                        "padding:0 12px; font-size:11px; font-weight:700;"
                    )
                    chip_grid.addWidget(chip, idx // 5, idx % 5)
                skl.addWidget(chip_grid_wrap)

            clo.addWidget(skills_card)
        right_col.addWidget(prof, 1)
        right_col.addStretch()
        body.addLayout(right_col, 1)
        root.addLayout(body, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        status_now = str(app_data.get("status") or "")
        is_final = status_now in {"approved", "rejected"}
        if not is_final:
            btn_reject = QPushButton("Từ chối")
            btn_reject.setCursor(Qt.PointingHandCursor)
            btn_reject.setFixedHeight(34)
            btn_reject.setStyleSheet(
                "QPushButton{background:#fee2e2;color:#b91c1c;border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}"
                "QPushButton:hover{background:#fecaca;}"
            )
            btn_reject.clicked.connect(
                lambda _=False, _aid=app_id: (self._hr_set_status(_aid, "rejected"), dlg.accept())
            )
            btn_row.addWidget(btn_reject)
            btn_row.addSpacing(8)

            btn_approve = QPushButton("Chấp nhận")
            btn_approve.setCursor(Qt.PointingHandCursor)
            btn_approve.setFixedHeight(34)
            btn_approve.setStyleSheet(
                "QPushButton{background:#dcfce7;color:#166534;border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}"
                "QPushButton:hover{background:#bbf7d0;}"
            )
            btn_approve.clicked.connect(
                lambda _=False, _aid=app_id: (self._hr_set_status(_aid, "approved"), dlg.accept())
            )
            btn_row.addWidget(btn_approve)
            btn_row.addSpacing(8)

        if can_full and bool(app_data.get("can_view_cv_detail")):
            btn_cv = QPushButton("Xem CV chi tiết")
            btn_cv.setCursor(Qt.PointingHandCursor)
            btn_cv.setFixedHeight(34)
            btn_cv.setStyleSheet(
                f"QPushButton{{background:{P};color:#fff;border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}}"
                f"QPushButton:hover{{background:{P_DARK};}}"
            )
            btn_cv.clicked.connect(lambda _=False, _aid=app_id, _cv=cv_name: self._open_application_cv(_aid, _cv, "approved"))
            btn_row.addWidget(btn_cv)
            btn_row.addSpacing(8)
        btn_close = QPushButton("Đóng")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setFixedHeight(34)
        btn_close.setStyleSheet(
            "QPushButton{background:#f1f5f9;color:#374151;border:none;border-radius:9px;padding:0 14px;font-size:12px;font-weight:700;}"
            "QPushButton:hover{background:#e2e8f0;}"
        )
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)
        dlg.exec()

    # ── Status update (approve / reject / review) ─────────────
    def _open_bytes_file(self, data: bytes, suggested_name: str | None, fallback: str = "cv.pdf") -> Path:
        import os as _os
        import subprocess as _sub
        import sys as _sys
        import tempfile

        fname = suggested_name or fallback
        suffix = Path(fname).suffix or ".pdf"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.flush()
        tmp.close()
        path = Path(tmp.name)
        if _sys.platform.startswith("win"):
            _os.startfile(str(path))
        elif _sys.platform == "darwin":
            _sub.Popen(["open", str(path)])
        else:
            _sub.Popen(["xdg-open", str(path)])
        return path

    def _open_application_cv(self, app_id: int, cv_name: str = "", status: str = "") -> None:
        try:
            cv_bytes, suggested_name = jobhub_api.hr_view_application_cv(app_id)
            self._open_bytes_file(cv_bytes, suggested_name or cv_name)
            if status == "pending":
                try:
                    jobhub_api.hr_view_candidate_profile(app_id)
                    self._fill_cands_table()
                except ApiError:
                    pass
            self._show_toast(f"Đã mở CV đơn #{app_id}", "ic_view.svg", "#0ea5e9")
        except ApiError as e:
            self._show_toast(str(e), "ic_x.svg", "#ef4444")
        except Exception:
            self._show_toast("Không thể mở CV trên máy hiện tại.", "ic_x.svg", "#ef4444")

    def _download_application_cv(self, app_id: int, cv_name: str = "") -> None:
        try:
            cv_bytes, suggested_name = jobhub_api.hr_download_application_cv(app_id)
        except ApiError as e:
            self._show_toast(str(e), "ic_x.svg", "#ef4444")
            return

        from PySide6.QtWidgets import QFileDialog
        default_name = suggested_name or cv_name or f"cv_{app_id}.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self.win, "Lưu CV ứng viên", default_name, "PDF/Document (*.pdf *.doc *.docx);;Tất cả tệp (*)"
        )
        if not save_path:
            return
        try:
            Path(save_path).write_bytes(cv_bytes)
        except OSError as e:
            self._show_toast(f"Không thể lưu CV: {e}", "ic_x.svg", "#ef4444")
            return
        self._show_toast("Đã tải CV ứng viên", "ic_download.svg", "#6366f1")

    _STATUS_LABEL_VI: dict[str, str] = {
        "reviewed": "Đã xem",
        "approved": "Phê duyệt",
        "rejected": "Từ chối",
    }
    _STATUS_CONFIRM: dict[str, str] = {
        "reviewed": "Đánh dấu đã xem xét đơn #{id}?",
        "approved": "Phê duyệt đơn ứng tuyển #{id}? Hệ thống sẽ tạo invoice phí tuyển dụng = 10% mức lương trung bình của công việc.",
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

        try:
            result = jobhub_api.hr_update_application_status(app_id, new_status)
            ok = bool(result.get("ok"))
        except ApiError as e:
            ok = False
            detail = str(e).strip() or "Không thể cập nhật trạng thái đơn ứng tuyển."
            if getattr(e, "status", None) == 403:
                detail = "Tài khoản đang bị tạm khóa thao tác do hóa đơn quá hạn. Vui lòng thanh toán để tiếp tục."
            elif getattr(e, "status", None) == 404:
                detail = f"Không tìm thấy đơn ứng tuyển #{app_id}."
            elif getattr(e, "status", None) == 400 and "khong the thay doi trang thai" in detail.lower():
                detail = f"Đơn #{app_id} đã chốt trạng thái, không thể cập nhật."
            self._show_toast(detail, "ic_x.svg", "#ef4444")
        if ok:
            _TOAST = {
                "reviewed": ("ic_view.svg",   "#0ea5e9", f"Đã đánh dấu xem xét đơn #{app_id}"),
                "approved": ("ic_check.svg",  "#10b981", f"Đã phê duyệt đơn ứng tuyển #{app_id}"),
                "rejected": ("ic_x.svg",      "#ef4444", f"Đã từ chối đơn ứng tuyển #{app_id}"),
            }
            ic, col, msg = _TOAST.get(new_status, ("ic_alert.svg", "#6366f1", f"Cập nhật → {label_vi}"))
            if new_status == "approved" and result.get("invoice_amount_vnd"):
                amount = int(result.get("invoice_amount_vnd") or 0)
                msg = f"Đã phê duyệt đơn #{app_id}. Đã tạo invoice: {amount:,} VND"
            self._show_toast(msg, ic, col)
        elif 'result' in locals():
            # API trả về phản hồi hợp lệ nhưng không thành công.
            self._show_toast(f"Không tìm thấy đơn #{app_id}", "ic_x.svg", "#ef4444")
        # Refresh table với dữ liệu mới nhất
        self._fill_cands_table()

    # ── pagination ────────────────────────────────────────────
    def _update_cands_pagination(self, n_pages: int, total: int, page_size: int) -> None:
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
        s = self._cands_page * page_size + 1 if total > 0 else 0
        e = min((self._cands_page + 1) * page_size, total)
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
        self._fetch_cands_page()

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
