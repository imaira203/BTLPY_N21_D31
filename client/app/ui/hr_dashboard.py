from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
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
        self.nav_dash = self._find_button(["navDash"], "Dashboard")
        self.nav_post = self._find_button(["navPost"], "Đăng tin tuyển dụng")
        self.nav_jobs = self._find_button(["navJobs"], "Quản lý tin đăng")
        self.nav_cands = self._find_button(["navCands"], "Danh sách ứng viên")
        self.btn_logout = self._find_button(["btnLogout", "logoutButton"], "Đăng xuất")

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
        self.page_jobs = win.findChild(QWidget, "pageJobs")
        self.page_cands = win.findChild(QWidget, "pageCands")
        self.page_post = win.findChild(QWidget, "pagePost")

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
            self.nav_jobs.clicked.connect(lambda: (self._go(2), self._load_jobs_table()))
        if self.nav_cands:
            self.nav_cands.clicked.connect(lambda: (self._go(3), self._load_cands_table()))
        if self.btn_logout:
            self.btn_logout.clicked.connect(self._logout)
        if self.btn_draft:
            self.btn_draft.clicked.connect(lambda: self._create_job(draft=True))
        if self.btn_submit_new:
            self.btn_submit_new.clicked.connect(lambda: self._create_job(draft=False))

        self._setup_page_layout(self.page_jobs)
        self._setup_page_layout(self.page_cands)
        self._setup_page_layout(self.page_post)
        self._setup_table(self.table_jobs, stretch_cols=[1, 2])
        self._setup_table(self.table_cands, stretch_cols=[0, 1, 2, 4])

        self._load_dash()
        self._load_jobs_table()
        self._load_cands_table()
        self._update_hr_status()

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
        for i, b in enumerate([self.nav_dash, self.nav_post, self.nav_jobs, self.nav_cands]):
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
        if not jobs:
            self._set_empty_row(self.table_jobs, "Chưa có tin đăng nào.", 4)
            return
        self.table_jobs.setRowCount(len(jobs))
        for row, j in enumerate(jobs):
            jid = j["id"]
            self.table_jobs.setItem(row, 0, QTableWidgetItem(str(jid)))
            self.table_jobs.setItem(row, 1, QTableWidgetItem(j.get("title", "")))
            status = str(j.get("status", ""))
            status_vi = {
                "draft": "Nháp",
                "pending_approval": "Chờ duyệt",
                "published": "Đã đăng",
                "rejected": "Bị từ chối",
            }.get(status, status)
            self.table_jobs.setItem(row, 2, QTableWidgetItem(status_vi))
            actions = QWidget(self.win)
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(6)
            btn_view = QPushButton("Xem")
            btn_edit = QPushButton("Sửa")
            btn_del = QPushButton("Xóa")
            btn_submit = QPushButton("Gửi duyệt")
            btn_view.setMinimumWidth(64)
            btn_edit.setMinimumWidth(64)
            btn_del.setMinimumWidth(64)
            btn_submit.setMinimumWidth(90)
            st = str(j.get("status") or "")
            btn_submit.setEnabled(st in ("draft", "rejected"))
            btn_edit.setEnabled(st != "published")
            btn_del.setEnabled(st != "published")
            btn_view.clicked.connect(lambda _=False, job_id=jid: self._view_job(job_id))
            btn_edit.clicked.connect(lambda _=False, job_id=jid: self._edit_job(job_id))
            btn_del.clicked.connect(lambda _=False, job_id=jid: self._delete_job(job_id))
            btn_submit.clicked.connect(lambda _=False, job_id=jid: self._submit_job(job_id))
            for b in (btn_view, btn_edit, btn_del, btn_submit):
                lay.addWidget(b)
            self.table_jobs.setCellWidget(row, 3, actions)

    def _view_job(self, job_id: int) -> None:
        try:
            job = jobhub_api.hr_get_job(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Xem tin", str(e))
            return
        text = "\n".join(
            [
                f"Tiêu đề: {job.get('title', '')}",
                f"Địa điểm: {job.get('location') or ''}",
                f"Lương: {job.get('salary_text') or ''}",
                f"Loại hình: {job.get('job_type') or ''}",
                f"Trạng thái: {job.get('status') or ''}",
                "",
                str(job.get("description") or ""),
            ]
        )
        QMessageBox.information(self.win, "Chi tiết tin tuyển dụng", text)

    def _edit_job(self, job_id: int) -> None:
        try:
            job = jobhub_api.hr_get_job(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Sửa tin", str(e))
            return

        dlg = QDialog(self.win)
        dlg.setWindowTitle("Sửa tin tuyển dụng")
        dlg.setMinimumWidth(560)
        root = QVBoxLayout(dlg)
        form = QFormLayout()

        line_title = QLineEdit(str(job.get("title") or ""))
        line_salary = QLineEdit(str(job.get("salary_text") or ""))
        line_location = QLineEdit(str(job.get("location") or ""))
        line_type = QLineEdit(str(job.get("job_type") or ""))
        plain_desc = QPlainTextEdit(str(job.get("description") or ""))
        plain_desc.setMinimumHeight(140)
        form.addRow("Tiêu đề", line_title)
        form.addRow("Lương", line_salary)
        form.addRow("Địa điểm", line_location)
        form.addRow("Loại hình", line_type)
        form.addRow("Mô tả", plain_desc)
        root.addLayout(form)

        row = QHBoxLayout()
        btn_cancel = QPushButton("Hủy")
        btn_save = QPushButton("Lưu")
        row.addWidget(btn_cancel)
        row.addStretch(1)
        row.addWidget(btn_save)
        root.addLayout(row)

        def save() -> None:
            payload = {
                "title": line_title.text().strip(),
                "description": plain_desc.toPlainText().strip() or None,
                "salary_text": line_salary.text().strip() or None,
                "location": line_location.text().strip() or None,
                "job_type": line_type.text().strip() or None,
                "as_draft": True,
            }
            if not payload["title"]:
                QMessageBox.warning(dlg, "Sửa tin", "Tiêu đề không được để trống.")
                return
            try:
                jobhub_api.hr_update_job(job_id, payload)
            except ApiError as e:
                QMessageBox.warning(dlg, "Sửa tin", str(e))
                return
            dlg.accept()
            self._load_jobs_table()

        btn_cancel.clicked.connect(dlg.reject)
        btn_save.clicked.connect(save)
        dlg.exec()

    def _delete_job(self, job_id: int) -> None:
        ok = QMessageBox.question(self.win, "Xóa tin", f"Bạn có chắc muốn xóa tin #{job_id}?")
        if ok != QMessageBox.StandardButton.Yes:
            return
        try:
            jobhub_api.hr_delete_job(job_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Xóa tin", str(e))
            return
        self._load_jobs_table()
        self._load_dash()

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
        self.table_cands.setColumnCount(6)
        self.table_cands.setHorizontalHeaderLabels(["Ứng viên", "Email", "Việc", "Trạng thái", "File CV", "Thao tác"])
        if not rows:
            self._set_empty_row(self.table_cands, "Chưa có ứng viên ứng tuyển.", 6)
            return
        self.table_cands.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table_cands.setItem(i, 0, QTableWidgetItem(r.get("candidate_name", "")))
            self.table_cands.setItem(i, 1, QTableWidgetItem(r.get("candidate_email", "")))
            self.table_cands.setItem(i, 2, QTableWidgetItem(r.get("job_title", "")))
            st = str(r.get("status", ""))
            st_vi = {"submitted": "Đã nộp", "reviewed": "Đã xem", "rejected": "Từ chối"}.get(st, st)
            self.table_cands.setItem(i, 3, QTableWidgetItem(st_vi))
            self.table_cands.setItem(i, 4, QTableWidgetItem(r.get("cv_name") or "Không có"))
            app_id = r.get("application_id")
            actions = QWidget(self.win)
            lay = QHBoxLayout(actions)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(6)
            btn_view = QPushButton("Xem")
            btn_down = QPushButton("Tải")
            btn_view.setMinimumWidth(64)
            btn_down.setMinimumWidth(64)
            has_cv = app_id is not None
            btn_view.setEnabled(has_cv)
            btn_down.setEnabled(has_cv)
            if has_cv:
                btn_view.clicked.connect(lambda _=False, x=int(app_id): self._view_cv(x))
                btn_down.clicked.connect(lambda _=False, x=int(app_id): self._download_cv(x))
            lay.addWidget(btn_view)
            lay.addWidget(btn_down)
            self.table_cands.setCellWidget(i, 5, actions)

    def _download_cv(self, application_id: int) -> None:
        try:
            data, filename = jobhub_api.hr_download_application_cv(application_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Tải CV", str(e))
            return
        default_name = filename or f"cv_{application_id}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self.win,
            "Lưu CV",
            default_name,
            "Documents (*.pdf *.doc *.docx);;All (*)",
        )
        if not path:
            return
        Path(path).write_bytes(data)
        QMessageBox.information(self.win, "Tải CV", f"Đã lưu file: {path}")

    def _view_cv(self, application_id: int) -> None:
        try:
            data, filename = jobhub_api.hr_view_application_cv(application_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Xem CV", str(e))
            return
        suffix = Path(filename or "cv.pdf").suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(data)
            temp_path = f.name
        os.startfile(temp_path)  # type: ignore[attr-defined]

    def show(self) -> None:
        self.win.show()
