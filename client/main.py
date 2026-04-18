"""JobHub desktop client — PySide6 + file .ui."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

# Enable High DPI scaling
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

from app.config import log_client_startup
from app.ui.admin_dashboard import AdminDashboard
from app.ui.auth_window import AuthWindow, try_resume_session
from app.ui.hr_dashboard import HRDashboard
from app.ui.user_dashboard import UserDashboard


class JobHubApp:
    def __init__(self) -> None:
        self.qapp = QApplication(sys.argv)
        
        # Force light theme globally
        self.qapp.setStyle("Fusion")  # Use Fusion style as base
        self._setup_light_palette()
        
        self._auth: AuthWindow | None = None
        self._dash: UserDashboard | HRDashboard | AdminDashboard | None = None
        if not try_resume_session(self._enter_main):
            self._show_auth()

    def _setup_light_palette(self) -> None:
        """Set light palette to override system dark theme."""
        palette = QPalette()
        
        # Background colors
        palette.setColor(QPalette.Window, QColor("#F5F5F5"))
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, QColor("#F0F0F0"))
        
        # Text colors
        palette.setColor(QPalette.WindowText, QColor("#000000"))
        palette.setColor(QPalette.Text, QColor("#000000"))
        palette.setColor(QPalette.ButtonText, QColor("#000000"))
        
        # Button colors
        palette.setColor(QPalette.Button, QColor("#F0F0F0"))
        palette.setColor(QPalette.BrightText, QColor("#FFFFFF"))
        
        # Highlight/selection colors
        palette.setColor(QPalette.Highlight, QColor("#0078D4"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
        
        # Link colors
        palette.setColor(QPalette.Link, QColor("#0078D4"))
        palette.setColor(QPalette.LinkVisited, QColor("#004B8F"))
        
        self.qapp.setPalette(palette)

    def _show_auth(self) -> None:
        self._dash = None
        self._auth = AuthWindow(self._enter_main)
        self._auth.show()

    def _enter_main(self, user: dict) -> None:
        self._auth = None
        role = user.get("role")
        if role == "candidate":
            self._dash = UserDashboard(self._show_auth)
        elif role == "hr":
            self._dash = HRDashboard(self._show_auth)
        elif role == "admin":
            self._dash = AdminDashboard(self._show_auth)
        else:
            self._show_auth()
            return
        self._dash.show()

    def run(self) -> int:
        return self.qapp.exec()


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s %(name)s: %(message)s",
    )
    log_client_startup()
    app = JobHubApp()
    raise SystemExit(app.run())


if __name__ == "__main__":
    main()
