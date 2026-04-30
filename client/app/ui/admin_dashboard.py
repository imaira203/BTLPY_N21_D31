from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPropertyAnimation, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..client import jobhub_api
from ..client.jobhub_api import ApiError
from ..paths import resource_icon, resource_ui
from ..session_store import clear_session
from .charts import (
    make_recruitment_trend_chart,
    make_donut_chart,
    make_revenue_trend_chart,
    make_dept_bar_chart,
)
from .ui_loader import load_ui
from .quanly_enhanced import apply_search_icon, enhance_table


# ── Helpers ────────────────────────────────────────────────────
def _shadow(widget: QWidget, blur: int = 16, dy: int = 2, alpha: int = 20) -> None:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)


def _pill(text: str, bg: str, fg: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"QLabel {{ background:{bg}; color:{fg}; font-size:12px; font-weight:600;"
        f" border-radius:10px; padding:3px 10px; border:none; }}"
    )
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    return lbl


_STATUS_COLORS: dict[str, tuple[str, str]] = {
    "active":           ("#DCFCE7", "#15803D"),
    "inactive":         ("#F3F4F6", "#6B7280"),
    "published":        ("#DCFCE7", "#15803D"),
    "draft":            ("#FEF9C3", "#92400E"),
    "closed":           ("#F3F4F6", "#6B7280"),
    "rejected":         ("#FEE2E2", "#B91C1C"),
    "pending_approval": ("#DBEAFE", "#1D4ED8"),
}

_JOB_TYPE_COLORS: dict[str, tuple[str, str]] = {
    "Full-time":  ("#DBEAFE", "#1D4ED8"),
    "Part-time":  ("#FEF9C3", "#92400E"),
    "Remote":     ("#F0FDF4", "#166534"),
    "Contract":   ("#F3E8FF", "#6D28D9"),
    "Internship": ("#FFF7ED", "#C2410C"),
}



def _toast(parent_win, message: str, success: bool = True) -> None:
    """Show a brief auto-dismiss notification at the top-center of the window."""
    from PySide6.QtCore import QPropertyAnimation, QRect
    bg   = "#16A34A" if success else "#DC2626"
    icon = "✓ " if success else "✕ "

    lbl = QLabel(icon + message, parent_win)
    lbl.setStyleSheet(
        f"QLabel {{ background:{bg}; color:#FFFFFF; font-size:13px; font-weight:600;"
        f" border-radius:8px; padding:10px 20px; border:none; }}"
    )
    lbl.setAlignment(Qt.AlignCenter)
    lbl.adjustSize()
    lbl.setFixedWidth(max(lbl.width() + 40, 260))

    pw = parent_win.width()
    x  = (pw - lbl.width()) // 2
    lbl.move(x, -50)
    lbl.show()
    lbl.raise_()

    anim_in = QPropertyAnimation(lbl, b"pos")
    anim_in.setDuration(260)
    anim_in.setStartValue(lbl.pos())
    from PySide6.QtCore import QPoint
    anim_in.setEndValue(QPoint(x, 16))
    anim_in.start()

    def _dismiss():
        anim_out = QPropertyAnimation(lbl, b"pos")
        anim_out.setDuration(220)
        anim_out.setStartValue(QPoint(x, 16))
        anim_out.setEndValue(QPoint(x, -60))
        anim_out.finished.connect(lbl.deleteLater)
        anim_out.start()
        lbl._anim_out = anim_out

    lbl._anim_in = anim_in
    QTimer.singleShot(2400, _dismiss)


