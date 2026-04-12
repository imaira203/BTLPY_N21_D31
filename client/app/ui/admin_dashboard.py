from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
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
from ..paths import resource_ui
from ..session_store import clear_session
from ..theme import ADMIN_ACCENT
from .charts import make_line_chart_single
from .qss_loader import apply_theme_qss
from .ui_loader import load_ui


class AdminDashboard:
    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout
        win = load_ui(resource_ui("admin_dashboard.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("admin_dashboard.ui phải là QMainWindow")
        self.win = win
        apply_theme_qss(self.win, "admin_shell")

        self.stack = win.findChild(QStackedWidget, "stackedPages")
        self.nav_dash = win.findChild(QPushButton, "navDash")
        self.nav_users = win.findChild(QPushButton, "navUsers")
        self.nav_hr = win.findChild(QPushButton, "navHr")
        self.nav_jobs = win.findChild(QPushButton, "navJobs")
        self.btn_logout = win.findChild(QPushButton, "btnLogout")

        self.chart_holder = win.findChild(QWidget, "chartHolder")
        self.cards_row = win.findChild(QHBoxLayout, "horizontalLayout_cards")

        self.table_users = win.findChild(QTableWidget, "tableUsers")
        self.table_hr = win.findChild(QTableWidget, "tableHr")
        self.table_jobs = win.findChild(QTableWidget, "tableJobs")

        self._nav_group = QButtonGroup(self.win)
        for b in (self.nav_dash, self.nav_users, self.nav_hr, self.nav_jobs):
            if b:
                b.setCheckable(True)
                self._nav_group.addButton(b)
        if self.nav_dash:
            self.nav_dash.clicked.connect(lambda: self._go(0))
        if self.nav_users:
            self.nav_users.clicked.connect(lambda: self._go(1))
        if self.nav_hr:
            self.nav_hr.clicked.connect(lambda: self._go(2))
        if self.nav_jobs:
            self.nav_jobs.clicked.connect(lambda: self._go(3))
        if self.btn_logout:
            self.btn_logout.clicked.connect(self._logout)

        self._load_dash()
        self._load_users()
        self._load_pending_hr()
        self._load_pending_jobs()

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)
        for i, b in enumerate([self.nav_dash, self.nav_users, self.nav_hr, self.nav_jobs]):
            if b:
                b.setChecked(i == index)

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    def _load_dash(self) -> None:
        try:
            data = jobhub_api.admin_dashboard()
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        cards = data.get("cards") or {}
        labels = data.get("labels") or []
        values = data.get("values") or []
        if self.cards_row:
            while self.cards_row.count():
                it = self.cards_row.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            items = [
                ("👤", "Tổng Users", f"{cards.get('users', 0):,}".replace(",", "."), "+52 tháng này"),
                ("🏢", "Tổng HR", str(cards.get("hr", 0)), "+8 tháng này"),
                ("💼", "Tổng Jobs", str(cards.get("jobs", 0)), "+23 tháng này"),
                ("⚡", "Hoạt động hôm nay", str(cards.get("activity_today", 0)), "Đang hoạt động"),
            ]
            for icon, title, val, hint in items:
                sc = load_ui(resource_ui("stat_card.ui"))
                ic = sc.findChild(QLabel, "labelStatIcon")
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
                self.cards_row.addWidget(sc)
        if self.chart_holder and labels and values:
            lay = self.chart_holder.layout()
            if lay is None:
                lay = QVBoxLayout(self.chart_holder)
                self.chart_holder.setLayout(lay)
            while lay.count():
                it = lay.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            canvas = make_line_chart_single([str(x) for x in labels], [int(x) for x in values], ADMIN_ACCENT)
            lay.addWidget(canvas)

    def _load_users(self) -> None:
        if not self.table_users:
            return
        try:
            users = jobhub_api.admin_list_users()
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self.table_users.setColumnCount(3)
        self.table_users.setHorizontalHeaderLabels(["ID", "Email", "Vai trò"])
        self.table_users.setRowCount(len(users))
        for i, u in enumerate(users):
            self.table_users.setItem(i, 0, QTableWidgetItem(str(u.get("id", ""))))
            self.table_users.setItem(i, 1, QTableWidgetItem(u.get("email", "")))
            role = u.get("role", "")
            self.table_users.setItem(i, 2, QTableWidgetItem(str(role)))

    def _load_pending_hr(self) -> None:
        if not self.table_hr:
            return
        try:
            rows = jobhub_api.admin_pending_hr()
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self.table_hr.setColumnCount(3)
        self.table_hr.setHorizontalHeaderLabels(["ID", "Email", "Hành động"])
        self.table_hr.setRowCount(len(rows))
        for i, u in enumerate(rows):
            uid = u["id"]
            self.table_hr.setItem(i, 0, QTableWidgetItem(str(uid)))
            self.table_hr.setItem(i, 1, QTableWidgetItem(u.get("email", "")))
            cell = load_ui(resource_ui("action_buttons.ui"))
            bp = cell.findChild(QPushButton, "btnPrimary")
            bs = cell.findChild(QPushButton, "btnSecondary")
            if bp:
                bp.setText("Duyệt")
                bp.clicked.connect(lambda _=False, x=uid: self._approve_hr(x))
            if bs:
                bs.setText("Từ chối")
                bs.clicked.connect(lambda _=False, x=uid: self._reject_hr(x))
            self.table_hr.setCellWidget(i, 2, cell)

    def _approve_hr(self, user_id: int) -> None:
        try:
            jobhub_api.admin_approve_hr(user_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self._load_pending_hr()
        self._load_dash()

    def _reject_hr(self, user_id: int) -> None:
        try:
            jobhub_api.admin_reject_hr(user_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self._load_pending_hr()
        self._load_dash()

    def _load_pending_jobs(self) -> None:
        if not self.table_jobs:
            return
        try:
            jobs = jobhub_api.admin_pending_jobs()
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self.table_jobs.setColumnCount(3)
        self.table_jobs.setHorizontalHeaderLabels(["ID", "Tiêu đề", "Hành động"])
        self.table_jobs.setRowCount(len(jobs))
        for i, j in enumerate(jobs):
            jid = j["id"]
            self.table_jobs.setItem(i, 0, QTableWidgetItem(str(jid)))
            self.table_jobs.setItem(i, 1, QTableWidgetItem(j.get("title", "")))
            cell = load_ui(resource_ui("action_buttons.ui"))
            bp = cell.findChild(QPushButton, "btnPrimary")
            bs = cell.findChild(QPushButton, "btnSecondary")
            if bp:
                bp.setText("Duyệt đăng")
                bp.clicked.connect(lambda _=False, x=jid: self._approve_job(x))
            if bs:
                bs.setText("Từ chối")
                bs.clicked.connect(lambda _=False, x=jid: self._reject_job(x))
            self.table_jobs.setCellWidget(i, 2, cell)

    def _approve_job(self, job_id: int) -> None:
        try:
            jobhub_api.admin_approve_job(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self._load_pending_jobs()
        self._load_dash()

    def _reject_job(self, job_id: int) -> None:
        try:
            jobhub_api.admin_reject_job(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Admin", str(e))
            return
        self._load_pending_jobs()
        self._load_dash()

    def show(self) -> None:
        self.win.show()
