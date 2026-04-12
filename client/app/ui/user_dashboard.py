from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QWidget,
)

from ..client import jobhub_api
from ..client.jobhub_api import ApiError
from ..paths import resource_ui
from ..session_store import clear_session
from .qss_loader import apply_theme_qss
from .ui_loader import load_ui


class UserDashboard:
    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout
        self._all_jobs: list[dict] = []
        win = load_ui(resource_ui("dashboard_shell.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("dashboard_shell.ui phải là QMainWindow")
        self.win = win
        apply_theme_qss(self.win, "user_shell")

        self.stack = win.findChild(QStackedWidget, "stackedPages")
        self.nav_home = win.findChild(QPushButton, "navHome")
        self.nav_saved = win.findChild(QPushButton, "navSaved")
        self.nav_cv = win.findChild(QPushButton, "navCv")
        self.nav_profile = win.findChild(QPushButton, "navProfile")
        self.btn_logout = win.findChild(QPushButton, "btnLogout")
        self.line_search = win.findChild(QLineEdit, "lineSearch")

        self.scroll = win.findChild(QScrollArea, "scrollJobs")
        self.grid: QGridLayout | None = None
        if self.scroll and self.scroll.widget():
            lay = self.scroll.widget().layout()
            if isinstance(lay, QGridLayout):
                self.grid = lay
                self.grid.setHorizontalSpacing(18)
                self.grid.setVerticalSpacing(18)

        page_cv = win.findChild(QWidget, "pageCv")
        self.list_cvs = page_cv.findChild(QListWidget, "listCvs") if page_cv else None
        self.btn_pick = win.findChild(QPushButton, "btnPickCv")
        self.btn_upload = win.findChild(QPushButton, "btnUploadCv")

        self._cv_path: str | None = None

        self._nav_group = QButtonGroup(self.win)
        for b in (self.nav_home, self.nav_saved, self.nav_cv, self.nav_profile):
            if b:
                b.setCheckable(True)
                self._nav_group.addButton(b)
        if self.nav_home:
            self.nav_home.clicked.connect(lambda: self._go(0))
        if self.nav_saved:
            self.nav_saved.clicked.connect(lambda: self._go(1))
        if self.nav_cv:
            self.nav_cv.clicked.connect(lambda: self._go(2))
        if self.nav_profile:
            self.nav_profile.clicked.connect(lambda: self._go(3))
        if self.btn_logout:
            self.btn_logout.clicked.connect(self._logout)
        if self.btn_pick:
            self.btn_pick.clicked.connect(self._pick_cv)
        if self.btn_upload:
            self.btn_upload.clicked.connect(self._upload_cv)
        if self.line_search:
            self.line_search.textChanged.connect(lambda _t: self._apply_job_filter())

        self._refresh_jobs()
        self._refresh_cv_list()

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)
        for i, b in enumerate([self.nav_home, self.nav_saved, self.nav_cv, self.nav_profile]):
            if b:
                b.setChecked(i == index)

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    def _clear_grid(self) -> None:
        if not self.grid:
            return
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _job_matches_filter(self, job: dict, q: str) -> bool:
        if not q:
            return True
        blob = " ".join(
            [
                str(job.get("title") or ""),
                str(job.get("description") or ""),
                str(job.get("location") or ""),
                str(job.get("company_name") or ""),
                str(job.get("job_type") or ""),
                str(job.get("salary_text") or ""),
            ]
        ).lower()
        return q in blob

    def _refresh_jobs(self) -> None:
        try:
            self._all_jobs = jobhub_api.list_jobs_public()
        except ApiError as e:
            QMessageBox.warning(self.win, "JobHub", str(e))
            self._all_jobs = []
        self._apply_job_filter()

    def _apply_job_filter(self) -> None:
        self._clear_grid()
        if not self.grid:
            return
        q = (self.line_search.text() if self.line_search else "").strip().lower()
        jobs = [j for j in self._all_jobs if self._job_matches_filter(j, q)]
        cols = 2
        for idx, job in enumerate(jobs):
            card = self._make_job_card(job)
            r, c = divmod(idx, cols)
            self.grid.addWidget(card, r, c)

    def _make_job_card(self, job: dict) -> QWidget:
        card = load_ui(resource_ui("job_card.ui"))
        lt = card.findChild(QLabel, "labelJobTitle")
        lc = card.findChild(QLabel, "labelJobCompany")
        lk = card.findChild(QLabel, "labelJobType")
        ld = card.findChild(QLabel, "labelJobDesc")
        ls = card.findChild(QLabel, "labelSalary")
        ll = card.findChild(QLabel, "labelLocation")
        combo = card.findChild(QComboBox, "comboCv")
        btn = card.findChild(QPushButton, "btnApply")
        bm = card.findChild(QToolButton, "btnBookmark")

        company = job.get("company_name") or "Nhà tuyển dụng"
        if lt:
            lt.setText(job.get("title", ""))
        if lc:
            lc.setText(company)
        if lk:
            lk.setText(job.get("job_type") or "Full-time")
        if ld:
            ld.setText((job.get("description") or "")[:220])
        sal = job.get("salary_text") or ""
        if ls:
            ls.setText(f"$ {sal}" if sal else "")
        loc = job.get("location") or ""
        if ll:
            ll.setText(f"📍 {loc}" if loc else "")
        if combo:
            self._fill_cv_combo(combo)

        if bm:
            bm.setCheckable(True)
            bm.setChecked(False)

        def on_apply() -> None:
            jid = int(job["id"])
            cv_id = combo.currentData() if combo else None
            if cv_id is None:
                QMessageBox.warning(self.win, "JobHub", "Tải CV trong mục «CV của tôi» trước khi ứng tuyển.")
                return
            try:
                jobhub_api.apply_job(jid, int(cv_id))
            except ApiError as e:
                QMessageBox.warning(self.win, "Ứng tuyển", str(e))
                return
            QMessageBox.information(self.win, "JobHub", "Đã gửi hồ sơ ứng tuyển.")

        if btn:
            btn.clicked.connect(on_apply)
        return card

    def _fill_cv_combo(self, combo: QComboBox) -> None:
        combo.clear()
        combo.addItem("— Chọn CV —", None)
        try:
            cvs = jobhub_api.list_my_cvs()
        except ApiError:
            cvs = []
        for c in cvs:
            combo.addItem(c.get("original_name", f"CV #{c['id']}"), c["id"])

    def _refresh_cv_list(self) -> None:
        if not self.list_cvs:
            return
        self.list_cvs.clear()
        try:
            cvs = jobhub_api.list_my_cvs()
        except ApiError:
            cvs = []
        for c in cvs:
            self.list_cvs.addItem(f"{c['id']} — {c.get('original_name', '')}")

    def _pick_cv(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self.win, "Chọn CV", "", "Documents (*.pdf *.doc *.docx);;All (*)")
        if path:
            self._cv_path = path

    def _upload_cv(self) -> None:
        if not self._cv_path:
            QMessageBox.warning(self.win, "JobHub", "Chọn file trước.")
            return
        try:
            jobhub_api.upload_cv(self._cv_path)
        except ApiError as e:
            QMessageBox.warning(self.win, "Tải CV", str(e))
            return
        self._cv_path = None
        self._refresh_cv_list()
        self._refresh_jobs()
        QMessageBox.information(self.win, "JobHub", "Đã tải CV lên máy chủ.")

    def show(self) -> None:
        self.win.show()
