from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QByteArray, QRectF, QPointF, QSize
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QPen,
    QBrush, QPixmap, QRadialGradient, QPainterPath, QIcon,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
    QGraphicsDropShadowEffect,
)

from .. import session_store
from ..client import jobhub_api
from ..client.jobhub_api import ApiError

# ══════════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ══════════════════════════════════════════════════════════════
P        = "#2563eb"
P_DARK   = "#1d4ed8"
P_PRESS  = "#1e40af"
BG_PAGE  = "#f0f5ff"
BG_CARD  = "#ffffff"
BG_IN    = "#f1f3f9"          # input background — slightly cooler than plain gray
TXT_H    = "#111827"
TXT_S    = "#374151"          # label color
TXT_M    = "#6b7280"          # subtitle / helper — darker than before
TXT_PH   = "#a0adb8"          # placeholder — lighter than label
BORDER   = "#d1d5db"          # input border — slightly more visible
BORDER_F = P                  # focused border
ERR      = "#ef4444"
CHK_BORDER = "#9ca3af"        # checkbox border — clearly visible

_ICONS_DIR = Path(__file__).resolve().parent.parent.parent / "resources" / "icons"


# ══════════════════════════════════════════════════════════════
#  SVG HELPER
# ══════════════════════════════════════════════════════════════
def _svg_pixmap(name: str, size: int = 18, color: str = TXT_PH) -> QPixmap:
    path = _ICONS_DIR / name
    if not path.exists():
        return QPixmap()
    raw = path.read_text(encoding="utf-8").replace("currentColor", color)
    data = QByteArray(raw.encode())
    rdr  = QSvgRenderer(data)
    pm   = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    rdr.render(p)
    p.end()
    return pm


def _svg_icon(name: str, size: int = 18, color: str = TXT_PH) -> QIcon:
    return QIcon(_svg_pixmap(name, size, color))


# ══════════════════════════════════════════════════════════════
#  BASE QSS  — only structural styles; colors set inline
# ══════════════════════════════════════════════════════════════
_BASE_QSS = f"""
* {{
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 14px;
}}
QFrame#authCard   {{ background:{BG_CARD}; border-radius:24px; }}
QFrame#pillWrap   {{
    background:#eef2ff; border-radius:14px;
    border:1.5px solid #c7d2fe;
}}
QGroupBox {{
    border:1.5px solid {BORDER}; border-radius:14px;
    margin-top:20px; padding:14px 12px 12px 12px;
    background:#fafafa;
}}
QGroupBox::title {{
    subcontrol-origin:margin; subcontrol-position:top left;
    left:14px; padding:0 6px;
    color:{P}; font-weight:700; font-size:13px; background:#fafafa;
}}
QPlainTextEdit {{
    background:{BG_IN}; border:1.5px solid {BORDER};
    border-radius:10px; padding:8px 12px;
    color:{TXT_H};
}}
QPlainTextEdit:focus {{ border-color:{P}; background:#fff; }}
QScrollArea {{ border:none; background:transparent; }}
QScrollBar:vertical {{ width:4px; background:transparent; margin:0; }}
QScrollBar::handle:vertical {{
    background:#d1d5db; border-radius:2px; min-height:32px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
"""

# ── Button styles (applied directly to instances) ──────────────
_BTN_PRIMARY = f"""
QPushButton {{
    background-color: {P};
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    min-height: 52px;
    padding: 0 20px;
    letter-spacing: 0.4px;
}}
QPushButton:hover   {{ background-color: {P_DARK}; }}
QPushButton:pressed {{ background-color: {P_PRESS}; }}
QPushButton:disabled {{
    background-color: #93c5fd;
    color: rgba(255,255,255,0.7);
}}
"""

_BTN_TAB_ACTIVE = f"""
QPushButton {{
    background-color: {P};
    color: #ffffff;
    border: none;
    border-radius: 11px;
    font-size: 14px;
    font-weight: 700;
    min-height: 38px;
    padding: 0 30px;
}}
"""

