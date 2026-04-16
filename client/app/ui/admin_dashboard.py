from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
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
        self.nav_dash = self._find_button(["navDash"], "Dashboard")
        self.nav_users = self._find_button(["navUsers"], "Quản lý User")
        self.nav_hr = self._find_button(["navHr"], "Quản lý HR")
        self.nav_jobs = self._find_button(["navJobs"], "Quản lý Jobs")
        self.btn_logout = self._find_button(["btnLogout", "logoutButton"], "Đăng xuất")

        self.chart_holder = win.findChild(QWidget, "chartHolder")
        self.cards_row = win.findChild(QHBoxLayout, "horizontalLayout_cards")

        self.table_users = win.findChild(QTableWidget, "tableUsers")
        self.table_hr = win.findChild(QTableWidget, "tableHr")
        self.table_jobs = win.findChild(QTableWidget, "tableJobs")
        self.page_users = win.findChild(QWidget, "pageUsers")
        self.page_hr = win.findChild(QWidget, "pageHr")

        self._nav_group = QButtonGroup(self.win)
        for b in (self.nav_dash, self.nav_users, self.nav_hr, self.nav_jobs):
            if b:
                b.setCheckable(True)
                self._nav_group.addButton(b)
        if self.nav_dash:
            self.nav_dash.clicked.connect(lambda: self._go(0))
        if self.nav_users:
            self.nav_users.clicked.connect(lambda: (self._go(1), self._load_users()))
        if self.nav_hr:
            self.nav_hr.clicked.connect(lambda: (self._go(2), self._load_pending_hr()))
        if self.nav_jobs:
            self.nav_jobs.clicked.connect(lambda: (self._go(3), self._load_pending_jobs()))
        if self.btn_logout:
            self.btn_logout.clicked.connect(self._logout)

        self._setup_page_layout(self.page_users)
        self._setup_page_layout(self.page_hr)
        self._setup_table(self.table_users, stretch_cols=[1, 2])
        self._setup_table(self.table_hr, stretch_cols=[1])
        self._setup_table(self.table_jobs, stretch_cols=[1])

        self._load_dash()
        self._load_users()
        self._load_pending_hr()
        self._load_pending_jobs()

    def _find_button(self, names: list[str], text_fallback: str) -> QPushButton | None:
        for name in names:
            b = self.win.findChild(QPushButton, name)
            if b:
                return b
        for b in self.win.findChildren(QPushButton):
            if b.text().strip() == text_fallback:
                return b
        return None

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)
        for i, b in enumerate([self.nav_dash, self.nav_users, self.nav_hr, self.nav_jobs]):
            if b:
                b.setChecked(i == index)

    def _setup_page_layout(self, page: QWidget | None) -> None:
        if not page or not page.layout():
            return
        page.layout().setContentsMargins(28, 24, 28, 20)
        page.layout().setSpacing(12)

    def _setup_table(self, table: QTableWidget | None, stretch_cols: list[int] | None = None) -> None:
        if not table:
            return
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        hh = table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setMinimumSectionSize(80)
        if stretch_cols:
            for c in stretch_cols:
                hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def _set_empty_row(self, table: QTableWidget, message: str, columns: int) -> None:
        table.setColumnCount(columns)
        table.setRowCount(1)
        table.clearContents()
        cell = QTableWidgetItem(message)
        cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(0, 0, cell)
        table.setSpan(0, 0, 1, columns)

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
        self.table_users.setColumnCount(5)
        self.table_users.setHorizontalHeaderLabels(["ID", "Email", "Vai trò", "Trạng thái", "Hành động"])
        if not users:
            self._set_empty_row(self.table_users, "Chưa có người dùng để hiển thị.", 5)
            return
        self.table_users.setRowCount(len(users))
        for i, u in enumerate(users):
            uid = int(u.get("id", 0))
            self.table_users.setItem(i, 0, QTableWidgetItem(str(uid)))
            self.table_users.setItem(i, 1, QTableWidgetItem(u.get("email", "")))
            role = str(u.get("role", ""))
            role_vi = {"candidate": "Ứng viên", "hr": "Nhà tuyển dụng", "admin": "Quản trị viên"}.get(role, role)
            self.table_users.setItem(i, 2, QTableWidgetItem(role_vi))
            active = bool(u.get("is_active", True))
            self.table_users.setItem(i, 3, QTableWidgetItem("Đang hoạt động" if active else "Đã khóa"))
            actions = QWidget(self.win)
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(6)
            btn_view = QPushButton("Xem")
            btn_view.setMinimumWidth(64)
            btn_toggle = QPushButton("Khóa" if active else "Mở khóa")
            btn_toggle.setMinimumWidth(90)
            btn_view.clicked.connect(lambda _=False, x=uid: self._view_user(x))
            btn_toggle.clicked.connect(lambda _=False, x=uid, a=active: self._toggle_user_lock(x, a))
            lay.addWidget(btn_view)
            lay.addWidget(btn_toggle)
            self.table_users.setCellWidget(i, 4, actions)

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
        if not rows:
            self._set_empty_row(self.table_hr, "Hiện không có HR chờ duyệt.", 3)
            return
        self.table_hr.setRowCount(len(rows))
        for i, u in enumerate(rows):
            uid = u["id"]
            self.table_hr.setItem(i, 0, QTableWidgetItem(str(uid)))
            self.table_hr.setItem(i, 1, QTableWidgetItem(u.get("email", "")))
            cell = load_ui(resource_ui("action_buttons.ui"))
            bp = cell.findChild(QPushButton, "btnPrimary")
            bs = cell.findChild(QPushButton, "btnSecondary")
            bv = QPushButton("Xem")
            bv.setMinimumWidth(64)
            lay = cell.layout()
            if lay:
                lay.addWidget(bv)
            bv.clicked.connect(lambda _=False, x=uid: self._view_hr(x))
            if bp:
                bp.setText("Duyệt")
                bp.setMinimumWidth(72)
                bp.clicked.connect(lambda _=False, x=uid: self._approve_hr(x))
            if bs:
                bs.setText("Từ chối")
                bs.setMinimumWidth(72)
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
        if not jobs:
            self._set_empty_row(self.table_jobs, "Hiện không có công việc chờ duyệt.", 3)
            return
        self.table_jobs.setRowCount(len(jobs))
        for i, j in enumerate(jobs):
            jid = j["id"]
            self.table_jobs.setItem(i, 0, QTableWidgetItem(str(jid)))
            self.table_jobs.setItem(i, 1, QTableWidgetItem(j.get("title", "")))
            cell = load_ui(resource_ui("action_buttons.ui"))
            bp = cell.findChild(QPushButton, "btnPrimary")
            bs = cell.findChild(QPushButton, "btnSecondary")
            bv = QPushButton("Xem")
            bv.setMinimumWidth(64)
            lay = cell.layout()
            if lay:
                lay.addWidget(bv)
            bv.clicked.connect(lambda _=False, x=jid: self._view_job(x))
            if bp:
                bp.setText("Duyệt đăng")
                bp.setMinimumWidth(88)
                bp.clicked.connect(lambda _=False, x=jid: self._approve_job(x))
            if bs:
                bs.setText("Từ chối")
                bs.setMinimumWidth(72)
                bs.clicked.connect(lambda _=False, x=jid: self._reject_job(x))
            self.table_jobs.setCellWidget(i, 2, cell)

    def _view_user(self, user_id: int) -> None:
        try:
            u = jobhub_api.admin_get_user(user_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "User", str(e))
            return
        text = "\n".join(
            [
                f"ID: {u.get('id')}",
                f"Email: {u.get('email')}",
                f"Họ tên: {u.get('full_name') or ''}",
                f"Vai trò: {u.get('role')}",
                f"Trạng thái: {'Đang hoạt động' if u.get('is_active', True) else 'Đã khóa'}",
            ]
        )
        QMessageBox.information(self.win, "Thông tin người dùng", text)

    def _toggle_user_lock(self, user_id: int, active: bool) -> None:
        try:
            if active:
                jobhub_api.admin_lock_user(user_id)
            else:
                jobhub_api.admin_unlock_user(user_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Quản lý tài khoản", str(e))
            return
        self._load_users()

    def _view_hr(self, user_id: int) -> None:
        try:
            p = jobhub_api.admin_hr_detail(user_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "HR", str(e))
            return
        text = "\n".join(
            [
                f"Email: {p.get('email')}",
                f"Họ tên: {p.get('full_name') or ''}",
                f"Công ty: {p.get('company_name') or ''}",
                f"Điện thoại: {p.get('contact_phone') or ''}",
                f"Trạng thái duyệt: {p.get('approval_status')}",
                "",
                f"Mô tả:\n{p.get('company_description') or ''}",
            ]
        )
        QMessageBox.information(self.win, "Thông tin HR", text)

    def _view_job(self, job_id: int) -> None:
        try:
            j = jobhub_api.admin_job_detail(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Job", str(e))
            return
        text = "\n".join(
            [
                f"Tiêu đề: {j.get('title')}",
                f"Địa điểm: {j.get('location') or ''}",
                f"Lương: {j.get('salary_text') or ''}",
                f"Loại hình: {j.get('job_type') or ''}",
                f"Trạng thái: {j.get('status')}",
                "",
                f"Mô tả:\n{j.get('description') or ''}",
            ]
        )
        QMessageBox.information(self.win, "Thông tin Job", text)

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
