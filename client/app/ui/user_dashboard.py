from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..client import jobhub_api
from ..client.jobhub_api import ApiError
from ..paths import resource_icon, resource_ui
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

        self.stack = win.findChild(QStackedWidget, "stackedPages") or win.findChild(QStackedWidget, "mainStack")
        self.nav_home = self._find_button(["navHome"], "Trang chủ")
        self.nav_saved = self._find_button(["navSaved"], "Việc đã lưu")
        self.nav_cv = self._find_button(["navCv"], "CV của tôi")
        self.nav_profile = self._find_button(["navProfile"], "Hồ sơ")
        self.btn_logout = self._find_button(["btnLogout", "logoutButton"], "Đăng xuất")
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
        self.btn_upload = win.findChild(QPushButton, "btnUploadCv")
        self.list_saved_jobs = win.findChild(QListWidget, "listSavedJobs")
        self.label_profile_name = win.findChild(QLabel, "labelProfileName")
        self.label_profile_email = win.findChild(QLabel, "labelProfileEmail")
        self.label_profile_role = win.findChild(QLabel, "labelProfileRole")
        self.label_avatar_preview = win.findChild(QLabel, "labelAvatarPreview")
        self.btn_change_avatar = win.findChild(QPushButton, "btnChangeAvatar")
        self.line_new_email = win.findChild(QLineEdit, "lineNewEmail")
        self.line_current_password_for_email = win.findChild(QLineEdit, "lineCurrentPasswordForEmail")
        self.btn_update_email = win.findChild(QPushButton, "btnUpdateEmail")
        self.line_current_password = win.findChild(QLineEdit, "lineCurrentPassword")
        self.line_new_password = win.findChild(QLineEdit, "lineNewPassword")
        self.line_confirm_password = win.findChild(QLineEdit, "lineConfirmPassword")
        self.btn_update_password = win.findChild(QPushButton, "btnUpdatePassword")
        self.btn_refresh_profile = win.findChild(QPushButton, "btnRefreshProfile")
        self.page_job_detail = win.findChild(QWidget, "pageJobDetail")
        self.btn_back_jobs = win.findChild(QPushButton, "btnBackToJobs")
        self.btn_save_job_icon = win.findChild(QPushButton, "btnSaveJobIcon")
        self.label_detail_title = win.findChild(QLabel, "labelDetailTitle")
        self.label_detail_company = win.findChild(QLabel, "labelDetailCompany")
        self.label_detail_meta = win.findChild(QLabel, "labelDetailMeta")
        self.plain_job_detail = win.findChild(QPlainTextEdit, "plainJobDetail")
        self.combo_detail_cv = win.findChild(QComboBox, "comboDetailCv")
        self.btn_detail_apply = win.findChild(QPushButton, "btnDetailApply")

        self._selected_job_id: int | None = None
        self._selected_job: dict | None = None
        self._saved_job_ids: set[int] = set()
        self._icon_eye = QIcon(str(resource_icon("eye.svg")))
        self._icon_trash = QIcon(str(resource_icon("trash_white.svg")))
        self._icon_bookmark_off = QIcon(str(resource_icon("bookmark_outline.svg")))
        self._icon_bookmark_on = QIcon(str(resource_icon("bookmark_filled.svg")))

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
            self.nav_profile.clicked.connect(lambda: self._go(4))
        if self.btn_logout:
            self.btn_logout.clicked.connect(self._logout)
        if self.btn_upload:
            self.btn_upload.clicked.connect(self._upload_cv)
        if self.btn_back_jobs:
            self.btn_back_jobs.clicked.connect(lambda: self._go(0))
        if self.btn_save_job_icon:
            self.btn_save_job_icon.clicked.connect(self._toggle_save_selected_job)
            self.btn_save_job_icon.setText("")
            self.btn_save_job_icon.setIcon(self._icon_bookmark_off)
            self.btn_save_job_icon.setIconSize(QSize(18, 18))
        if self.btn_detail_apply:
            self.btn_detail_apply.clicked.connect(self._apply_selected_job)
        if self.btn_refresh_profile:
            self.btn_refresh_profile.clicked.connect(self._refresh_profile)
        if self.btn_change_avatar:
            self.btn_change_avatar.clicked.connect(self._change_avatar)
        if self.btn_update_email:
            self.btn_update_email.clicked.connect(self._update_email)
        if self.btn_update_password:
            self.btn_update_password.clicked.connect(self._update_password)
        if self.line_search:
            self.line_search.textChanged.connect(lambda _t: self._apply_job_filter())
        self._refresh_jobs()
        self._refresh_cv_list()
        self._init_saved_jobs()
        self._refresh_saved_jobs()
        self._refresh_profile()

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
        nav_active = {0: 0, 1: 1, 2: 2, 4: 3}.get(index, 0)
        for i, b in enumerate([self.nav_home, self.nav_saved, self.nav_cv, self.nav_profile]):
            if b:
                b.setChecked(i == nav_active)

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
            ls.setText(sal)
        loc = job.get("location") or ""
        if ll:
            ll.setText(loc)
        if combo:
            combo.setVisible(False)

        if bm:
            bm.setVisible(False)

        if btn:
            btn.setText("Xem chi tiết")
            btn.clicked.connect(lambda: self._open_job_detail(job))
        return card

    def _open_job_detail(self, job: dict) -> None:
        self._selected_job_id = int(job["id"])
        self._selected_job = job
        if self.label_detail_title:
            self.label_detail_title.setText(str(job.get("title") or "Chi tiết công việc"))
        if self.label_detail_company:
            self.label_detail_company.setText(str(job.get("company_name") or "Nhà tuyển dụng"))
        if self.label_detail_meta:
            self.label_detail_meta.setText(
                " • ".join(
                    x
                    for x in [
                        str(job.get("job_type") or ""),
                        str(job.get("location") or ""),
                        str(job.get("salary_text") or ""),
                    ]
                    if x
                )
            )
        if self.plain_job_detail:
            self.plain_job_detail.setPlainText(str(job.get("description") or ""))
        if self.combo_detail_cv:
            self._fill_cv_combo(self.combo_detail_cv)
        if self.stack and self.page_job_detail:
            self.stack.setCurrentWidget(self.page_job_detail)
        if self.btn_save_job_icon:
            self._update_save_icon()
        if self.nav_home:
            self.nav_home.setChecked(True)

    def _update_save_icon(self) -> None:
        if not self.btn_save_job_icon or self._selected_job_id is None:
            return
        icon = self._icon_bookmark_on if self._selected_job_id in self._saved_job_ids else self._icon_bookmark_off
        self.btn_save_job_icon.setIcon(icon)

    def _toggle_save_selected_job(self) -> None:
        if self._selected_job_id is None:
            return
        if self._selected_job_id in self._saved_job_ids:
            self._saved_job_ids.remove(self._selected_job_id)
        else:
            self._saved_job_ids.add(self._selected_job_id)
        self._update_save_icon()
        self._refresh_saved_jobs()

    def _apply_selected_job(self) -> None:
        if self._selected_job_id is None or not self.combo_detail_cv:
            return
        cv_id = self.combo_detail_cv.currentData()
        if cv_id is None:
            QMessageBox.warning(self.win, "JobHub", "Tải CV trong mục «CV của tôi» trước khi ứng tuyển.")
            return
        try:
            jobhub_api.apply_job(self._selected_job_id, int(cv_id))
        except ApiError as e:
            QMessageBox.warning(self.win, "Ứng tuyển", str(e))
            return
        QMessageBox.information(self.win, "JobHub", "Đã gửi hồ sơ ứng tuyển.")
        self._go(0)

    def _fill_cv_combo(self, combo: QComboBox) -> None:
        combo.clear()
        combo.setMaxVisibleItems(6)
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
            row = QWidget(self.win)
            row.setObjectName("cvRow")
            row.setMinimumHeight(44)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(8, 4, 8, 4)
            lay.setSpacing(8)
            label = QLabel(f"{c['id']} — {c.get('original_name', '')}")
            label.setObjectName("cvRowLabel")
            btn_view = QPushButton("")
            btn_view.setObjectName("btnCvView")
            btn_del = QPushButton("")
            btn_del.setObjectName("btnCvDelete")
            btn_view.setToolTip("Xem CV")
            btn_del.setToolTip("Xóa CV")
            btn_view.setFixedSize(36, 30)
            btn_del.setFixedSize(36, 30)
            btn_view.setIcon(self._icon_eye)
            btn_view.setIconSize(QSize(16, 16))
            btn_del.setIcon(self._icon_trash)
            btn_del.setIconSize(QSize(15, 15))
            cv_id = int(c["id"])
            btn_view.clicked.connect(lambda _=False, x=cv_id: self._view_cv(x))
            btn_del.clicked.connect(lambda _=False, x=cv_id: self._delete_cv(x))
            lay.addWidget(label, 1)
            lay.addWidget(btn_view)
            lay.addWidget(btn_del)
            it = QListWidgetItem()
            it.setSizeHint(QSize(0, 44))
            self.list_cvs.addItem(it)
            self.list_cvs.setItemWidget(it, row)

    def _view_cv(self, cv_id: int) -> None:
        try:
            data, filename = jobhub_api.candidate_view_cv(cv_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "CV", str(e))
            return
        suffix = Path(filename or "cv.pdf").suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(data)
            temp_path = f.name
        os.startfile(temp_path)  # type: ignore[attr-defined]

    def _delete_cv(self, cv_id: int) -> None:
        ok = QMessageBox.question(self.win, "Xóa CV", "Bạn có chắc muốn xóa CV đã chọn?")
        if ok != QMessageBox.StandardButton.Yes:
            return
        try:
            jobhub_api.candidate_delete_cv(cv_id)
        except ApiError as e:
            QMessageBox.warning(self.win, "Xóa CV", str(e))
            return
        self._refresh_cv_list()
        self._refresh_jobs()
        QMessageBox.information(self.win, "CV", "Đã xóa CV.")

    def _refresh_saved_jobs(self) -> None:
        if not self.list_saved_jobs:
            return
        self.list_saved_jobs.clear()
        saved_jobs = [j for j in self._all_jobs if int(j.get("id", 0)) in self._saved_job_ids]
        for j in saved_jobs:
            row = QWidget(self.win)
            row.setObjectName("savedJobRow")
            row.setMinimumHeight(134)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(14, 10, 14, 10)
            lay.setSpacing(10)

            info = QWidget(row)
            info_lay = QVBoxLayout(info)
            info_lay.setContentsMargins(0, 0, 0, 0)
            info_lay.setSpacing(6)
            title = str(j.get("title") or "Tin tuyển dụng")
            company = str(j.get("company_name") or "Nhà tuyển dụng")
            meta = " · ".join(
                x for x in [str(j.get("job_type") or ""), str(j.get("location") or ""), str(j.get("salary_text") or "")] if x
            )
            label_title = QLabel(title)
            label_title.setObjectName("labelSavedJobTitle")
            label_company = QLabel(company)
            label_company.setObjectName("labelSavedJobCompany")
            label_meta = QLabel(meta)
            label_meta.setObjectName("labelSavedJobMeta")
            btn_open = QPushButton("Xem chi tiết")
            btn_open.setObjectName("btnSavedJobOpen")
            btn_open.setMinimumHeight(36)
            btn_remove = QPushButton("")
            btn_remove.setObjectName("btnSavedRemoveIcon")
            btn_remove.setToolTip("Xóa lưu công việc")
            btn_remove.setMinimumSize(34, 34)
            btn_remove.setIcon(self._icon_trash)
            btn_remove.setIconSize(QSize(16, 16))
            jid = int(j["id"])
            btn_open.clicked.connect(lambda _=False, x=j: self._open_job_detail(x))
            btn_remove.clicked.connect(lambda _=False, x=jid: self._unsave_job(x))
            info_lay.addWidget(label_title)
            info_lay.addWidget(label_company)
            info_lay.addWidget(label_meta)
            info_lay.addWidget(btn_open)
            lay.addWidget(info, 1)
            lay.addWidget(btn_remove)
            it = QListWidgetItem()
            it.setSizeHint(QSize(0, 134))
            self.list_saved_jobs.addItem(it)
            self.list_saved_jobs.setItemWidget(it, row)

    def _unsave_job(self, job_id: int) -> None:
        if job_id in self._saved_job_ids:
            self._saved_job_ids.remove(job_id)
            self._refresh_saved_jobs()
            self._update_save_icon()

    def _init_saved_jobs(self) -> None:
        if self._saved_job_ids:
            return
        for j in self._all_jobs[:3]:
            if "id" in j:
                self._saved_job_ids.add(int(j["id"]))

    def _refresh_profile(self) -> None:
        try:
            me = jobhub_api.me()
        except ApiError as e:
            QMessageBox.warning(self.win, "Hồ sơ", str(e))
            return
        if self.label_profile_name:
            self.label_profile_name.setText(str(me.get("full_name") or "(chưa cập nhật)"))
        if self.label_profile_email:
            self.label_profile_email.setText(str(me.get("email") or ""))
        if self.label_profile_role:
            role = str(me.get("role") or "")
            role_vi = {"candidate": "Ứng viên", "hr": "Nhà tuyển dụng", "admin": "Quản trị viên"}.get(role, role)
            self.label_profile_role.setText(role_vi)
        if self.label_avatar_preview:
            self.label_avatar_preview.setText("👤")

    def _change_avatar(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self.win, "Chọn ảnh đại diện", "", "Images (*.png *.jpg *.jpeg *.webp *.gif)")
        if not path:
            return
        try:
            jobhub_api.upload_avatar(path)
        except ApiError as e:
            QMessageBox.warning(self.win, "Ảnh đại diện", str(e))
            return
        self._refresh_profile()
        QMessageBox.information(self.win, "Ảnh đại diện", "Đã cập nhật ảnh đại diện.")

    def _update_email(self) -> None:
        if not self.line_new_email or not self.line_current_password_for_email:
            return
        new_email = self.line_new_email.text().strip()
        current_password = self.line_current_password_for_email.text()
        if not new_email:
            QMessageBox.warning(self.win, "Đổi email", "Vui lòng nhập email mới.")
            return
        if not current_password:
            QMessageBox.warning(self.win, "Đổi email", "Vui lòng nhập mật khẩu hiện tại.")
            return
        try:
            jobhub_api.update_my_email(new_email, current_password)
        except ApiError as e:
            QMessageBox.warning(self.win, "Đổi email", str(e))
            return
        self.line_new_email.clear()
        self.line_current_password_for_email.clear()
        self._refresh_profile()
        QMessageBox.information(self.win, "Đổi email", "Cập nhật email thành công.")

    def _update_password(self) -> None:
        if not self.line_current_password or not self.line_new_password or not self.line_confirm_password:
            return
        current_password = self.line_current_password.text()
        new_password = self.line_new_password.text()
        confirm_password = self.line_confirm_password.text()
        if not current_password:
            QMessageBox.warning(self.win, "Đổi mật khẩu", "Vui lòng nhập mật khẩu hiện tại.")
            return
        if len(new_password) < 6:
            QMessageBox.warning(self.win, "Đổi mật khẩu", "Mật khẩu mới phải có ít nhất 6 ký tự.")
            return
        if new_password != confirm_password:
            QMessageBox.warning(self.win, "Đổi mật khẩu", "Xác nhận mật khẩu không khớp.")
            return
        try:
            jobhub_api.update_my_password(current_password, new_password)
        except ApiError as e:
            QMessageBox.warning(self.win, "Đổi mật khẩu", str(e))
            return
        self.line_current_password.clear()
        self.line_new_password.clear()
        self.line_confirm_password.clear()
        QMessageBox.information(self.win, "Đổi mật khẩu", "Cập nhật mật khẩu thành công.")

    def _upload_cv(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self.win, "Chọn CV", "", "Documents (*.pdf *.doc *.docx);;All (*)")
        if not path:
            return
        try:
            jobhub_api.upload_cv(path)
        except ApiError as e:
            QMessageBox.warning(self.win, "Tải CV", str(e))
            return
        self._refresh_cv_list()
        self._refresh_jobs()
        QMessageBox.information(self.win, "JobHub", "Đã tải CV lên máy chủ.")

    def show(self) -> None:
        self.win.show()
