"""Revenue line chart — smooth curve with soft area fill.

Uses pyqtgraph for performance; falls back to a plain label if pyqtgraph
is not installed so the app still runs.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.theme import COLORS

try:
    import pyqtgraph as pg
    _HAS_PG = True
except ImportError:  # pragma: no cover
    _HAS_PG = False


class RevenueChart(QWidget):
    def __init__(self, x_labels: list[str], y_values: list[float], parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not _HAS_PG:
            fallback = QLabel("pyqtgraph is not installed — run `pip install pyqtgraph`.")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 13px;")
            layout.addWidget(fallback)
            return

        pg.setConfigOption("background", COLORS.card)
        pg.setConfigOption("foreground", COLORS.text_muted)
        pg.setConfigOption("antialias", True)

        plot = pg.PlotWidget()
        plot.setMenuEnabled(False)
        plot.setMouseEnabled(x=False, y=False)
        plot.hideButtons()
        plot.setBackground(None)

        # axes
        for side in ("left", "bottom"):
            ax = plot.getAxis(side)
            ax.setPen(pg.mkPen(COLORS.border, width=1))
            ax.setTextPen(pg.mkPen(COLORS.text_muted))
            ax.setStyle(tickFont=_qfont(11))

        plot.getAxis("top").setStyle(showValues=False)
        plot.getAxis("right").setStyle(showValues=False)
        plot.getPlotItem().showGrid(x=False, y=True, alpha=0.25)

        x = list(range(len(x_labels)))
        xticks = [list(zip(x, x_labels))]
        plot.getAxis("bottom").setTicks(xticks)

        # Area fill under the curve
        fill_brush = QColor(COLORS.primary)
        fill_brush.setAlpha(40)
        fill_curve = plot.plot(x, y_values, pen=None)
        baseline = pg.PlotCurveItem(x, [min(y_values) * 0.9] * len(x), pen=None)
        fill = pg.FillBetweenItem(fill_curve, baseline, brush=fill_brush)
        plot.addItem(fill)

        # Main line
        line_pen = pg.mkPen(color=COLORS.primary, width=2.5)
        plot.plot(x, y_values, pen=line_pen,
                  symbol="o",
                  symbolSize=8,
                  symbolBrush=COLORS.card,
                  symbolPen=pg.mkPen(color=COLORS.primary, width=2))

        layout.addWidget(plot)


def _qfont(pt: int):
    from PyQt6.QtGui import QFont
    f = QFont("Inter")
    f.setPointSize(pt)
    return f
