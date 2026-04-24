from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
from ..theme import ADMIN_ACCENT
from .charts import make_line_chart_single
from .qss_loader import apply_theme_qss
from .ui_loader import load_ui
from .quanly_enhanced import (
    apply_nav_icons,
    apply_search_icon,
    make_status_badge,
    make_action_buttons,
    enhance_table,
    inject_pagination,
    apply_modern_qss,
)


class AdminDashboard:
    @staticmethod
    def _fmt_date(raw: str) -> str:
        if "T" in raw:
            return raw.split("T", 1)[0]
        return raw

    """Admin panel that loads QuanLyUser/HR/Jobs .ui and fills tables from Python mock data."""

    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout

        # Load the base admin_dashboard.ui for Dashboard page
        win = load_ui(resource_ui("admin_dashboard.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("admin_dashboard.ui phải là QMainWindow")
        self.win = win

        # Load sub-UIs for management pages (extract main content only)
        self._user_widget = self._load_sub_ui("QuanLyUser.ui", "userTable")
        self._hr_widget = self._load_sub_ui("QuanLyHR.ui", "hrTable")
        self._jobs_widget = self._load_sub_ui("QuanLyJobs.ui", "jobTable")

        self._bind_widgets()
        self._inject_management_pages()
        self._setup_navigation()
        self._setup_revenue_chart()
        self._load_dash()
        self._go(0)

    # ── Load sub-UI: extract mainArea widget ───────────────────────
    def _load_sub_ui(self, ui_name: str, table_name: str) -> QWidget:
        sub_win = load_ui(resource_ui(ui_name))
        main_area = sub_win.findChild(QWidget, "mainArea")
        if main_area:
            main_area.setParent(None)
            return main_area
        return sub_win

    # ── Inject management pages into stacked widget ────────────────
    def _inject_management_pages(self) -> None:
        if not self.stack:
            return
        # Add pages: index 1=User, 2=HR, 3=Jobs
        for widget in (self._user_widget, self._hr_widget, self._jobs_widget):
            self.stack.addWidget(widget)

        # Get table references from injected pages
        self.table_users = self._user_widget.findChild(QTableWidget, "userTable")
        self.table_hr = self._hr_widget.findChild(QTableWidget, "hrTable")
        self.table_jobs = self._jobs_widget.findChild(QTableWidget, "jobTable")

        # Get search/filter references
        self.search_user = self._user_widget.findChild(QLineEdit, "searchInput")
        self.search_hr = self._hr_widget.findChild(QLineEdit, "searchInput")
        self.search_jobs = self._jobs_widget.findChild(QLineEdit, "searchInput")
        self.filter_user = self._user_widget.findChild(QComboBox, "statusFilter")
        self.filter_hr = self._hr_widget.findChild(QComboBox, "statusFilter")
        self.filter_jobs = self._jobs_widget.findChild(QComboBox, "statusFilter")

        # Apply nav icons & search icons to sub-UIs
        for w in (self._user_widget, self._hr_widget, self._jobs_widget):
            search = w.findChild(QLineEdit, "searchInput")
            if search:
                apply_search_icon(search)

    def _bind_widgets(self) -> None:
        self.nav_dash = self.win.findChild(QPushButton, "navDashboard")
        self.nav_users = self.win.findChild(QPushButton, "navUserMgmt")
        self.nav_hr = self.win.findChild(QPushButton, "navHRMgmt")
        self.nav_jobs = self.win.findChild(QPushButton, "navJobMgmt")
        self.btn_logout = self.win.findChild(QPushButton, "logoutButton")
        self.page_title = self.win.findChild(QLabel, "pageTitle")
        self.page_subtitle = self.win.findChild(QLabel, "pageSubTitle")
        self.stack = self.win.findChild(QStackedWidget, "stackedPages")
        self.cards_row = self.win.findChild(QHBoxLayout, "horizontalLayout_cards")
        self.chart_placeholder = self.win.findChild(QLabel, "chartPlaceholder")
        self.month_filter = self.win.findChild(QComboBox, "monthFilter")

    def _setup_revenue_chart(self) -> None:
        """Setup revenue chart with month filter callback."""
        if self.month_filter:
            self.month_filter.currentIndexChanged.connect(self._update_revenue_chart)
    
    def _get_revenue_by_month(self, month: int = 0) -> tuple[list[str], list[float]]:
        """
        Generate revenue data by month.
        month=0: all months, month=1-12: specific month (daily breakdown)
        Returns: (labels, values) - values in millions (as float)
        """
        if month == 0:  # All months - show monthly totals
            labels = [f"T{i}" for i in range(1, 13)]
            values = [12.5, 18.3, 15.7, 20.2, 22.5, 18.9, 14.2, 16.5, 19.8, 22.1, 25.5, 21.3]
            return labels, values
        elif 1 <= month <= 12:  # Specific month - show daily breakdown
            # Generate daily revenue for the selected month
            days = 30
            base_value = 15 + month  # Different base for each month
            labels = [f"N{i}" for i in range(1, days + 1)]  # N = Ngày (Day)
            
            # Generate daily values with some variance (in millions)
            values = []
            for day in range(1, days + 1):
                # Create wave pattern with random-like variance
                daily_value = base_value + 5 * ((day % 7) - 3) / 7
                daily_value += (day % 3) - 1  # Add some variance
                values.append(daily_value)  # Keep as float in millions
            
            return labels, values
        
        return [], []
    
    def _update_revenue_chart(self) -> None:
        """Update chart based on selected month."""
        if not self.month_filter:
            return
        
        month_index = self.month_filter.currentIndex()
        labels, values = self._get_revenue_by_month(month_index)
        
        if not labels or not values:
            return
        
        # Find the chart frame and its layout
        chart_frame = self.win.findChild(QFrame, "chartFrame")
        if not chart_frame:
            return
        
        layout = chart_frame.layout()
        if not layout or not isinstance(layout, QVBoxLayout):
            return
        
        # Remove old chart widget if exists (keep title/header, remove canvas)
        for i in range(layout.count() - 1, -1, -1):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # Keep header layout/title, remove chart canvas
                if widget.objectName() not in ["chartTitle"]:
                    layout.removeWidget(widget)
                    widget.deleteLater()
        
        # Create and add new chart
        canvas = make_line_chart_single(
            [str(x) for x in labels], 
            [int(x * 1000000) if isinstance(x, (int, float)) else int(x) for x in values],
            "#6366F1"
        )
        layout.addWidget(canvas)

    def _setup_navigation(self) -> None:
        self._nav_group = QButtonGroup(self.win)
        nav_buttons = [
            (self.nav_dash, "ic_dashboard.svg"),
            (self.nav_users, "ic_users.svg"),
            (self.nav_hr, "ic_hr.svg"),
            (self.nav_jobs, "ic_jobs.svg"),
        ]
        for idx, (btn, icon_name) in enumerate(nav_buttons):
            if btn:
                btn.setCheckable(True)
                btn.setIcon(QIcon(str(resource_icon(icon_name))))
                btn.setIconSize(QSize(20, 20))
                self._nav_group.addButton(btn)
                btn.clicked.connect(lambda checked, i=idx: self._go(i))
        if self.btn_logout:
            self.btn_logout.setIcon(QIcon(str(resource_icon("ic_logout.svg"))))
            self.btn_logout.setIconSize(QSize(20, 20))
            self.btn_logout.clicked.connect(self._logout)

    def _go(self, index: int) -> None:
        if self.stack:
            # page 0 = Dashboard, 1 = User, 2 = HR, 3 = Jobs
            self.stack.setCurrentIndex(index)

        nav_buttons = [self.nav_dash, self.nav_users, self.nav_hr, self.nav_jobs]
        for i, btn in enumerate(nav_buttons):
            if btn:
                btn.setChecked(i == index)

        titles = ["Bảng điều khiển Admin", "Quản lý Người dùng", "Quản lý Nhà tuyển dụng", "Quản lý Công việc"]
        subtitles = [
            "Tổng quan hệ thống quản lý việc làm",
            "Danh sách người tìm việc trên hệ thống",
            "Danh sách nhà tuyển dụng trên hệ thống",
            "Danh sách tất cả tin tuyển dụng trên hệ thống",
        ]
        if self.page_title and index < len(titles):
            self.page_title.setText(titles[index])
        if self.page_subtitle and index < len(subtitles):
            self.page_subtitle.setText(subtitles[index])

        if index == 0:
            self._load_dash()
        elif index == 1:
            self._fill_user_table()
        elif index == 2:
            self._fill_hr_table()
        elif index == 3:
            self._fill_jobs_table()

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    # ── Dashboard page ─────────────────────────────────────────────
    def _load_dash(self) -> None:
        try:
            data = jobhub_api.admin_dashboard()
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return
        cards_data = data.get("cards") or {}
        if self.cards_row:
            while self.cards_row.count():
                item = self.cards_row.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            items = [
                ("ic_user.svg", "Tổng Người dùng", f"{cards_data.get('users', 0):,}"),
                ("ic_hr_stat.svg", "Tổng Nhà tuyển dụng", str(cards_data.get("hr", 0))),
                ("ic_jobs.svg", "Tổng Công việc", str(cards_data.get("jobs", 0))),
                ("ic_activity.svg", "Hoạt động hôm nay", str(cards_data.get("activity_today", 0))),
            ]
            for icon_name, title, val in items:
                sc = load_ui(resource_ui("stat_card.ui"))
                lbl_icon = sc.findChild(QLabel, "labelStatIcon")
                if lbl_icon:
                    lbl_icon.setPixmap(QIcon(str(resource_icon(icon_name))).pixmap(QSize(24, 24)))
                lbl_t = sc.findChild(QLabel, "labelStatTitle")
                lbl_v = sc.findChild(QLabel, "labelStatValue")
                lbl_h = sc.findChild(QLabel, "labelStatHint")
                if lbl_t:
                    lbl_t.setText(title)
                if lbl_v:
                    lbl_v.setText(val)
                if lbl_h:
                    lbl_h.setText("")
                self.cards_row.addWidget(sc)

        # Load revenue chart
        self._update_revenue_chart()

    # ── Fill User table from mock data ─────────────────────────────
    def _fill_user_table(self) -> None:
        table = self.table_users
        if not table:
            return
        try:
            users = list(jobhub_api.admin_candidate_overview())
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return
        table.setRowCount(0)
        table.setRowCount(len(users))
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            ["ID", "Họ tên", "Email", "Số điện thoại", "Ngày tham gia", "Đơn ứng tuyển", "Trạng thái", "Thao tác"]
        )
        for row, u in enumerate(users):
            table.setItem(row, 0, QTableWidgetItem(f"#{u['id']}"))
            name_item = QTableWidgetItem(u.get("full_name", ""))
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            table.setItem(row, 1, name_item)
            table.setItem(row, 2, QTableWidgetItem(f"✉ {u.get('email', '')}"))
            table.setItem(row, 3, QTableWidgetItem(u.get("phone", "")))
            table.setItem(row, 4, QTableWidgetItem(f"📅 {self._fmt_date(str(u.get('created_at', '')))}"))
            table.setItem(row, 5, QTableWidgetItem(str(u.get("applications_count", 0))))
            status = "Hoạt động" if u.get("is_active", True) else "Bị khóa"
            table.setItem(row, 6, QTableWidgetItem(status))
            table.setItem(row, 7, QTableWidgetItem(""))

        enhance_table(table, status_col=6, action_col=7, stretch_cols=[1, 2], show_lock_btn=True)

    # ── Fill HR table from mock data ───────────────────────────────
    def _fill_hr_table(self) -> None:
        table = self.table_hr
        if not table:
            return
        try:
            hrs = list(jobhub_api.admin_hr_overview())
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return
        table.setRowCount(0)
        table.setRowCount(len(hrs))
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            ["ID", "Tên công ty", "Email", "Số điện thoại", "Ngày tham gia", "Tin đã đăng", "Trạng thái", "Thao tác"]
        )
        for row, h in enumerate(hrs):
            table.setItem(row, 0, QTableWidgetItem(f"#{h['id']}"))
            name_item = QTableWidgetItem(h.get("company_name", ""))
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            table.setItem(row, 1, name_item)
            table.setItem(row, 2, QTableWidgetItem(f"✉ {h.get('email', '')}"))
            table.setItem(row, 3, QTableWidgetItem(h.get("phone", "")))
            table.setItem(row, 4, QTableWidgetItem(f"📅 {self._fmt_date(str(h.get('created_at', '')))}"))
            table.setItem(row, 5, QTableWidgetItem(f"📋 {h.get('jobs_count', 0)}"))
            status = "Hoạt động" if h.get("is_active", True) else "Bị khóa"
            table.setItem(row, 6, QTableWidgetItem(status))
            table.setItem(row, 7, QTableWidgetItem(""))

        enhance_table(table, status_col=6, action_col=7, stretch_cols=[1, 2], show_lock_btn=True)

    _ADMIN_JOB_STATUS_MAP = {
        "published":        "Đang tuyển",
        "draft":            "Bản nháp",
        "closed":           "Đã đóng",
        "rejected":         "Vi phạm",
        "pending_approval": "Chờ duyệt",
    }

    # ── Fill Jobs table from shared JOB_STORE ──────────────────────
    def _fill_jobs_table(self) -> None:
        table = self.table_jobs
        if not table:
            return
        try:
            jobs = list(jobhub_api.admin_all_jobs())
        except ApiError as e:
            QMessageBox.warning(self.win, "Lỗi", str(e))
            return
        table.setRowCount(0)
        table.setRowCount(len(jobs))
        table.setColumnCount(10)
        table.setHorizontalHeaderLabels(
            ["ID", "Vị trí", "Công ty", "Địa điểm", "Lương", "Loại hình",
             "Ứng viên", "Ngày đăng", "Trạng thái", "Thao tác"]
        )
        for row, j in enumerate(jobs):
            table.setItem(row, 0, QTableWidgetItem(f"#{j['id']}"))
            title_item = QTableWidgetItem(j.get("title", ""))
            title_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            table.setItem(row, 1, title_item)
            table.setItem(row, 2, QTableWidgetItem(j.get("company_name", "")))
            table.setItem(row, 3, QTableWidgetItem(j.get("location", "")))
            table.setItem(row, 4, QTableWidgetItem(j.get("salary_text", "")))
            table.setItem(row, 5, QTableWidgetItem(j.get("job_type", "")))
            table.setItem(row, 6, QTableWidgetItem(f"👥 {j.get('applicants_count', 0)}"))
            table.setItem(row, 7, QTableWidgetItem(f"📅 {self._fmt_date(str(j.get('created_at', '')))}"))
            status_vi = self._ADMIN_JOB_STATUS_MAP.get(j.get("status", ""), j.get("status", ""))
            table.setItem(row, 8, QTableWidgetItem(status_vi))
            table.setItem(row, 9, QTableWidgetItem(""))

        enhance_table(table, status_col=8, action_col=9, stretch_cols=[1, 2], show_lock_btn=False)

        # Override action column with context-aware admin buttons
        for row, j in enumerate(jobs):
            table.setCellWidget(row, 9, self._make_admin_job_actions(j["id"], j.get("status", "")))

    def _make_admin_job_actions(self, job_id: int, status: str) -> QWidget:
        """Action buttons cho admin: duyệt/từ chối (chờ duyệt) hoặc xoá."""
        wrap = QWidget()
        wrap.setStyleSheet("background:transparent;")
        lo = QHBoxLayout(wrap)
        lo.setContentsMargins(6, 0, 6, 0)
        lo.setSpacing(4)
        lo.setAlignment(Qt.AlignVCenter)

        def _btn(label: str, bg: str, hover: str) -> QPushButton:
            b = QPushButton(label)
            b.setFixedHeight(28)
            b.setMinimumWidth(60)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:{bg};color:#fff;"
                "font-size:11px;font-weight:700;border:none;"
                "border-radius:6px;padding:0 8px;}}"
                f"QPushButton:hover{{background:{hover};}}"
            )
            return b

        if status == "pending_approval":
            btn_approve = _btn("✓ Duyệt",  "#059669", "#047857")
            btn_reject  = _btn("✗ Từ chối", "#dc2626", "#b91c1c")

            def _approve(_jid=job_id):
                try:
                    jobhub_api.admin_approve_job(_jid)
                except ApiError as e:
                    QMessageBox.warning(self.win, "Lỗi", str(e))
                    return
                self._fill_jobs_table()

            def _reject(_jid=job_id):
                try:
                    jobhub_api.admin_reject_job(_jid)
                except ApiError as e:
                    QMessageBox.warning(self.win, "Lỗi", str(e))
                    return
                self._fill_jobs_table()

            btn_approve.clicked.connect(_approve)
            btn_reject.clicked.connect(_reject)
            lo.addWidget(btn_approve)
            lo.addWidget(btn_reject)
        else:
            btn_del = _btn("🗑 Xoá", "#ef4444", "#dc2626")

            def _delete(_jid=job_id):
                ret = QMessageBox.question(
                    self.win, "Xác nhận xoá",
                    f"Xoá tin #{_jid}?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret == QMessageBox.Yes:
                    try:
                        jobhub_api.admin_delete_job(_jid)
                    except ApiError as e:
                        QMessageBox.warning(self.win, "Lỗi", str(e))
                        return
                    self._fill_jobs_table()

            btn_del.clicked.connect(_delete)
            lo.addWidget(btn_del)

        lo.addStretch()
        return wrap

    def show(self) -> None:
        if self.win:
            self.win.show()

    def raise_(self) -> None:
        if self.win:
            self.win.raise_()
            self.win.activateWindow()
