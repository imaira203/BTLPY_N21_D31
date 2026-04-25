"""Unified icon system — inline Lucide-style SVG → QIcon.

Usage:
    from app.components.icons import Icon
    btn.setIcon(Icon.get("search", size=18, color="#6B7280"))

All icons share the same visual language: 24x24 viewBox, 1.5 stroke,
round joins/caps, currentColor for the stroke. `Icon.get()` substitutes
the requested color, renders to a QPixmap at the requested size (with
device pixel ratio applied for sharpness on HiDPI), and returns a QIcon.
"""
from __future__ import annotations

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


# ---------------------------------------------------------------------------
# SVG source (Lucide-style).  {color} is substituted at render time.
# ---------------------------------------------------------------------------
_SVG: dict[str, str] = {
    # ---- brand / navigation ----
    "logo": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'>
        <path d='M13 2L3 14h7l-1 8 10-12h-7l1-8z' fill='{color}' stroke='none'/></svg>""",

    "dashboard": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <rect x='3' y='3' width='7' height='9' rx='1.5'/>
        <rect x='14' y='3' width='7' height='5' rx='1.5'/>
        <rect x='14' y='12' width='7' height='9' rx='1.5'/>
        <rect x='3' y='16' width='7' height='5' rx='1.5'/></svg>""",

    "users": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <path d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'/>
        <circle cx='9' cy='7' r='4'/>
        <path d='M22 21v-2a4 4 0 0 0-3-3.87'/>
        <path d='M16 3.13a4 4 0 0 1 0 7.75'/></svg>""",

    "building": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <rect x='4' y='2' width='16' height='20' rx='2'/>
        <path d='M9 22v-4h6v4'/>
        <path d='M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01'/></svg>""",

    "briefcase": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <rect x='2' y='7' width='20' height='14' rx='2'/>
        <path d='M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'/></svg>""",

    "activity": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <path d='M22 12h-4l-3 9L9 3l-3 9H2'/></svg>""",

    # ---- actions ----
    "search": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <circle cx='11' cy='11' r='8'/><path d='M21 21l-4.35-4.35'/></svg>""",

    "bell": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <path d='M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9'/>
        <path d='M13.73 21a2 2 0 0 1-3.46 0'/></svg>""",

    "eye": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <path d='M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z'/>
        <circle cx='12' cy='12' r='3'/></svg>""",

    "edit": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <path d='M12 20h9'/>
        <path d='M16.5 3.5a2.121 2.121 0 1 1 3 3L7 19l-4 1 1-4L16.5 3.5z'/></svg>""",

    "trash": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <polyline points='3 6 5 6 21 6'/>
        <path d='M19 6l-2 14a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2L5 6'/>
        <path d='M10 11v6M14 11v6'/>
        <path d='M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2'/></svg>""",

    "lock": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <rect x='3' y='11' width='18' height='11' rx='2'/>
        <path d='M7 11V7a5 5 0 0 1 10 0v4'/></svg>""",

    "logout": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <path d='M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'/>
        <polyline points='16 17 21 12 16 7'/>
        <line x1='21' y1='12' x2='9' y2='12'/></svg>""",

    "plus": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
        <line x1='12' y1='5' x2='12' y2='19'/><line x1='5' y1='12' x2='19' y2='12'/></svg>""",

    "chevron_down": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <polyline points='6 9 12 15 18 9'/></svg>""",

    "trend_up": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
        <polyline points='23 6 13.5 15.5 8.5 10.5 1 18'/><polyline points='17 6 23 6 23 12'/></svg>""",

    "trend_down": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'>
        <polyline points='23 18 13.5 8.5 8.5 13.5 1 6'/><polyline points='17 18 23 18 23 12'/></svg>""",

    "menu": """<svg viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'
        fill='none' stroke='{color}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'>
        <line x1='3' y1='12' x2='21' y2='12'/>
        <line x1='3' y1='6' x2='21' y2='6'/>
        <line x1='3' y1='18' x2='21' y2='18'/></svg>""",
}


class Icon:
    """Factory for producing crisp, tinted QIcons from a single SVG source."""

    @staticmethod
    def get(name: str, size: int = 20, color: str = "#6B7280") -> QIcon:
        svg = _SVG.get(name)
        if svg is None:
            return QIcon()  # graceful no-op
        svg = svg.replace("{color}", color)

        dpr = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
        px = QPixmap(int(size * dpr), int(size * dpr))
        px.setDevicePixelRatio(dpr)
        px.fill(Qt.GlobalColor.transparent)

        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        painter = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        renderer.render(painter)
        painter.end()

        return QIcon(px)

    @staticmethod
    def pixmap(name: str, size: int = 20, color: str = "#6B7280") -> QPixmap:
        return Icon.get(name, size, color).pixmap(size, size)