class AdminDashboard:
    @staticmethod
    def _fmt_date(raw: str) -> str:
        if "T" in raw:
            return raw.split("T", 1)[0]
        return raw

    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout

        win = load_ui(resource_ui("admin_dashboard.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("admin_dashboard.ui must be a QMainWindow")
        self.win = win

        # ── Rebuild centralwidget layout to guarantee sidebar width ──
        # Qt can ignore min/maxSize from .ui files when other children
        # in the same layout have large minimum sizes (e.g. searchBoxFrame
        # minWidth=260).  The only rock-solid fix is to tear down the
        # QHBoxLayout items and re-add them with explicit stretch factors.
        self._fix_sidebar_layout(win)

        # Load sub-UIs
        self._user_widget   = self._load_sub_ui("QuanLyUser.ui")
        self._jobs_widget   = self._load_sub_ui("QuanLyJobs.ui")
        self._hr_widget     = self._load_sub_ui("QuanLyHR.ui")
        self._reports_widget = self._load_sub_ui("QuanLyReports.ui")

        self._bind_widgets()
        self._inject_pages()
        self._setup_nav()
        self._restyle_sidebar()
        self._go(0)

    # ── Guarantee sidebar width ────────────────────────────────
    def _fix_sidebar_layout(self, win: QMainWindow) -> None:
        """
        Tear down the centralwidget's QHBoxLayout and re-add sidebar +
        content area with explicit stretch so the sidebar is always 260 px.
        """
        central = win.centralWidget()
        if not central:
            return
        layout = central.layout()
        if not layout:
            return

        # Pull all widgets out of the layout (without deleting them)
        widgets: list[QWidget] = []
        while layout.count():
            item = layout.takeAt(0)
            if item and item.widget():
                widgets.append(item.widget())

        # Re-add: sidebar gets stretch=0 + fixed width; rest gets stretch=1
        for w in widgets:
            if w.objectName() == "sidebar":
                w.setFixedWidth(260)
                w.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
                layout.addWidget(w, 0)          # stretch = 0
            else:
                w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                layout.addWidget(w, 1)          # stretch = 1

    # ── Sub-UI loader ──────────────────────────────────────────
    def _load_sub_ui(self, ui_name: str) -> QWidget:
        sub = load_ui(resource_ui(ui_name))
        area = sub.findChild(QWidget, "mainArea")
        if area:
            area.setParent(None)
            return area
        return sub

    # ── Inject management pages into stacked widget ────────────
    def _inject_pages(self) -> None:
        if not self.stack:
            return

        # ── Wrap the built-in Dashboard page (index 0) in a QScrollArea ──
        # Without this, content overflows and gets visually squished when
        # the window is not tall enough.
        dash_page = self.stack.widget(0)   # pageDashboard from .ui
        if dash_page:
            dash_page.setParent(None)      # detach from stack temporarily
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet(
                "QScrollArea { background:#F8F9FA; border:none; }"
                "QScrollArea > QWidget > QWidget { background:#F8F9FA; }"
            )
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll.setWidget(dash_page)
            self.stack.insertWidget(0, scroll)   # put it back at index 0

        for w in (self._user_widget, self._jobs_widget,
                  self._hr_widget, self._reports_widget):
            self.stack.addWidget(w)

        # Table refs (Users)
        self.table_users = self._user_widget.findChild(QTableWidget, "userTable")
        # Jobs scroll content grid
        self._jobs_grid = self._jobs_widget.findChild(QGridLayout, "jobsGridLayout")
        # HR cards layout + chart frame + metrics container
        self._hr_cards_layout    = self._hr_widget.findChild(QHBoxLayout, "hrCardsLayout")
        self._dept_chart_frame   = self._hr_widget.findChild(QLabel, "deptChartPlaceholder")
        self._metrics_container  = self._hr_widget.findChild(QVBoxLayout, "metricsContainerLayout")

        # Search refs
        self.search_user = self._user_widget.findChild(QLineEdit, "searchInput")
        self.search_jobs = self._jobs_widget.findChild(QLineEdit, "searchInput")
        if self.search_user:
            apply_search_icon(self.search_user)
        if self.search_jobs:
            apply_search_icon(self.search_jobs)

    # ── Bind main-window widgets ───────────────────────────────
    def _bind_widgets(self) -> None:
        f = self.win.findChild
        self.nav_dash     = f(QPushButton, "navDashboard")
        self.nav_users    = f(QPushButton, "navUserMgmt")
        self.nav_jobs     = f(QPushButton, "navJobMgmt")
        self.nav_hr       = f(QPushButton, "navHRMgmt")
        self.nav_reports  = f(QPushButton, "navReports")
        self.nav_settings = f(QPushButton, "navSettings")
        self.btn_logout   = f(QPushButton, "logoutButton")
        self.page_title   = f(QLabel, "pageTitle")
        self.page_subtitle= f(QLabel, "pageSubTitle")
        self.stack        = f(QStackedWidget, "stackedPages")
        self.cards_row    = f(QHBoxLayout, "horizontalLayout_cards")
        self.chart_ph     = f(QLabel, "chartPlaceholder")
        self.donut_ph     = f(QLabel, "donutPlaceholder")
        self.activities_layout = f(QVBoxLayout, "activitiesLayout")

        # ── Topbar search ─────────────────────────────────────────
        search_frame = f(QFrame, "searchBoxFrame")
        if search_frame:
            # Wider + white background, clean border
            search_frame.setMinimumWidth(320)
            search_frame.setMaximumWidth(480)
            search_frame.setFixedHeight(40)
            search_frame.setStyleSheet(
                "QFrame#searchBoxFrame {"
                " background:#FFFFFF;"
                " border:1.5px solid #E5E7EB;"
                " border-radius:10px;"
                "}"
                "QFrame#searchBoxFrame:focus-within {"
                " border-color:#2563EB;"
                " background:#FFFFFF;"
                "}"
            )

        # Set SVG pixmap on the dedicated icon label (not background-image hack)
        icon_lbl = f(QLabel, "searchIconLabel")
        if icon_lbl:
            icon_lbl.setPixmap(
                QIcon(str(resource_icon("ic_search.svg"))).pixmap(QSize(16, 16))
            )
            icon_lbl.setFixedSize(16, 16)
            icon_lbl.setStyleSheet("QLabel { background:transparent; border:none; }")

        sb = f(QLineEdit, "searchInput")
        if sb:
            sb.setPlaceholderText("Tìm kiếm...")
            sb.setStyleSheet(
                "QLineEdit { background:transparent; border:none;"
                " font-size:13px; color:#374151; }"
                "QLineEdit::placeholder { color:#9CA3AF; }"
            )

        # ── Bell notification button ───────────────────────────────
        btn_notify = f(QPushButton, "btnNotify")
        if btn_notify:
            btn_notify.setFixedSize(40, 40)
            btn_notify.setIcon(QIcon(str(resource_icon("ic_bell.svg"))))
            btn_notify.setIconSize(QSize(18, 18))
            btn_notify.setStyleSheet(
                "QPushButton { background:#F9FAFB; border:1.5px solid #E5E7EB;"
                " border-radius:20px; }"
                "QPushButton:hover { background:#EFF6FF; border-color:#BFDBFE; }"
            )

        # ── Topbar avatar ──────────────────────────────────────────
        avatar = f(QLabel, "topBarAvatar")
        if avatar:
            avatar.setFixedSize(40, 40)
            avatar.setAlignment(Qt.AlignCenter)
            avatar.setStyleSheet(
                "QLabel { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                "stop:0 #2563EB,stop:1 #3B82F6);"
                " color:#FFFFFF; font-size:15px; font-weight:800;"
                " border-radius:20px; border:none; }"
            )

    # ── Navigation ─────────────────────────────────────────────
    def _setup_nav(self) -> None:
        self._nav_group = QButtonGroup(self.win)
        nav_items = [
            (self.nav_dash,    0, "ic_dashboard.svg",  "Bảng điều khiển",   "Chào mừng trở lại, Admin"),
            (self.nav_users,   1, "ic_users.svg",      "Quản lý người dùng","Quản lý tài khoản và quyền hạn"),
            (self.nav_jobs,    2, "ic_jobs.svg",       "Quản lý việc làm",  "Quản lý tin tuyển dụng và đơn ứng tuyển"),
            (self.nav_hr,      3, "ic_hr.svg",         "Quản lý HR",         "Danh sách nhà tuyển dụng trên hệ thống"),
            (self.nav_reports, 4, "ic_doc.svg",        "Báo cáo",           "Tạo và tải xuống phân tích dữ liệu"),
        ]
        for btn, idx, icon, title, sub in nav_items:
            if not btn:
                continue
            btn.setCheckable(True)
            btn.setIcon(QIcon(str(resource_icon(icon))))
            btn.setIconSize(QSize(18, 18))
            self._nav_group.addButton(btn)
            btn.clicked.connect(lambda _, i=idx: self._go(i))

        # Hide Settings button — not used
        if self.nav_settings:
            self.nav_settings.hide()

        if self.btn_logout:
            self.btn_logout.setIcon(QIcon(str(resource_icon("ic_logout.svg"))))
            self.btn_logout.setIconSize(QSize(16, 16))
            self.btn_logout.clicked.connect(self._logout)

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)

        nav_btns = [self.nav_dash, self.nav_users, self.nav_jobs,
                    self.nav_hr, self.nav_reports]
        for i, btn in enumerate(nav_btns):
            if btn:
                btn.setChecked(i == index)

        titles = [
            ("Bảng điều khiển",   "Chào mừng trở lại, Admin"),
            ("Quản lý người dùng","Quản lý tài khoản và quyền hạn"),
            ("Quản lý việc làm",  "Quản lý tin tuyển dụng và đơn ứng tuyển"),
            ("Quản lý HR",         "Danh sách nhà tuyển dụng trên hệ thống"),
            ("Báo cáo",           "Tạo và tải xuống phân tích dữ liệu"),
        ]
        if index < len(titles):
            t, s = titles[index]
            if self.page_title:   self.page_title.setText(t)
            if self.page_subtitle: self.page_subtitle.setText(s)

        {0: self._load_dash,
         1: self._fill_user_table,
         2: self._fill_jobs_grid,
         3: self._fill_hr_page,
         4: self._fill_reports_page,
        }.get(index, lambda: None)()

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    # ══════════════════════════════════════════════════════════════
    #  DASHBOARD PAGE
    # ══════════════════════════════════════════════════════════════
    def _load_dash(self) -> None:
        try:
            data = jobhub_api.admin_dashboard()
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return

        cards_data = data.get("cards") or {}
        self._build_stat_cards(cards_data)
        self._build_recruitment_chart()
        self._build_donut()
        self._build_recent_activities()

    def _build_stat_cards(self, cards_data: dict) -> None:
        if not self.cards_row:
            return
        # Clear
        while self.cards_row.count():
            item = self.cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        items = [
            ("ic_users.svg",  "Tổng ứng viên",
             f"{cards_data.get('users', 0):,}",
             "+12.5% so tháng trước",
             "#2563EB", "#EFF6FF"),
            ("ic_jobs.svg",   "Việc đang tuyển",
             str(cards_data.get("jobs", 0)),
             "+4 mới tuần này",
             "#0891B2", "#ECFEFF"),
            ("ic_hr.svg",       "Tổng HR",
             str(cards_data.get("hr", 0)),
             f"+{cards_data.get('hr', 0)} tài khoản HR",
             "#059669", "#F0FDF4"),
            ("ic_activity.svg", "Tổng hoạt động",
             str(cards_data.get("activity_today", 0)),
             "Tin đăng trong 24h qua",
             "#7C3AED", "#FAF5FF"),
        ]

        for icon_name, title, val, hint, accent, icon_bg in items:
            card = self._make_stat_card(icon_name, title, val, hint, accent, icon_bg)
            self.cards_row.addWidget(card)

    def _make_stat_card(
        self,
        icon_name: str,
        title: str,
        val: str,
        hint: str,
        accent: str,
        icon_bg: str,
    ) -> QFrame:
        # ── Card frame ────────────────────────────────────────────────
        card = QFrame()
        card.setMinimumHeight(148)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet(
            f"QFrame {{ background:#FFFFFF; border-radius:14px;"
            f" border:1px solid #E5E7EB;"
            f" border-left:4px solid {accent}; }}"
        )
        _shadow(card, blur=20, dy=4, alpha=14)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(20, 14, 20, 14)
        outer.setSpacing(5)

        # ── Row 1: title + icon ───────────────────────────────────────
        r1 = QHBoxLayout()
        r1.setSpacing(8)
        r1.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel(title)
        lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl_title.setStyleSheet(
            "QLabel { font-size:13px; font-weight:500; color:#6B7280;"
            " background:transparent; border:none; }"
        )
        r1.addWidget(lbl_title, stretch=1)

        # Icon box
        icon_box = QLabel()
        icon_box.setFixedSize(44, 44)
        icon_box.setAlignment(Qt.AlignCenter)
        icon_box.setStyleSheet(
            f"QLabel {{ background:{icon_bg}; border-radius:12px; border:none; }}"
        )
        icon_box.setPixmap(
            QIcon(str(resource_icon(icon_name))).pixmap(QSize(24, 24))
        )
        r1.addWidget(icon_box)
        outer.addLayout(r1)

        # ── Row 2: value ──────────────────────────────────────────────
        lbl_val = QLabel(val)
        lbl_val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl_val.setMinimumHeight(42)
        lbl_val.setStyleSheet(
            "QLabel { font-size:26px; font-weight:800; color:#111827;"
            " background:transparent; border:none; }"
        )
        outer.addWidget(lbl_val)

        # ── Row 3: trend hint with auto color ─────────────────────────
        is_pos = hint.strip().startswith("+")
        is_neg = hint.strip().startswith("-")
        arrow  = "↑ " if is_pos else ("↓ " if is_neg else "→ ")
        color  = "#16A34A" if is_pos else ("#DC2626" if is_neg else "#6B7280")

        lbl_hint = QLabel(arrow + hint)
        lbl_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl_hint.setMinimumHeight(18)
        lbl_hint.setStyleSheet(
            f"QLabel {{ font-size:12px; font-weight:600; color:{color};"
            " background:transparent; border:none; }"
        )
        outer.addWidget(lbl_hint)

        return card

    def _build_recruitment_chart(self) -> None:
        chart_frame = self.win.findChild(QFrame, "chartFrame")
        if not chart_frame:
            return
        layout = chart_frame.layout()
        if not layout:
            return

        # Remove old canvas / legend row / placeholder — keep only header block
        # (chartHeaderLayout is a QHBoxLayout item, NOT a widget → survives loop)
        _KEEP = {"chartTitle", "chartSubTitle"}
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if w and w.objectName() not in _KEEP:
                layout.removeWidget(w)
                w.deleteLater()

        # ── Legend row (Qt widget, NOT matplotlib) ─────────────────
        # Placed between the title block and the canvas so it is
        # fully outside the chart's fill_between area.
        leg_row = QWidget()
        leg_row.setObjectName("_chartLegendRow")
        leg_row.setStyleSheet("background:transparent;")
        leg_h = QHBoxLayout(leg_row)
        leg_h.setSpacing(20)
        leg_h.setContentsMargins(4, 2, 4, 2)
        for label, color in [("Ứng tuyển", "#2563EB"), ("Tuyển dụng", "#10B981")]:
            dot = QLabel("━━")
            dot.setStyleSheet(
                f"QLabel{{color:{color};font-size:13px;font-weight:700;"
                "background:transparent;border:none;}}"
            )
            txt = QLabel(label)
            txt.setStyleSheet(
                f"QLabel{{color:#374151;font-size:12px;font-weight:600;"
                "background:transparent;border:none;}}"
            )
            row_h = QHBoxLayout()
            row_h.setSpacing(6)
            row_h.setContentsMargins(0, 0, 0, 0)
            row_h.addWidget(dot)
            row_h.addWidget(txt)
            leg_h.addLayout(row_h)
        leg_h.addStretch()
        layout.addWidget(leg_row)

        # ── Canvas ─────────────────────────────────────────────────
        labels = ["Th.1", "Th.2", "Th.3", "Th.4", "Th.5", "Th.6"]
        applications = [130, 160, 185, 170, 195, 240]
        hired = [8, 12, 10, 9, 11, 14]
        canvas = make_recruitment_trend_chart(labels, applications, hired)
        canvas.setMinimumHeight(200)
        layout.addWidget(canvas)

    def _build_donut(self) -> None:
        donut_frame = self.win.findChild(QFrame, "donutFrame")
        if not donut_frame:
            return
        layout = donut_frame.layout()
        if not layout:
            return
        # Remove old placeholder/canvas, keep header labels
        _KEEP = {"donutTitle", "donutSubTitle"}
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if w and w.objectName() not in _KEEP:
                layout.removeWidget(w)
                w.deleteLater()

        labels = ["Đã nộp", "Phỏng vấn", "Tuyển dụng", "Từ chối"]
        values = [45.0, 25.0, 18.0, 12.0]
        colors = ["#2563EB", "#06B6D4", "#10B981", "#8B5CF6"]
        canvas = make_donut_chart(labels, values, colors)
        canvas.setMinimumHeight(210)
        canvas.setMinimumWidth(200)
        layout.addWidget(canvas)

    def _build_recent_activities(self) -> None:
        if not self.activities_layout:
            return
        # Clear old items
        while self.activities_layout.count():
            item = self.activities_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        activities = [
            ("Nguyễn Văn A", "Ứng tuyển vị trí Senior Developer", "5 phút trước", "mới",          "#DBEAFE", "#1D4ED8"),
            ("Trần Thị B",   "Lên lịch phỏng vấn",                "1 giờ trước",  "đã lên lịch",  "#FEF9C3", "#92400E"),
            ("Lê Văn C",     "Chấp nhận offer",                    "2 giờ trước",  "đã tuyển",     "#DCFCE7", "#15803D"),
            ("Phạm Thị D",   "Từ chối đơn ứng tuyển",             "3 giờ trước",  "từ chối",      "#FEE2E2", "#B91C1C"),
            ("Hoàng Văn E",  "Hoàn thành bài test kỹ thuật",      "5 giờ trước",  "đang xử lý",   "#F3F4F6", "#6B7280"),
        ]
        for name, action, time_str, badge_text, badge_bg, badge_fg in activities:
            row = QFrame()
            row.setMinimumHeight(64)
            row.setStyleSheet(
                "QFrame { background:transparent; border:none;"
                " border-bottom:1px solid #F3F4F6; }"
            )
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 10, 0, 10)
            h.setSpacing(12)

            col = QVBoxLayout()
            col.setSpacing(2)
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet(
                "QLabel { font-size:14px; font-weight:600; color:#111827;"
                " background:transparent; border:none; }"
            )
            lbl_action = QLabel(action)
            lbl_action.setStyleSheet(
                "QLabel { font-size:12px; color:#6B7280;"
                " background:transparent; border:none; }"
            )
            col.addWidget(lbl_name)
            col.addWidget(lbl_action)
            h.addLayout(col)
            h.addStretch()

            lbl_time = QLabel(time_str)
            lbl_time.setStyleSheet(
                "QLabel { font-size:12px; color:#9CA3AF;"
                " background:transparent; border:none; }"
            )
            lbl_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            h.addWidget(lbl_time)

            badge = _pill(badge_text, badge_bg, badge_fg)
            h.addWidget(badge)

            self.activities_layout.addWidget(row)

    # ══════════════════════════════════════════════════════════════
    #  USER MANAGEMENT PAGE
    # ══════════════════════════════════════════════════════════════
    def _fill_user_table(self) -> None:
        """Fetch data from API, set up signals (once), then filter."""
        table = self.table_users
        if not table:
            return
        try:
            users = list(jobhub_api.admin_candidate_overview())
        except ApiError as e:
            _toast(self.win, f"Lỗi tải dữ liệu: {e}", success=False)
            return

        self._user_all_data = users
        self._user_page_idx  = 0
        self._user_page_size = 10

        if not getattr(self, "_user_signals_connected", False):
            self._user_signals_connected = True
            w = self._user_widget

            # ── Hide title block (already shown in topbar) ────────────────
            for obj in ("userPageTitle", "userPageSubTitle"):
                lbl = w.findChild(QLabel, obj)
                if lbl:
                    lbl.hide()
            # Hide "Thêm người dùng" button (not implemented)
            btn_add = w.findChild(QPushButton, "btnAddUser")
            if btn_add:
                btn_add.hide()
            # Hide the "Xuất dữ liệu" button and roleFilter — not needed here
            btn_exp = w.findChild(QPushButton, "btnExportUsers")
            if btn_exp:
                btn_exp.hide()
            role_cb_hide = w.findChild(QComboBox, "roleFilter")
            if role_cb_hide:
                role_cb_hide.hide()
            # Hide divider line above table
            divider = w.findChild(QFrame, "tableTopDivider")
            if divider:
                divider.hide()

            # ── Restyle search frame ──────────────────────────────────────
            search_frame = w.findChild(QFrame, "userSearchFrame")
            if search_frame:
                search_frame.setStyleSheet(
                    "QFrame { background:#FFFFFF; border:1px solid #E5E7EB;"
                    " border-radius:8px; }"
                    "QFrame:focus-within { border-color:#2563EB; }"
                )
                search_frame.setFixedHeight(38)
            search_icon = w.findChild(QLabel, "userSearchIcon")
            if search_icon:
                search_icon.setPixmap(
                    QIcon(str(resource_icon("ic_search.svg"))).pixmap(QSize(16, 16))
                )
                search_icon.setStyleSheet(
                    "QLabel { background:transparent; border:none; }"
                )
            if self.search_user:
                self.search_user.setStyleSheet(
                    "QLineEdit { background:transparent; border:none;"
                    " font-size:13px; color:#374151; }"
                    "QLineEdit::placeholder { color:#9CA3AF; }"
                )
                self.search_user.textChanged.connect(self._user_apply_filter)

            # ── Restyle statusFilter combo ────────────────────────────────
            _CB_SS = (
                "QComboBox { background:#FFFFFF; border:1px solid #E5E7EB;"
                " border-radius:8px; padding:0 12px; font-size:13px; color:#374151;"
                " height:38px; }"
                "QComboBox:hover { border-color:#2563EB; }"
                "QComboBox::drop-down { border:none; width:20px; }"
                "QComboBox QAbstractItemView { background:#FFFFFF;"
                " border:1px solid #E5E7EB; selection-background-color:#EEF2FF;"
                " color:#374151; outline:none; }"
            )
            status_cb = w.findChild(QComboBox, "statusFilter")
            if status_cb:
                self._user_status_cb = status_cb
                status_cb.setFixedHeight(38)
                status_cb.setFixedWidth(160)
                status_cb.setStyleSheet(_CB_SS)
                status_cb.currentIndexChanged.connect(self._user_apply_filter)

            # ── Pagination buttons ────────────────────────────────────────
            btn_prev = w.findChild(QPushButton, "btnPrevPage")
            btn_next = w.findChild(QPushButton, "btnNextPage")
            if btn_prev:
                self._user_btn_prev = btn_prev
                btn_prev.clicked.connect(self._user_prev_page)
            if btn_next:
                self._user_btn_next = btn_next
                btn_next.clicked.connect(self._user_next_page)

            # ── Style table ───────────────────────────────────────────────
            _TBL_SS = (
                "QTableWidget { background:#FFFFFF; border:none; font-size:13px;"
                " color:#374151; gridline-color:transparent; outline:none; }"
                "QTableWidget::item { padding:0 14px; border-bottom:1px solid #F3F4F6; }"
                "QTableWidget::item:hover { background:#F8FAFF; }"
                "QTableWidget::item:selected { background:#EEF2FF; color:#1D4ED8; }"
                "QHeaderView::section { background:#F9FAFB; color:#6B7280;"
                " font-size:11px; font-weight:700; letter-spacing:0.5px;"
                " padding:12px 14px; border:none; border-bottom:2px solid #E5E7EB; }"
            )
            table.setStyleSheet(_TBL_SS)
            table.setShowGrid(False)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.verticalHeader().setVisible(False)
            table.setAlternatingRowColors(False)

            # ── Column widths ─────────────────────────────────────────────
            hdr = table.horizontalHeader()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(
                ["Người dùng", "Vai trò", "Trạng thái", "Ngày tạo", "Thao tác"]
            )
            hdr.setSectionResizeMode(0, QHeaderView.Stretch)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(2, QHeaderView.Fixed)
            hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            hdr.setSectionResizeMode(4, QHeaderView.Fixed)
            table.setColumnWidth(2, 130)
            table.setColumnWidth(4, 118)

        self._user_apply_filter()

    def _user_apply_filter(self) -> None:
        data = list(getattr(self, "_user_all_data", []))
        q    = self.search_user
        text = q.text().strip().lower() if q else ""

        # Status filter (0=Tất cả, 1=Hoạt động, 2=Vô hiệu)
        status_cb = getattr(self, "_user_status_cb", None)
        sidx = status_cb.currentIndex() if status_cb else 0
        if sidx == 1:
            data = [u for u in data if bool(u.get("is_active", True))]
        elif sidx == 2:
            data = [u for u in data if not bool(u.get("is_active", True))]

        # Text search
        if text:
            data = [u for u in data if
                    text in str(u.get("full_name", "")).lower()
                    or text in str(u.get("email", "")).lower()]

        self._user_filtered = data
        self._user_page_idx = 0
        self._populate_user_table(data)
        self._user_update_pagination()

    def _user_update_pagination(self) -> None:
        total = len(getattr(self, "_user_filtered", []))
        ps    = getattr(self, "_user_page_size", 10)
        pages = max(1, (total + ps - 1) // ps)
        idx   = getattr(self, "_user_page_idx", 0)
        start = idx * ps + 1
        end   = min((idx + 1) * ps, total)

        w = self._user_widget
        info_lbl = w.findChild(QLabel, "paginationInfo")
        if info_lbl:
            if total == 0:
                info_lbl.setText("Không có kết quả")
            else:
                info_lbl.setText(f"Hiển thị {start}–{end} trong tổng số {total} người dùng")

        _PAGE_SS = (
            "QPushButton { background:#FFFFFF; color:#374151;"
            " border:1px solid #E5E7EB; border-radius:6px; font-size:12px;"
            " font-weight:500; min-width:60px; height:28px; padding:0 12px; }"
            "QPushButton:hover { border-color:#2563EB; color:#2563EB; }"
            "QPushButton:disabled { color:#D1D5DB; border-color:#F3F4F6; }"
        )
        btn_prev = getattr(self, "_user_btn_prev", None)
        btn_next = getattr(self, "_user_btn_next", None)
        if btn_prev:
            btn_prev.setStyleSheet(_PAGE_SS)
            btn_prev.setEnabled(idx > 0)
        if btn_next:
            btn_next.setStyleSheet(_PAGE_SS)
            btn_next.setEnabled(idx < pages - 1)

    def _user_prev_page(self) -> None:
        if getattr(self, "_user_page_idx", 0) > 0:
            self._user_page_idx -= 1
            ps = self._user_page_size
            page = self._user_filtered[self._user_page_idx*ps:(self._user_page_idx+1)*ps]
            self._populate_user_table(page)
            self._user_update_pagination()

    def _user_next_page(self) -> None:
        total = len(getattr(self, "_user_filtered", []))
        ps    = getattr(self, "_user_page_size", 10)
        pages = max(1, (total + ps - 1) // ps)
        if getattr(self, "_user_page_idx", 0) < pages - 1:
            self._user_page_idx += 1
            page = self._user_filtered[self._user_page_idx*ps:(self._user_page_idx+1)*ps]
            self._populate_user_table(page)
            self._user_update_pagination()

    def _populate_user_table(self, users: list) -> None:
        table = self.table_users
        if not table:
            return

        # Slice to current page
        ps    = getattr(self, "_user_page_size", 10)
        idx   = getattr(self, "_user_page_idx", 0)
        page  = users[idx*ps:(idx+1)*ps]

        table.setRowCount(len(page))

        _BTN_SS = (
            "QPushButton { background:transparent; border:none; border-radius:6px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        _AVATAR_COLORS = [
            ("#DBEAFE","#1D4ED8"), ("#D1FAE5","#065F46"),
            ("#F3E8FF","#6D28D9"), ("#FEF3C7","#92400E"),
            ("#FCE7F3","#9D174D"), ("#CFFAFE","#0E7490"),
        ]

        for row, u in enumerate(page):
            table.setRowHeight(row, 56)
            uid      = int(u.get("id", 0))
            name     = str(u.get("full_name", "—"))
            email    = str(u.get("email", "—"))
            is_active = bool(u.get("is_active", True))

            # ── col 0: avatar + name + email ─────────────────────
            cell_w = QWidget(); cell_w.setStyleSheet("background:transparent;")
            cell_h = QHBoxLayout(cell_w)
            cell_h.setContentsMargins(14, 0, 14, 0); cell_h.setSpacing(12)

            initials = "".join(w[0].upper() for w in name.split()[:2]) or "?"
            bg, fg = _AVATAR_COLORS[uid % len(_AVATAR_COLORS)]
            av = QLabel(initials)
            av.setFixedSize(36, 36); av.setAlignment(Qt.AlignCenter)
            av.setStyleSheet(
                f"QLabel {{ background:{bg}; color:{fg}; font-size:12px;"
                " font-weight:700; border-radius:18px; border:none; }}"
            )
            info_v = QVBoxLayout(); info_v.setSpacing(1)
            lbl_n = QLabel(name)
            lbl_n.setStyleSheet(
                "QLabel { font-size:13px; font-weight:600; color:#111827;"
                " background:transparent; border:none; }"
            )
            lbl_e = QLabel(email)
            lbl_e.setStyleSheet(
                "QLabel { font-size:12px; color:#6B7280;"
                " background:transparent; border:none; }"
            )
            info_v.addWidget(lbl_n); info_v.addWidget(lbl_e)
            cell_h.addWidget(av); cell_h.addLayout(info_v); cell_h.addStretch()
            table.setCellWidget(row, 0, cell_w)

            # ── col 1: role ───────────────────────────────────────
            role_item = QTableWidgetItem("Ứng viên")
            role_item.setTextAlignment(Qt.AlignCenter)
            role_item.setForeground(QColor("#374151"))
            table.setItem(row, 1, role_item)

            # ── col 2: status pill ────────────────────────────────
            if is_active:
                pill = _pill("Hoạt động", "#DCFCE7", "#15803D")
            else:
                pill = _pill("Vô hiệu",   "#F3F4F6", "#6B7280")
            pill.setMinimumWidth(96)
            pill_w = QWidget(); pill_w.setStyleSheet("background:transparent;")
            pill_h = QHBoxLayout(pill_w)
            pill_h.setContentsMargins(8,0,8,0)
            pill_h.setAlignment(Qt.AlignCenter)
            pill_h.addWidget(pill, alignment=Qt.AlignCenter)
            table.setCellWidget(row, 2, pill_w)

            # ── col 3: date ───────────────────────────────────────
            raw = str(u.get("created_at", "—"))
            date_item = QTableWidgetItem(self._fmt_date(raw) if raw != "—" else "—")
            date_item.setTextAlignment(Qt.AlignCenter)
            date_item.setForeground(QColor("#6B7280"))
            table.setItem(row, 3, date_item)

            # ── col 4: 3 icon buttons: view | unlock | lock ───────
            act_w = QWidget(); act_w.setStyleSheet("background:transparent;")
            act_h = QHBoxLayout(act_w)
            act_h.setContentsMargins(6,0,6,0); act_h.setSpacing(2)

            btn_view = QPushButton()
            btn_view.setFixedSize(30, 30); btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.setIcon(QIcon(str(resource_icon("ic_view.svg"))))
            btn_view.setIconSize(QSize(16, 16)); btn_view.setStyleSheet(_BTN_SS)
            btn_view.setToolTip("Xem hồ sơ")
            def _mk_view_user(hid: int, udata: dict):
                def _h(): self._show_user_detail_dialog(hid, udata)
                return _h
            btn_view.clicked.connect(_mk_view_user(uid, u))
            act_h.addWidget(btn_view)

            btn_unlock = QPushButton()
            btn_unlock.setFixedSize(30, 30); btn_unlock.setCursor(Qt.PointingHandCursor)
            btn_unlock.setIcon(QIcon(str(resource_icon("ic_unlock.svg"))))
            btn_unlock.setIconSize(QSize(16, 16)); btn_unlock.setStyleSheet(_BTN_SS)
            btn_unlock.setToolTip("Mở khóa tài khoản")

            def _mk_unlock(hid: int):
                def _h():
                    try:
                        jobhub_api.admin_unlock_user(hid)
                        _toast(self.win, "Đã mở khóa tài khoản", success=True)
                    except ApiError as e:
                        _toast(self.win, f"Thao tác thất bại: {e}", success=False)
                        return
                    QTimer.singleShot(0, self._fill_user_table)
                return _h
            btn_unlock.clicked.connect(_mk_unlock(uid))
            act_h.addWidget(btn_unlock)

            btn_lock = QPushButton()
            btn_lock.setFixedSize(30, 30); btn_lock.setCursor(Qt.PointingHandCursor)
            btn_lock.setIcon(QIcon(str(resource_icon("ic_lock.svg"))))
            btn_lock.setIconSize(QSize(16, 16)); btn_lock.setStyleSheet(_BTN_SS)
            btn_lock.setToolTip("Khóa tài khoản")

            def _mk_lock(hid: int):
                def _h():
                    try:
                        jobhub_api.admin_lock_user(hid)
                        _toast(self.win, "Đã khóa tài khoản", success=True)
                    except ApiError as e:
                        _toast(self.win, f"Thao tác thất bại: {e}", success=False)
                        return
                    QTimer.singleShot(0, self._fill_user_table)
                return _h
            btn_lock.clicked.connect(_mk_lock(uid))
            act_h.addWidget(btn_lock)

            act_h.addStretch()
            table.setCellWidget(row, 4, act_w)

    # ══════════════════════════════════════════════════════════════
    #  JOBS MANAGEMENT PAGE — card grid
    # ══════════════════════════════════════════════════════════════
    _STATUS_VI_JOBS = {
        "published":        ("Đang tuyển",  "#DCFCE7", "#15803D"),
        "draft":            ("Nháp",        "#FEF9C3", "#92400E"),
        "closed":           ("Đã đóng",     "#F3F4F6", "#6B7280"),
        "rejected":         ("Từ chối",     "#FEE2E2", "#B91C1C"),
        "pending_approval": ("Chờ duyệt",   "#DBEAFE", "#1D4ED8"),
    }

    def _fill_jobs_grid(self) -> None:
        if not self._jobs_grid:
            return
        try:
            jobs = list(jobhub_api.admin_all_jobs())
        except ApiError as e:
            _toast(self.win, f"Lỗi tải dữ liệu: {e}", success=False)
            return

        self._jobs_all_data = jobs

        if not getattr(self, "_jobs_signals_connected", False):
            self._jobs_signals_connected = True
            w = self._jobs_widget

            # ── Hide title block ──────────────────────────────────────
            for obj in ("jobPageTitle", "jobPageSubTitle"):
                lbl = w.findChild(QLabel, obj)
                if lbl: lbl.hide()
            btn_create = w.findChild(QPushButton, "btnCreateJob")
            if btn_create: btn_create.hide()

            # ── Hide deptFilter (static, doesn't match API data) ──────
            dept_cb = w.findChild(QComboBox, "deptFilter")
            if dept_cb: dept_cb.hide()

            # ── Fix search icon & frame ───────────────────────────────
            search_frame = w.findChild(QFrame, "jobSearchFrame")
            if search_frame:
                search_frame.setFixedHeight(40)
                search_frame.setStyleSheet(
                    "QFrame#jobSearchFrame {"
                    " background:#FFFFFF; border:1.5px solid #E5E7EB;"
                    " border-radius:10px; }"
                    "QFrame#jobSearchFrame:focus-within {"
                    " border-color:#2563EB; }"
                )
            icon_lbl = w.findChild(QLabel, "jobSearchIcon")
            if icon_lbl:
                icon_lbl.setPixmap(
                    QIcon(str(resource_icon("ic_search.svg"))).pixmap(QSize(16, 16))
                )
                icon_lbl.setFixedSize(16, 16)
                icon_lbl.setStyleSheet(
                    "QLabel { background:transparent; border:none; }"
                )
            if self.search_jobs:
                self.search_jobs.setStyleSheet(
                    "QLineEdit { background:transparent; border:none;"
                    " font-size:13px; color:#374151; }"
                    "QLineEdit::placeholder { color:#9CA3AF; }"
                )
                self.search_jobs.textChanged.connect(self._jobs_apply_filter)

            # ── statusFilter: connect + restyle ───────────────────────
            _CB_SS = (
                "QComboBox { background:#FFFFFF; border:1.5px solid #E5E7EB;"
                " border-radius:8px; padding:0 12px; font-size:13px; color:#374151;"
                " height:40px; }"
                "QComboBox:hover { border-color:#2563EB; }"
                "QComboBox::drop-down { border:none; width:20px; }"
                "QComboBox QAbstractItemView { background:#FFFFFF;"
                " border:1px solid #E5E7EB; selection-background-color:#EEF2FF;"
                " color:#374151; outline:none; }"
            )
            status_cb = w.findChild(QComboBox, "statusFilter")
            if status_cb:
                self._jobs_status_cb = status_cb
                status_cb.setFixedHeight(40)
                status_cb.setStyleSheet(_CB_SS)
                status_cb.currentIndexChanged.connect(self._jobs_apply_filter)

            # ── Pagination bar — add below scroll area ────────────────
            self._jobs_page_idx  = 0
            self._jobs_page_size = 6
            self._jobs_filtered  = []

            pagin_bar = QFrame()
            pagin_bar.setObjectName("_jobsPaginBar")
            pagin_bar.setFixedHeight(52)
            pagin_bar.setStyleSheet(
                "QFrame { background:#FFFFFF; border-radius:12px;"
                " border:1px solid #E5E7EB; }"
            )
            pagin_lo = QHBoxLayout(pagin_bar)
            pagin_lo.setContentsMargins(16, 0, 16, 0)
            pagin_lo.setSpacing(6)
            self._jobs_pagin_bar = pagin_bar

            # Insert pagination bar into mainAreaLayout (after scroll area)
            main_lo = w.findChild(QVBoxLayout, "mainAreaLayout")
            if main_lo:
                main_lo.addWidget(pagin_bar)
            else:
                # fallback: append to widget's own layout
                if w.layout():
                    w.layout().addWidget(pagin_bar)

        self._jobs_apply_filter()

    # Status index → API value mapping
    _JOBS_STATUS_MAP = {
        1: "published",
        2: "draft",
        3: "closed",
        4: "rejected",
        5: "pending_approval",
    }

    def _jobs_apply_filter(self) -> None:
        q    = self.search_jobs
        text = q.text().strip().lower() if q else ""
        data = list(getattr(self, "_jobs_all_data", []))

        # Status filter
        status_cb = getattr(self, "_jobs_status_cb", None)
        sidx = status_cb.currentIndex() if status_cb else 0
        if sidx > 0:
            target = self._JOBS_STATUS_MAP.get(sidx, "")
            if target:
                data = [j for j in data if
                        str(j.get("status","")).lower() == target]

        # Text search
        if text:
            data = [j for j in data if
                    text in str(j.get("title","")).lower()
                    or text in str(j.get("company_name","")).lower()
                    or text in str(j.get("location","")).lower()]

        # Sort: pending_approval đầu, rejected cuối
        _ORDER = {"pending_approval":0,"published":1,"draft":2,"closed":3,"rejected":4}
        data.sort(key=lambda j: _ORDER.get(j.get("status",""), 5))

        self._jobs_filtered  = data
        self._jobs_page_idx  = 0
        self._populate_jobs_grid()

    def _populate_jobs_grid(self) -> None:
        grid = self._jobs_grid
        if not grid:
            return

        jobs     = getattr(self, "_jobs_filtered", [])
        page_sz  = getattr(self, "_jobs_page_size", 6)
        page_idx = getattr(self, "_jobs_page_idx", 0)
        total    = len(jobs)
        total_pages = max(1, (total + page_sz - 1) // page_sz)
        page_idx = max(0, min(page_idx, total_pages - 1))
        self._jobs_page_idx = page_idx

        start = page_idx * page_sz
        page_jobs = jobs[start:start + page_sz]

        # Clear grid
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, j in enumerate(page_jobs):
            row, col = divmod(i, 2)
            card = self._make_job_card(j, self._STATUS_VI_JOBS)
            grid.addWidget(card, row, col)

        # Trailing spacer
        grid.setRowStretch((len(page_jobs) + 1) // 2, 1)

        # Update pagination row
        self._jobs_update_pagination(total, total_pages)

    def _make_job_card(self, j: dict, status_map: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#FFFFFF; border-radius:12px;"
            " border:1px solid #E5E7EB; }"
            "QFrame:hover { border-color:#BFDBFE; }"
        )
        _shadow(card, blur=12, dy=2, alpha=14)
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)

        status_raw = j.get("status", "draft")
        label_txt, s_bg, s_fg = status_map.get(
            status_raw, (status_raw, "#F3F4F6", "#6B7280")
        )

        # Row 1: title + status + menu
        r1 = QHBoxLayout(); r1.setSpacing(8)
        title_lbl = QLabel(j.get("title", "Không tiêu đề"))
        title_lbl.setStyleSheet(
            "QLabel { font-size:15px; font-weight:700; color:#111827;"
            " background:transparent; border:none; }"
        )
        r1.addWidget(title_lbl, stretch=1)
        r1.addWidget(_pill(label_txt, s_bg, s_fg))
        v.addLayout(r1)

        # Dept
        dept = QLabel(j.get("department", j.get("company_name", "")))
        dept.setStyleSheet(
            "QLabel { font-size:12px; color:#6B7280;"
            " background:transparent; border:none; }"
        )
        v.addWidget(dept)

        # Location + type
        r2 = QHBoxLayout(); r2.setSpacing(8)
        loc = QLabel(f"  {j.get('location', 'Chưa cập nhật')}")
        loc.setStyleSheet(
            "QLabel { font-size:13px; color:#374151;"
            " background:transparent; border:none; }"
        )
        r2.addWidget(loc)
        job_type = j.get("job_type", "Full-time")
        jt_bg, jt_fg = _JOB_TYPE_COLORS.get(job_type, ("#DBEAFE", "#1D4ED8"))
        r2.addWidget(_pill(job_type, jt_bg, jt_fg))
        r2.addStretch()
        v.addLayout(r2)

        # Salary
        sal = QLabel(f"  {j.get('salary_text', 'Thỏa thuận')}")
        sal.setStyleSheet(
            "QLabel { font-size:13px; color:#374151;"
            " background:transparent; border:none; }"
        )
        v.addWidget(sal)

        # Posted date
        posted = QLabel(f"  Đăng ngày {self._fmt_date(str(j.get('created_at', '')))} ")
        posted.setStyleSheet(
            "QLabel { font-size:13px; color:#374151;"
            " background:transparent; border:none; }"
        )
        v.addWidget(posted)

        # Applicants
        apps = QLabel(f"  {j.get('applicants_count', 0)} ứng viên")
        apps.setStyleSheet(
            "QLabel { font-size:13px; color:#2563EB; font-weight:500;"
            " background:transparent; border:none; }"
        )
        v.addWidget(apps)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("QFrame { background:#F3F4F6; border:none; }")
        v.addWidget(div)

        # Bottom: manager + buttons
        r3 = QHBoxLayout(); r3.setSpacing(8)
        mgr = QLabel(f"Quản lý: {j.get('manager_name', j.get('company_name', 'N/A'))}")
        mgr.setStyleSheet(
            "QLabel { font-size:12px; color:#6B7280;"
            " background:transparent; border:none; }"
        )
        r3.addWidget(mgr, stretch=1)

        btn_detail = QPushButton("Chi tiết")
        btn_detail.setCursor(Qt.PointingHandCursor)
        btn_detail.setFixedHeight(34)
        btn_detail.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#374151;"
            " border:1px solid #E5E7EB; border-radius:7px;"
            " font-size:13px; font-weight:500; padding:0 14px; }"
            "QPushButton:hover { border-color:#2563EB; color:#2563EB; }"
        )
        jid_d = j["id"]
        btn_detail.clicked.connect(lambda _, _jid=jid_d: self._show_job_detail_dialog(_jid))
        r3.addWidget(btn_detail)

        jid = j["id"]

        # "Không duyệt" button — show for all statuses except already-rejected
        if status_raw != "rejected":
            btn_no = QPushButton("  Không duyệt")
            btn_no.setCursor(Qt.PointingHandCursor)
            btn_no.setIcon(QIcon(str(resource_icon("ic_x.svg"))))
            btn_no.setIconSize(QSize(13, 13))
            btn_no.setFixedHeight(34)
            btn_no.setStyleSheet(
                "QPushButton { background:#FEF2F2; color:#DC2626;"
                " border:1.5px solid #FECACA; border-radius:8px;"
                " font-size:13px; font-weight:600; padding:0 12px; }"
                "QPushButton:hover { background:#FEE2E2; border-color:#DC2626; }"
            )
            btn_no.clicked.connect(lambda _, _jid=jid: self._reject_job(_jid))
            r3.addWidget(btn_no)
        else:
            # Already rejected — show a muted pill label
            lbl_rej = QLabel("Đã từ chối")
            lbl_rej.setFixedHeight(34)
            lbl_rej.setAlignment(Qt.AlignCenter)
            lbl_rej.setStyleSheet(
                "QLabel { font-size:12px; color:#B91C1C; font-weight:600;"
                " background:#FEF2F2; border:1px solid #FECACA;"
                " border-radius:8px; padding:0 12px;"
                " background:transparent; border:none; }"
            )
            r3.addWidget(lbl_rej)

        # "Phê duyệt" — only for pending
        if status_raw == "pending_approval":
            btn_approve = QPushButton("  Phê duyệt")
            btn_approve.setCursor(Qt.PointingHandCursor)
            btn_approve.setIcon(QIcon(str(resource_icon("ic_check.svg"))))
            btn_approve.setIconSize(QSize(13, 13))
            btn_approve.setFixedHeight(34)
            btn_approve.setStyleSheet(
                "QPushButton { background:#2563EB; color:#FFFFFF; border:none;"
                " border-radius:8px; font-size:13px; font-weight:600; padding:0 14px; }"
                "QPushButton:hover { background:#1D4ED8; }"
            )
            btn_approve.clicked.connect(lambda _, _jid=jid: self._approve_job(_jid))
            r3.addWidget(btn_approve)

        v.addLayout(r3)
        return card

    def _approve_job(self, job_id: int) -> None:
        try:
            jobhub_api.admin_approve_job(job_id)
            _toast(self.win, "Đã phê duyệt tin tuyển dụng", success=True)
        except ApiError as e:
            _toast(self.win, f"Lỗi: {e}", success=False)
            return
        QTimer.singleShot(0, self._fill_jobs_grid)

    def _reject_job(self, job_id: int) -> None:
        try:
            jobhub_api.admin_reject_job(job_id)
            _toast(self.win, "Đã từ chối tin tuyển dụng", success=False)
        except ApiError as e:
            _toast(self.win, f"Lỗi: {e}", success=False)
            return
        QTimer.singleShot(0, self._fill_jobs_grid)

    def _jobs_update_pagination(self, total: int, total_pages: int) -> None:
        """Rebuild the page-number buttons in the pagination bar."""
        bar = getattr(self, "_jobs_pagin_bar", None)
        if not bar:
            return
        lo = bar.layout()
        # Clear all items
        while lo.count():
            item = lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        page_idx = self._jobs_page_idx
        page_sz  = self._jobs_page_size

        # Info label
        start = page_idx * page_sz + 1
        end   = min((page_idx + 1) * page_sz, total)
        info  = QLabel(f"Hiển thị {start}–{end} / {total} tin")
        info.setStyleSheet(
            "QLabel { font-size:13px; color:#6B7280;"
            " background:transparent; border:none; }"
        )
        lo.addWidget(info)
        lo.addStretch(1)

        if total_pages <= 1:
            bar.setVisible(False)
            return
        bar.setVisible(True)

        def _page_btn(label, enabled, active=False):
            b = QPushButton(label)
            b.setFixedSize(36, 36)
            b.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
            b.setEnabled(enabled)
            if active:
                b.setStyleSheet(
                    "QPushButton { background:#2563EB; color:#FFFFFF; border:none;"
                    " border-radius:8px; font-size:13px; font-weight:700; }"
                )
            elif enabled:
                b.setStyleSheet(
                    "QPushButton { background:#FFFFFF; color:#374151;"
                    " border:1px solid #E5E7EB; border-radius:8px; font-size:13px; }"
                    "QPushButton:hover { border-color:#2563EB; color:#2563EB; }"
                )
            else:
                b.setStyleSheet(
                    "QPushButton { background:#F9FAFB; color:#D1D5DB;"
                    " border:1px solid #E5E7EB; border-radius:8px; font-size:13px; }"
                )
            return b

        # Prev
        btn_prev = _page_btn("←", page_idx > 0)
        btn_prev.clicked.connect(self._jobs_prev_page)
        lo.addWidget(btn_prev)

        # Page numbers (show at most 5 around current)
        half = 2
        p_start = max(0, page_idx - half)
        p_end   = min(total_pages, p_start + 5)
        p_start = max(0, p_end - 5)

        if p_start > 0:
            b0 = _page_btn("1", True)
            b0.clicked.connect(lambda _, p=0: self._jobs_goto_page(p))
            lo.addWidget(b0)
            if p_start > 1:
                dots = QLabel("…")
                dots.setStyleSheet("QLabel{color:#9CA3AF;background:transparent;border:none;}")
                lo.addWidget(dots)

        for p in range(p_start, p_end):
            bp = _page_btn(str(p + 1), True, active=(p == page_idx))
            bp.clicked.connect(lambda _, _p=p: self._jobs_goto_page(_p))
            lo.addWidget(bp)

        if p_end < total_pages:
            if p_end < total_pages - 1:
                dots2 = QLabel("…")
                dots2.setStyleSheet("QLabel{color:#9CA3AF;background:transparent;border:none;}")
                lo.addWidget(dots2)
            blast = _page_btn(str(total_pages), True)
            blast.clicked.connect(lambda _, p=total_pages-1: self._jobs_goto_page(p))
            lo.addWidget(blast)

        # Next
        btn_next = _page_btn("→", page_idx < total_pages - 1)
        btn_next.clicked.connect(self._jobs_next_page)
        lo.addWidget(btn_next)

    def _jobs_goto_page(self, page: int) -> None:
        self._jobs_page_idx = page
        self._populate_jobs_grid()

    def _jobs_prev_page(self) -> None:
        if self._jobs_page_idx > 0:
            self._jobs_page_idx -= 1
            self._populate_jobs_grid()

    def _jobs_next_page(self) -> None:
        jobs = getattr(self, "_jobs_filtered", [])
        total_pages = max(1, (len(jobs) + self._jobs_page_size - 1) // self._jobs_page_size)
        if self._jobs_page_idx < total_pages - 1:
            self._jobs_page_idx += 1
            self._populate_jobs_grid()

    # ------------------------------------------------------------------
    def _show_job_detail_dialog(self, job_id: int) -> None:
        """Full job-detail dialog — all icons are SVG, no emoji."""
        BLUE   = "#2563EB"; BLUE_D = "#1D4ED8"; BLUE_L = "#EFF6FF"
        TXT_H  = "#111827"; TXT_M  = "#6B7280"; TXT_S  = "#374151"
        CARD   = "#FFFFFF"; PAGE   = "#F8FAFC"; BORDER = "#E5E7EB"
        LOGO_PALETTE = [
            ("#DBEAFE","#1D4ED8"),("#D1FAE5","#065F46"),("#FEF3C7","#92400E"),
            ("#FCE7F3","#9D174D"),("#EDE9FE","#5B21B6"),("#ECFEFF","#164E63"),
        ]
        STATUS_MAP = {
            "published":        ("Đã duyệt",  "#D1FAE5","#059669"),
            "pending_approval": ("Chờ duyệt", "#FEF3C7","#D97706"),
            "draft":            ("Bản nháp",  "#F1F5F9","#64748B"),
            "rejected":         ("Từ chối",   "#FEE2E2","#DC2626"),
            "closed":           ("Đã đóng",   "#F3F4F6","#6B7280"),
        }

        # ── fetch ──────────────────────────────────────────────────────
        try:
            j = jobhub_api.admin_job_detail(job_id)
        except Exception as e:
            _toast(self.win, f"Không tải được chi tiết: {e}", success=False)
            return

        st_raw = j.get("status", "draft")
        st_label, st_bg, st_fg = STATUS_MAP.get(st_raw, (st_raw, "#F1F5F9","#64748B"))
        title      = j.get("title")       or "—"
        company    = j.get("company_name")or "—"
        dept       = j.get("department")  or ""
        level      = j.get("level")       or "—"
        job_type   = j.get("job_type")    or "—"
        location   = j.get("location")    or "—"
        count      = str(j.get("count") or "—")
        deadline   = j.get("deadline")    or "—"
        desc_raw   = (j.get("description") or "").strip()
        applicants = j.get("applicants_count", 0)
        created_at = str(j.get("created_at",""))[:10]
        admin_note = j.get("admin_note") or ""
        mn, mx, st_txt = j.get("min_salary"), j.get("max_salary"), j.get("salary_text")
        if st_txt:  sal = st_txt
        elif mn and mx: sal = f"${mn:,} – ${mx:,}"
        elif mn:        sal = f"Từ ${mn:,}"
        elif mx:        sal = f"Đến ${mx:,}"
        else:           sal = "Thỏa thuận"

        logo_bg, logo_fg = LOGO_PALETTE[job_id % len(LOGO_PALETTE)]

        # ── svg helpers ────────────────────────────────────────────────
        def _svg_ic(name, size=16, color=None) -> QLabel:
            lbl = QLabel()
            lbl.setFixedSize(size, size)
            pm = QIcon(str(resource_icon(name))).pixmap(QSize(size, size))
            lbl.setPixmap(pm)
            lbl.setStyleSheet("background:transparent; border:none;")
            return lbl

        def _svg_pm_col(name, size, hex_color):
            """Return pixmap — color tinting via stylesheet not supported in Qt pixmap,
            so we just return the raw SVG pixmap at requested size."""
            return QIcon(str(resource_icon(name))).pixmap(QSize(size, size))

        # ── layout helpers ─────────────────────────────────────────────
        def _card_frame(parent_lo) -> tuple:
            f = QFrame()
            f.setStyleSheet(
                f"QFrame{{background:{CARD}; border-radius:16px; border:1px solid {BORDER};}}"
            )
            _shadow(f, blur=12, dy=3, alpha=10)
            lo = QVBoxLayout(f)
            lo.setContentsMargins(24, 20, 24, 22)
            lo.setSpacing(12)
            parent_lo.addWidget(f)
            return f, lo

        def _section_hdr(lo, icon_svg, txt):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 0, 0, 0)
            ic = _svg_ic(icon_svg, 18)
            lbl = QLabel(txt)
            lbl.setStyleSheet(
                f"color:{TXT_H}; font-size:16px; font-weight:800;"
                " border:none; background:transparent;"
            )
            row.addWidget(ic)
            row.addWidget(lbl)
            row.addStretch()
            lo.addLayout(row)
            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER}; border:none;")
            lo.addWidget(div)

        def _body_lbl(txt):
            lbl = QLabel(txt)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            lbl.setStyleSheet(
                f"color:{TXT_S}; font-size:13px; line-height:1.7;"
                " border:none; background:transparent;"
            )
            return lbl

        def _bullet(txt):
            row = QHBoxLayout()
            row.setSpacing(10); row.setContentsMargins(4, 2, 0, 2)
            dot = QLabel(); dot.setFixedSize(7,7)
            dot.setStyleSheet(f"background:{BLUE}; border-radius:4px; border:none;")
            lbl = QLabel(txt); lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{TXT_S}; font-size:13px; border:none; background:transparent;")
            row.addWidget(dot, 0, Qt.AlignTop | Qt.AlignHCenter)
            row.addWidget(lbl, 1)
            return row

        def _info_chip(chip_title, chip_val, accent):
            chip = QFrame()
            chip.setStyleSheet(
                f"QFrame{{background:#F8FAFC; border:1px solid {BORDER}; border-radius:10px;}}"
            )
            chip.setFixedHeight(54); chip.setMinimumWidth(140)
            clo = QVBoxLayout(chip)
            clo.setContentsMargins(12,6,12,6); clo.setSpacing(2)
            ct = QLabel(chip_title)
            ct.setStyleSheet(
                f"color:{TXT_M}; font-size:10px; font-weight:600;"
                " letter-spacing:0.4px; border:none; background:transparent;"
            )
            cv = QLabel(chip_val or "—")
            cv.setStyleSheet(
                f"color:{accent}; font-size:12px; font-weight:700;"
                " border:none; background:transparent;"
            )
            clo.addWidget(ct); clo.addWidget(cv)
            return chip

        # ── Dialog ─────────────────────────────────────────────────────
        dlg = QDialog(self.win)
        dlg.setWindowTitle(f"Chi tiết tin tuyển dụng #{job_id}")
        dlg.setMinimumSize(1040, 680); dlg.resize(1080, 760)
        dlg.setStyleSheet(f"QDialog{{background:{PAGE};}}")
        root_lo = QVBoxLayout(dlg)
        root_lo.setContentsMargins(0,0,0,0); root_lo.setSpacing(0)

        # ── TOP BAR ────────────────────────────────────────────────────
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet(
            f"QFrame{{background:{CARD}; border:none; border-bottom:1px solid {BORDER};}}"
        )
        tb_lo = QHBoxLayout(topbar)
        tb_lo.setContentsMargins(24,0,24,0); tb_lo.setSpacing(14)

        btn_back = QPushButton()
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setIcon(QIcon(str(resource_icon("ic_chevron_left.svg"))))
        btn_back.setIconSize(QSize(16,16))
        btn_back.setText("  Quay lại danh sách")
        btn_back.setStyleSheet(
            f"QPushButton{{background:transparent; color:{TXT_M}; border:none;"
            " font-size:13px; font-weight:600; padding:0;}}"
            f"QPushButton:hover{{color:{BLUE};}}"
        )
        btn_back.clicked.connect(dlg.reject)
        tb_lo.addWidget(btn_back)

        tb_div = QFrame(); tb_div.setFixedSize(1,28)
        tb_div.setStyleSheet(f"background:{BORDER}; border:none;")
        tb_lo.addWidget(tb_div)

        ic_jobs_lbl = _svg_ic("ic_jobs.svg", 16)
        tb_lo.addWidget(ic_jobs_lbl)
        lbl_page = QLabel("Chi tiết công việc")
        lbl_page.setStyleSheet(
            f"color:{TXT_H}; font-size:15px; font-weight:700; border:none; background:transparent;"
        )
        tb_lo.addWidget(lbl_page)

        pill = QLabel(st_label)
        pill.setFixedHeight(24); pill.setAlignment(Qt.AlignCenter)
        pill.setStyleSheet(
            f"background:{st_bg}; color:{st_fg}; border-radius:12px;"
            f" padding:0 12px; font-size:11px; font-weight:700; border:none;"
        )
        tb_lo.addWidget(pill)
        tb_lo.addStretch()

        btn_hdr_approve = btn_hdr_reject = None
        if st_raw == "pending_approval":
            btn_hdr_reject = QPushButton("  Từ chối")
            btn_hdr_reject.setCursor(Qt.PointingHandCursor)
            btn_hdr_reject.setIcon(QIcon(str(resource_icon("ic_x.svg"))))
            btn_hdr_reject.setIconSize(QSize(14,14))
            btn_hdr_reject.setFixedHeight(36)
            btn_hdr_reject.setStyleSheet(
                f"QPushButton{{background:{CARD}; color:#DC2626;"
                f" border:1.5px solid #DC2626; border-radius:9px;"
                f" font-size:13px; font-weight:600; padding:0 16px;}}"
                "QPushButton:hover{background:#FEF2F2;}"
            )
            tb_lo.addWidget(btn_hdr_reject)

            btn_hdr_approve = QPushButton("  Phê duyệt")
            btn_hdr_approve.setCursor(Qt.PointingHandCursor)
            btn_hdr_approve.setIcon(QIcon(str(resource_icon("ic_check.svg"))))
            btn_hdr_approve.setIconSize(QSize(14,14))
            btn_hdr_approve.setFixedHeight(36)
            btn_hdr_approve.setStyleSheet(
                f"QPushButton{{background:{BLUE}; color:#FFFFFF; border:none;"
                f" border-radius:9px; font-size:13px; font-weight:600; padding:0 16px;}}"
                f"QPushButton:hover{{background:{BLUE_D};}}"
            )
            tb_lo.addWidget(btn_hdr_approve)

        root_lo.addWidget(topbar)

        # ── SCROLL ─────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea{{background:{PAGE}; border:none;}}")
        body_w = QWidget(); body_w.setStyleSheet(f"background:{PAGE};")
        body_lo = QVBoxLayout(body_w)
        body_lo.setContentsMargins(28,22,28,28); body_lo.setSpacing(16)
        scroll.setWidget(body_w)
        root_lo.addWidget(scroll)

        # ── HERO CARD ──────────────────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet(
            f"QFrame{{background:{CARD}; border-radius:18px; border:1px solid {BORDER};}}"
        )
        _shadow(hero, blur=14, dy=4, alpha=12)
        hero_lo = QHBoxLayout(hero)
        hero_lo.setContentsMargins(28,24,28,24); hero_lo.setSpacing(22)

        logo_lbl = QLabel((company[0].upper()) if company != "—" else "J")
        logo_lbl.setFixedSize(72,72); logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet(
            f"background:{logo_bg}; color:{logo_fg}; border-radius:18px;"
            " font-size:28px; font-weight:800; border:none;"
        )
        hero_lo.addWidget(logo_lbl, 0, Qt.AlignTop)

        title_col = QVBoxLayout(); title_col.setSpacing(6)
        h1 = QLabel(title); h1.setWordWrap(True)
        h1.setStyleSheet(
            f"color:{TXT_H}; font-size:22px; font-weight:800; border:none; background:transparent;"
        )
        title_col.addWidget(h1)

        comp_row = QHBoxLayout(); comp_row.setSpacing(8)
        comp_lbl = QLabel(company)
        comp_lbl.setStyleSheet(
            f"color:{BLUE}; font-size:14px; font-weight:700; border:none; background:transparent;"
        )
        comp_row.addWidget(comp_lbl)
        if dept:
            dot = QLabel("·")
            dot.setStyleSheet(f"color:{TXT_M}; border:none; background:transparent;")
            dept_lbl = QLabel(dept)
            dept_lbl.setStyleSheet(
                f"color:{TXT_M}; font-size:13px; border:none; background:transparent;"
            )
            comp_row.addWidget(dot); comp_row.addWidget(dept_lbl)
        comp_row.addStretch()
        title_col.addLayout(comp_row)

        meta_row = QHBoxLayout(); meta_row.setSpacing(20)
        meta_row.setContentsMargins(0,4,0,0)
        for ic_name, meta_txt in [
            ("ic_jobs.svg",  f"Đăng ngày {created_at}" if created_at else "Mới đăng"),
            ("ic_users.svg", f"{applicants} ứng viên đã nộp"),
            ("ic_check.svg", "Nhà tuyển dụng đã xác minh"),
        ]:
            mr = QHBoxLayout(); mr.setSpacing(6)
            mr.addWidget(_svg_ic(ic_name, 14))
            mt = QLabel(meta_txt)
            mt.setStyleSheet(
                f"color:{TXT_M}; font-size:12px; border:none; background:transparent;"
            )
            mr.addWidget(mt)
            meta_row.addLayout(mr)
        meta_row.addStretch()
        title_col.addLayout(meta_row)
        hero_lo.addLayout(title_col, 1)

        chips_grid = QGridLayout(); chips_grid.setSpacing(8)
        chip_defs = [
            ("Mức lương",   sal,               BLUE,     0,0),
            ("Loại hình",   job_type,          TXT_S,    0,1),
            ("Địa điểm",    location,          TXT_S,    1,0),
            ("Cấp bậc",     level,             "#6366F1", 1,1),
            ("Số lượng",    f"{count} vị trí", "#059669", 2,0),
            ("Hạn nộp",     deadline,          "#D97706", 2,1),
        ]
        for ct,cv,ca,cr,cc in chip_defs:
            chips_grid.addWidget(_info_chip(ct,cv,ca), cr, cc)
        hero_lo.addLayout(chips_grid)
        body_lo.addWidget(hero)

        # ── TWO-COLUMN BODY ────────────────────────────────────────────
        cols = QHBoxLayout(); cols.setSpacing(18)

        left_lo  = QVBoxLayout(); left_lo.setSpacing(14)
        right_lo = QVBoxLayout(); right_lo.setSpacing(14)
        right_lo.setAlignment(Qt.AlignTop)

        # ── LEFT: Description ──────────────────────────────────────────
        _, desc_clo = _card_frame(left_lo)
        _section_hdr(desc_clo, "ic_doc.svg", "Mô tả công việc")
        if desc_raw:
            for para in desc_raw.split("\n"):
                para = para.strip()
                if para:
                    if para.startswith("-") or para.startswith("•"):
                        desc_clo.addLayout(_bullet(para.lstrip("-•").strip()))
                    else:
                        desc_clo.addWidget(_body_lbl(para))
        else:
            desc_clo.addWidget(_body_lbl(
                f"{company} đang tuyển dụng vị trí {title}. "
                "Vui lòng liên hệ nhà tuyển dụng để biết thêm thông tin chi tiết."
            ))

        kw_row = QHBoxLayout(); kw_row.setSpacing(8)
        kw_row.setContentsMargins(0,6,0,0)
        kw_row.addWidget(_svg_ic("ic_jobs.svg", 14))
        kw = QLabel("Nhiệm vụ chính:")
        kw.setStyleSheet(
            f"color:{TXT_H}; font-size:13px; font-weight:700;"
            " border:none; background:transparent;"
        )
        kw_row.addWidget(kw); kw_row.addStretch()
        desc_clo.addLayout(kw_row)
        for b in [
            f"Đảm nhận công việc chuyên môn với cấp bậc {level}.",
            f"Làm việc tại {location} theo hình thức {job_type}.",
            "Phối hợp chặt chẽ với các team liên quan.",
            "Chủ động cải tiến và đảm bảo chất lượng công việc.",
        ]:
            desc_clo.addLayout(_bullet(b))

        # ── LEFT: Requirements ─────────────────────────────────────────
        _, req_clo = _card_frame(left_lo)
        _section_hdr(req_clo, "ic_folder.svg", "Yêu cầu")
        req_row = QHBoxLayout(); req_row.setSpacing(20)
        for col_title, items in [
            ("Yêu cầu chuyên môn", [
                f"Phù hợp với cấp bậc: {level}.",
                "Có kinh nghiệm thực tế trong lĩnh vực liên quan.",
                "Thành thạo công cụ và quy trình hiện đại.",
            ]),
            ("Kỹ năng mềm", [
                "Giao tiếp và trình bày hiệu quả.",
                "Tư duy phân tích và giải quyết vấn đề.",
                "Làm việc nhóm và hỗ trợ đồng nghiệp.",
            ]),
        ]:
            sub = QVBoxLayout(); sub.setSpacing(8)
            sub_hdr = QHBoxLayout(); sub_hdr.setSpacing(8)
            sub_hdr.addWidget(_svg_ic("ic_jobs.svg", 14))
            sub_ttl = QLabel(col_title)
            sub_ttl.setStyleSheet(
                f"color:{TXT_H}; font-size:13px; font-weight:700;"
                " border:none; background:transparent;"
            )
            sub_hdr.addWidget(sub_ttl); sub_hdr.addStretch()
            sub.addLayout(sub_hdr)
            for item in items:
                row = QHBoxLayout(); row.setSpacing(8)
                chk_ic = _svg_ic("ic_check.svg", 14)
                t = QLabel(item); t.setWordWrap(True)
                t.setStyleSheet(
                    f"color:{TXT_S}; font-size:12px; border:none; background:transparent;"
                )
                row.addWidget(chk_ic, 0, Qt.AlignTop)
                row.addWidget(t, 1)
                sub.addLayout(row)
            req_row.addLayout(sub, 1)
        req_clo.addLayout(req_row)

        # ── LEFT: Perks ────────────────────────────────────────────────
        _, perks_clo = _card_frame(left_lo)
        _section_hdr(perks_clo, "ic_hr_stat.svg", "Quyền lợi & Phúc lợi")
        perks_grid = QGridLayout(); perks_grid.setSpacing(10)
        perks_data = [
            ("ic_trend.svg",   "Lương cạnh tranh",    sal,              "#DBEAFE","#1D4ED8"),
            ("ic_check.svg",   "Bảo hiểm toàn diện",  "Y tế & Nha khoa","#DCFCE7","#16A34A"),
            ("ic_jobs.svg",    "Trang thiết bị",       "Đầy đủ thiết bị","#F3E8FF","#9333EA"),
            ("ic_clock.svg",   "Giờ làm linh hoạt",   job_type,         "#FEF3C7","#D97706"),
        ]
        for i, (ic_svg, name, desc_txt, pbg, pfg) in enumerate(perks_data):
            pf = QFrame()
            pf.setStyleSheet(f"QFrame{{background:{pbg}; border-radius:12px; border:none;}}")
            pf_lo = QHBoxLayout(pf)
            pf_lo.setContentsMargins(14,12,14,12); pf_lo.setSpacing(12)
            ic_box = QFrame()
            ic_box.setFixedSize(36,36)
            ic_box.setStyleSheet("QFrame{background:white; border-radius:9px; border:none;}")
            ic_box_lo = QHBoxLayout(ic_box)
            ic_box_lo.setContentsMargins(0,0,0,0)
            ic_inner = _svg_ic(ic_svg, 18)
            ic_box_lo.addWidget(ic_inner, 0, Qt.AlignCenter)
            txt_col = QVBoxLayout(); txt_col.setSpacing(2)
            n = QLabel(name)
            n.setStyleSheet(
                f"color:{TXT_H}; font-size:12px; font-weight:700; border:none; background:transparent;"
            )
            d = QLabel(desc_txt)
            d.setStyleSheet(
                f"color:{TXT_M}; font-size:11px; border:none; background:transparent;"
            )
            txt_col.addWidget(n); txt_col.addWidget(d)
            pf_lo.addWidget(ic_box)
            pf_lo.addLayout(txt_col, 1)
            perks_grid.addWidget(pf, i//2, i%2)
        perks_clo.addLayout(perks_grid)

        # Admin note
        if admin_note:
            _, note_clo = _card_frame(left_lo)
            _section_hdr(note_clo, "ic_edit.svg", "Ghi chú Admin")
            note_clo.addWidget(_body_lbl(admin_note))

        left_lo.addStretch()

        # ── RIGHT: Job Summary ─────────────────────────────────────────
        _, sum_clo = _card_frame(right_lo)
        sum_ttl = QLabel("TÓM TẮT CÔNG VIỆC")
        sum_ttl.setStyleSheet(
            f"color:{TXT_M}; font-size:11px; font-weight:700;"
            " letter-spacing:1px; border:none; background:transparent;"
        )
        sum_clo.addWidget(sum_ttl)
        div0 = QFrame(); div0.setFixedHeight(1)
        div0.setStyleSheet(f"background:{BORDER}; border:none;")
        sum_clo.addWidget(div0)

        sum_rows = [
            ("ic_trend.svg",   "Mức lương",     sal),
            ("ic_clock.svg",   "Hạn nộp",       deadline),
            ("ic_user.svg",    "Cấp bậc",       level),
            ("ic_clock.svg",   "Loại hình",     job_type),
            ("ic_pin.svg",     "Địa điểm",      location),
            ("ic_users.svg",   "Số lượng tuyển",f"{count} vị trí"),
            ("ic_activity.svg","Ứng viên nộp",  str(applicants)),
        ]
        for i, (ic_svg, k, v) in enumerate(sum_rows):
            row_f = QFrame()
            row_f.setStyleSheet(
                "QFrame{background:transparent; border:none;"
                + ("border-bottom:1px solid #F3F4F6;" if i < len(sum_rows)-1 else "")
                + "}"
            )
            r_lo = QHBoxLayout(row_f)
            r_lo.setContentsMargins(0,8,0,8); r_lo.setSpacing(8)
            r_lo.addWidget(_svg_ic(ic_svg, 14))
            k_lbl = QLabel(k)
            k_lbl.setStyleSheet(
                f"color:{TXT_M}; font-size:12px; background:transparent; border:none;"
            )
            v_lbl = QLabel(v or "—")
            v_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            v_lbl.setStyleSheet(
                f"color:{TXT_H}; font-size:12px; font-weight:600;"
                " background:transparent; border:none;"
            )
            r_lo.addWidget(k_lbl, 1); r_lo.addWidget(v_lbl)
            sum_clo.addWidget(row_f)

        # ── RIGHT: Company Card ────────────────────────────────────────
        _, co_clo = _card_frame(right_lo)
        co_ttl = QLabel("CÔNG TY ĐĂNG TIN")
        co_ttl.setStyleSheet(
            f"color:{TXT_M}; font-size:11px; font-weight:700;"
            " letter-spacing:1px; border:none; background:transparent;"
        )
        co_clo.addWidget(co_ttl)
        div1 = QFrame(); div1.setFixedHeight(1)
        div1.setStyleSheet(f"background:{BORDER}; border:none;")
        co_clo.addWidget(div1)

        co_row = QHBoxLayout(); co_row.setSpacing(12)
        co_logo = QLabel((company[0].upper()) if company != "—" else "?")
        co_logo.setFixedSize(44,44); co_logo.setAlignment(Qt.AlignCenter)
        co_logo.setStyleSheet(
            f"background:{logo_bg}; color:{logo_fg}; border-radius:11px;"
            " font-size:18px; font-weight:800; border:none;"
        )
        co_info = QVBoxLayout(); co_info.setSpacing(2)
        co_name = QLabel(company)
        co_name.setStyleSheet(
            f"color:{TXT_H}; font-size:14px; font-weight:800; background:transparent; border:none;"
        )
        co_dept = QLabel(dept or "Phòng tuyển dụng")
        co_dept.setStyleSheet(
            f"color:{TXT_M}; font-size:12px; background:transparent; border:none;"
        )
        co_info.addWidget(co_name); co_info.addWidget(co_dept)
        co_row.addWidget(co_logo); co_row.addLayout(co_info, 1)
        co_clo.addLayout(co_row)

        for ic_svg, k, v in [
            ("ic_pin.svg",    "Địa điểm", location),
            ("ic_folder.svg", "Phòng ban", dept or "—"),
        ]:
            r = QHBoxLayout(); r.setSpacing(8)
            r.addWidget(_svg_ic(ic_svg, 13))
            kl = QLabel(k)
            kl.setStyleSheet(
                f"color:{TXT_M}; font-size:12px; border:none; background:transparent;"
            )
            vl = QLabel(v)
            vl.setAlignment(Qt.AlignRight)
            vl.setStyleSheet(
                f"color:{TXT_H}; font-size:12px; font-weight:600;"
                " border:none; background:transparent;"
            )
            r.addWidget(kl, 1); r.addWidget(vl, 1)
            co_clo.addLayout(r)

        # ── RIGHT: Admin Actions Card ──────────────────────────────────
        act_card = QFrame()
        if st_raw == "pending_approval":
            act_card.setStyleSheet(
                "QFrame{background:#1E3A8A; border-radius:16px; border:none;}"
            )
        else:
            act_card.setStyleSheet(
                f"QFrame{{background:{CARD}; border-radius:16px; border:1px solid {BORDER};}}"
            )
        _shadow(act_card, blur=16, dy=4, alpha=18)
        act_lo = QVBoxLayout(act_card)
        act_lo.setContentsMargins(20,18,20,18); act_lo.setSpacing(10)

        act_ttl = QLabel("HÀNH ĐỘNG QUẢN TRỊ")
        act_ttl.setStyleSheet(
            ("color:rgba(255,255,255,0.65);" if st_raw == "pending_approval" else f"color:{TXT_M};")
            + " font-size:11px; font-weight:700; letter-spacing:1px;"
            " border:none; background:transparent;"
        )
        act_lo.addWidget(act_ttl)

        def _do_approve():
            try:
                jobhub_api.admin_approve_job(job_id)
                _toast(self.win, "Đã phê duyệt tin tuyển dụng", success=True)
                dlg.accept()
                QTimer.singleShot(0, self._fill_jobs_grid)
            except ApiError as e:
                _toast(self.win, f"Lỗi: {e}", success=False)

        def _do_reject():
            nd = QDialog(dlg)
            nd.setWindowTitle("Nhập lý do từ chối")
            nd.setMinimumWidth(400)
            nd.setStyleSheet(
                "QDialog{background:#FFFFFF;}"
                f"QLabel{{background:transparent; border:none; color:{TXT_H};}}"
                "QPlainTextEdit{background:#F9FAFB; border:1.5px solid #E5E7EB;"
                " border-radius:8px; padding:8px; font-size:13px;}"
                "QPlainTextEdit:focus{border-color:#2563EB;}"
            )
            nd_lo = QVBoxLayout(nd)
            nd_lo.setContentsMargins(24,20,24,20); nd_lo.setSpacing(12)

            nd_hdr = QHBoxLayout(); nd_hdr.setSpacing(8)
            nd_hdr.addWidget(_svg_ic("ic_alert.svg", 18))
            nd_hdr_lbl = QLabel("Lý do từ chối")
            nd_hdr_lbl.setStyleSheet(
                f"color:{TXT_H}; font-size:15px; font-weight:700;"
                " border:none; background:transparent;"
            )
            nd_hdr.addWidget(nd_hdr_lbl); nd_hdr.addStretch()
            nd_lo.addLayout(nd_hdr)

            sub_lbl = QLabel("Nhập lý do để HR có thể chỉnh sửa và nộp lại:")
            sub_lbl.setStyleSheet(
                f"color:{TXT_M}; font-size:12px; border:none; background:transparent;"
            )
            nd_lo.addWidget(sub_lbl)
            txt_note = QPlainTextEdit()
            txt_note.setPlaceholderText("Mô tả lý do từ chối chi tiết...")
            txt_note.setFixedHeight(100)
            nd_lo.addWidget(txt_note)

            btn_row2 = QHBoxLayout(); btn_row2.setSpacing(8)
            btn_cancel2 = QPushButton("  Hủy")
            btn_cancel2.setIcon(QIcon(str(resource_icon("ic_x.svg"))))
            btn_cancel2.setIconSize(QSize(13,13))
            btn_cancel2.setFixedHeight(36)
            btn_cancel2.setStyleSheet(
                "QPushButton{background:#F3F4F6; color:#374151; border:none;"
                " border-radius:8px; font-size:13px; padding:0 16px;}"
                "QPushButton:hover{background:#E5E7EB;}"
            )
            btn_cancel2.clicked.connect(nd.reject)

            btn_confirm2 = QPushButton("  Xác nhận từ chối")
            btn_confirm2.setIcon(QIcon(str(resource_icon("ic_check.svg"))))
            btn_confirm2.setIconSize(QSize(13,13))
            btn_confirm2.setFixedHeight(36)
            btn_confirm2.setStyleSheet(
                "QPushButton{background:#DC2626; color:#FFFFFF; border:none;"
                " border-radius:8px; font-size:13px; font-weight:600; padding:0 16px;}"
                "QPushButton:hover{background:#B91C1C;}"
            )
            def _confirm_reject():
                note = txt_note.toPlainText().strip() or None
                try:
                    jobhub_api.admin_reject_job(job_id, note)
                    _toast(self.win, "Đã từ chối tin tuyển dụng", success=False)
                    nd.accept(); dlg.accept()
                    QTimer.singleShot(0, self._fill_jobs_grid)
                except ApiError as e:
                    _toast(self.win, f"Lỗi: {e}", success=False)
            btn_confirm2.clicked.connect(_confirm_reject)
            btn_row2.addWidget(btn_cancel2); btn_row2.addWidget(btn_confirm2)
            nd_lo.addLayout(btn_row2)
            nd.exec()

        if st_raw == "pending_approval":
            btn_approve2 = QPushButton("  Phê duyệt tin này")
            btn_approve2.setCursor(Qt.PointingHandCursor)
            btn_approve2.setIcon(QIcon(str(resource_icon("ic_check.svg"))))
            btn_approve2.setIconSize(QSize(16,16))
            btn_approve2.setFixedHeight(44)
            btn_approve2.setStyleSheet(
                "QPushButton{background:#FFFFFF; color:#1E3A8A; border:none;"
                " border-radius:11px; font-size:14px; font-weight:700;}"
                "QPushButton:hover{background:#DBEAFE;}"
            )
            act_lo.addWidget(btn_approve2)
            btn_approve2.clicked.connect(_do_approve)

            btn_reject2 = QPushButton("  Từ chối tin này")
            btn_reject2.setCursor(Qt.PointingHandCursor)
            btn_reject2.setIcon(QIcon(str(resource_icon("ic_x.svg"))))
            btn_reject2.setIconSize(QSize(16,16))
            btn_reject2.setFixedHeight(44)
            btn_reject2.setStyleSheet(
                "QPushButton{background:rgba(255,255,255,0.1); color:#FFFFFF;"
                " border:1.5px solid rgba(255,255,255,0.25); border-radius:11px;"
                " font-size:14px; font-weight:600;}"
                "QPushButton:hover{background:rgba(239,68,68,0.35); border-color:#EF4444;}"
            )
            act_lo.addWidget(btn_reject2)
            btn_reject2.clicked.connect(_do_reject)

            if btn_hdr_approve: btn_hdr_approve.clicked.connect(_do_approve)
            if btn_hdr_reject:  btn_hdr_reject.clicked.connect(_do_reject)
        else:
            st_row = QHBoxLayout(); st_row.setSpacing(8)
            st_icon = "ic_check.svg" if st_raw == "published" else "ic_x.svg"
            st_row.addWidget(_svg_ic(st_icon, 16))
            status_lbl = QLabel(f"Trạng thái: {st_label}")
            status_lbl.setStyleSheet(
                f"color:{st_fg}; font-size:14px; font-weight:700;"
                " background:transparent; border:none;"
            )
            st_row.addWidget(status_lbl); st_row.addStretch()
            act_lo.addLayout(st_row)
            if st_raw == "rejected" and admin_note:
                note2 = QLabel(f"Lý do: {admin_note}")
                note2.setWordWrap(True)
                note2.setStyleSheet(
                    f"color:{TXT_S}; font-size:12px; background:transparent; border:none;"
                )
                act_lo.addWidget(note2)

        right_lo.addWidget(act_card)
        right_lo.addStretch()

        cols.addLayout(left_lo, 3)
        cols.addLayout(right_lo, 2)
        body_lo.addLayout(cols)

        dlg.exec()

    # ══════════════════════════════════════════════════════════════
    #  REPORTS PAGE — Doanh thu
    # ══════════════════════════════════════════════════════════════
    def _fill_reports_page(self) -> None:
        w = self._reports_widget
        if not w:
            return

        # ── Clear & hide ALL old .ui widgets ─────────────────────────
        for obj_name in ("reportPageTitle","reportPageSubTitle","btnGenerateReport",
                         "recentReportsCard","reportHeaderSpacer"):
            child = w.findChild(QWidget, obj_name)
            if child:
                child.hide()

        main_lo = w.findChild(QVBoxLayout, "mainAreaLayout")
        if not main_lo:
            return
        # Aggressively clear
        while main_lo.count():
            item = main_lo.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().setParent(None)
            elif item.layout():
                AdminDashboard._clear_layout(item.layout())

        # ── palette ──────────────────────────────────────────────────
        BLUE  = "#2563EB"; BLUE_D = "#1D4ED8"
        TXT_H = "#111827"; TXT_M  = "#6B7280"; TXT_S = "#374151"
        CARD  = "#FFFFFF"; BORDER = "#E5E7EB"; PAGE  = "#F0F2F5"

        # ── fetch data ────────────────────────────────────────────────
        try:
            dash   = jobhub_api.admin_dashboard()
            cards  = dash.get("cards", {})
            vals   = dash.get("values", [0]*6)
        except Exception:
            cards = {}; vals = [0]*6

        try:
            hr_list  = list(jobhub_api.admin_hr_overview())
        except Exception:
            hr_list = []
        try:
            can_list = list(jobhub_api.admin_candidate_overview())
        except Exception:
            can_list = []

        total_hr  = int(cards.get("hr",  len(hr_list))  or 0)
        total_can = int(cards.get("users", len(can_list)) or 0)

        HR_FEE  = 35_500_000
        CAN_FEE = 850_000
        hr_rev  = total_hr  * HR_FEE
        can_rev = total_can * CAN_FEE
        tot_rev = hr_rev + can_rev

        # Smooth monthly data — spread total evenly then vary ±20%
        import random; random.seed(42)
        def _smooth(total, n=6):
            base = total / n if n else 0
            pts  = [base * (0.8 + 0.4 * random.random()) for _ in range(n)]
            # scale to sum ≈ total
            s = sum(pts) or 1
            return [p * total / s for p in pts]

        base_hr  = _smooth(hr_rev)
        base_can = _smooth(can_rev)
        month_labels = [f"Tháng {i+1}" for i in range(6)]

        # ── helpers ───────────────────────────────────────────────────
        def _fmt(n):
            if n >= 1_000_000_000: return f"{n/1_000_000_000:.2f}B đ"
            if n >= 1_000_000:     return f"{n/1_000_000:.1f}M đ"
            return f"{n:,}đ"

        def _pill_lbl(txt, bg, fg):
            p = QLabel(txt)
            p.setFixedHeight(22); p.setAlignment(Qt.AlignCenter)
            p.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:4px;"
                " padding:0 8px; font-size:11px; font-weight:700; border:none;"
            )
            return p

        # ════════════════════════════════════════════════════════════
        # SCROLL AREA wrapping all content
        # ════════════════════════════════════════════════════════════
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background:{PAGE}; border:none; }}"
            "QScrollBar:vertical { background:#F0F2F5; width:6px; border-radius:3px; }"
            "QScrollBar::handle:vertical { background:#D1D5DB; border-radius:3px; }"
        )
        page_w = QWidget(); page_w.setStyleSheet(f"background:{PAGE};")
        page_lo = QVBoxLayout(page_w)
        page_lo.setContentsMargins(28, 20, 28, 28)
        page_lo.setSpacing(18)
        scroll.setWidget(page_w)
        main_lo.addWidget(scroll)

        # ── HEADER ───────────────────────────────────────────────────
        hdr = QFrame(); hdr.setStyleSheet("background:transparent; border:none;")
        hdr_lo = QHBoxLayout(hdr)
        hdr_lo.setContentsMargins(0,0,0,0); hdr_lo.setSpacing(10)

        tc = QVBoxLayout(); tc.setSpacing(2)
        t = QLabel("Báo cáo Doanh thu")
        t.setStyleSheet(f"color:{TXT_H}; font-size:22px; font-weight:800; border:none; background:transparent;")
        s = QLabel("Phân tích dòng tiền từ Candidate và HR")
        s.setStyleSheet(f"color:{TXT_M}; font-size:13px; border:none; background:transparent;")
        tc.addWidget(t); tc.addWidget(s)
        hdr_lo.addLayout(tc, 1)

        from datetime import date
        today = date.today()
        date_lbl = QLabel(f"  01/01/{today.year} – {today.strftime('%d/%m/%Y')}")
        date_lbl.setFixedHeight(36)
        date_lbl.setStyleSheet(
            f"QLabel {{ background:{CARD}; color:{TXT_M}; border:1px solid {BORDER};"
            " border-radius:8px; font-size:13px; padding:0 14px; }}"
        )
        hdr_lo.addWidget(date_lbl)

        hdr_lo.addStretch()
        page_lo.addWidget(hdr)

        # ── STAT CARDS ────────────────────────────────────────────────
        stat_row = QHBoxLayout(); stat_row.setSpacing(14)

        def _stat(title, value, hint, pct, accent):
            f = QFrame()
            f.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:14px;"
                f" border:1px solid {BORDER}; border-top:3px solid {accent}; }}"
            )
            _shadow(f, blur=14, dy=3, alpha=10)
            fl = QVBoxLayout(f); fl.setContentsMargins(18,16,18,16); fl.setSpacing(5)
            lbl_t = QLabel(title.upper())
            lbl_t.setStyleSheet(
                f"color:{TXT_M}; font-size:10px; font-weight:700;"
                " letter-spacing:0.8px; border:none; background:transparent;"
            )
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet(
                f"color:{TXT_H}; font-size:21px; font-weight:800;"
                " border:none; background:transparent;"
            )
            lbl_v.setMinimumHeight(30)
            is_pos = pct >= 0
            c_col  = "#16A34A" if is_pos else "#DC2626"
            lbl_p  = QLabel(f"{'↑' if is_pos else '↓'} {'+' if is_pos else ''}{pct}%  {hint}")
            lbl_p.setStyleSheet(
                f"color:{c_col}; font-size:12px; font-weight:600;"
                " border:none; background:transparent;"
            )
            fl.addWidget(lbl_t); fl.addWidget(lbl_v); fl.addWidget(lbl_p)
            return f

        stat_row.addWidget(_stat("Tổng doanh thu", _fmt(tot_rev), "so kỳ trước",  12, "#2563EB"))
        stat_row.addWidget(_stat("Candidate Pro",  _fmt(can_rev), "tăng trưởng",   8, "#06B6D4"))
        stat_row.addWidget(_stat("Hóa đơn HR",     _fmt(hr_rev),  "so kỳ trước",  -2, "#8B5CF6"))
        page_lo.addLayout(stat_row)

        # ── CHART ─────────────────────────────────────────────────────
        ch_card = QFrame()
        ch_card.setStyleSheet(
            f"QFrame {{ background:{CARD}; border-radius:16px; border:1px solid {BORDER}; }}"
        )
        _shadow(ch_card, blur=14, dy=3, alpha=10)
        ch_lo = QVBoxLayout(ch_card)
        ch_lo.setContentsMargins(24,18,24,14); ch_lo.setSpacing(10)

        # Chart header row
        ch_hdr = QHBoxLayout(); ch_hdr.setSpacing(10)
        ic_t = QLabel()
        ic_t.setFixedSize(18,18)
        ic_t.setPixmap(QIcon(str(resource_icon("ic_trend.svg"))).pixmap(QSize(18,18)))
        ic_t.setStyleSheet("background:transparent; border:none;")
        ch_hdr.addWidget(ic_t)
        ch_ttl = QLabel("Xu hướng Doanh thu")
        ch_ttl.setStyleSheet(
            f"color:{TXT_H}; font-size:15px; font-weight:800; border:none; background:transparent;"
        )
        ch_hdr.addWidget(ch_ttl, 1)

        for lc, lt, dash in [("#2563EB","HR Invoices",False),("#9CA3AF","Candidate Pro",True)]:
            dot = QLabel("━━" if not dash else "╌╌")
            dot.setStyleSheet(
                f"color:{lc}; font-size:11px; font-weight:700; background:transparent; border:none;"
            )
            lt2 = QLabel(lt)
            lt2.setStyleSheet(
                f"color:{TXT_S}; font-size:12px; background:transparent; border:none;"
            )
            ch_hdr.addWidget(dot); ch_hdr.addWidget(lt2)
        ch_lo.addLayout(ch_hdr)

        div0 = QFrame(); div0.setFixedHeight(1)
        div0.setStyleSheet(f"background:{BORDER}; border:none;")
        ch_lo.addWidget(div0)

        canvas = make_revenue_trend_chart(month_labels, base_hr, base_can)
        canvas.setMinimumHeight(230)
        ch_lo.addWidget(canvas)
        page_lo.addWidget(ch_card)

        # ── BOTTOM 2 TABLES ───────────────────────────────────────────
        bot = QHBoxLayout(); bot.setSpacing(16)

        # ── shared table stylesheet ────────────────────────────────
        TBL_SS = (
            f"QTableWidget {{ background:{CARD}; border:none; font-size:13px;"
            f" color:{TXT_S}; outline:none; }}"
            "QTableWidget::item { padding:0 14px; border-bottom:1px solid #F0F2F5; }"
            "QTableWidget::item:selected { background:#EEF2FF; color:#1D4ED8; }"
            f"QHeaderView::section {{ background:#F9FAFB; color:#9CA3AF;"
            " font-size:10px; font-weight:700; letter-spacing:0.5px;"
            " border:none; border-bottom:1px solid #E5E7EB; padding:0 14px; height:36px; }}"
        )

        def _build_tbl(tbl_widget, headers, rows, pill_cols=(), fixed_widths=None):
            """Populate a QTableWidget with headers/rows; pill_cols = set of col indices that hold QWidget."""
            ROW_H = 52; HDR_H = 36
            tbl_widget.setColumnCount(len(headers))
            tbl_widget.setHorizontalHeaderLabels(headers)
            tbl_widget.setRowCount(len(rows))
            tbl_widget.setShowGrid(False)
            tbl_widget.setEditTriggers(QTableWidget.NoEditTriggers)
            tbl_widget.setSelectionBehavior(QTableWidget.SelectRows)
            tbl_widget.setSelectionMode(QTableWidget.SingleSelection)
            tbl_widget.verticalHeader().setVisible(False)
            tbl_widget.setAlternatingRowColors(False)
            tbl_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tbl_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            tbl_widget.setFixedHeight(ROW_H * max(len(rows), 1) + HDR_H + 2)
            tbl_widget.setStyleSheet(TBL_SS)
            hh = tbl_widget.horizontalHeader()
            hh.setStretchLastSection(False)
            hh.setSectionResizeMode(0, QHeaderView.Stretch)
            fw = fixed_widths or [110, 130, 130]
            for ci in range(1, len(headers)):
                hh.setSectionResizeMode(ci, QHeaderView.Fixed)
                tbl_widget.setColumnWidth(ci, fw[min(ci - 1, len(fw) - 1)])
            for r, row in enumerate(rows):
                tbl_widget.setRowHeight(r, ROW_H)
                for c2, cell in enumerate(row):
                    if isinstance(cell, QWidget):
                        cnt = QWidget(); cnt.setStyleSheet("background:transparent;")
                        clo = QHBoxLayout(cnt); clo.setContentsMargins(6,0,6,0); clo.setSpacing(0)
                        clo.addStretch(); clo.addWidget(cell); clo.addStretch()
                        tbl_widget.setCellWidget(r, c2, cnt)
                    else:
                        itm = QTableWidgetItem(str(cell))
                        align = Qt.AlignVCenter | (Qt.AlignRight if c2 == len(row)-1 else Qt.AlignLeft)
                        itm.setTextAlignment(align)
                        tbl_widget.setItem(r, c2, itm)

        def _tbl_card(title, headers, rows, on_view_all=None, fixed_widths=None):
            tc2 = QFrame()
            tc2.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:16px; border:1px solid {BORDER}; }}"
            )
            _shadow(tc2, blur=14, dy=3, alpha=10)
            tl = QVBoxLayout(tc2); tl.setContentsMargins(0,0,0,0); tl.setSpacing(0)

            # Card header bar
            th = QFrame(); th.setFixedHeight(52)
            th.setStyleSheet(
                f"QFrame {{ background:transparent; border:none; border-bottom:1px solid {BORDER}; }}"
            )
            th_lo = QHBoxLayout(th); th_lo.setContentsMargins(20,0,20,0)
            lbl_th = QLabel(title)
            lbl_th.setStyleSheet(
                f"color:{TXT_H}; font-size:14px; font-weight:800; border:none; background:transparent;"
            )
            lnk = QPushButton("Xem tất cả →")
            lnk.setCursor(Qt.PointingHandCursor)
            lnk.setStyleSheet(
                f"QPushButton {{ color:{BLUE}; font-size:12px; font-weight:600;"
                " border:none; background:transparent; padding:0; }}"
                f"QPushButton:hover {{ color:{BLUE_D}; }}"
            )
            if on_view_all:
                lnk.clicked.connect(on_view_all)
            th_lo.addWidget(lbl_th, 1); th_lo.addWidget(lnk)
            tl.addWidget(th)

            tbl = QTableWidget()
            _build_tbl(tbl, headers, rows, fixed_widths=fixed_widths)
            tl.addWidget(tbl)
            tl.addStretch()   # prevent card from stretching table vertically
            return tc2

        # ── helpers for "Xem tất cả" dialogs ─────────────────────
        def _fmt_date(raw):
            s = str(raw or "")[:10]
            if len(s) == 10 and s[4] == "-":
                y,m,d = s.split("-"); return f"{d}/{m}/{y}"
            return s or "—"

        PLANS = ["BASIC","ELITE","PRO"]
        AMTS  = [450_000, 1_200_000, 2_500_000]
        PC    = {"BASIC":("#DBEAFE","#1D4ED8"), "ELITE":("#D1FAE5","#065F46"), "PRO":("#EDE9FE","#5B21B6")}
        STS   = ["Paid","Paid","Pending","Overdue","Paid","Paid"]
        SC    = {"Paid":("#D1FAE5","#059669"),"Pending":("#FEF9C3","#92400E"),"Overdue":("#FEE2E2","#B91C1C")}

        def _make_can_rows(src):
            rows = []
            for i, c in enumerate(src):
                nm = (c.get("full_name") or c.get("email") or "—")[:22]
                pl = PLANS[i % 3]; am = AMTS[i % 3]
                pb, pf = PC[pl]
                rows.append((nm, _pill_lbl(pl,pb,pf), _fmt_date(c.get("created_at","")), f"{am:,}đ"))
            return rows

        def _make_hr_rows(src):
            rows = []
            for i, h in enumerate(src):
                co  = (h.get("company_name") or h.get("full_name") or "—")[:24]
                inv = f"INV-{today.year}-{i+1:03d}"
                st  = STS[i % len(STS)]; amt = (i+1)*12_500_000
                sb, sf = SC.get(st, ("#F3F4F6","#6B7280"))
                rows.append((co, inv, _pill_lbl(st,sb,sf), f"{amt:,}đ"))
            return rows

        def _view_all_dialog(title, headers, rows, fixed_widths=None):
            dlg = QDialog(self.win)
            dlg.setWindowTitle(title)
            dlg.setMinimumWidth(720)
            dlg.setStyleSheet(f"QDialog {{ background:{PAGE}; }}")
            lo = QVBoxLayout(dlg); lo.setContentsMargins(24,24,24,24); lo.setSpacing(16)

            # Dialog header
            hd = QLabel(title)
            hd.setStyleSheet(f"color:{TXT_H}; font-size:18px; font-weight:800; background:transparent;")
            lo.addWidget(hd)

            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER}; border:none;")
            lo.addWidget(div)

            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:12px; border:1px solid {BORDER}; }}"
            )
            _shadow(card, blur=14, dy=3, alpha=10)
            c_lo = QVBoxLayout(card); c_lo.setContentsMargins(0,0,0,0); c_lo.setSpacing(0)

            tbl = QTableWidget()
            _build_tbl(tbl, headers, rows, fixed_widths=fixed_widths)
            # Override fixed height for full-list: allow scroll
            tbl.setFixedHeight(min(52 * len(rows) + 38, 480))
            tbl.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            tbl.setStyleSheet(TBL_SS +
                "QScrollBar:vertical { background:#F0F2F5; width:6px; border-radius:3px; }"
                "QScrollBar::handle:vertical { background:#D1D5DB; border-radius:3px; }"
            )
            c_lo.addWidget(tbl)
            lo.addWidget(card)

            # Close button
            btn_close = QPushButton("Đóng")
            btn_close.setFixedHeight(38); btn_close.setCursor(Qt.PointingHandCursor)
            btn_close.setStyleSheet(
                f"QPushButton {{ background:{BLUE}; color:#fff; border:none;"
                " border-radius:8px; font-size:13px; font-weight:700; padding:0 24px; }}"
                f"QPushButton:hover {{ background:{BLUE_D}; }}"
            )
            btn_close.clicked.connect(dlg.accept)
            row_btn = QHBoxLayout(); row_btn.addStretch(); row_btn.addWidget(btn_close)
            lo.addLayout(row_btn)
            dlg.exec()

        # ── Build row data ─────────────────────────────────────────
        can_src = can_list or [
            {"full_name":"Nguyễn Văn A","created_at":"2026-04-21"},
            {"full_name":"Trần Thị B",  "created_at":"2026-04-19"},
            {"full_name":"Lê Văn C",    "created_at":"2026-04-18"},
        ]
        hr_src = hr_list or [
            {"company_name":"Pending Corp"},
            {"company_name":"TechViet Solutions"},
            {"company_name":"FPT Retail"},
        ]

        can_rows_preview = _make_can_rows(can_src[:6])
        hr_rows_preview  = _make_hr_rows(hr_src[:6])

        can_headers = ["CANDIDATE","KẾ HOẠCH","NGÀY","SỐ TIỀN"]
        hr_headers  = ["CÔNG TY","MÃ HÓA ĐƠN","TRẠNG THÁI","SỐ TIỀN"]

        def _open_can_all():
            _view_all_dialog("Tất cả giao dịch Candidate Pro",
                             can_headers, _make_can_rows(can_src),
                             fixed_widths=[110, 130, 130])

        def _open_hr_all():
            _view_all_dialog("Tất cả hóa đơn HR",
                             hr_headers, _make_hr_rows(hr_src),
                             fixed_widths=[130, 130, 130])

        bot.addWidget(_tbl_card("Giao dịch Candidate Pro",
                                can_headers, can_rows_preview,
                                on_view_all=_open_can_all,
                                fixed_widths=[110, 130, 130]), 1)
        bot.addWidget(_tbl_card("Hóa đơn HR gần đây",
                                hr_headers, hr_rows_preview,
                                on_view_all=_open_hr_all,
                                fixed_widths=[130, 130, 130]), 1)
        page_lo.addLayout(bot)
        page_lo.addStretch()


    # ══════════════════════════════════════════════════════════════
    #  USER DETAIL DIALOG
    # ══════════════════════════════════════════════════════════════
    def _show_user_detail_dialog(self, user_id: int, base_data: dict) -> None:
        """Full-screen style dialog: candidate profile."""
        BLUE = "#2563EB"; BLUE_D = "#1D4ED8"
        TXT_H = "#111827"; TXT_M = "#6B7280"; TXT_S = "#374151"
        CARD = "#FFFFFF"; BORDER = "#E5E7EB"; PAGE = "#F0F2F5"
        _AVATAR_COLORS = [
            ("#DBEAFE","#1D4ED8"), ("#D1FAE5","#065F46"),
            ("#F3E8FF","#6D28D9"), ("#FEF3C7","#92400E"),
            ("#FCE7F3","#9D174D"), ("#CFFAFE","#0E7490"),
        ]

        # Fetch full detail
        try:
            u = jobhub_api.admin_get_user(user_id)
        except Exception:
            u = base_data

        name      = str(u.get("full_name") or base_data.get("full_name") or "—")
        email     = str(u.get("email")     or base_data.get("email")     or "—")
        phone     = str(u.get("phone")     or u.get("phone_number")      or "—")
        address   = str(u.get("address")   or u.get("location")          or "—")
        bio       = str(u.get("bio")       or u.get("about")             or "")
        is_active = bool(u.get("is_active", base_data.get("is_active", True)))
        joined    = self._fmt_date(str(u.get("created_at") or base_data.get("created_at") or ""))

        dlg = QDialog(self.win)
        dlg.setWindowTitle(f"Hồ sơ ứng viên – {name}")
        dlg.setMinimumWidth(620); dlg.setMinimumHeight(540)
        dlg.setStyleSheet(f"QDialog {{ background:{PAGE}; }}")
        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── Top hero banner ───────────────────────────────────────
        hero = QFrame()
        hero.setFixedHeight(130)
        hero.setStyleSheet(f"QFrame {{ background:{BLUE}; border:none; }}")
        hero_lo = QHBoxLayout(hero)
        hero_lo.setContentsMargins(32, 0, 32, 0); hero_lo.setSpacing(20)

        initials = "".join(w[0].upper() for w in name.split()[:2]) or "?"
        bg, fg = _AVATAR_COLORS[user_id % len(_AVATAR_COLORS)]
        av_big = QLabel(initials)
        av_big.setFixedSize(72, 72); av_big.setAlignment(Qt.AlignCenter)
        av_big.setStyleSheet(
            f"QLabel {{ background:{bg}; color:{fg}; font-size:22px; font-weight:800;"
            " border-radius:36px; border:3px solid rgba(255,255,255,0.4); }}"
        )
        hero_lo.addWidget(av_big)

        hero_info = QVBoxLayout(); hero_info.setSpacing(4)
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(
            "QLabel { color:#FFFFFF; font-size:18px; font-weight:800;"
            " background:transparent; border:none; }"
        )
        lbl_email = QLabel(email)
        lbl_email.setStyleSheet(
            "QLabel { color:rgba(255,255,255,0.8); font-size:13px;"
            " background:transparent; border:none; }"
        )
        pill_bg = "#DCFCE7" if is_active else "#F3F4F6"
        pill_fg = "#15803D" if is_active else "#6B7280"
        pill_txt = "Đang hoạt động" if is_active else "Vô hiệu hóa"
        status_pill = QLabel(f"  {pill_txt}  ")
        status_pill.setFixedHeight(22)
        status_pill.setStyleSheet(
            f"QLabel {{ background:{pill_bg}; color:{pill_fg}; border-radius:4px;"
            " font-size:11px; font-weight:700; border:none; padding:0 6px; }}"
        )
        status_row = QHBoxLayout(); status_row.setSpacing(8)
        status_row.addWidget(status_pill); status_row.addStretch()
        hero_info.addWidget(lbl_name)
        hero_info.addWidget(lbl_email)
        hero_info.addLayout(status_row)
        hero_lo.addLayout(hero_info, 1)
        root.addWidget(hero)

        # ── Scrollable body ───────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background:{PAGE}; border:none; }}"
            "QScrollBar:vertical { background:#F0F2F5; width:6px; border-radius:3px; }"
            "QScrollBar::handle:vertical { background:#D1D5DB; border-radius:3px; }"
        )
        body_w = QWidget(); body_w.setStyleSheet(f"background:{PAGE};")
        body_lo = QVBoxLayout(body_w)
        body_lo.setContentsMargins(24, 20, 24, 20); body_lo.setSpacing(16)
        scroll.setWidget(body_w)
        root.addWidget(scroll, 1)

        def _info_card(title, fields):
            """fields = list of (label, value)"""
            c = QFrame()
            c.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:12px; border:1px solid {BORDER}; }}"
            )
            _shadow(c, blur=12, dy=2, alpha=8)
            cl = QVBoxLayout(c); cl.setContentsMargins(20, 16, 20, 16); cl.setSpacing(12)
            ttl = QLabel(title)
            ttl.setStyleSheet(
                f"QLabel {{ color:{TXT_H}; font-size:13px; font-weight:800;"
                " border:none; background:transparent; }}"
            )
            cl.addWidget(ttl)
            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER}; border:none;")
            cl.addWidget(div)
            grid = QGridLayout(); grid.setSpacing(10); grid.setColumnStretch(1, 1); grid.setColumnStretch(3, 1)
            for i, (lbl, val) in enumerate(fields):
                row_i = i // 2; col_base = (i % 2) * 2
                lbl_w = QLabel(lbl)
                lbl_w.setStyleSheet(
                    f"QLabel {{ color:{TXT_M}; font-size:12px; font-weight:600;"
                    " background:transparent; border:none; }}"
                )
                val_w = QLabel(str(val) if val else "—")
                val_w.setWordWrap(True)
                val_w.setStyleSheet(
                    f"QLabel {{ color:{TXT_S}; font-size:13px; font-weight:500;"
                    " background:transparent; border:none; }}"
                )
                grid.addWidget(lbl_w, row_i, col_base)
                grid.addWidget(val_w, row_i, col_base + 1)
            cl.addLayout(grid)
            return c

        # Info cards
        body_lo.addWidget(_info_card("Thông tin tài khoản", [
            ("ID người dùng", f"#{user_id}"),
            ("Ngày tham gia",  joined),
            ("Vai trò",        "Ứng viên"),
            ("Trạng thái",     pill_txt),
        ]))

        contact_fields = [("Email", email), ("Số điện thoại", phone)]
        if address and address != "—":
            contact_fields.append(("Địa chỉ", address))
        body_lo.addWidget(_info_card("Thông tin liên hệ", contact_fields))

        if bio:
            bio_card = QFrame()
            bio_card.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:12px; border:1px solid {BORDER}; }}"
            )
            _shadow(bio_card, blur=12, dy=2, alpha=8)
            bio_lo = QVBoxLayout(bio_card); bio_lo.setContentsMargins(20,16,20,16); bio_lo.setSpacing(8)
            bio_ttl = QLabel("Giới thiệu bản thân")
            bio_ttl.setStyleSheet(
                f"QLabel {{ color:{TXT_H}; font-size:13px; font-weight:800;"
                " border:none; background:transparent; }}"
            )
            bio_div = QFrame(); bio_div.setFixedHeight(1)
            bio_div.setStyleSheet(f"background:{BORDER}; border:none;")
            bio_txt = QLabel(bio); bio_txt.setWordWrap(True)
            bio_txt.setStyleSheet(
                f"QLabel {{ color:{TXT_S}; font-size:13px; line-height:1.6;"
                " background:transparent; border:none; }}"
            )
            bio_lo.addWidget(bio_ttl); bio_lo.addWidget(bio_div); bio_lo.addWidget(bio_txt)
            body_lo.addWidget(bio_card)

        body_lo.addStretch()

        # ── Bottom action bar ─────────────────────────────────────
        bar = QFrame(); bar.setFixedHeight(60)
        bar.setStyleSheet(
            f"QFrame {{ background:{CARD}; border:none; border-top:1px solid {BORDER}; }}"
        )
        bar_lo = QHBoxLayout(bar); bar_lo.setContentsMargins(24,0,24,0); bar_lo.setSpacing(10)
        bar_lo.addStretch()

        if is_active:
            btn_toggle = QPushButton("  Khóa tài khoản")
            btn_toggle.setIcon(QIcon(str(resource_icon("ic_lock.svg"))))
            btn_toggle.setStyleSheet(
                "QPushButton { background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA;"
                " border-radius:8px; font-size:13px; font-weight:600; padding:0 18px; height:36px; }"
                "QPushButton:hover { background:#FEE2E2; }"
            )
            def _do_lock():
                try:
                    jobhub_api.admin_lock_user(user_id)
                    _toast(self.win, "Đã khóa tài khoản", success=True)
                except ApiError as e:
                    _toast(self.win, f"Thất bại: {e}", success=False)
                    return
                dlg.accept()
                QTimer.singleShot(0, self._fill_user_table)
            btn_toggle.clicked.connect(_do_lock)
        else:
            btn_toggle = QPushButton("  Mở khóa tài khoản")
            btn_toggle.setIcon(QIcon(str(resource_icon("ic_unlock.svg"))))
            btn_toggle.setStyleSheet(
                "QPushButton { background:#F0FDF4; color:#15803D; border:1px solid #BBF7D0;"
                " border-radius:8px; font-size:13px; font-weight:600; padding:0 18px; height:36px; }"
                "QPushButton:hover { background:#DCFCE7; }"
            )
            def _do_unlock():
                try:
                    jobhub_api.admin_unlock_user(user_id)
                    _toast(self.win, "Đã mở khóa tài khoản", success=True)
                except ApiError as e:
                    _toast(self.win, f"Thất bại: {e}", success=False)
                    return
                dlg.accept()
                QTimer.singleShot(0, self._fill_user_table)
            btn_toggle.clicked.connect(_do_unlock)

        btn_toggle.setIconSize(QSize(15, 15))
        btn_toggle.setCursor(Qt.PointingHandCursor)

        btn_close = QPushButton("Đóng")
        btn_close.setFixedHeight(36); btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            f"QPushButton {{ background:{BLUE}; color:#fff; border:none;"
            " border-radius:8px; font-size:13px; font-weight:700; padding:0 24px; }}"
            f"QPushButton:hover {{ background:{BLUE_D}; }}"
        )
        btn_close.clicked.connect(dlg.accept)
        bar_lo.addWidget(btn_toggle); bar_lo.addWidget(btn_close)
        root.addWidget(bar)
        dlg.exec()

    # ══════════════════════════════════════════════════════════════
    #  HR DETAIL DIALOG
    # ══════════════════════════════════════════════════════════════
    def _show_hr_detail_dialog(self, hr_id: int, base_data: dict) -> None:
        """Full dialog: HR / nhà tuyển dụng profile."""
        BLUE = "#2563EB"; BLUE_D = "#1D4ED8"
        TXT_H = "#111827"; TXT_M = "#6B7280"; TXT_S = "#374151"
        CARD = "#FFFFFF"; BORDER = "#E5E7EB"; PAGE = "#F0F2F5"
        PURPLE = "#7C3AED"
        _AVATAR_COLORS = [
            ("#DBEAFE","#1D4ED8"), ("#D1FAE5","#065F46"),
            ("#F3E8FF","#6D28D9"), ("#FEF3C7","#92400E"),
            ("#FCE7F3","#9D174D"), ("#CFFAFE","#0E7490"),
        ]

        # Fetch full HR detail
        try:
            h = jobhub_api.admin_hr_detail(hr_id)
        except Exception:
            h = base_data

        company   = str(h.get("company_name") or base_data.get("company_name") or "—")
        email     = str(h.get("email")        or base_data.get("email")        or "—")
        phone     = str(h.get("phone")        or h.get("phone_number")         or "—")
        website   = str(h.get("website")      or h.get("company_website")      or "—")
        industry  = str(h.get("industry")     or h.get("company_type")         or "—")
        city      = str(h.get("city")         or h.get("location")             or "—")
        address   = str(h.get("address")      or h.get("company_address")      or "—")
        desc      = str(h.get("description")  or h.get("company_description")  or "")
        job_count = int(h.get("job_count")    or base_data.get("job_count")    or 0)
        is_active = bool(h.get("is_active",   base_data.get("is_active", True)))
        joined    = self._fmt_date(str(h.get("created_at") or base_data.get("created_at") or ""))

        dlg = QDialog(self.win)
        dlg.setWindowTitle(f"Hồ sơ nhà tuyển dụng – {company}")
        dlg.setMinimumWidth(660); dlg.setMinimumHeight(580)
        dlg.setStyleSheet(f"QDialog {{ background:{PAGE}; }}")
        root = QVBoxLayout(dlg)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # ── Hero banner (purple gradient feel) ────────────────────
        hero = QFrame(); hero.setFixedHeight(140)
        hero.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #4F46E5, stop:1 #7C3AED); border:none; }"
        )
        hero_lo = QHBoxLayout(hero)
        hero_lo.setContentsMargins(32, 0, 32, 0); hero_lo.setSpacing(20)

        initials = (company[:2].upper()) if company not in ("—","") else "?"
        bg, fg = _AVATAR_COLORS[hr_id % len(_AVATAR_COLORS)]
        av_big = QLabel(initials)
        av_big.setFixedSize(76, 76); av_big.setAlignment(Qt.AlignCenter)
        av_big.setStyleSheet(
            f"QLabel {{ background:{bg}; color:{fg}; font-size:22px; font-weight:800;"
            " border-radius:38px; border:3px solid rgba(255,255,255,0.4); }}"
        )
        hero_lo.addWidget(av_big)

        hero_info = QVBoxLayout(); hero_info.setSpacing(4)
        lbl_company = QLabel(company)
        lbl_company.setStyleSheet(
            "QLabel { color:#FFFFFF; font-size:18px; font-weight:800;"
            " background:transparent; border:none; }"
        )
        lbl_email = QLabel(email)
        lbl_email.setStyleSheet(
            "QLabel { color:rgba(255,255,255,0.8); font-size:13px;"
            " background:transparent; border:none; }"
        )
        pill_bg = "#DCFCE7" if is_active else "#FEE2E2"
        pill_fg = "#15803D" if is_active else "#B91C1C"
        pill_txt = "Đang hoạt động" if is_active else "Bị khóa"
        status_pill = QLabel(f"  {pill_txt}  ")
        status_pill.setFixedHeight(22)
        status_pill.setStyleSheet(
            f"QLabel {{ background:{pill_bg}; color:{pill_fg}; border-radius:4px;"
            " font-size:11px; font-weight:700; border:none; padding:0 6px; }}"
        )
        stat_jobs = QLabel(f"  {job_count} tin đăng  ")
        stat_jobs.setFixedHeight(22)
        stat_jobs.setStyleSheet(
            "QLabel { background:rgba(255,255,255,0.2); color:#FFFFFF; border-radius:4px;"
            " font-size:11px; font-weight:600; border:none; padding:0 6px; }"
        )
        pill_row = QHBoxLayout(); pill_row.setSpacing(6)
        pill_row.addWidget(status_pill); pill_row.addWidget(stat_jobs); pill_row.addStretch()
        hero_info.addWidget(lbl_company)
        hero_info.addWidget(lbl_email)
        hero_info.addLayout(pill_row)
        hero_lo.addLayout(hero_info, 1)
        root.addWidget(hero)

        # ── Scrollable body ───────────────────────────────────────
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background:{PAGE}; border:none; }}"
            "QScrollBar:vertical { background:#F0F2F5; width:6px; border-radius:3px; }"
            "QScrollBar::handle:vertical { background:#D1D5DB; border-radius:3px; }"
        )
        body_w = QWidget(); body_w.setStyleSheet(f"background:{PAGE};")
        body_lo = QVBoxLayout(body_w)
        body_lo.setContentsMargins(24, 20, 24, 20); body_lo.setSpacing(16)
        scroll.setWidget(body_w)
        root.addWidget(scroll, 1)

        def _info_card(title, fields):
            c = QFrame()
            c.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:12px; border:1px solid {BORDER}; }}"
            )
            _shadow(c, blur=12, dy=2, alpha=8)
            cl = QVBoxLayout(c); cl.setContentsMargins(20,16,20,16); cl.setSpacing(12)
            ttl = QLabel(title)
            ttl.setStyleSheet(
                f"QLabel {{ color:{TXT_H}; font-size:13px; font-weight:800;"
                " border:none; background:transparent; }}"
            )
            cl.addWidget(ttl)
            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{BORDER}; border:none;")
            cl.addWidget(div)
            grid = QGridLayout(); grid.setSpacing(10)
            grid.setColumnStretch(1, 1); grid.setColumnStretch(3, 1)
            for i, (lbl, val) in enumerate(fields):
                row_i = i // 2; col_base = (i % 2) * 2
                lbl_w = QLabel(lbl)
                lbl_w.setStyleSheet(
                    f"QLabel {{ color:{TXT_M}; font-size:12px; font-weight:600;"
                    " background:transparent; border:none; }}"
                )
                val_w = QLabel(str(val) if val and val != "—" else "—")
                val_w.setWordWrap(True)
                val_w.setStyleSheet(
                    f"QLabel {{ color:{TXT_S}; font-size:13px; font-weight:500;"
                    " background:transparent; border:none; }}"
                )
                grid.addWidget(lbl_w, row_i, col_base)
                grid.addWidget(val_w, row_i, col_base + 1)
            cl.addLayout(grid)
            return c

        body_lo.addWidget(_info_card("Thông tin tài khoản", [
            ("ID",             f"#{hr_id}"),
            ("Ngày tham gia",  joined),
            ("Tin đã đăng",    str(job_count)),
            ("Trạng thái",     pill_txt),
        ]))

        contact_fields = [
            ("Email",         email),
            ("Số điện thoại", phone),
        ]
        if website and website != "—": contact_fields.append(("Website",    website))
        if city     and city     != "—": contact_fields.append(("Thành phố", city))
        if industry and industry != "—": contact_fields.append(("Lĩnh vực",  industry))
        if address  and address  != "—": contact_fields.append(("Địa chỉ",   address))
        body_lo.addWidget(_info_card("Thông tin công ty", contact_fields))

        if desc:
            desc_card = QFrame()
            desc_card.setStyleSheet(
                f"QFrame {{ background:{CARD}; border-radius:12px; border:1px solid {BORDER}; }}"
            )
            _shadow(desc_card, blur=12, dy=2, alpha=8)
            d_lo = QVBoxLayout(desc_card); d_lo.setContentsMargins(20,16,20,16); d_lo.setSpacing(8)
            d_ttl = QLabel("Giới thiệu công ty")
            d_ttl.setStyleSheet(
                f"QLabel {{ color:{TXT_H}; font-size:13px; font-weight:800;"
                " border:none; background:transparent; }}"
            )
            d_div = QFrame(); d_div.setFixedHeight(1)
            d_div.setStyleSheet(f"background:{BORDER}; border:none;")
            d_txt = QLabel(desc); d_txt.setWordWrap(True)
            d_txt.setStyleSheet(
                f"QLabel {{ color:{TXT_S}; font-size:13px; line-height:1.6;"
                " background:transparent; border:none; }}"
            )
            d_lo.addWidget(d_ttl); d_lo.addWidget(d_div); d_lo.addWidget(d_txt)
            body_lo.addWidget(desc_card)

        body_lo.addStretch()

        # ── Bottom action bar ─────────────────────────────────────
        bar = QFrame(); bar.setFixedHeight(60)
        bar.setStyleSheet(
            f"QFrame {{ background:{CARD}; border:none; border-top:1px solid {BORDER}; }}"
        )
        bar_lo = QHBoxLayout(bar); bar_lo.setContentsMargins(24,0,24,0); bar_lo.setSpacing(10)
        bar_lo.addStretch()

        if is_active:
            btn_toggle = QPushButton("  Khóa tài khoản")
            btn_toggle.setIcon(QIcon(str(resource_icon("ic_lock.svg"))))
            btn_toggle.setStyleSheet(
                "QPushButton { background:#FEF2F2; color:#B91C1C; border:1px solid #FECACA;"
                " border-radius:8px; font-size:13px; font-weight:600; padding:0 18px; height:36px; }"
                "QPushButton:hover { background:#FEE2E2; }"
            )
            def _do_lock_hr():
                try:
                    jobhub_api.admin_lock_user(hr_id)
                    _toast(self.win, "Đã khóa tài khoản HR", success=True)
                except ApiError as e:
                    _toast(self.win, f"Thất bại: {e}", success=False)
                    return
                dlg.accept()
                QTimer.singleShot(0, self._hr_refresh_data)
            btn_toggle.clicked.connect(_do_lock_hr)
        else:
            btn_toggle = QPushButton("  Mở khóa tài khoản")
            btn_toggle.setIcon(QIcon(str(resource_icon("ic_unlock.svg"))))
            btn_toggle.setStyleSheet(
                "QPushButton { background:#F0FDF4; color:#15803D; border:1px solid #BBF7D0;"
                " border-radius:8px; font-size:13px; font-weight:600; padding:0 18px; height:36px; }"
                "QPushButton:hover { background:#DCFCE7; }"
            )
            def _do_unlock_hr():
                try:
                    jobhub_api.admin_unlock_user(hr_id)
                    _toast(self.win, "Đã mở khóa tài khoản HR", success=True)
                except ApiError as e:
                    _toast(self.win, f"Thất bại: {e}", success=False)
                    return
                dlg.accept()
                QTimer.singleShot(0, self._hr_refresh_data)
            btn_toggle.clicked.connect(_do_unlock_hr)

        btn_toggle.setIconSize(QSize(15, 15))
        btn_toggle.setCursor(Qt.PointingHandCursor)

        btn_close = QPushButton("Đóng")
        btn_close.setFixedHeight(36); btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet(
            "QPushButton { background:#4F46E5; color:#fff; border:none;"
            " border-radius:8px; font-size:13px; font-weight:700; padding:0 24px; }"
            "QPushButton:hover { background:#4338CA; }"
        )
        btn_close.clicked.connect(dlg.accept)
        bar_lo.addWidget(btn_toggle); bar_lo.addWidget(btn_close)
        root.addWidget(bar)
        dlg.exec()

    # ══════════════════════════════════════════════════════════════
    #  HR MANAGEMENT PAGE — table of HR companies
    # ══════════════════════════════════════════════════════════════
    def _fill_hr_page(self) -> None:
        """First call: build structure. Subsequent calls: refresh data only."""
        main = self._hr_widget
        if not main:
            return

        # ── If already built, just re-fetch and repopulate ────────────────
        if getattr(self, "_hr_built", False):
            self._hr_refresh_data()
            return

        self._hr_built     = True
        self._hr_page_idx  = 0
        self._hr_page_size = 10
        self._hr_all_data  = []
        self._hr_filtered  = []

        main_lo = main.layout()
        if not main_lo:
            return

        # Remove the .ui header (layout item at index 0 inside mainAreaLayout)
        while main_lo.count():
            item = main_lo.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                AdminDashboard._clear_layout(item.layout())

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setStyleSheet("background:transparent;")
        tb_v = QVBoxLayout(toolbar)
        tb_v.setContentsMargins(0, 0, 0, 12)
        tb_v.setSpacing(12)

        r1 = QHBoxLayout(); r1.setSpacing(10)
        r1.addStretch()

        btn_export = QPushButton("Xuất báo cáo")
        btn_export.setFixedHeight(36); btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet(
            "QPushButton { background:#FFFFFF; color:#374151;"
            " border:1px solid #D1D5DB; border-radius:8px;"
            " font-size:13px; font-weight:500; padding:0 16px; }"
            "QPushButton:hover { border-color:#2563EB; color:#2563EB; }"
        )
        btn_schedule = QPushButton("+ Lên lịch phỏng vấn")
        btn_schedule.setFixedHeight(36); btn_schedule.setCursor(Qt.PointingHandCursor)
        btn_schedule.setStyleSheet(
            "QPushButton { background:#2563EB; color:#FFFFFF; border:none;"
            " border-radius:8px; font-size:13px; font-weight:600; padding:0 16px; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        r1.addWidget(btn_export); r1.addWidget(btn_schedule)
        tb_v.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(8)
        search = QLineEdit()
        search.setPlaceholderText("Tìm kiếm công ty, email, số điện thoại…")
        search.setFixedHeight(38)
        search.setStyleSheet(
            "QLineEdit { background:#FFFFFF; border:1px solid #E5E7EB;"
            " border-radius:8px; padding:0 14px; font-size:13px; color:#374151; }"
            "QLineEdit:focus { border-color:#2563EB; }"
        )
        r2.addWidget(search, stretch=1)

        status_filter = QComboBox()
        status_filter.addItems(["Tất cả trạng thái", "Hoạt động", "Bị khóa"])
        status_filter.setFixedHeight(38); status_filter.setFixedWidth(170)
        _CB_SS = (
            "QComboBox { background:#FFFFFF; border:1px solid #E5E7EB;"
            " border-radius:8px; padding:0 12px; font-size:13px; color:#374151; }"
            "QComboBox::drop-down { border:none; width:20px; }"
            "QComboBox QAbstractItemView { background:#FFFFFF; border:1px solid #E5E7EB;"
            " selection-background-color:#EEF2FF; color:#374151; outline:none; }"
        )
        status_filter.setStyleSheet(_CB_SS)
        r2.addWidget(status_filter)

        sort_box = QComboBox()
        sort_box.addItems(["Mới nhất","Cũ nhất","Tên A–Z","Nhiều tin nhất"])
        sort_box.setFixedHeight(38); sort_box.setFixedWidth(140)
        sort_box.setStyleSheet(_CB_SS)
        r2.addWidget(sort_box)
        tb_v.addLayout(r2)
        main_lo.addWidget(toolbar)

        # ── Table card ────────────────────────────────────────────────────
        card = QFrame(); card.setObjectName("hrCard")
        card.setStyleSheet(
            "QFrame#hrCard { background:#FFFFFF; border-radius:12px;"
            " border:1px solid #E5E7EB; }"
        )
        _shadow(card, blur=16, dy=3, alpha=10)
        card_v = QVBoxLayout(card)
        card_v.setContentsMargins(0,0,0,0); card_v.setSpacing(0)

        table = QTableWidget(); table.setObjectName("hrCompanyTable")
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels([
            "ID","Tên công ty","Email",
            "Số điện thoại","Ngày tham gia",
            "Tin đã đăng","Trạng thái","Thao tác",
        ])
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(False)
        table.setStyleSheet(
            "QTableWidget { background:#FFFFFF; border:none; font-size:13px;"
            " color:#374151; gridline-color:transparent; outline:none; }"
            "QTableWidget::item { padding:0 14px; border-bottom:1px solid #F3F4F6; }"
            "QTableWidget::item:hover { background:#F8FAFF; }"
            "QTableWidget::item:selected { background:#EEF2FF; color:#1D4ED8; }"
            "QHeaderView::section { background:#F9FAFB; color:#6B7280;"
            " font-size:11px; font-weight:700; letter-spacing:0.5px;"
            " padding:12px 14px; border:none; border-bottom:2px solid #E5E7EB; }"
        )
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.Fixed)
        hdr.setSectionResizeMode(7, QHeaderView.Fixed)
        hdr.setStretchLastSection(False)
        table.setColumnWidth(6, 130)
        table.setColumnWidth(7, 118)
        card_v.addWidget(table)

        # ── Pagination footer ─────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(48)
        footer.setStyleSheet(
            "QFrame { background:#F9FAFB; border:none;"
            " border-top:1px solid #E5E7EB; }"
        )
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16,0,16,0); fl.setSpacing(8)
        count_lbl = QLabel()
        count_lbl.setStyleSheet(
            "QLabel { font-size:12px; color:#6B7280;"
            " background:transparent; border:none; }"
        )
        fl.addWidget(count_lbl); fl.addStretch()
        PAGE_BTN = (
            "QPushButton { background:#FFFFFF; color:#374151;"
            " border:1px solid #E5E7EB; border-radius:6px; font-size:12px;"
            " font-weight:500; min-width:32px; height:28px; padding:0 10px; }"
            "QPushButton:hover { border-color:#2563EB; color:#2563EB; }"
            "QPushButton:disabled { color:#D1D5DB; border-color:#F3F4F6; }"
        )
        btn_prev = QPushButton("← Trước")
        btn_prev.setCursor(Qt.PointingHandCursor)
        btn_prev.setStyleSheet(PAGE_BTN)
        page_lbl = QLabel()
        page_lbl.setStyleSheet(
            "QLabel { font-size:12px; color:#374151;"
            " background:transparent; border:none; padding:0 8px; }"
        )
        btn_next = QPushButton("Tiếp →")
        btn_next.setCursor(Qt.PointingHandCursor)
        btn_next.setStyleSheet(PAGE_BTN)
        fl.addWidget(btn_prev); fl.addWidget(page_lbl); fl.addWidget(btn_next)
        card_v.addWidget(footer)
        main_lo.addWidget(card, stretch=1)

        # ── Store refs ────────────────────────────────────────────────────
        self._hr_table     = table
        self._hr_search    = search
        self._hr_filter    = status_filter
        self._hr_sort      = sort_box
        self._hr_count_lbl = count_lbl
        self._hr_page_lbl  = page_lbl
        self._btn_prev     = btn_prev
        self._btn_next     = btn_next

        btn_prev.clicked.connect(self._hr_prev_page)
        btn_next.clicked.connect(self._hr_next_page)
        search.textChanged.connect(self._hr_apply_filter)
        status_filter.currentIndexChanged.connect(self._hr_apply_filter)
        sort_box.currentIndexChanged.connect(self._hr_apply_filter)

        # Initial data load
        self._hr_refresh_data()

    def _hr_refresh_data(self) -> None:
        """Re-fetch data from API and repopulate table (no widget rebuild)."""
        try:
            hrs = list(jobhub_api.admin_hr_overview())
        except ApiError as e:
            _toast(self.win, f"Lỗi tải dữ liệu: {e}", success=False)
            return
        self._hr_all_data = hrs
        self._hr_page_idx = 0
        self._hr_apply_filter()

    # ── HR table helpers ───────────────────────────────────────────────────

    def _hr_apply_filter(self) -> None:
        """Filter + sort _hr_all_data → _hr_filtered, then repopulate table."""
        q        = getattr(self, "_hr_search",  None)
        f_combo  = getattr(self, "_hr_filter",  None)
        s_combo  = getattr(self, "_hr_sort",    None)

        text   = q.text().strip().lower()       if q       else ""
        fval   = f_combo.currentIndex()         if f_combo else 0
        sval   = s_combo.currentIndex()         if s_combo else 0

        data: list = list(self._hr_all_data)

        # --- status filter (API trả về is_active: bool) ---
        if fval == 1:          # Hoạt động
            data = [r for r in data if bool(r.get("is_active", True))]
        elif fval == 2:        # Bị khóa
            data = [r for r in data if not bool(r.get("is_active", True))]

        # --- text search ---
        if text:
            def _match(r):
                return (
                    text in str(r.get("company_name","")).lower()
                    or text in str(r.get("email","")).lower()
                    or text in str(r.get("phone","")).lower()
                )
            data = [r for r in data if _match(r)]

        # --- sort ---
        if sval == 0:          # Mới nhất
            data.sort(key=lambda r: r.get("created_at",""), reverse=True)
        elif sval == 1:        # Cũ nhất
            data.sort(key=lambda r: r.get("created_at",""))
        elif sval == 2:        # Tên A–Z
            data.sort(key=lambda r: str(r.get("company_name","")).lower())
        elif sval == 3:        # Nhiều tin nhất
            data.sort(key=lambda r: int(r.get("job_count", 0)), reverse=True)

        self._hr_filtered  = data
        self._hr_page_idx  = 0
        self._populate_hr_table(self._hr_filtered)
        self._hr_update_pagination()

    def _populate_hr_table(self, hrs: list) -> None:
        """Fill the HR QTableWidget with one page of data."""
        table = getattr(self, "_hr_table", None)
        if table is None:
            return

        ps    = self._hr_page_size
        start = self._hr_page_idx * ps
        page  = hrs[start : start + ps]

        table.setRowCount(len(page))
        table.setRowCount(len(page))
        for row, hr in enumerate(page):
            table.setRowHeight(row, 52)

            # col 0 – ID
            id_item = QTableWidgetItem(str(hr.get("id", "")))
            id_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, id_item)

            # col 1 – Company name (with avatar circle)
            name_w  = QWidget()
            name_w.setStyleSheet("background:transparent;")
            name_h  = QHBoxLayout(name_w)
            name_h.setContentsMargins(14, 0, 14, 0)
            name_h.setSpacing(10)

            company = str(hr.get("company_name", "—"))
            initials = (company[:2].upper()) if company not in ("—", "") else "?"
            av = QLabel(initials)
            av.setFixedSize(34, 34)
            av.setAlignment(Qt.AlignCenter)
            # Pick a deterministic colour from the id
            _AVATAR_COLORS = [
                ("#DBEAFE","#1D4ED8"), ("#D1FAE5","#065F46"),
                ("#F3E8FF","#6D28D9"), ("#FEF3C7","#92400E"),
                ("#FCE7F3","#9D174D"), ("#CFFAFE","#0E7490"),
            ]
            bg, fg = _AVATAR_COLORS[int(hr.get("id", 0)) % len(_AVATAR_COLORS)]
            av.setStyleSheet(
                f"QLabel {{ background:{bg}; color:{fg}; font-size:12px;"
                " font-weight:700; border-radius:17px; border:none; }}"
            )
            name_lbl = QLabel(company)
            name_lbl.setStyleSheet(
                "QLabel { font-size:13px; font-weight:600; color:#111827;"
                " background:transparent; border:none; }"
            )
            name_h.addWidget(av)
            name_h.addWidget(name_lbl)
            name_h.addStretch()
            table.setCellWidget(row, 1, name_w)

            # col 2 – Email
            email_item = QTableWidgetItem(str(hr.get("email", "—")))
            email_item.setForeground(QColor("#6B7280"))
            table.setItem(row, 2, email_item)

            # col 3 – Phone
            ph_item = QTableWidgetItem(str(hr.get("phone", "—")))
            ph_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 3, ph_item)

            # col 4 – Joined date
            raw_date = str(hr.get("created_at", "—"))
            date_str = self._fmt_date(raw_date) if raw_date != "—" else "—"
            date_item = QTableWidgetItem(date_str)
            date_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 4, date_item)

            # col 5 – Job count
            jc_item = QTableWidgetItem(str(hr.get("job_count", 0)))
            jc_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 5, jc_item)

            # col 6 – Status pill  (API field: is_active: bool)
            is_active = bool(hr.get("is_active", True))
            if is_active:
                pill = _pill("Hoạt động", "#DCFCE7", "#15803D")
            else:
                pill = _pill("Bị khóa", "#FEE2E2", "#B91C1C")
            # Give explicit minimum so Qt knows the widget width
            pill.setMinimumWidth(96)
            pill_w = QWidget()
            pill_w.setStyleSheet("background:transparent;")
            pill_h = QHBoxLayout(pill_w)
            pill_h.setContentsMargins(8, 0, 8, 0)
            pill_h.setAlignment(Qt.AlignCenter)
            pill_h.addWidget(pill, alignment=Qt.AlignCenter)
            table.setCellWidget(row, 6, pill_w)

            # col 7 – 3 action buttons: view | unlock | lock
            act_w = QWidget()
            act_w.setStyleSheet("background:transparent;")
            act_h = QHBoxLayout(act_w)
            act_h.setContentsMargins(6, 0, 6, 0)
            act_h.setSpacing(2)

            _BTN_SS = (
                "QPushButton { background:transparent; border:none;"
                " border-radius:6px; }"
                "QPushButton:hover { background:#F3F4F6; }"
            )

            # ── View button ──────────────────────────────────────
            btn_view = QPushButton()
            btn_view.setFixedSize(30, 30)
            btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.setIcon(QIcon(str(resource_icon("ic_view.svg"))))
            btn_view.setIconSize(QSize(16, 16))
            btn_view.setStyleSheet(_BTN_SS)
            btn_view.setToolTip("Xem hồ sơ")
            hr_id = int(hr.get("id", 0))
            def _mk_view_hr(hid: int, hdata: dict):
                def _h(): self._show_hr_detail_dialog(hid, hdata)
                return _h
            btn_view.clicked.connect(_mk_view_hr(hr_id, hr))
            act_h.addWidget(btn_view)

            # ── Unlock button (mở khóa) ──────────────────────────
            btn_unlock = QPushButton()
            btn_unlock.setFixedSize(30, 30)
            btn_unlock.setCursor(Qt.PointingHandCursor)
            btn_unlock.setIcon(QIcon(str(resource_icon("ic_unlock.svg"))))
            btn_unlock.setIconSize(QSize(16, 16))
            btn_unlock.setStyleSheet(_BTN_SS)

            def _make_unlock(hid: int):
                def _handler():
                    try:
                        jobhub_api.admin_unlock_user(hid)
                        _toast(self.win, "Đã mở khóa tài khoản nhà tuyển dụng", success=True)
                    except ApiError as e:
                        _toast(self.win, f"Thao tác thất bại: {e}", success=False)
                        return
                    QTimer.singleShot(0, self._hr_refresh_data)
                return _handler

            btn_unlock.clicked.connect(_make_unlock(hr_id))
            act_h.addWidget(btn_unlock)

            # ── Lock button (khóa) ───────────────────────────────
            btn_lock = QPushButton()
            btn_lock.setFixedSize(30, 30)
            btn_lock.setCursor(Qt.PointingHandCursor)
            btn_lock.setIcon(QIcon(str(resource_icon("ic_lock.svg"))))
            btn_lock.setIconSize(QSize(16, 16))
            btn_lock.setStyleSheet(_BTN_SS)

            def _make_lock(hid: int):
                def _handler():
                    try:
                        jobhub_api.admin_lock_user(hid)
                        _toast(self.win, "Đã khóa tài khoản nhà tuyển dụng", success=True)
                    except ApiError as e:
                        _toast(self.win, f"Thao tác thất bại: {e}", success=False)
                        return
                    QTimer.singleShot(0, self._hr_refresh_data)
                return _handler

            btn_lock.clicked.connect(_make_lock(hr_id))
            act_h.addWidget(btn_lock)

            act_h.addStretch()
            table.setCellWidget(row, 7, act_w)

    def _hr_update_pagination(self) -> None:
        """Refresh the count label and prev/next button states."""
        total   = len(self._hr_filtered)
        ps      = self._hr_page_size
        pages   = max(1, (total + ps - 1) // ps)
        idx     = self._hr_page_idx
        start   = idx * ps + 1
        end     = min((idx + 1) * ps, total)

        count_lbl = getattr(self, "_hr_count_lbl", None)
        page_lbl  = getattr(self, "_hr_page_lbl",  None)
        btn_prev  = getattr(self, "_btn_prev",      None)
        btn_next  = getattr(self, "_btn_next",      None)

        if count_lbl:
            if total == 0:
                count_lbl.setText("Không có kết quả")
            else:
                count_lbl.setText(f"Hiển thị {start}\u2013{end} trong tổng số {total} công ty")
        if page_lbl:
            page_lbl.setText(f"Trang {idx + 1} / {pages}")
        if btn_prev:
            btn_prev.setEnabled(idx > 0)
        if btn_next:
            btn_next.setEnabled(idx < pages - 1)

    def _hr_prev_page(self) -> None:
        if self._hr_page_idx > 0:
            self._hr_page_idx -= 1
            self._populate_hr_table(self._hr_filtered)
            self._hr_update_pagination()

    def _hr_next_page(self) -> None:
        ps    = self._hr_page_size
        pages = max(1, (len(self._hr_filtered) + ps - 1) // ps)
        if self._hr_page_idx < pages - 1:
            self._hr_page_idx += 1
            self._populate_hr_table(self._hr_filtered)
            self._hr_update_pagination()

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                AdminDashboard._clear_layout(item.layout())


    # ── Sidebar light-theme redesign ───────────────────────────────────────
    def _restyle_sidebar(self) -> None:
        """Rebuild sidebar to white light-theme with blue left-border active indicator."""
        win = self.win

        sidebar = win.findChild(QFrame, "sidebar")
        if sidebar:
            sidebar.setStyleSheet(
                "QFrame#sidebar { background:#FFFFFF; border-right:1px solid #E5E7EB; }"
            )

        logo_sec = win.findChild(QFrame, "logoSection")
        if logo_sec:
            logo_sec.setStyleSheet(
                "QFrame#logoSection { background:transparent;"
                " border-bottom:1px solid #E5E7EB; }"
            )
        logo_icon = win.findChild(QLabel, "logoIconLabel")
        if logo_icon:
            logo_icon.setStyleSheet(
                "QLabel { background:#2563EB; border-radius:10px; border:none; }"
            )
        brand = win.findChild(QLabel, "brandLabel")
        if brand:
            brand.setStyleSheet(
                "QLabel { color:#2563EB; font-size:20px; font-weight:800;"
                " background:transparent; border:none; }"
            )
            if not win.findChild(QLabel, "_sidebarSubTitle") and logo_sec:
                logo_lay = logo_sec.layout()
                if logo_lay:
                    for i in range(logo_lay.count()):
                        item = logo_lay.itemAt(i)
                        if item and item.widget() == brand:
                            logo_lay.takeAt(i)
                            break
                    vb = QVBoxLayout()
                    vb.setSpacing(0)
                    vb.setContentsMargins(0, 0, 0, 0)
                    vb.addWidget(brand)
                    sub = QLabel("ADMIN CONSOLE")
                    sub.setObjectName("_sidebarSubTitle")
                    sub.setStyleSheet(
                        "QLabel { color:#9CA3AF; font-size:9px; font-weight:700;"
                        " letter-spacing:1.5px; background:transparent; border:none; }"
                    )
                    vb.addWidget(sub)
                    logo_lay.addLayout(vb)

        NAV_SS = (
            "QPushButton {"
            " background:transparent; color:#4B5563;"
            " border:none; border-left:3px solid transparent;"
            " border-radius:0px; padding:0px 16px 0px 17px;"
            " text-align:left; font-size:14px; font-weight:500; }"
            "QPushButton:hover { background:#F0F4FF; color:#2563EB; }"
            "QPushButton:checked { background:#EEF2FF; color:#2563EB;"
            " border-left:3px solid #2563EB; font-weight:700; }"
        )
        for oname in ("navDashboard", "navUserMgmt", "navJobMgmt",
                      "navHRMgmt", "navReports"):
            b = win.findChild(QPushButton, oname)
            if b:
                b.setStyleSheet(NAV_SS)

        nav_area = win.findChild(QFrame, "navArea")
        if nav_area and nav_area.layout():
            nav_area.layout().setContentsMargins(0, 16, 0, 8)

        dv = win.findChild(QFrame, "sidebarDivider")
        if dv:
            dv.setStyleSheet("QFrame { background:#E5E7EB; border:none; }")

        sidebar_layout = sidebar.layout() if sidebar else None

        if dv:
            dv.hide()

        admin_sec = win.findChild(QFrame, "adminSection")
        if admin_sec:
            admin_sec.setStyleSheet(
                "QFrame#adminSection { background:#F8FAFC;"
                " border-top:1px solid #E5E7EB; }"
            )
            admin_sec.setMinimumHeight(68)
            admin_sec.setMaximumHeight(68)

        av = win.findChild(QLabel, "sidebarAdminAvatar")
        if av:
            av.setStyleSheet(
                "QLabel { background:#2563EB; color:#FFFFFF; font-size:13px;"
                " font-weight:800; border-radius:18px; border:none; }"
            )
        nm = win.findChild(QLabel, "sidebarAdminName")
        if nm:
            nm.setStyleSheet(
                "QLabel { color:#111827; font-size:13px; font-weight:700;"
                " background:transparent; border:none; }"
            )
        em_lbl = win.findChild(QLabel, "sidebarAdminEmail")
        if em_lbl:
            em_lbl.setStyleSheet(
                "QLabel { color:#9CA3AF; font-size:11px; font-weight:400;"
                " background:transparent; border:none; }"
            )

        old_logout = win.findChild(QPushButton, "logoutButton")
        if old_logout:
            old_logout.hide()

        if sidebar_layout and not win.findChild(QPushButton, "_btnLogoutText"):
            btn_lo = QPushButton("  \u0110\u0103ng xu\u1ea5t")
            btn_lo.setObjectName("_btnLogoutText")
            btn_lo.setFixedHeight(44)
            btn_lo.setCursor(Qt.PointingHandCursor)
            btn_lo.setIcon(QIcon(str(resource_icon("ic_logout.svg"))))
            btn_lo.setIconSize(QSize(16, 16))
            btn_lo.setStyleSheet(
                "QPushButton { background:transparent; color:#EF4444; border:none;"
                " border-left:3px solid transparent; border-radius:0px;"
                " text-align:left; font-size:13px; font-weight:600;"
                " padding:0px 16px 0px 17px; }"
                "QPushButton:hover { background:#FEF2F2; }"
            )
            btn_lo.clicked.connect(self._logout)
            self.btn_logout = btn_lo
            sidebar_layout.addWidget(btn_lo)

    # Expose window
    def show(self) -> None:
        if self.win:
            self.win.show()

    def raise_(self) -> None:
        if self.win:
            self.win.raise_()
            self.win.activateWindow()