_BTN_TAB_INACT = f"""
QPushButton {{
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 11px;
    font-size: 14px;
    font-weight: 500;
    min-height: 38px;
    padding: 0 30px;
}}
QPushButton:hover {{
    background-color: #e0e7ff;
    color: {P};
}}
"""

_CHK_REMEMBER = f"""
QCheckBox {{
    font-size: 13px;
    color: {TXT_S};
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 2px solid {CHK_BORDER};
    border-radius: 5px;
    background: #ffffff;
}}
QCheckBox::indicator:hover {{
    border-color: {P};
}}
QCheckBox::indicator:checked {{
    background-color: {P};
    border-color: {P};
    image: none;
}}
"""

_CHK_HR = f"""
QCheckBox {{
    font-size: 13px;
    color: {TXT_S};
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 2px solid {CHK_BORDER};
    border-radius: 5px;
    background: #ffffff;
}}
QCheckBox::indicator:hover {{ border-color: {P}; }}
QCheckBox::indicator:checked {{
    background-color: {P};
    border-color: {P};
}}
"""


# ══════════════════════════════════════════════════════════════
#  LABEL HELPER
# ══════════════════════════════════════════════════════════════
def _lbl(text: str, size: int = 14, bold: bool = False,
         color: str = TXT_H, wrap: bool = False) -> QLabel:
    w = QLabel(text)
    w.setWordWrap(wrap)
    w.setStyleSheet(
        f"color:{color}; font-size:{size}px; "
        f"font-weight:{'700' if bold else '500'}; "
        "background:transparent; border:none;"
    )
    return w


def _shadow(w: QWidget, blur: int = 48, dy: int = 14, alpha: int = 28) -> None:
    fx = QGraphicsDropShadowEffect(w)
    fx.setBlurRadius(blur)
    fx.setOffset(0, dy)
    fx.setColor(QColor(37, 99, 235, alpha))
    w.setGraphicsEffect(fx)


