from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..theme import ADMIN_ACCENT, USER_ACCENT
from ..ui_theme import chart_facecolor


def make_bar_chart(labels: list[str], values: list[int], color: str) -> FigureCanvasQTAgg:
    bg = chart_facecolor()
    fig = Figure(figsize=(5, 3), layout="constrained")
    ax = fig.add_subplot(111)
    ax.bar(labels, values, color=color, alpha=0.85)
    ax.set_facecolor(bg)
    fig.patch.set_facecolor(bg)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    return FigureCanvasQTAgg(fig)


def make_line_chart_single(labels: list[str], values: list[int], color: str = ADMIN_ACCENT) -> FigureCanvasQTAgg:
    bg = chart_facecolor()
    fig = Figure(figsize=(5, 3), layout="constrained")
    ax = fig.add_subplot(111)
    x = range(len(labels))
    ax.plot(list(x), values, color=color, linewidth=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=0)
    ax.set_facecolor(bg)
    fig.patch.set_facecolor(bg)
    ax.grid(linestyle="--", alpha=0.3)
    return FigureCanvasQTAgg(fig)


def make_line_chart(labels: list[str], series_a: list[int], series_b: list[int]) -> FigureCanvasQTAgg:
    bg = chart_facecolor()
    fig = Figure(figsize=(5, 3), layout="constrained")
    ax = fig.add_subplot(111)
    x = range(len(labels))
    ax.plot(list(x), series_a, color=USER_ACCENT, linewidth=2, label="Users")
    ax.plot(list(x), series_b, color=ADMIN_ACCENT, linewidth=2, label="Jobs")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_facecolor(bg)
    fig.patch.set_facecolor(bg)
    ax.legend()
    ax.grid(linestyle="--", alpha=0.3)
    return FigureCanvasQTAgg(fig)
