"""
quanly_enhanced.py  –  JobHub Admin Panel – UI Enhancement Module
==================================================================
Áp dụng cho 3 màn hình: QuanLyUser · QuanLyHR · QuanLyJobs

Tính năng v2 (modern web dashboard):
  ✦ SVG icons cho toàn bộ Sidebar nav buttons
  ✦ Tải và áp dụng admin_modern.qss (dark sidebar, striped table …)
  ✦ Status badges dạng pill có màu theo trạng thái
  ✦ Action buttons với SVG icon – View / Edit / Delete / Lock-Unlock
  ✦ PaginationWidget: phân trang đầy đủ với ellipsis, prev/next
  ✦ Search bar: inject icon kính lúp qua background-image QSS
  ✦ Column resize: Stretch cho nội dung, ResizeToContents cho ngắn
  ✦ Row height 58px, alternating rows, hover tím nhạt

Cách dùng nhanh:
    from app.ui.quanly_enhanced import enhance_quanly_hr
    win = load_ui(resource_ui("QuanLyHR.ui"))
    enhance_quanly_hr(win)
    win.show()
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

# ─── Paths ─────────────────────────────────────────────────────────────────────

_HERE      = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR  = os.path.normpath(os.path.join(_HERE, "..", "..", "resources", "icons"))
_STYLES_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "resources", "ui", "styles"))


def _icon(name: str) -> QIcon:
    return QIcon(os.path.join(ICONS_DIR, name))


def load_modern_qss() -> str:
    """Đọc file admin_modern.qss và trả về nội dung string."""
    path = os.path.join(_STYLES_DIR, "admin_modern.qss")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def apply_modern_qss(win: QMainWindow) -> None:
    """Áp dụng admin_modern.qss lên toàn bộ cửa sổ."""
    qss = load_modern_qss()
    if qss:
        # Nối vào stylesheet hiện tại để không mất inline styles từ .ui
        current = win.styleSheet() or ""
        win.setStyleSheet(current + "\n" + qss)


# ─────────────────────────────────────────────────────────────────────────────
#  STATUS BADGE  –  pill shape với màu theo trạng thái
# ─────────────────────────────────────────────────────────────────────────────

_STATUS_PALETTE: dict[str, tuple[str, str]] = {
    # fg_color, bg_color
    "Hoạt động":  ("#059669", "#D1FAE5"),   # xanh lá
    "Đang tuyển": ("#059669", "#D1FAE5"),
    "Bị khóa":    ("#DC2626", "#FEE2E2"),   # đỏ
    "Vi phạm":    ("#DC2626", "#FEE2E2"),
    "Đã đóng":    ("#64748B", "#F1F5F9"),   # xám
    "Chờ duyệt":  ("#D97706", "#FEF3C7"),   # vàng
}

_BADGE_TEMPLATE = """
    QLabel {{
        background-color: {bg};
        color: {fg};
        border-radius: 11px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 600;
        font-family: 'Segoe UI', sans-serif;
        min-width: 86px;
        max-width: 120px;
    }}