# ══════════════════════════════════════════════════════════════
#  ICON INPUT
# ══════════════════════════════════════════════════════════════
class _IconInput(QFrame):
    """[SVG icon] [QLineEdit] [optional eye-toggle] in a styled frame."""

    _SS_NORMAL = (
        f"QFrame {{ background:{BG_IN}; border:1.5px solid {BORDER}; "
        f"border-radius:12px; }}"
    )
    _SS_FOCUS = (
        f"QFrame {{ background:#ffffff; border:2px solid {P}; "
        f"border-radius:12px; }}"
    )

    def __init__(self, icon_svg: str, placeholder: str = "",
                 is_password: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setStyleSheet(self._SS_NORMAL)
        self._svg    = icon_svg
        self._shown  = False

        lo = QHBoxLayout(self)
        lo.setContentsMargins(13, 0, 8, 0)
        lo.setSpacing(9)
        lo.setAlignment(Qt.AlignVCenter)      # ← vertical centering for ALL children

        # ── Left icon ──────────────────────────────────────
        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(18, 18)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet("background:transparent;border:none;")
        self._icon_lbl.setPixmap(_svg_pixmap(icon_svg, 18, TXT_PH))
        lo.addWidget(self._icon_lbl, 0, Qt.AlignVCenter)

        # ── Input ──────────────────────────────────────────
        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.setFrame(False)
        self._edit.setMinimumHeight(30)
        self._edit.setStyleSheet(
            f"background:transparent; border:none; outline:none; "
            f"font-size:14px; color:{TXT_H}; "
            f"selection-background-color:{P};"
        )
        if is_password:
            self._edit.setEchoMode(QLineEdit.Password)
        # wire focus
        _orig_in  = self._edit.focusInEvent
        _orig_out = self._edit.focusOutEvent
        def _in(e):
            self.setStyleSheet(self._SS_FOCUS)
            self._icon_lbl.setPixmap(_svg_pixmap(icon_svg, 18, P))
            _orig_in(e)
        def _out(e):
            self.setStyleSheet(self._SS_NORMAL)
            self._icon_lbl.setPixmap(_svg_pixmap(icon_svg, 18, TXT_PH))
            _orig_out(e)
        self._edit.focusInEvent  = _in
        self._edit.focusOutEvent = _out
        lo.addWidget(self._edit, 1, Qt.AlignVCenter)

        # ── Eye toggle (password only) ──────────────────────
        if is_password:
            self._eye = QPushButton()
            self._eye.setFixedSize(22, 22)
            self._eye.setCursor(Qt.PointingHandCursor)
            self._eye.setFocusPolicy(Qt.NoFocus)
            self._eye.setFlat(True)
            self._eye.setStyleSheet(
                "QPushButton { background:transparent; border:none; padding:0; }"
            )
            self._eye.setIconSize(QSize(18, 18))
            self._update_eye()
            self._eye.clicked.connect(self._toggle_pw)
            lo.addWidget(self._eye, 0, Qt.AlignVCenter)

    def _update_eye(self) -> None:
        svg = "ic_eye2.svg" if self._shown else "ic_eye_off.svg"
        self._eye.setIcon(_svg_icon(svg, 18, TXT_PH))

    def _toggle_pw(self) -> None:
        self._shown = not self._shown
        self._edit.setEchoMode(
            QLineEdit.Normal if self._shown else QLineEdit.Password
        )
        self._update_eye()

    # proxy
    def text(self) -> str:              return self._edit.text()
    def setText(self, v: str) -> None:  self._edit.setText(v)
    def clear(self) -> None:            self._edit.clear()

    @property
    def edit(self) -> QLineEdit:
        return self._edit


# ══════════════════════════════════════════════════════════════
#  BRAND PANEL
# ══════════════════════════════════════════════════════════════
class _BrandPanel(QWidget):
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        bg = QLinearGradient(0, 0, w * .5, h)
        bg.setColorAt(0.0, QColor("#60a5fa"))
        bg.setColorAt(.45, QColor("#3b82f6"))
        bg.setColorAt(1.0, QColor("#1d4ed8"))
        p.fillRect(self.rect(), bg)

        for cx, cy, r, a in [(w*.82,h*.10,130,20),(w*.10,h*.80,100,16),(w*.62,h*.90,70,13)]:
            rg = QRadialGradient(cx, cy, r)
            rg.setColorAt(0, QColor(255,255,255,a))
            rg.setColorAt(1, QColor(255,255,255,0))
            p.setBrush(rg); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(cx,cy), r, r)

        self._scene(p, w, h)
        p.end()

    def _scene(self, p: QPainter, pw: float, ph: float) -> None:
        sc = min(pw/400, 1.0)
        cx = pw * .5
        cy = ph * .63

        def line(x1,y1,x2,y2,a=52,lw=1.4):
            p.setPen(QPen(QColor(255,255,255,a),lw*sc,Qt.SolidLine,Qt.RoundCap))
            p.drawLine(QPointF(x1,y1),QPointF(x2,y2))

        def card(x,y,bw,bh,a=28):
            p.setBrush(QColor(255,255,255,a)); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x-bw/2,y-bh/2,bw,bh),10*sc,10*sc)
            p.setPen(QPen(QColor(255,255,255,50),1.4*sc,Qt.SolidLine,Qt.RoundCap))
            for dy in [-6*sc, 3*sc]:
                p.drawLine(QPointF(x-bw*.35,y+dy), QPointF(x+bw*.35,y+dy))

        nodes = [
            (cx,          cy-110*sc, 27*sc),
            (cx-125*sc,   cy-18*sc,  21*sc),
            (cx+125*sc,   cy-18*sc,  21*sc),
            (cx-55*sc,    cy+78*sc,  17*sc),
            (cx+55*sc,    cy+78*sc,  17*sc),
        ]
        for a,b in [(0,1),(0,2),(1,3),(2,4),(1,2),(3,4)]:
            line(nodes[a][0],nodes[a][1],nodes[b][0],nodes[b][1])

        for nx,ny,nr in nodes:
            gw = QRadialGradient(nx,ny,nr*2)
            gw.setColorAt(0,QColor(255,255,255,28)); gw.setColorAt(1,QColor(255,255,255,0))
            p.setBrush(gw); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(nx,ny),nr*2,nr*2)
            p.setBrush(QColor(255,255,255,228))
            p.setPen(QPen(QColor(255,255,255),1.5*sc))
            p.drawEllipse(QPointF(nx,ny),nr,nr)
            p.setBrush(QColor(99,149,230,200)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(nx,ny-nr*.16),nr*.34,nr*.34)
            path = QPainterPath()
            path.moveTo(nx-nr*.54,ny+nr*.75)
            path.quadTo(nx,ny+nr*.28,nx+nr*.54,ny+nr*.75)
            path.lineTo(nx+nr*.54,ny+nr); path.lineTo(nx-nr*.54,ny+nr)
            path.closeSubpath()
            p.fillPath(path,QColor(99,149,230,200))

        for fx,fy,fw,fh in [(cx-148*sc,cy+18*sc,76*sc,38*sc),
                             (cx+148*sc,cy+18*sc,76*sc,38*sc),
                             (cx,cy+112*sc,86*sc,38*sc)]:
            card(fx,fy,fw,fh)

        # briefcase
        bx,by,bw2,bh2 = cx,cy-198*sc,52*sc,40*sc
        p.setBrush(QColor(255,255,255,215)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(bx-bw2/2,by-bh2/2+5*sc,bw2,bh2),8*sc,8*sc)
        hw,hh = bw2*.43,13*sc
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255,255,255,215),3.2*sc,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        p.drawRoundedRect(QRectF(bx-hw/2,by-hh*.65-bh2/2+5*sc,hw,hh),4*sc,4*sc)
        p.drawLine(QPointF(bx-bw2/2+2*sc,by+5*sc),QPointF(bx+bw2/2-2*sc,by+5*sc))

        for dx,dy,dr in [(cx-175*sc,cy-148*sc,5*sc),(cx+165*sc,cy-128*sc,4*sc),
                          (cx+8*sc,cy-172*sc,3.5*sc),(cx-158*sc,cy+108*sc,4*sc),
                          (cx+170*sc,cy+95*sc,5*sc)]:
            p.setBrush(QColor(255,255,255,110)); p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(dx,dy),dr,dr)


