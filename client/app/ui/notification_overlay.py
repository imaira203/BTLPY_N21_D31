from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class NotificationOverlayController(QObject):
    """Positions a notification panel as a right-side overlay and closes it on outside clicks."""

    def __init__(
        self,
        *,
        window: QWidget,
        host: QWidget,
        panel: QWidget,
        bell_button: QWidget | None = None,
        width: int = 400,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._host = host
        self._panel = panel
        self._bell_button = bell_button
        self._width = width

        self._panel.setParent(self._host)
        self._panel.setWindowFlags(Qt.Widget)
        self._panel.setFixedWidth(self._width)
        self._panel.hide()
        self.reposition()

        self._host.installEventFilter(self)
        self._window.installEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def reposition(self) -> None:
        host_w = max(0, self._host.width())
        host_h = max(0, self._host.height())
        panel_w = min(self._width, host_w) if host_w else self._width
        self._panel.setGeometry(max(0, host_w - panel_w), 0, panel_w, host_h)
        if self._panel.isVisible():
            self._panel.raise_()

    def show(self) -> None:
        self.reposition()
        self._panel.show()
        self._panel.raise_()

    def close(self) -> None:
        self._panel.hide()

    def eventFilter(self, obj, event) -> bool:  # noqa: N802
        if event.type() == QEvent.Resize and (obj is self._host or obj is self._window):
            self.reposition()
            return False

        if event.type() != QEvent.MouseButtonPress or not self._panel.isVisible():
            return False

        if not isinstance(obj, QWidget):
            return False

        if self._is_descendant(obj, self._panel):
            return False
        if self._bell_button is not None and self._is_descendant(obj, self._bell_button):
            return False

        if self._is_descendant(obj, self._window):
            self.close()
        return False

    @staticmethod
    def _is_descendant(widget: QWidget, ancestor: QWidget) -> bool:
        cur: QWidget | None = widget
        while cur is not None:
            if cur is ancestor:
                return True
            parent = cur.parentWidget()
            cur = parent if isinstance(parent, QWidget) else None
        return False


class NotificationCard(QFrame):
    def __init__(self, row: dict, on_click: Callable[[dict], None], parent=None) -> None:
        super().__init__(parent)
        self._row = row
        self._on_click = on_click
        is_read = bool(row.get("is_read"))
        accent = "#CBD5E1" if is_read else "#2563EB"
        bg = "#FFFFFF" if is_read else "#EFF6FF"
        border = "#E2E8F0" if is_read else "#BFDBFE"
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setStyleSheet(
            "QFrame#notifItem{"
            f"background:{bg};border:1px solid {border};border-left:4px solid {accent};"
            "border-radius:10px;"
            "}"
            "QFrame#notifItem:hover{background:#F8FAFC;border-color:#93C5FD;}"
        )
        self.setObjectName("notifItem")

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        dot = QLabel()
        dot.setFixedSize(9, 9)
        dot.setStyleSheet(
            f"background:{'#2563EB' if not is_read else '#CBD5E1'};"
            "border-radius:4px;border:none;"
        )
        root.addWidget(dot, 0, Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(5)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)
        title_lbl = QLabel(str(row.get("title") or "Thông báo"))
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            f"color:#0F172A;font-size:13px;font-weight:{'600' if is_read else '800'};"
            "background:transparent;border:none;"
        )
        top.addWidget(title_lbl, 1)

        time_txt = _format_notification_time(row.get("created_at"))
        if time_txt:
            time_lbl = QLabel(time_txt)
            time_lbl.setStyleSheet(
                "color:#94A3B8;font-size:10px;font-weight:700;"
                "background:transparent;border:none;"
            )
            top.addWidget(time_lbl, 0, Qt.AlignTop)
        text_col.addLayout(top)

        msg_lbl = QLabel(str(row.get("message") or ""))
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            "color:#475569;font-size:12px;line-height:150%;"
            "background:transparent;border:none;"
        )
        text_col.addWidget(msg_lbl)
        root.addLayout(text_col, 1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._on_click(self._row)
        super().mousePressEvent(event)


def populate_notification_list(
    layout: QVBoxLayout,
    rows: list[dict],
    *,
    build_item: Callable[[dict], QWidget],
    mark_all_cb: Callable[[], None],
) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()

    unread = [r for r in rows if not bool(r.get("is_read"))]
    read = [r for r in rows if bool(r.get("is_read"))]

    if unread:
        layout.addWidget(_mark_all_row(mark_all_cb))
        layout.addWidget(_section_label(f"Chưa đọc ({len(unread)})", "#1D4ED8"))
        for row in unread:
            layout.addWidget(build_item(row))

    if read:
        layout.addWidget(_section_label(f"Đã đọc ({len(read)})", "#64748B"))
        for row in read:
            layout.addWidget(build_item(row))

    if not rows:
        empty = QLabel("Không có thông báo")
        empty.setAlignment(Qt.AlignCenter)
        empty.setMinimumHeight(180)
        empty.setStyleSheet(
            "color:#94A3B8;font-size:13px;font-weight:600;"
            "background:transparent;border:none;"
        )
        layout.addWidget(empty)

    layout.addStretch()


def _mark_all_row(callback: Callable[[], None]) -> QWidget:
    row = QWidget()
    row.setStyleSheet("background:transparent;border:none;")
    lo = QHBoxLayout(row)
    lo.setContentsMargins(14, 10, 14, 8)
    lo.setSpacing(8)
    lo.addStretch()
    btn = QPushButton("Đánh dấu đã đọc tất cả")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFixedHeight(30)
    btn.setStyleSheet(
        "QPushButton{background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;"
        "border-radius:8px;padding:0 12px;font-size:12px;font-weight:800;}"
        "QPushButton:hover{background:#DBEAFE;border-color:#93C5FD;}"
    )
    btn.clicked.connect(callback)
    lo.addWidget(btn)
    return row


def _section_label(text: str, color: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        f"color:{color};font-size:11px;font-weight:900;"
        "background:transparent;border:none;padding:10px 14px 6px 14px;"
        "text-transform:uppercase;"
    )
    return label


def _format_notification_time(raw: object) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    try:
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00")).replace(tzinfo=None)
        delta = datetime.utcnow() - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "Vừa xong"
        if seconds < 3600:
            return f"{seconds // 60} phút"
        if seconds < 86400:
            return f"{seconds // 3600} giờ"
        return dt.strftime("%d/%m")
    except Exception:
        return txt[:10]
