from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt
<<<<<<< HEAD
from PySide6.QtGui import QIcon, QFont
=======
from PySide6.QtGui import QIcon
>>>>>>> bae1316834b693c78f435307b0ccca0f2b8732b9
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..client import jobhub_api
from ..client.jobhub_api import ApiError
<<<<<<< HEAD
from .. import mock_data
=======
>>>>>>> bae1316834b693c78f435307b0ccca0f2b8732b9
from ..paths import resource_icon, resource_ui
from ..session_store import clear_session
from ..theme import HR_ACCENT
from .charts import make_bar_chart
from .qss_loader import apply_theme_qss
from .ui_loader import load_ui
from .quanly_enhanced import (
    apply_nav_icons,
    enhance_table,
    make_status_badge,
    make_action_buttons,
)


class HRDashboard:
    """HR Panel that loads hr_dashboard.ui and fills tables from Python mock data."""

    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout
        win = load_ui(resource_ui("hr_dashboard.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("hr_dashboard.ui phải là QMainWindow")
        self.win = win

        self._bind_widgets()
        self._setup_navigation()
        self._go(0)

    def _bind_widgets(self) -> None:
        # Navigation
        self.nav_dash = self.win.findChild(QPushButton, "navDash")
        self.nav_post = self.win.findChild(QPushButton, "navPost")
        self.nav_jobs = self.win.findChild(QPushButton, "navJobs")
        self.nav_cands = self.win.findChild(QPushButton, "navCands")
        self.btn_logout = self.win.findChild(QPushButton, "btnLogout")
        
        # Header info
        self.page_title = self.win.findChild(QLabel, "pageTitle")
        self.page_subtitle = self.win.findChild(QLabel, "pageSubTitle")
        self.hr_name = self.win.findChild(QLabel, "hrName")
        self.hr_avatar = self.win.findChild(QLabel, "hrAvatar")
        
        # Dashboard elements
        self.stack = self.win.findChild(QStackedWidget, "stackedPages")
        self.cards_row = self.win.findChild(QHBoxLayout, "horizontalLayout_cards")
        self.chart_holder = self.win.findChild(QWidget, "chartHolder")
        
        # Job Posting elements
        self.line_title = self.win.findChild(QLineEdit, "lineJobTitle")
        self.plain_desc = self.win.findChild(QPlainTextEdit, "plainJobDesc")
        self.line_salary = self.win.findChild(QLineEdit, "lineSalary")
        self.line_location = self.win.findChild(QLineEdit, "lineLocation")
        self.line_job_type = self.win.findChild(QLineEdit, "lineJobType")
        self.btn_draft = self.win.findChild(QPushButton, "btnSaveDraft")
        self.btn_submit_new = self.win.findChild(QPushButton, "btnSubmitJob")
        self.label_hr_status = self.win.findChild(QLabel, "labelHrStatus")
        
        # Tables
        self.table_jobs = self.win.findChild(QTableWidget, "tableJobs")
        self.table_cands = self.win.findChild(QTableWidget, "tableCands")

    def _setup_navigation(self) -> None:
        self._nav_group = QButtonGroup(self.win)
        nav_buttons = [
            (self.nav_dash, "ic_dashboard.svg"),
            (self.nav_post, "ic_edit.svg"),
            (self.nav_jobs, "ic_jobs.svg"),
            (self.nav_cands, "ic_users.svg"),
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

        if self.btn_draft:
            self.btn_draft.clicked.connect(lambda: self._create_job(draft=True))
        if self.btn_submit_new:
            self.btn_submit_new.clicked.connect(lambda: self._create_job(draft=False))

        # Set HR name and brand icon
        if self.hr_name:
            self.hr_name.setText("TechCorp HR")
        if self.win.findChild(QLabel, "brandTitle"):
            lbl_brand = self.win.findChild(QLabel, "brandTitle")
            lbl_brand.setText(" JobHub")
            lbl_brand.setPixmap(QIcon(str(resource_icon("ic_hr.svg"))).pixmap(QSize(28, 28)))
            lbl_brand.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # Use a layout to keep text next to icon if needed, 
            # but QLabel.setPixmap replaces text. 
            # Better: use a layout for brandTitle or just use text with emoji-replacement SVG.
            # Actually, I'll just set the icon on the nav buttons which I already did.
            # For brandTitle, I'll keep it as text or use a separate label for icon.

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)
        
        nav_buttons = [self.nav_dash, self.nav_post, self.nav_jobs, self.nav_cands]
        for i, btn in enumerate(nav_buttons):
            if btn:
                btn.setChecked(i == index)
        
        titles = ["Bảng điều khiển", "Đăng tin mới", "Quản lý tin đăng", "Đơn ứng tuyển"]
        subtitles = [
            "Theo dõi hiệu quả tuyển dụng của bạn",
            "Tạo tin tuyển dụng mới cho ứng viên",
            "Xem và chỉnh sửa các tin tuyển dụng đang hoạt động",
            "Quản lý các ứng viên đã ứng tuyển vào công việc của bạn"
        ]
        
        if self.page_title and index < len(titles):
            self.page_title.setText(titles[index])
        if self.page_subtitle and index < len(subtitles):
            self.page_subtitle.setText(subtitles[index])
            
        if index == 0:
            self._load_dash()
        elif index == 1:
            self._update_hr_status()
        elif index == 2:
            self._fill_jobs_table()
        elif index == 3:
            self._fill_cands_table()

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    # ── Dashboard Page ─────────────────────────────────────────────
    def _load_dash(self) -> None:
        # Use mock data
        data = mock_data.MOCK_HR_DASHBOARD
        cards = data.get("cards") or {}
        labels = data.get("labels") or []
        values = data.get("values") or []

        if self.cards_row:
            while self.cards_row.count():
                it = self.cards_row.takeAt(0)
                if it.widget():
                    it.widget().deleteLater()
            
            items = [
<<<<<<< HEAD
                ("ic_jobs.svg", "Tin đang đăng", str(cards.get("jobs", 0)), "+2 tuần này"),
                ("ic_users.svg", "Tổng ứng viên", str(cards.get("candidates", 0)), "+15 mới"),
                ("ic_view.svg", "Lượt xem tin", f"{cards.get('views', 0):,}", "+12% xu hướng"),
                ("ic_trend.svg", "Tỷ lệ phản hồi", f"{cards.get('response_rate', 0)}%", "Tối ưu"),
            ]
            for icon_name, title, val, hint in items:
                sc = load_ui(resource_ui("stat_card.ui"))
                lbl_icon = sc.findChild(QLabel, "labelStatIcon")
                if lbl_icon:
                    lbl_icon.setPixmap(QIcon(str(resource_icon(icon_name))).pixmap(QSize(24, 24)))
                    lbl_icon.setText("")
                lbl_t = sc.findChild(QLabel, "labelStatTitle")
                lbl_v = sc.findChild(QLabel, "labelStatValue")
                lbl_h = sc.findChild(QLabel, "labelStatHint")
                if lbl_t: lbl_t.setText(title)
                if lbl_v: lbl_v.setText(val)
                if lbl_h: lbl_h.setText(hint)
=======
                ("ic_jobs.svg", "Tổng tin đăng", str(cards.get("jobs", 0)), "+3 tuần này"),
                ("ic_users.svg", "Tổng ứng viên", str(cards.get("candidates", 0)), "+12 tuần này"),
                (
                    "ic_view.svg",
                    "Lượt xem (ước lượng)",
                    f"{int(cards.get('views', 0) or 0):,}".replace(",", "."),
                    "+245 tuần này",
                ),
                ("ic_trend.svg", "Tỷ lệ phản hồi", f"{cards.get('response_rate', 0)}%", "+5% so với tháng trước"),
            ]
            for icon_name, title, val, hint in items:
                sc = load_ui(resource_ui("stat_card.ui"))
                ic = sc.findChild(QLabel, "labelStatIcon")
                if ic:
                    ic.setPixmap(QIcon(str(resource_icon(icon_name))).pixmap(QSize(24, 24)))
                    ic.setText("")
                t = sc.findChild(QLabel, "labelStatTitle")
                v = sc.findChild(QLabel, "labelStatValue")
                h = sc.findChild(QLabel, "labelStatHint")
                if ic:
                    ic.setText(icon)
                if t:
                    t.setText(title)
                if v:
                    v.setText(val)
                if h:
                    h.setText(hint)
>>>>>>> bae1316834b693c78f435307b0ccca0f2b8732b9
                self.cards_row.addWidget(sc)

        if self.chart_holder:
            lay = self.chart_holder.layout()
            if not lay:
                lay = QVBoxLayout(self.chart_holder)
                self.chart_holder.setLayout(lay)
            while lay.count():
                it = lay.takeAt(0)
                if it.widget(): it.widget().deleteLater()
            
            canvas = make_bar_chart([str(x) for x in labels], [int(x) for x in values], "#6366F1")
            lay.addWidget(canvas)

    # ── Job Posting Page ───────────────────────────────────────────
    def _update_hr_status(self) -> None:
        if self.label_hr_status:
            self.label_hr_status.setText("Tài khoản HR của bạn đã được xác thực. Bạn có thể đăng và quản lý tin.")

    def _create_job(self, draft: bool) -> None:
        title = self.line_title.text().strip() if self.line_title else ""
        if not title:
            QMessageBox.warning(self.win, "Cảnh báo", "Vui lòng nhập tiêu đề công việc.")
            return
        
        msg = "Đã lưu bản nháp." if draft else "Đã đăng tin tuyển dụng thành công!"
        QMessageBox.information(self.win, "Thành công", msg)
        self._go(2) # Go to Manage Jobs

    # ── Manage Jobs Table ──────────────────────────────────────────
    def _fill_jobs_table(self) -> None:
        if not self.table_jobs: return
        jobs = mock_data.MOCK_HR_JOBS
        
        self.table_jobs.setRowCount(0)
        self.table_jobs.setRowCount(len(jobs))
        self.table_jobs.setColumnCount(4)
        self.table_jobs.setHorizontalHeaderLabels(["ID", "Tiêu đề công việc", "Trạng thái", "Thao tác"])
        
        status_map = {
            "draft": "Nháp",
            "pending_approval": "Chờ duyệt",
            "published": "Đang tuyển",
            "rejected": "Vi phạm",
        }
        
        for row, j in enumerate(jobs):
            self.table_jobs.setItem(row, 0, QTableWidgetItem(f"#{j['id']}"))
            title_item = QTableWidgetItem(j.get("title", ""))
            title_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table_jobs.setItem(row, 1, title_item)
            
            st_raw = j.get("status", "draft")
            status_text = status_map.get(st_raw, st_raw)
            self.table_jobs.setItem(row, 2, QTableWidgetItem(status_text))
            self.table_jobs.setItem(row, 3, QTableWidgetItem(""))

        enhance_table(self.table_jobs, status_col=2, action_col=3, stretch_cols=[1])

    # ── Applications Table ─────────────────────────────────────────
    def _fill_cands_table(self) -> None:
        if not self.table_cands: return
        apps = mock_data.MOCK_HR_APPLICATIONS
        
        self.table_cands.setRowCount(0)
        self.table_cands.setRowCount(len(apps))
        self.table_cands.setColumnCount(6)
        self.table_cands.setHorizontalHeaderLabels(["Ứng viên", "Email", "Vị trí ứng tuyển", "Trạng thái", "CV", "Thao tác"])
        
        status_map = {
            "pending": "Chờ duyệt",
            "reviewed": "Hoạt động",
            "rejected": "Vi phạm",
        }
        
        for row, a in enumerate(apps):
            name_item = QTableWidgetItem(a.get("candidate_name", ""))
            name_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table_cands.setItem(row, 0, name_item)
            self.table_cands.setItem(row, 1, QTableWidgetItem(a.get("candidate_email", "")))
            self.table_cands.setItem(row, 2, QTableWidgetItem(a.get("job_title", "")))
            
            st_raw = a.get("status", "pending")
            status_text = status_map.get(st_raw, st_raw)
            self.table_cands.setItem(row, 3, QTableWidgetItem(status_text))
            
            # Use SVG Icon for CV
            cv_item = QTableWidgetItem(a.get('cv_name', ''))
            cv_item.setIcon(QIcon(str(resource_icon("ic_folder.svg"))))
            self.table_cands.setItem(row, 4, cv_item)
            
            self.table_cands.setItem(row, 5, QTableWidgetItem(""))

        enhance_table(self.table_cands, status_col=3, action_col=5, stretch_cols=[0, 2])



    def show(self) -> None:
        self.win.show()

    def raise_(self) -> None:
        self.win.raise_()
        self.win.activateWindow()