# ══════════════════════════════════════════════════════════════
#  PILL TAB CONTROL
# ══════════════════════════════════════════════════════════════
class _PillTabs(QFrame):
    def __init__(self, labels: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("pillWrap")
        self.setFixedHeight(50)
        self._btns: list[QPushButton] = []
        self._cb = None
        lo = QHBoxLayout(self)
        lo.setContentsMargins(5,5,5,5)
        lo.setSpacing(4)
        for i, lbl in enumerate(labels):
            btn = QPushButton(lbl)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            lo.addWidget(btn)
            self._btns.append(btn)
            btn.clicked.connect(lambda _, idx=i: self._sel(idx))
        self._sel(0)

    def _sel(self, idx: int) -> None:
        self._cur = idx
        for i, b in enumerate(self._btns):
            # Apply stylesheet DIRECTLY — guaranteed to override platform defaults
            b.setStyleSheet(_BTN_TAB_ACTIVE if i == idx else _BTN_TAB_INACT)
        if self._cb:
            self._cb(idx)

    def on_change(self, fn) -> None:
        self._cb = fn

    @property
    def current(self) -> int:
        return self._cur


# ══════════════════════════════════════════════════════════════
#  AUTH WINDOW
# ══════════════════════════════════════════════════════════════
class AuthWindow:
    def __init__(self, on_success: Callable[[dict], None]) -> None:
        self._on_success = on_success
        self._build()

    # ── window ────────────────────────────────────────────────
    def _build(self) -> None:
        win = QMainWindow()
        win.setWindowTitle("JobHub — Đăng nhập")
        win.setMinimumSize(860, 580)
        win.resize(1140, 680)
        win.setStyleSheet(_BASE_QSS)
        self.win = win

        root = QWidget()
        root.setStyleSheet(f"background:{BG_PAGE};")
        rlo = QHBoxLayout(root)
        rlo.setSpacing(0); rlo.setContentsMargins(0,0,0,0)
        rlo.addWidget(self._make_brand(), 44)
        rlo.addWidget(self._make_right(), 56)
        win.setCentralWidget(root)

    # ── brand panel ───────────────────────────────────────────
    def _make_brand(self) -> _BrandPanel:
        panel = _BrandPanel()
        lo = QVBoxLayout(panel)
        lo.setContentsMargins(52,52,44,48); lo.setSpacing(0)

        row = QHBoxLayout(); row.setSpacing(8)
        bolt = QLabel("⚡")
        bolt.setStyleSheet("color:#fff;font-size:30px;background:transparent;border:none;")
        name = QLabel("JobHub")
        name.setStyleSheet(
            "color:#fff;font-size:40px;font-weight:800;"
            "letter-spacing:-0.5px;background:transparent;border:none;"
        )
        row.addWidget(bolt); row.addWidget(name); row.addStretch()
        lo.addLayout(row); lo.addSpacing(14)

        tag = QLabel("Nền tảng kết nối nhà tuyển dụng\nvà ứng viên hiện đại.")
        tag.setWordWrap(True)
        tag.setStyleSheet(
            "color:rgba(255,255,255,0.87);font-size:18px;font-weight:500;"
            "background:transparent;border:none;"
        )
        lo.addWidget(tag); lo.addStretch()

        foot = QLabel("© 2025 JobHub Inc.")
        foot.setStyleSheet(
            "color:rgba(255,255,255,0.45);font-size:11px;"
            "background:transparent;border:none;"
        )
        lo.addWidget(foot)
        return panel

    # ── right side ────────────────────────────────────────────
    def _make_right(self) -> QWidget:
        side = QWidget()
        side.setStyleSheet(f"background:{BG_PAGE};")
        lo = QVBoxLayout(side)
        lo.setContentsMargins(0,0,0,0)
        lo.addStretch(1)
        lo.addWidget(self._make_card(), alignment=Qt.AlignHCenter)
        lo.addStretch(1)
        return side

    # ── card ──────────────────────────────────────────────────
    def _make_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("authCard")
        card.setFixedWidth(460)
        card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        _shadow(card)

        lo = QVBoxLayout(card)
        lo.setContentsMargins(40,34,40,40); lo.setSpacing(0)

        # pill tabs
        self._tabs = _PillTabs(["Đăng nhập", "Đăng ký"])
        lo.addWidget(self._tabs); lo.addSpacing(24)

        # title + subtitle
        self._title    = _lbl("Đăng nhập vào tài khoản", 22, bold=True)
        self._subtitle = _lbl("Nhập thông tin đăng nhập của bạn.",
                               13, color=TXT_M)
        lo.addWidget(self._title); lo.addSpacing(5)
        lo.addWidget(self._subtitle); lo.addSpacing(22)

        # stacked pages
        self._stack = QStackedWidget()
        self._stack.addWidget(self._make_login_page())     # 0 → Đăng nhập
        self._stack.addWidget(self._make_register_page())  # 1 → Đăng ký
        self._stack.setCurrentIndex(0)
        lo.addWidget(self._stack)

        self._tabs.on_change(self._switch_tab)
        return card

    # ── login page ────────────────────────────────────────────
    def _make_login_page(self) -> QWidget:
        pg = QWidget(); pg.setStyleSheet("background:transparent;")
        lo = QVBoxLayout(pg)
        lo.setContentsMargins(0,0,0,0); lo.setSpacing(0)

        # Email field
        lo.addWidget(_lbl("Email", 13, bold=True, color=TXT_S))
        lo.addSpacing(7)
        self.inp_email = _IconInput("ic_email.svg", "you@email.com")
        lo.addWidget(self.inp_email)
        lo.addSpacing(18)

        # Password field
        lo.addWidget(_lbl("Mật khẩu", 13, bold=True, color=TXT_S))
        lo.addSpacing(7)
        self.inp_password = _IconInput("ic_lock2.svg", "Nhập mật khẩu",
                                       is_password=True)
        lo.addWidget(self.inp_password)
        lo.addSpacing(8)

        # "Quên mật khẩu?" — subtle, right-aligned, under password field
        forgot_row = QHBoxLayout()
        forgot_row.setContentsMargins(0,0,0,0)
        forgot_row.addStretch()
        forgot = QPushButton("Quên mật khẩu?")
        forgot.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; "
            f"color:{TXT_M}; font-size:12px; font-weight:500; padding:0; }}"
            f"QPushButton:hover {{ color:{P}; }}"
        )
        forgot.setCursor(Qt.PointingHandCursor)
        forgot.setFocusPolicy(Qt.NoFocus)
        forgot_row.addWidget(forgot)
        lo.addLayout(forgot_row)
        lo.addSpacing(16)

        # Remember me checkbox
        self.chk_remember = QCheckBox("Ghi nhớ đăng nhập")
        self.chk_remember.setStyleSheet(_CHK_REMEMBER)
        lo.addWidget(self.chk_remember)
        lo.addSpacing(22)

        # ── CTA Button — set stylesheet DIRECTLY to guarantee blue ──
        self.btn_login = QPushButton("Đăng nhập")
        self.btn_login.setStyleSheet(_BTN_PRIMARY)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)
        lo.addWidget(self.btn_login)

        self.lbl_login_err = _lbl("", 13, color=ERR)
        self.lbl_login_err.setVisible(False)
        lo.addSpacing(8); lo.addWidget(self.lbl_login_err)
        lo.addStretch()
        return pg

    # ── register page ─────────────────────────────────────────
    def _make_register_page(self) -> QWidget:
        pg = QWidget(); pg.setStyleSheet("background:transparent;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget(); inner.setStyleSheet("background:transparent;")
        lo = QVBoxLayout(inner)
        lo.setContentsMargins(0,0,4,4); lo.setSpacing(0)

        def _field(label, widget):
            lo.addWidget(_lbl(label, 13, bold=True, color=TXT_S))
            lo.addSpacing(7); lo.addWidget(widget); lo.addSpacing(16)

        self.inp_reg_name     = _IconInput("ic_user.svg",  "Nguyễn Văn A")
        self.inp_reg_email    = _IconInput("ic_email.svg", "you@email.com")
        self.inp_reg_password = _IconInput("ic_lock2.svg", "Tối thiểu 6 ký tự",
                                            is_password=True)
        _field("Họ và tên", self.inp_reg_name)
        _field("Email",     self.inp_reg_email)
        _field("Mật khẩu", self.inp_reg_password)

        self.chk_hr = QCheckBox("Bạn là nhà tuyển dụng?")
        self.chk_hr.setStyleSheet(_CHK_HR)
        lo.addWidget(self.chk_hr); lo.addSpacing(10)

        self.grp_company = QGroupBox("Thông tin doanh nghiệp")
        self.grp_company.setVisible(False)
        gl = QVBoxLayout(self.grp_company)
        gl.setSpacing(8); gl.setContentsMargins(8,14,8,10)

        self.inp_company = _IconInput("ic_building.svg","Tên công ty")
        self.inp_phone   = _IconInput("ic_phone.svg",   "0901 234 567")
        self.txt_desc    = QPlainTextEdit()
        self.txt_desc.setPlaceholderText("Mô tả ngắn về công ty...")
        self.txt_desc.setFixedHeight(80)

        def _gf(label, w):
            gl.addWidget(_lbl(label,12,bold=True,color=TXT_S))
            gl.addSpacing(5); gl.addWidget(w); gl.addSpacing(8)

        _gf("Tên công ty", self.inp_company)
        _gf("Điện thoại",  self.inp_phone)
        _gf("Mô tả",       self.txt_desc)
        lo.addWidget(self.grp_company)

        self.chk_hr.toggled.connect(
            lambda v: (self.grp_company.setVisible(v),
                       self.grp_company.setEnabled(v))
        )

        lo.addSpacing(20)
        self.btn_register = QPushButton("Tạo tài khoản")
        self.btn_register.setStyleSheet(_BTN_PRIMARY)   # direct — không dùng objectName
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.clicked.connect(self._do_register)
        lo.addWidget(self.btn_register)

        self.lbl_reg_err = _lbl("", 13, color=ERR)
        self.lbl_reg_err.setVisible(False)
        lo.addSpacing(8); lo.addWidget(self.lbl_reg_err)
        lo.addStretch()

        scroll.setWidget(inner)
        olo = QVBoxLayout(pg); olo.setContentsMargins(0,0,0,0)
        olo.addWidget(scroll)
        return pg

    # ── tab switch ────────────────────────────────────────────
    def _switch_tab(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)
        if idx == 0:
            self._title.setText("Đăng nhập vào tài khoản")
            self._subtitle.setText("Nhập thông tin đăng nhập của bạn.")
        else:
            self._title.setText("Tạo tài khoản mới")
            self._subtitle.setText("Điền đầy đủ thông tin để bắt đầu.")

    # ── actions ───────────────────────────────────────────────
    def _do_login(self) -> None:
        self.lbl_login_err.setVisible(False)
        email = self.inp_email.text().strip()
        pwd   = self.inp_password.text()
        if not email or not pwd:
            self._err(self.lbl_login_err, "Vui lòng nhập email và mật khẩu.")
            return
        if not self._ping(self.lbl_login_err):
            return
        try:
            data = jobhub_api.login(email, pwd)
        except ApiError as e:
            self._err(self.lbl_login_err, str(e))
            return
        self._finalize(data)

    def _do_register(self) -> None:
        self.lbl_reg_err.setVisible(False)
        email     = self.inp_reg_email.text().strip()
        pwd       = self.inp_reg_password.text()
        full_name = self.inp_reg_name.text().strip() or None
        if not email or not pwd:
            self._err(self.lbl_reg_err, "Vui lòng nhập email và mật khẩu.")
            return
        if not self._ping(self.lbl_reg_err):
            return
        try:
            if self.chk_hr.isChecked():
                company = self.inp_company.text().strip()
                if not company:
                    self._err(self.lbl_reg_err, "Vui lòng nhập tên công ty.")
                    return
                data = jobhub_api.register_hr(
                    email, pwd, full_name, company,
                    self.inp_phone.text().strip() or None,
                    self.txt_desc.toPlainText().strip() or None,
                )
            else:
                data = jobhub_api.register_candidate(email, pwd, full_name)
        except ApiError as e:
            self._err(self.lbl_reg_err, str(e))
            return
        self._finalize(data)

    def _ping(self, err: QLabel) -> bool:
        try:
            jobhub_api.health(); return True
        except Exception:
            self._err(err, "Không kết nối được máy chủ."); return False

    def _finalize(self, data: dict) -> None:
        token = data.get("access_token")
        session_store.save_session(token)
        try:
            user = jobhub_api.me()
        except ApiError as e:
            session_store.clear_session()
            QMessageBox.critical(self.win, "JobHub", str(e))
            return
        session_store.save_session(token, user)
        self.win.hide()
        self._on_success(user)

    @staticmethod
    def _err(lbl: QLabel, msg: str) -> None:
        lbl.setText(f"⚠  {msg}"); lbl.setVisible(True)

    # ── public ────────────────────────────────────────────────
    def show(self) -> None:       self.win.show()
    def raise_(self) -> None:
        self.win.raise_(); self.win.activateWindow()
    def set_startup_pos(self) -> None:
        self.win.setGeometry(80, 60, 1140, 680)

    # back-compat aliases
    @property
    def line_login_email(self):    return self.inp_email
    @property
    def line_login_password(self): return self.inp_password
    @property
    def line_reg_name(self):       return self.inp_reg_name
    @property
    def line_reg_email(self):      return self.inp_reg_email
    @property
    def line_reg_password(self):   return self.inp_reg_password
    @property
    def check_is_hr(self):         return self.chk_hr
    @property
    def group_hr(self):            return self.grp_company
    @property
    def line_company(self):        return self.inp_company
    @property
    def line_phone(self):          return self.inp_phone
    @property
    def plain_company(self):       return self.txt_desc


# ══════════════════════════════════════════════════════════════
def try_resume_session(on_success: Callable[[dict], None]) -> bool:
    if not session_store.get_token():
        return False
    try:
        user = jobhub_api.me()
    except Exception:
        session_store.clear_session(); return False
    session_store.save_session(session_store.get_token(), user)
    on_success(user)
    return True
