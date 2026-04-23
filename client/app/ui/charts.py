"""Improved chart helpers — gradient bars, rounded tops, hover tooltips."""
from __future__ import annotations

import numpy as np
import matplotlib
import matplotlib.colors as mc
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ..theme import ADMIN_ACCENT, USER_ACCENT
from ..ui_theme import chart_facecolor

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.unicode_minus": False,
})


# ═══════════════════════════════════════════════════════════════
#  GRADIENT + ROUNDED-TOP BAR CHART
# ═══════════════════════════════════════════════════════════════
def make_bar_chart(labels: list[str], values: list[int],
                   color: str = "#6366f1",
                   dark: bool = True) -> FigureCanvasQTAgg:
    """Bar chart — dark navy glassmorphism background, gradient bars, hover tooltip."""
    bg      = "#0e1a4a" if dark else "#ffffff"
    lbl_col = "#94a3b8" if dark else "#64748b"
    val_col = "#c7d2fe" if dark else "#475569"
    grid_c  = "#1e2d6b" if dark else "#e2e8f0"

    fig = Figure(figsize=(6, 3.2), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.93, bottom=0.14)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)

    n  = len(labels)
    x  = np.arange(n)
    w  = 0.52
    mx = max(values) if values else 1

    # Gradient palette: base → brighter top
    base  = mc.to_rgb(color)
    light = tuple(min(1.0, c + 0.28) for c in base)
    cmap  = mc.LinearSegmentedColormap.from_list("bg", [color, light])

    ax.set_xlim(-0.65, n - 0.35)
    ax.set_ylim(0, mx * 1.28)

    grad_img = np.linspace(0, 1, 256).reshape(-1, 1)
    bar_hits = []

    for xi, v in zip(x, values):
        ax.imshow(
            grad_img, aspect="auto", cmap=cmap, origin="lower",
            extent=[xi - w / 2, xi + w / 2, 0, v],
            zorder=2, clip_on=True,
        )
        cap_h = mx * 0.042
        ell = mpatches.Ellipse(
            (xi, v), w, cap_h * 2,
            facecolor=light, edgecolor="none", zorder=3,
        )
        ax.add_patch(ell)

        ax.text(xi, v + mx * 0.045, str(v),
                ha="center", va="bottom",
                fontsize=10, fontweight="700",
                color=val_col, zorder=4)
        bar_hits.append((xi, v))

    # ── Axes styling ───────────────────────────────────────────
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, color=lbl_col, fontweight="600")
    ax.yaxis.set_tick_params(labelsize=9, labelcolor=lbl_col)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5,
                  color=grid_c, alpha=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)

    # ── Hover tooltip ──────────────────────────────────────────
    tooltip_bg = "#1e2d6b" if dark else "#1e293b"
    annot = ax.annotate(
        "", xy=(0, 0), xytext=(0, 16), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.5", fc=tooltip_bg, ec="none", alpha=0.95),
        arrowprops=dict(arrowstyle="-", color=tooltip_bg, lw=0),
        color="#f1f5f9", fontsize=10, fontweight="600", zorder=10,
    )
    annot.set_visible(False)
    canvas = FigureCanvasQTAgg(fig)

    def _hover(event):
        vis = annot.get_visible()
        if event.inaxes != ax:
            if vis:
                annot.set_visible(False)
                canvas.draw_idle()
            return
        found = False
        for xi, v in bar_hits:
            if abs(event.xdata - xi) <= w / 2 + 0.05 and 0 <= event.ydata <= v * 1.08:
                annot.xy = (xi, v)
                annot.set_text(f"  {v:,} ứng viên  ")
                annot.set_visible(True)
                canvas.draw_idle()
                found = True
                break
        if not found and vis:
            annot.set_visible(False)
            canvas.draw_idle()

    canvas.mpl_connect("motion_notify_event", _hover)
    return canvas


# ═══════════════════════════════════════════════════════════════
#  SINGLE LINE CHART
# ═══════════════════════════════════════════════════════════════
def make_line_chart_single(labels: list[str], values: list[int],
                            color: str = "#6366f1") -> FigureCanvasQTAgg:
    bg = "#ffffff"
    fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.12)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)

    xi = list(range(len(labels)))
    ax.plot(xi, values, color=color, linewidth=2.4,
            marker="o", markerfacecolor="#fff",
            markeredgecolor=color, markersize=6, zorder=3)
    ax.fill_between(xi, values, alpha=0.09, color=color, zorder=1)

    ax.set_xticks(xi)
    ax.set_xticklabels(labels, color="#94a3b8", fontsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.15, color="#a3aed0")
    ax.tick_params(axis="both", length=0)
    return FigureCanvasQTAgg(fig)


# ═══════════════════════════════════════════════════════════════
#  DUAL LINE CHART
# ═══════════════════════════════════════════════════════════════
def make_line_chart(labels: list[str], series_a: list[int],
                    series_b: list[int]) -> FigureCanvasQTAgg:
    bg = chart_facecolor()
    fig = Figure(figsize=(5, 3), dpi=100, facecolor=bg)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    xi = list(range(len(labels)))
    ax.plot(xi, series_a, color=USER_ACCENT,  linewidth=2, label="Users")
    ax.plot(xi, series_b, color=ADMIN_ACCENT, linewidth=2, label="Jobs")
    ax.set_xticks(xi)
    ax.set_xticklabels(labels)
    ax.legend(fontsize=9)
    ax.grid(linestyle="--", alpha=0.18)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return FigureCanvasQTAgg(fig)
