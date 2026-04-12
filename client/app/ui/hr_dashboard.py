from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
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
from ..paths import resource_ui
from ..session_store import clear_session
from ..theme import HR_ACCENT
from .charts import make_bar_chart
from .qss_loader import apply_theme_qss
from .ui_loader import load_ui


class HRDashboard:
    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout
        win = load_ui(resource_ui("hr_dashboard.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("hr_dashboard.ui phải là QMainWindow")
        self.win = win
        apply_theme_qss(self.win, "hr_shell")

        self.stack = win.findChild(QStackedWidget, "stackedPages")
        self.nav_dash = win.findChild(QPushButton, "navDash")
        self.nav_post = win.findChild(QPushButton, "navPost")
        self.nav_jobs = win.findChild(QPushButton, "navJobs")
        self.nav_cands = win.findChild(QPushButton, "navCands")
        self.btn_logout = win.findChild(QPushButton, "btnLogout")

        self.chart_holder = win.findChild(QWidget, "chartHolder")
        self.cards_row = win.findChild(QHBoxLayout, "horizontalLayout_cards")

        self.line_title = win.findChild(QLineEdit, "lineJobTitle")
        self.plain_desc = win.findChild(QPlainTextEdit, "plainJobDesc")
        self.line_salary = win.findChild(QLineEdit, "lineSalary")
        self.line_location = win.findChild(QLineEdit, "lineLocation")
        self.line_job_type = win.findChild(QLineEdit, "lineJobType")
        self.btn_draft = win.findChild(QPushButton, "btnSaveDraft")
        self.btn_submit_new = win.findChild(QPushButton, "btnSubmitJob")
        self.label_hr_status = win.findChild(QLabel, "labelHrStatus")

        self.table_jobs = win.findChild(QTableWidget, "tableJobs")
        self.table_cands = win.findChild(QTableWidget, "tableCands")

        self._nav_group = QButtonGroup(self.win)
        for b in (self.nav_dash, self.nav_post, self.nav_jobs, self.nav_cands):
            if b:
                b.setCheckable(True)
                self._nav_group.addButton(b)
        if self.nav_dash:
            self.nav_dash.clicked.connect(lambda: self._go(0))
        if self.nav_post:
            self.nav_post.clicked.connect(lambda: self._go(1))
        if self.nav_jobs:
            self.nav_jobs.clicked.connect(lambda: self._go(2))
        if self.nav_cands:
            self.nav_cands.clicked.connect(lambda: self._go(3))
        if self.btn_logout:
            self.btn_logout.clicked.connect(self._logout)
        if self.btn_draft:
            self.btn_draft.clicked.connect(lambda: self._create_job(draft=True))
        if self.btn_submit_new:
            self.btn_submit_new.clicked.connect(lambda: self._create_job(draft=False))

        self._load_dash()
        self._load_jobs_table()
        self._load_cands_table()
        self._update_hr_status()

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)
        for i, b in enumerate([self.nav_dash, self.nav_post, self.nav_jobs, self.nav_cands]):
            if b:
                b.setChecked(i == index)

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    def _update_hr_status(self) -> None:
        if not self.label_hr_status:
            return
        try:
            p = jobhub_api.hr_profile()
        except ApiError:
            p = None
        if not p:
            self.label_hr_status.setText("Không tìm thấy hồ sơ HR.")
            return
        st = p.get("approval_status", "")
        self.label_hr_status.setText(
            f"Trạng thái hồ sơ HR: {st}. "
            "Khi được duyệt, bạn có thể đăng tin và gửi duyệt tin tuyển dụng."
        )

    def _load_dash(self) -> None:
        try:
            data = jobhub_api.hr_dashboard()
        except ApiError as e:
            QMessageBox.warning(self.win, "HR", str(e))
            return
        cards = data.get("cards") or {}
        labels = data.get("labels") or ["T1", "T2", "T3"]
        values = data.get("values") or [0, 0, 0]
        if self.cards_row:
            while self.cards_row.count():
                it = self.cards_row.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            items = [
                ("💼", "Tổng tin đăng", str(cards.get("jobs", 0)), "+3 tuần này"),
                ("👥", "Tổng ứng viên", str(cards.get("candidates", 0)), "+12 tuần này"),
                (
                    "👁",
                    "Lượt xem (ước lượng)",
                    f"{int(cards.get('views', 0) or 0):,}".replace(",", "."),
                    "+245 tuần này",
                ),
                ("📈", "Tỷ lệ phản hồi", f"{cards.get('response_rate', 0)}%", "+5% so với tháng trước"),
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
        if self.chart_holder:
            lay = self.chart_holder.layout()
            if lay is None:
                lay = QVBoxLayout(self.chart_holder)
                self.chart_holder.setLayout(lay)
            while lay.count():
                it = lay.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
            canvas = make_bar_chart([str(x) for x in labels], [int(x) for x in values], HR_ACCENT)
            lay.addWidget(canvas)

    def _create_job(self, draft: bool) -> None:
        payload = {
            "title": self.line_title.text().strip() if self.line_title else "",
            "description": self.plain_desc.toPlainText().strip() if self.plain_desc else "",
            "salary_text": self.line_salary.text().strip() if self.line_salary else None,
            "location": self.line_location.text().strip() if self.line_location else None,
            "job_type": self.line_job_type.text().strip() if self.line_job_type else None,
            "as_draft": draft,
        }
        if not payload["title"]:
            QMessageBox.warning(self.win, "HR", "Nhập tiêu đề tin.")
            return
        try:
            jobhub_api.hr_create_job(payload)
        except ApiError as e:
            QMessageBox.warning(self.win, "Đăng tin", str(e))
            return
        QMessageBox.information(self.win, "HR", "Đã lưu tin.")
        self._load_jobs_table()
        self._load_dash()

    def _load_jobs_table(self) -> None:
        if not self.table_jobs:
            return
        try:
            jobs = jobhub_api.hr_my_jobs()
        except ApiError as e:
            QMessageBox.warning(self.win, "HR", str(e))
            return
        self.table_jobs.setColumnCount(4)
        self.table_jobs.setHorizontalHeaderLabels(["ID", "Tiêu đề", "Trạng thái", "Hành động"])
        self.table_jobs.setRowCount(len(jobs))
        for row, j in enumerate(jobs):
            jid = j["id"]
            self.table_jobs.setItem(row, 0, QTableWidgetItem(str(jid)))
            self.table_jobs.setItem(row, 1, QTableWidgetItem(j.get("title", "")))
            self.table_jobs.setItem(row, 2, QTableWidgetItem(j.get("status", "")))
            btn = QPushButton("Gửi duyệt")
            st = j.get("status")
            btn.setEnabled(st in ("draft", "rejected"))
            btn.clicked.connect(lambda _=False, job_id=jid: self._submit_job(job_id))
            self.table_jobs.setCellWidget(row, 3, btn)

    def _submit_job(self, job_id: int) -> None:
        try:
            jobhub_api.hr_submit_job(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Gửi duyệt", str(e))
            return
        QMessageBox.information(self.win, "HR", "Đã gửi tin chờ Admin duyệt.")
        self._load_jobs_table()

    def _load_cands_table(self) -> None:
        if not self.table_cands:
            return
        try:
            rows = jobhub_api.hr_applications()
        except ApiError as e:
            QMessageBox.warning(self.win, "HR", str(e))
            return
        self.table_cands.setColumnCount(4)
        self.table_cands.setHorizontalHeaderLabels(["Ứng viên", "Email", "Việc", "Trạng thái"])
        self.table_cands.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table_cands.setItem(i, 0, QTableWidgetItem(r.get("candidate_name", "")))
            self.table_cands.setItem(i, 1, QTableWidgetItem(r.get("candidate_email", "")))
            self.table_cands.setItem(i, 2, QTableWidgetItem(r.get("job_title", "")))
            self.table_cands.setItem(i, 3, QTableWidgetItem(r.get("status", "")))

    def show(self) -> None:
        self.win.show()
