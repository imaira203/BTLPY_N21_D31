"""JobHub desktop client — PySide6 + file .ui."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor, QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

# Enable High DPI scaling
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

from app.config import log_client_startup
from app.ui.admin_dashboard import AdminDashboard
from app.ui.auth_window import AuthWindow, try_resume_session
from app.ui.hr_dashboard import HRDashboard
from app.ui.user_dashboard import UserDashboard

# Font files directory (bundled with app)
_FONTS_DIR = Path(__file__).resolve().parent / "resources" / "fonts"


def _load_bundled_fonts() -> str:
    """
    Load Plus Jakarta Sans from resources/fonts/ if present.
    Returns the family name that was successfully loaded, or empty string.
    """
    if not _FONTS_DIR.exists():
        return ""

    loaded_family = ""
    # Expected weight files — load all available
    for ttf in sorted(_FONTS_DIR.glob("*.ttf")):
        fid = QFontDatabase.addApplicationFont(str(ttf))
        if fid >= 0:
            families = QFontDatabase.applicationFontFamilies(fid)
            if families and not loaded_family:
                loaded_family = families[0]
                logging.getLogger(__name__).info(
                    "Loaded bundled font: %s (%s)", families[0], ttf.name
                )
    return loaded_family


class JobHubApp:
    def __init__(self) -> None:
        self.qapp = QApplication(sys.argv)

        # ── Load bundled fonts first, then set global font ──────
        bundled = _load_bundled_fonts()   # e.g. "Plus Jakarta Sans"

        ui_font = QFont()
        if bundled:
            # Bundled font loaded — use it as first priority
            ui_font.setFamilies([
                bundled,
                "Inter", "SF Pro Display",
                "Segoe UI", "Helvetica Neue", "Arial", "sans-serif",
            ])
        else:
            # Fallback: rely on system-installed fonts
            ui_font.setFamilies([
                "Plus Jakarta Sans", "Inter", "SF Pro Display",
                "Segoe UI", "Helvetica Neue", "Arial", "sans-serif",
            ])
        ui_font.setPointSizeF(10.0)
        ui_font.setStyleHint(QFont.SansSerif)
        self.qapp.setFont(ui_font)

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
