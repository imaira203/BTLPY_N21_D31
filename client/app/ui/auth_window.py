from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGroupBox,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
)

from .. import session_store
from ..client import jobhub_api
from ..client.jobhub_api import ApiError
from ..paths import resource_ui
from .qss_loader import apply_theme_qss
from .ui_loader import load_ui


class AuthWindow:
    """Cửa sổ đăng nhập / đăng ký — load từ `auth_window.ui`."""

    def __init__(self, on_success: Callable[[dict], None]) -> None:
        self._on_success = on_success
        win = load_ui(resource_ui("auth_window.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("auth_window.ui phải là QMainWindow")
        self.win = win
        apply_theme_qss(self.win, "auth_shell")

        form_outer = win.findChild(QFrame, "formOuter")
        if form_outer is not None:
            lo = form_outer.layout()
            if lo is not None and lo.count() >= 2:
                lo.setStretch(1, 1)

        self.line_login_email = win.findChild(QLineEdit, "lineLoginEmail")
        self.line_login_password = win.findChild(QLineEdit, "lineLoginPassword")
        self.btn_login = win.findChild(QPushButton, "btnLogin")

        self.line_reg_name = win.findChild(QLineEdit, "lineRegFullName")
        self.line_reg_email = win.findChild(QLineEdit, "lineRegEmail")
        self.line_reg_password = win.findChild(QLineEdit, "lineRegPassword")
        self.check_is_hr = win.findChild(QCheckBox, "checkHr")
        self.group_hr = win.findChild(QGroupBox, "groupHr")
        self.line_company = win.findChild(QLineEdit, "lineCompany")
        self.line_phone = win.findChild(QLineEdit, "linePhone")
        self.plain_company = win.findChild(QPlainTextEdit, "plainCompanyDesc")
        self.btn_register = win.findChild(QPushButton, "btnRegister")

        self.tab = win.findChild(QTabWidget, "tabWidget")
        if self.tab:
            self.tab.setDocumentMode(True)
            self.tab.setElideMode(Qt.ElideNone)
            tb = self.tab.tabBar()
            tb.setExpanding(False)
            tb.setDrawBase(False)

        if self.check_is_hr and self.group_hr:
            self.check_is_hr.toggled.connect(self._toggle_hr)
            self._toggle_hr(self.check_is_hr.isChecked())
        if self.btn_login:
            self.btn_login.clicked.connect(self._do_login)
        if self.btn_register:
            self.btn_register.clicked.connect(self._do_register)

    def _toggle_hr(self, checked: bool) -> None:
        if self.group_hr:
            self.group_hr.setEnabled(checked)
            self.group_hr.setVisible(checked)

    def _do_login(self) -> None:
        email = self.line_login_email.text().strip() if self.line_login_email else ""
        password = self.line_login_password.text() if self.line_login_password else ""
        if not email or not password:
            QMessageBox.warning(self.win, "JobHub", "Nhập email và mật khẩu.")
            return
        try:
            jobhub_api.health()
        except Exception:
            QMessageBox.critical(
                self.win,
                "JobHub",
                "Không kết nối được máy chủ",
            )
            return
        try:
            data = jobhub_api.login(email, password)
        except ApiError as e:
            QMessageBox.critical(self.win, "Đăng nhập", str(e))
            return
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

    def _do_register(self) -> None:
        email = self.line_reg_email.text().strip() if self.line_reg_email else ""
        password = self.line_reg_password.text() if self.line_reg_password else ""
        full_name = self.line_reg_name.text().strip() if self.line_reg_name else None
        if not email or not password:
            QMessageBox.warning(self.win, "JobHub", "Nhập email và mật khẩu.")
            return
        try:
            jobhub_api.health()
        except Exception:
            QMessageBox.critical(
                self.win,
                "JobHub",
                "Không kết nối được máy chủ",
            )
            return
        try:
            if self.check_is_hr and self.check_is_hr.isChecked():
                company = self.line_company.text().strip() if self.line_company else ""
                if not company:
                    QMessageBox.warning(self.win, "JobHub", "Nhập tên công ty.")
                    return
                phone = self.line_phone.text().strip() if self.line_phone else None
                desc = self.plain_company.toPlainText().strip() if self.plain_company else None
                data = jobhub_api.register_hr(email, password, full_name, company, phone, desc or None)
            else:
                data = jobhub_api.register_candidate(email, password, full_name)
        except ApiError as e:
            QMessageBox.critical(self.win, "Đăng ký", str(e))
            return
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

    def show(self) -> None:
        self.win.show()

    def raise_(self) -> None:
        self.win.raise_()
        self.win.activateWindow()

    def set_startup_pos(self) -> None:
        self.win.setGeometry(120, 120, 520, 720)


def try_resume_session(on_success: Callable[[dict], None]) -> bool:
    """Nếu có token hợp lệ, bỏ qua màn hình đăng nhập."""
    if not session_store.get_token():
        return False
    try:
        user = jobhub_api.me()
    except Exception:
        session_store.clear_session()
        return False
    session_store.save_session(session_store.get_token(), user)
    on_success(user)
    return True