"""


def make_status_badge(text: str) -> QWidget:
    """
    Tạo widget badge dạng viên thuốc (pill) màu sắc theo trạng thái:
    • Hoạt động / Đang tuyển → xanh lá (#059669 / #D1FAE5)
    • Bị khóa  / Vi phạm    → đỏ      (#DC2626 / #FEE2E2)
    • Đã đóng               → xám     (#64748B / #F1F5F9)
    • Chờ duyệt             → vàng    (#D97706 / #FEF3C7)
    """
    container = QWidget()
    container.setStyleSheet("background: transparent;")

    lay = QHBoxLayout(container)
    lay.setContentsMargins(4, 0, 4, 0)
    lay.setAlignment(Qt.AlignCenter)
    lay.setSpacing(0)

    badge = QLabel(text.strip())
    badge.setAlignment(Qt.AlignCenter)
    badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    fg, bg = _STATUS_PALETTE.get(text.strip(), ("#374151", "#F3F4F6"))
    badge.setStyleSheet(_BADGE_TEMPLATE.format(fg=fg, bg=bg))

    lay.addWidget(badge)
    return container


# ─────────────────────────────────────────────────────────────────────────────
#  ACTION BUTTONS  –  View / Edit / Delete / Lock-Unlock
# ─────────────────────────────────────────────────────────────────────────────

_BTN_STYLE = """
    QPushButton {{
        background-color: {bg};
        border: none;
        border-radius: 8px;
    }}
    QPushButton:hover {{
        background-color: {bg_hover};
    }}
    QPushButton:pressed {{
        background-color: {bg_press};
    }}
"""


def _action_btn(
    icon_name: str,
    tooltip: str,
    bg: str,
    bg_hover: str,
    bg_press: str,
    callback: Optional[Callable] = None,
    size: int = 32,
) -> QPushButton:
    """Nút icon 32×32 bo góc với hover effect."""
    btn = QPushButton()
    btn.setIcon(_icon(icon_name))
    btn.setIconSize(QSize(16, 16))
    btn.setFixedSize(size, size)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(_BTN_STYLE.format(bg=bg, bg_hover=bg_hover, bg_press=bg_press))
    if callback:
        btn.clicked.connect(callback)
    return btn


def make_action_buttons(
    on_view:   Optional[Callable] = None,
    on_edit:   Optional[Callable] = None,
    on_delete: Optional[Callable] = None,
    on_lock:   Optional[Callable] = None,
    is_locked: bool = False,
) -> QWidget:
    """
    Tạo nhóm nút thao tác có SVG icon:
      👁  Xem chi tiết  – nền tím nhạt
      ✏  Chỉnh sửa     – nền xanh nhạt
      🗑  Xóa           – nền đỏ nhạt
      🔒  Khóa          – nền vàng nhạt  (chỉ hiện khi on_lock được truyền)
      🔓  Mở khóa       – nền xanh nhạt  (chỉ hiện khi on_lock + is_locked=True)

    Các nút cách đều nhau 5px, canh giữa ô.
    """
    container = QWidget()
    container.setStyleSheet("background: transparent;")

    lay = QHBoxLayout(container)
    lay.setContentsMargins(4, 4, 4, 4)
    lay.setSpacing(5)
    lay.setAlignment(Qt.AlignCenter)

    lay.addWidget(_action_btn(
        "ic_view.svg", "Xem chi tiết",
        "#EDE9FE", "#DDD6FE", "#C4B5FD", on_view))

    lay.addWidget(_action_btn(
        "ic_edit.svg", "Chỉnh sửa",
        "#DBEAFE", "#BFDBFE", "#93C5FD", on_edit))

    lay.addWidget(_action_btn(
        "ic_delete.svg", "Xóa",
        "#FEE2E2", "#FECACA", "#FCA5A5", on_delete))

    if on_lock is not None:
        if is_locked:
            lay.addWidget(_action_btn(
                "ic_unlock.svg", "Mở khóa tài khoản",
                "#D1FAE5", "#A7F3D0", "#6EE7B7", on_lock))
        else:
            lay.addWidget(_action_btn(
                "ic_lock.svg", "Khóa tài khoản",
                "#FEF3C7", "#FDE68A", "#FCD34D", on_lock))

    return container


# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR NAV ICONS
# ─────────────────────────────────────────────────────────────────────────────

_NAV_ICON_MAP: dict[str, str] = {
    "navDashboard":   "ic_dashboard.svg",
    "navDash":        "ic_dashboard.svg",
    "navQuanLyUser":  "ic_users.svg",
    "navUser":        "ic_users.svg",
    "navUsers":       "ic_users.svg",
    "navQuanLyHR":    "ic_hr.svg",
    "navHR":          "ic_hr.svg",
    "navHr":          "ic_hr.svg",
    "navQuanLyJobs":  "ic_jobs.svg",
    "navJobs":        "ic_jobs.svg",
    "navJob":         "ic_jobs.svg",
    "dangXuatButton": "ic_logout.svg",
    "btnDangXuat":    "ic_logout.svg",
    "btnLogout":      "ic_logout.svg",
    "logoutButton":   "ic_logout.svg",
}

_NAV_ICON_SIZE = QSize(20, 20)


def apply_nav_icons(win: QMainWindow) -> None:
    """Gán SVG icon cho tất cả nav buttons theo objectName."""
    for obj_name, svg_file in _NAV_ICON_MAP.items():
        btn: Optional[QPushButton] = win.findChild(QPushButton, obj_name)
        if btn is not None:
            btn.setIcon(_icon(svg_file))
            btn.setIconSize(_NAV_ICON_SIZE)


# ─────────────────────────────────────────────────────────────────────────────
#  SEARCH BAR  –  inject icon kính lúp
# ─────────────────────────────────────────────────────────────────────────────

def apply_search_icon(search_input: QLineEdit) -> None:
    """
    Nhúng icon kính lúp vào QLineEdit bằng background-image QSS.
    Qt hỗ trợ url() với đường dẫn tuyệt đối (dùng forward-slash).
    """
    svg_path = os.path.join(ICONS_DIR, "ic_search.svg").replace("\\", "/")
    existing = search_input.styleSheet() or ""
    extra = f"""
        QLineEdit {{
            padding-left: 38px;
            background-image: url("{svg_path}");
            background-repeat: no-repeat;
            background-position: left 10px center;
        }}
    """
    search_input.setStyleSheet(existing + extra)


# ─────────────────────────────────────────────────────────────────────────────
#  TABLE ENHANCEMENT  –  one-call upgrade toàn bộ table
# ─────────────────────────────────────────────────────────────────────────────

_HOVER_PATCH = "QTableWidget::item:hover { background-color: #F5F3FF; }\n"


def enhance_table(
    table:          QTableWidget,
    status_col:     int,
    action_col:     int,
    stretch_cols:   Optional[list[int]] = None,
    row_height:     int = 58,
    show_lock_btn:  bool = False,
) -> None:
    """
    Nâng cấp toàn diện QTableWidget:
    1. Hover QSS (tím nhạt #F5F3FF)
    2. alternatingRowColors = True
    3. Column resize: ID→ResizeToContents, nội dung→Stretch, status/action→Fixed
    4. Header: font DemiBold, align Left
    5. Ẩn vertical header (row numbers)
    6. Row height = row_height px
    7. Thay status cell → pill badge widget
    8. Thay action cell → icon buttons widget
    9. Căn lề text items

    Args:
        show_lock_btn: Nếu True, cột Thao tác có thêm nút Khóa/Mở khóa.
                       Status "Bị khóa" → nút Mở khóa (xanh); còn lại → nút Khóa (vàng).
    """
    if table is None:
        return

    # ── 0. Hover + alternating rows ────────────────────────────────
    existing_qss = table.styleSheet() or ""
    if "::item:hover" not in existing_qss:
        table.setStyleSheet(existing_qss + _HOVER_PATCH)
    table.setAlternatingRowColors(True)

    # ── 1. Column resize ────────────────────────────────────────────
    hh = table.horizontalHeader()
    col_count = table.columnCount()
    if stretch_cols is None:
        stretch_cols = [1, 2] if col_count > 4 else [1]

    for c in range(col_count):
        if c == 0:
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        elif c == action_col:
            col_w = 160 if show_lock_btn else 130
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(c, col_w)
        elif c == status_col:
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(c, 148)
        elif c in stretch_cols:
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)
        else:
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)

    hh.setMinimumSectionSize(56)

    # ── 2. Header font + alignment ──────────────────────────────────
    hfont = QFont("Segoe UI", 11)
    hfont.setWeight(QFont.Weight.DemiBold)
    hh.setFont(hfont)
    hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    # ── 3. Vertical header ──────────────────────────────────────────
    table.verticalHeader().setVisible(False)

    # ── 4. Rows: height + badge + action buttons ────────────────────
    for row in range(table.rowCount()):
        table.setRowHeight(row, row_height)

        # Căn lề text items
        for col in range(col_count):
            item = table.item(row, col)
            if item is None:
                continue
            align = (Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                     if col == 0
                     else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(int(align))

        # Status badge
        st_item = table.item(row, status_col)
        if st_item and st_item.text().strip():
            status_text = st_item.text().strip()
            table.takeItem(row, status_col)
            table.setCellWidget(row, status_col, make_status_badge(status_text))

        # Action buttons
        table.takeItem(row, action_col)
        if show_lock_btn:
            # Xác định trạng thái locked từ cột status (đã bị thay bằng widget)
            # Lấy status text từ dữ liệu gốc đã lưu
            is_locked = False
            status_widget = table.cellWidget(row, status_col)
            if status_widget:
                lbl = status_widget.findChild(QLabel)
                if lbl and lbl.text() in ("Bị khóa", "Vi phạm"):
                    is_locked = True
            table.setCellWidget(row, action_col,
                                make_action_buttons(is_locked=is_locked, on_lock=lambda: None))
        else:
            table.setCellWidget(row, action_col, make_action_buttons())


# ─────────────────────────────────────────────────────────────────────────────
#  PAGINATION WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class PaginationWidget(QWidget):
    """
    Widget phân trang hiện đại với prev/next, số trang, dấu ellipsis (…).

    Signals:
        pageChanged(int): Phát ra số trang mới (1-indexed) khi người dùng chuyển trang.

    Cách dùng:
        pg = PaginationWidget(total_items=87, items_per_page=10)
        pg.pageChanged.connect(lambda p: print(f"Chuyển trang {p}"))
        table_card.layout().addWidget(pg)
    """

    pageChanged = Signal(int)

    def __init__(
        self,
        total_items:    int = 10,
        items_per_page: int = 10,
        parent:         Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.total_items    = total_items
        self.items_per_page = items_per_page
        self.current_page   = 1
        self.setObjectName("paginationFrame")
        self.setFixedHeight(60)
        self._setup_ui()
        self._refresh()

    # ── Properties ─────────────────────────────────────────────────
    @property
    def total_pages(self) -> int:
        return max(1, (self.total_items + self.items_per_page - 1) // self.items_per_page)

    def set_total(self, total: int) -> None:
        """Cập nhật tổng số items (ví dụ sau khi load data từ API)."""
        self.total_items = total
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        self._refresh()

    # ── Setup UI ────────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            QWidget#paginationFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #F1F5F9;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 0, 20, 0)
        root.setSpacing(6)

        # ── Info label ──
        self._lbl_info = QLabel()
        self._lbl_info.setStyleSheet(
            "color: #64748B; font-size: 13px; font-family: 'Segoe UI', sans-serif; background: transparent;"
        )
        root.addWidget(self._lbl_info)
        root.addStretch()

        # ── Prev button ──
        self._btn_prev = self._nav_btn("ic_chevron_left.svg", "Trang trước")
        self._btn_prev.clicked.connect(self._go_prev)
        root.addWidget(self._btn_prev)

        # ── Page buttons container ──
        self._pages_container = QHBoxLayout()
        self._pages_container.setSpacing(4)
        root.addLayout(self._pages_container)

        # ── Next button ──
        self._btn_next = self._nav_btn("ic_chevron_right.svg", "Trang sau")
        self._btn_next.clicked.connect(self._go_next)
        root.addWidget(self._btn_next)

    # ── Button factories ────────────────────────────────────────────
    def _nav_btn(self, icon_name: str, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("class", "pageNavBtn")
        btn.setIcon(_icon(icon_name))
        btn.setIconSize(QSize(14, 14))
        btn.setFixedSize(36, 36)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #EDE9FE;
                border-color: #7B2FBE;
            }
            QPushButton:disabled {
                background-color: #F8FAFF;
                border-color: #E2E8F0;
                opacity: 0.4;
            }
        """)
        return btn

    def _page_btn(self, page: int) -> QPushButton:
        is_active = (page == self.current_page)
        btn = QPushButton(str(page))
        btn.setFixedSize(36, 36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        if is_active:
            btn.setProperty("class", "pageBtnActive")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #7B2FBE;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 700;
                    font-family: 'Segoe UI', sans-serif;
                }
            """)
        else:
            btn.setProperty("class", "pageBtn")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #475569;
                    border: 1.5px solid #E2E8F0;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 500;
                    font-family: 'Segoe UI', sans-serif;
                }
                QPushButton:hover {
                    background-color: #F5F3FF;
                    border-color: #7B2FBE;
                    color: #7B2FBE;
                }
            """)
            btn.clicked.connect(lambda _=False, p=page: self._go_to(p))

        return btn

    def _ellipsis_label(self) -> QLabel:
        lbl = QLabel("…")
        lbl.setFixedSize(28, 36)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color: #94A3B8; font-size: 15px; font-family: 'Segoe UI', sans-serif; background: transparent;"
        )
        return lbl

    # ── Refresh ────────────────────────────────────────────────────
    def _refresh(self) -> None:
        # Info label
        start = (self.current_page - 1) * self.items_per_page + 1
        end   = min(self.current_page * self.items_per_page, self.total_items)
        self._lbl_info.setText(
            f"Hiển thị <b>{start}–{end}</b> trong <b>{self.total_items}</b> kết quả"
        )

        # Clear page buttons
        while self._pages_container.count():
            item = self._pages_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # Build page list with smart ellipsis
        pages = self._visible_pages()
        prev_p: Optional[int] = None
        for p in pages:
            if prev_p is not None and p - prev_p > 1:
                self._pages_container.addWidget(self._ellipsis_label())
            self._pages_container.addWidget(self._page_btn(p))
            prev_p = p

        # Prev/Next enabled state
        self._btn_prev.setEnabled(self.current_page > 1)
        self._btn_next.setEnabled(self.current_page < self.total_pages)

    def _visible_pages(self) -> list[int]:
        """
        Trả về danh sách số trang cần hiển thị (có thể có khoảng trống → ellipsis).
        Logic: Luôn hiện trang 1, 2, tp-1, tp và các trang quanh current_page.
        """
        tp = self.total_pages
        cp = self.current_page
        if tp <= 7:
            return list(range(1, tp + 1))
        pages: set[int] = {1, 2, tp - 1, tp}
        for p in range(max(1, cp - 1), min(tp + 1, cp + 2)):
            pages.add(p)
        return sorted(pages)

    # ── Navigation ─────────────────────────────────────────────────
    def _go_prev(self) -> None:
        if self.current_page > 1:
            self._go_to(self.current_page - 1)

    def _go_next(self) -> None:
        if self.current_page < self.total_pages:
            self._go_to(self.current_page + 1)

    def _go_to(self, page: int) -> None:
        self.current_page = page
        self._refresh()
        self.pageChanged.emit(page)


def inject_pagination(
    table_card:    QFrame,
    total_items:   int = 10,
    items_per_page: int = 10,
) -> PaginationWidget:
    """
    Thêm PaginationWidget vào cuối layout của tableCard QFrame.

    Nếu tableCard đã có paginationFrame (từ .ui), sẽ nhúng vào bên trong;
    ngược lại thêm trực tiếp vào layout.

    Returns:
        PaginationWidget instance (có thể kết nối pageChanged signal)
    """
    pagination = PaginationWidget(
        total_items=total_items,
        items_per_page=items_per_page,
    )

    # Thử nhúng vào paginationFrame có sẵn trong .ui
    pg_frame: Optional[QFrame] = table_card.findChild(QFrame, "paginationFrame")
    if pg_frame is not None:
        if pg_frame.layout() is None:
            lay = QHBoxLayout(pg_frame)
            lay.setContentsMargins(0, 0, 0, 0)
        pg_frame.layout().addWidget(pagination)
        pg_frame.setFixedHeight(60)
    else:
        # Fallback: thêm thẳng vào tableCard layout
        if table_card.layout():
            table_card.layout().addWidget(pagination)

    return pagination


# ─────────────────────────────────────────────────────────────────────────────
#  FULL ENHANCE FUNCTIONS  –  một lệnh cho từng màn hình
# ─────────────────────────────────────────────────────────────────────────────

def enhance_quanly_user(win: QMainWindow) -> Optional[PaginationWidget]:
    """
    Áp dụng toàn bộ cải tiến cho QuanLyUser.

    Columns: ID(0) | Họ tên(1) | Email(2) | SĐT(3) |
             Ngày tham gia(4) | Đơn ứng tuyển(5) | Trạng thái(6) | Thao tác(7)
    """
    apply_modern_qss(win)
    apply_nav_icons(win)

    search: Optional[QLineEdit] = win.findChild(QLineEdit, "searchInput")
    if search:
        apply_search_icon(search)

    table: Optional[QTableWidget] = win.findChild(QTableWidget, "userTable")
    if table:
        enhance_table(table, status_col=6, action_col=7,
                      stretch_cols=[1, 2], show_lock_btn=True)

    table_card: Optional[QFrame] = win.findChild(QFrame, "tableCard")
    if table_card:
        row_count = table.rowCount() if table else 10
        return inject_pagination(table_card, total_items=row_count)
    return None


def enhance_quanly_hr(win: QMainWindow) -> Optional[PaginationWidget]:
    """
    Áp dụng toàn bộ cải tiến cho QuanLyHR.

    Columns: ID(0) | Tên công ty(1) | Email(2) | SĐT(3) |
             Ngày tham gia(4) | Tin đã đăng(5) | Trạng thái(6) | Thao tác(7)
    """
    apply_modern_qss(win)
    apply_nav_icons(win)

    search: Optional[QLineEdit] = win.findChild(QLineEdit, "searchInput")
    if search:
        apply_search_icon(search)

    table: Optional[QTableWidget] = win.findChild(QTableWidget, "hrTable")
    if table:
        enhance_table(table, status_col=6, action_col=7,
                      stretch_cols=[1, 2], show_lock_btn=True)

    table_card: Optional[QFrame] = win.findChild(QFrame, "tableCard")
    if table_card:
        row_count = table.rowCount() if table else 10
        return inject_pagination(table_card, total_items=row_count)
    return None


def enhance_quanly_jobs(win: QMainWindow) -> Optional[PaginationWidget]:
    """
    Áp dụng toàn bộ cải tiến cho QuanLyJobs.

    Columns: ID(0) | Vị trí(1) | Công ty(2) | Địa điểm(3) | Lương(4) |
             Loại hình(5) | Ứng viên(6) | Ngày đăng(7) | Trạng thái(8) | Thao tác(9)
    """
    apply_modern_qss(win)
    apply_nav_icons(win)

    search: Optional[QLineEdit] = win.findChild(QLineEdit, "searchInput")
    if search:
        apply_search_icon(search)

    table: Optional[QTableWidget] = win.findChild(QTableWidget, "jobTable")
    if table:
        enhance_table(table, status_col=8, action_col=9,
                      stretch_cols=[1, 2], show_lock_btn=False)

    table_card: Optional[QFrame] = win.findChild(QFrame, "tableCard")
    if table_card:
        row_count = table.rowCount() if table else 10
        return inject_pagination(table_card, total_items=row_count)
    return None
