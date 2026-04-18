from __future__ import annotations

import os
from typing import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QFont, QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFrame,
)

from ..client import jobhub_api
from ..paths import resource_icon, resource_ui
from ..session_store import clear_session
from .ui_loader import load_ui
from .quanly_enhanced import enhance_table, make_status_badge


class UserDashboard:
    """Optimized Dashboard for Candidates with Modernized Profile and Saved Jobs."""

    def __init__(self, on_logout: Callable[[], None]) -> None:
        self._on_logout = on_logout
        win = load_ui(resource_ui("user_dashboard.ui"))
        if not isinstance(win, QMainWindow):
            raise TypeError("user_dashboard.ui phải là QMainWindow")
        self.win = win

        self._bind_widgets()
        self._setup_navigation()
        self._load_jobs_grid(self.jobs_grid)
        self._load_jobs_grid(self.saved_jobs_grid, is_saved=True)
        self._load_history_table()
        self._go(0)

    def _bind_widgets(self) -> None:
        # Navigation
        self.nav_home = self.win.findChild(QPushButton, "navHome")
        self.nav_history = self.win.findChild(QPushButton, "navHistory")
        self.nav_saved = self.win.findChild(QPushButton, "navSaved")
        self.nav_profile = self.win.findChild(QPushButton, "navProfile")
        self.btn_logout = self.win.findChild(QPushButton, "btnLogout")
        
        # Content
        self.stack = self.win.findChild(QStackedWidget, "stackedPages")
        self.jobs_grid = self.win.findChild(QGridLayout, "jobsGrid")
        self.saved_jobs_grid = self.win.findChild(QGridLayout, "savedJobsGrid")
        self.table_apps = self.win.findChild(QTableWidget, "tableApps")
        self.page_title = self.win.findChild(QLabel, "pageTitle")
        self.page_subtitle = self.win.findChild(QLabel, "pageSubTitle")

        # Profile Page Buttons
        self.btn_edit_profile = self.win.findChild(QPushButton, "btnEditProfile")
        self.btn_view_cv = self.win.findChild(QPushButton, "btnViewCV")
        self.btn_download_cv = self.win.findChild(QPushButton, "btnDownloadCV")
        self.btn_replace_cv = self.win.findChild(QPushButton, "btnReplaceCV")

    def _setup_navigation(self) -> None:
        self._nav_group = QButtonGroup(self.win)
        nav_buttons = [
            (self.nav_home, 0, "ic_dashboard.svg"),
            (self.nav_history, 1, "ic_folder.svg"),
            (self.nav_saved, 2, "bookmark_filled.svg"),
            (self.nav_profile, 3, "ic_user.svg"),
        ]
        for idx, (btn, target_idx, icon_name) in enumerate(nav_buttons):
            if btn:
                btn.setCheckable(True)
                btn.setIcon(QIcon(str(resource_icon(icon_name))))
                btn.setIconSize(QSize(20, 20))
                self._nav_group.addButton(btn)
                btn.clicked.connect(lambda checked, i=target_idx: self._go(i))
        
        if self.btn_logout:
            self.btn_logout.setIcon(QIcon(str(resource_icon("ic_logout.svg"))))
            self.btn_logout.setIconSize(QSize(20, 20))
            self.btn_logout.clicked.connect(self._logout)

    def _go(self, index: int) -> None:
        if self.stack:
            self.stack.setCurrentIndex(index)
        
        titles = ["Khám phá việc làm", "Lịch sử ứng tuyển", "Việc làm đã lưu", "Hồ sơ cá nhân"]
        subtitles = [
            "Hàng ngàn cơ hội đang chờ đợi bạn",
            "Theo dõi trạng thái các đơn ứng tuyển của bạn",
            "Danh sách các vị trí bạn quan tâm",
            "Quản lý thông tin cá nhân và CV của bạn"
        ]
        
        if self.page_title and index < len(titles):
            self.page_title.setText(titles[index])
        if self.page_subtitle and index < len(subtitles):
            self.page_subtitle.setText(subtitles[index])

    def _load_jobs_grid(self, grid: QGridLayout, is_saved=False) -> None:
        if not grid: return
        
        jobs = [
            ("Senior Frontend Developer", "TechCorp Vietnam", "Toàn thời gian", "$2000 - $3000", "Hà Nội"),
            ("Backend Developer (Node.js)", "StartUp Innovation", "Toàn thời gian", "$1500 - $2500", "TP. Hồ Chí Minh"),
            ("UI/UX Designer", "Design Studio", "Từ xa", "$1200 - $1800", "Hà Nội / Remote"),
        ]
        if not is_saved:
            jobs += [
                ("Full Stack Developer", "Digital Agency", "Toàn thời gian", "$2500 - $4000", "Đà Nẵng"),
                ("Mobile Engineer (Flutter)", "Global IT Solutions", "Bán thời gian", "$1000 - $1500", "Remote"),
                ("DevOps Architect", "Cloud Systems", "Toàn thời gian", "$3500 - $5000", "Hà Nội"),
            ]
        
        while grid.count():
            item = grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        for i, (title, comp, ttype, sal, loc) in enumerate(jobs):
            card = QFrame()
            card.setObjectName("jobCard")
            card.setStyleSheet("""
                QFrame#jobCard {
                    background-color: white;
                    border: 1px solid #E2E8F0;
                    border-radius: 20px;
                    padding: 24px;
                }
                QFrame#jobCard:hover {
                    border: 1px solid #6366F1;
                    background-color: #F8FAFC;
                }
            """)
            lay = QVBoxLayout(card)
            lay.setSpacing(12)
            
            h_header = QHBoxLayout()
            lbl_title = QLabel(title)
            lbl_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1E293B;")
            lbl_title.setWordWrap(True)
            btn_save = QPushButton()
            icon_name = "bookmark_filled.svg" if is_saved else "bookmark_outline.svg"
            btn_save.setIcon(QIcon(str(resource_icon(icon_name))))
            btn_save.setFixedSize(28, 28)
            btn_save.setStyleSheet("border: none; background: transparent;")
            h_header.addWidget(lbl_title)
            h_header.addWidget(btn_save)
            lay.addLayout(h_header)
            
            lbl_comp = QLabel(comp)
            lbl_comp.setStyleSheet("color: #64748B; font-size: 14px; font-weight: 600;")
            lay.addWidget(lbl_comp)
            
            h_badges = QHBoxLayout()
            h_badges.setSpacing(8)
            
            type_badge = QLabel(ttype)
            type_badge.setStyleSheet("background-color: #EEF2FF; color: #6366F1; border-radius: 8px; padding: 4px 10px; font-size: 11px; font-weight: 700;")
            
            sal_label = QLabel(sal)
            sal_label.setStyleSheet("color: #05CD99; font-size: 13px; font-weight: 700;")
            
            h_badges.addWidget(type_badge)
            h_badges.addWidget(sal_label)
            h_badges.addStretch()
            lay.addLayout(h_badges)
            
            lbl_loc = QLabel(f"📍 {loc}")
            lbl_loc.setStyleSheet("color: #94A3B8; font-size: 13px;")
            lay.addWidget(lbl_loc)
            
            lay.addStretch()
            
            btn_apply = QPushButton("Ứng tuyển ngay")
            btn_apply.setFixedHeight(42)
            btn_apply.setCursor(Qt.PointingHandCursor)
            btn_apply.setStyleSheet("""
                QPushButton {
                    background-color: #6366F1;
                    color: white;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #4F46E5;
                }
            """)
            lay.addWidget(btn_apply)
            
            grid.addWidget(card, i // 2, i % 2)

    def _load_history_table(self) -> None:
        if not self.table_apps: return
        
        data = [
            ("APP-101", "TechCorp Vietnam", "Senior Frontend Developer", "15/03/2024", "Hoạt động"),
            ("APP-102", "StartUp Innovation", "Backend Developer (Node.js)", "14/03/2024", "Hoạt động"),
            ("APP-103", "Creative Studio", "UI/UX Designer", "10/03/2024", "Bị khóa"),
        ]
        
        self.table_apps.setRowCount(0)
        self.table_apps.setRowCount(len(data))
        self.table_apps.setColumnCount(6)
        self.table_apps.setHorizontalHeaderLabels(["ID", "Công ty", "Vị trí", "Ngày ứng tuyển", "Trạng thái", "Thao tác"])
        
        for row, (id, comp, pos, date, status) in enumerate(data):
            self.table_apps.setItem(row, 0, QTableWidgetItem(id))
            comp_item = QTableWidgetItem(comp)
            comp_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table_apps.setItem(row, 1, comp_item)
            self.table_apps.setItem(row, 2, QTableWidgetItem(pos))
            self.table_apps.setItem(row, 3, QTableWidgetItem(date))
            self.table_apps.setItem(row, 4, QTableWidgetItem(status))
            self.table_apps.setItem(row, 5, QTableWidgetItem(""))
            
            if status == "Bị khóa":
                for col in range(6):
                    item = self.table_apps.item(row, col)
                    if item: item.setBackground(QColor(255, 241, 242))

        enhance_table(self.table_apps, status_col=4, action_col=5, stretch_cols=[1, 2])

    def _logout(self) -> None:
        clear_session()
        self.win.close()
        self._on_logout()

    def show(self) -> None:
        self.win.show()

    def raise_(self) -> None:
        self.win.raise_()
        self.win.activateWindow()
