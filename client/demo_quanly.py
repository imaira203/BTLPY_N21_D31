"""
demo_quanly.py
==============
Script chạy thử 3 màn hình Admin QuanLy với mock data đầy đủ và UI enhancements.

Cách chạy:
    cd client
    python demo_quanly.py user       # Quản lý User
    python demo_quanly.py hr         # Quản lý HR
    python demo_quanly.py jobs       # Quản lý Jobs
    python demo_quanly.py            # Mặc định: Quản lý User

Yêu cầu: PySide6
    pip install PySide6
"""

from __future__ import annotations

import sys
import os

# ── Thêm thư mục client vào PYTHONPATH ──────────────────────────────────────
_CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CLIENT_DIR not in sys.path:
    sys.path.insert(0, _CLIENT_DIR)

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

# ── Import enhancement module ────────────────────────────────────────────────
from app.ui.quanly_enhanced import (
    enhance_quanly_user,
    enhance_quanly_hr,
    enhance_quanly_jobs,
)


# ── UI Loader (tái sử dụng loader có sẵn hoặc dùng trực tiếp) ───────────────
def _load_ui(ui_path: str) -> QMainWindow:
    """Load .ui file và trả về QMainWindow."""
    try:
        # Thử dùng ui_loader có sẵn trong project
        from app.ui.ui_loader import load_ui
        win = load_ui(ui_path)
    except ImportError:
        # Fallback: dùng PySide6.QtUiTools trực tiếp
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtCore import QFile, QIODevice
        loader = QUiLoader()
        f = QFile(ui_path)
        if not f.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"Không thể mở file UI: {ui_path}")
        win = loader.load(f)
        f.close()
    return win


def _resource_ui(name: str) -> str:
    """Trả về đường dẫn tuyệt đối tới file .ui."""
    try:
        from app.paths import resource_ui
        return resource_ui(name)
    except ImportError:
        return os.path.join(_CLIENT_DIR, "resources", "ui", name)


def _setup_light_palette(app: QApplication) -> None:
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
    
    app.setPalette(palette)


# ── Panel runners ────────────────────────────────────────────────────────────

def run_user_panel() -> None:
    """Mở màn hình Quản lý User với full mock data & enhancements."""
    win = _load_ui(_resource_ui("QuanLyUser.ui"))
    enhance_quanly_user(win)
    win.setWindowTitle("JobHub Admin – Quản lý User  [DEMO]")
    win.show()


def run_hr_panel() -> None:
    """Mở màn hình Quản lý HR với full mock data & enhancements."""
    win = _load_ui(_resource_ui("QuanLyHR.ui"))
    enhance_quanly_hr(win)
    win.setWindowTitle("JobHub Admin – Quản lý HR  [DEMO]")
    win.show()


def run_jobs_panel() -> None:
    """Mở màn hình Quản lý Jobs với full mock data & enhancements."""
    win = _load_ui(_resource_ui("QuanLyJobs.ui"))
    enhance_quanly_jobs(win)
    win.setWindowTitle("JobHub Admin – Quản lý Jobs  [DEMO]")
    win.show()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")  # Base style – QSS sẽ override
    
    # Force light theme globally
    _setup_light_palette(app)

    panel = sys.argv[1].lower() if len(sys.argv) > 1 else "user"

    _runners = {
        "user":  run_user_panel,
        "hr":    run_hr_panel,
        "jobs":  run_jobs_panel,
    }

    runner = _runners.get(panel)
    if runner is None:
        print(f"Panel không hợp lệ: '{panel}'")
        print(f"Các giá trị hợp lệ: {', '.join(_runners.keys())}")
        sys.exit(1)

    print(f"[JobHub Demo] Đang mở panel: {panel.upper()}")
    runner()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
