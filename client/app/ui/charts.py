"""Chart helpers — Recruitment Trend, Donut, Department Bar, legacy charts."""
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


def make_recruitment_trend_chart(
    labels: list[str],
    applications: list[int],
    hired: list[int],
) -> FigureCanvasQTAgg:
    bg = "#FFFFFF"
    C_APP = "#2563EB"
    C_HIR = "#10B981"

    fig = Figure(figsize=(8, 2.9), dpi=100, facecolor=bg)
    # Tighter top margin — legend is now a Qt widget above the canvas
    fig.subplots_adjust(left=0.07, right=0.93, top=0.93, bottom=0.20)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    xi = list(range(len(labels)))

    # ── Trục Y trái: Ứng tuyển ────────────────────────────────
    ax.plot(xi, applications, color=C_APP, linewidth=2.2,
            marker="o", markerfacecolor="#fff", markeredgecolor=C_APP,
            markersize=5, zorder=4, label="Ứng tuyển")
    ax.fill_between(xi, applications, alpha=0.10, color=C_APP, zorder=1)
    ax.tick_params(axis="y", labelcolor=C_APP, labelsize=8, length=0)

    # ── Trục Y phải: Tuyển dụng (twin) ────────────────────────
    ax2 = ax.twinx()
    ax2.set_facecolor(bg)
    ax2.plot(xi, hired, color=C_HIR, linewidth=2.0,
             marker="o", markerfacecolor="#fff", markeredgecolor=C_HIR,
             markersize=5, zorder=4, label="Tuyển dụng")
    ax2.fill_between(xi, hired, alpha=0.12, color=C_HIR, zorder=1)
    ax2.tick_params(axis="y", labelcolor=C_HIR, labelsize=8, length=0)
    for spine in ax2.spines.values():
        spine.set_visible(False)

    # ── Nhãn trục X ────────────────────────────────────────────
    ax.set_xticks(xi)
    ax.set_xticklabels(labels, color="#6B7280", fontsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.20, color="#E5E7EB")
    ax.xaxis.grid(True, linestyle="--", alpha=0.06, color="#E5E7EB")
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", length=0)

    # Không dùng legend matplotlib (bị fill_between che).
    # Legend sẽ được vẽ bằng Qt widget bên ngoài canvas.

    # ── Tooltip hover ──────────────────────────────────────────
    annot = ax.annotate(
        "", xy=(0, 0), xytext=(0, 14), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.4", fc="#1F2937", ec="none", alpha=0.95),
        color="#FFFFFF", fontsize=9, fontweight="600", zorder=10,
    )
    annot.set_visible(False)
    canvas = FigureCanvasQTAgg(fig)
    canvas.setMinimumHeight(200)
    pts = list(zip(xi, applications, hired))

    def _hover(event):
        vis = annot.get_visible()
        if event.inaxes not in (ax, ax2):
            if vis:
                annot.set_visible(False)
                canvas.draw_idle()
            return
        found = False
        for (x, a, h) in pts:
            if abs(event.xdata - x) < 0.38:
                annot.xy = (x, a)
                lbl = labels[x] if x < len(labels) else str(x)
                annot.set_text(f"  {lbl}  Ứng tuyển: {a}  Tuyển: {h}  ")
                annot.set_visible(True)
                canvas.draw_idle()
                found = True
                break
        if not found and vis:
            annot.set_visible(False)
            canvas.draw_idle()

    canvas.mpl_connect("motion_notify_event", _hover)
    return canvas


def make_donut_chart(
    labels: list[str],
    values: list[float],
    colors: list[str] | None = None,
) -> FigureCanvasQTAgg:
    bg = "#FFFFFF"
    if colors is None:
        colors = ["#2563EB", "#10B981", "#06B6D4", "#8B5CF6"]

    fig = Figure(figsize=(2.6, 3.4), dpi=100, facecolor=bg)
    # Place axes in top 68% of the figure; bottom 32% reserved for legend
    ax = fig.add_axes([0.05, 0.32, 0.90, 0.64])
    ax.set_facecolor(bg)

    wedges, _ = ax.pie(
        values,
        colors=colors[:len(values)],
        startangle=90,
        counterclock=False,
        wedgeprops=dict(width=0.52, edgecolor="white", linewidth=2.5),
    )
    # ax.pie() already calls axis("equal") internally; explicit call removed
    # to avoid clipping in a constrained axes box

    legend_labels = [f"{l}  {int(v)}%" for l, v in zip(labels, values)]
    # Attach legend to the figure (not axes) so it sits in the 32% bottom area
    fig.legend(
        wedges, legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.50, 0.02),
        ncol=2, fontsize=7.8, framealpha=0,
        handlelength=0.9, handletextpad=0.5,
        labelcolor="#374151", columnspacing=0.8,
    )

    canvas = FigureCanvasQTAgg(fig)
    canvas.setMinimumHeight(200)
    return canvas


def make_dept_bar_chart(
    departments: list[str],
    employees: list[int],
    openings: list[int],
    recent_hires: list[int],
) -> FigureCanvasQTAgg:
    bg = "#FFFFFF"
    fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.18)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    n = len(departments)
    x = np.arange(n)
    w = 0.26
    C_EMP = "#2563EB"
    C_OPN = "#06B6D4"
    C_HIR = "#10B981"
    ax.bar(x - w, employees, w, color=C_EMP, label="Nhân viên", linewidth=0, zorder=2)
    ax.bar(x, openings, w, color=C_OPN, label="Vị trí tuyển", linewidth=0, zorder=2)
    ax.bar(x + w, recent_hires, w, color=C_HIR, label="Tuyển mới", linewidth=0, zorder=2)
    ax.set_xticks(x)
    ax.set_xticklabels(departments, fontsize=9, color="#6B7280")
    ax.yaxis.set_tick_params(labelsize=9, labelcolor="#9CA3AF")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.20, color="#E5E7EB")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)
    ax.legend(fontsize=9, loc="upper right", framealpha=0,
              handlelength=1.0, handletextpad=0.5, ncol=3, labelcolor="#374151")
    return FigureCanvasQTAgg(fig)


def make_revenue_bar_chart(
    labels: list[str],
    values: list[float],
    selected_idx: int = 7,
) -> FigureCanvasQTAgg:
    bg = "#FFFFFF"
    fig = Figure(figsize=(8, 3.4), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.02, right=0.99, top=0.88, bottom=0.13)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    n = len(labels)
    x = np.arange(n)
    w = 0.34
    rng = np.random.default_rng(seed=42)
    noise = rng.uniform(0.68, 0.86, n)
    values_b = [float(v) * noise[i] for i, v in enumerate(values)]
    C_PUR = "#C4B5FD"
    C_GRN = "#86EFAC"
    C_SEL_PUR = "#4338CA"
    C_SEL_GRN = "#064E3B"
    bar_hits: list[tuple[float, float, int]] = []
    for i, (va, vb) in enumerate(zip(values, values_b)):
        sel = (i == selected_idx)
        x_a = float(x[i]) - w / 2 - 0.04
        x_b = float(x[i]) + w / 2 + 0.04
        ax.bar(x_a, va, w, color=C_SEL_PUR if sel else C_PUR, linewidth=0, zorder=2)
        ax.bar(x_b, vb, w, color=C_SEL_GRN if sel else C_GRN, linewidth=0, zorder=2)
        bar_hits.append((x_a, float(va), i))
        bar_hits.append((x_b, float(vb), i))
    mx = max(values) if values else 1
    ax.set_xlim(-0.75, n - 0.25)
    ax.set_ylim(0, mx * 1.22)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, color="#9CA3AF", fontweight="500")
    tick_lbls = ax.get_xticklabels()
    if 0 <= selected_idx < len(tick_lbls):
        tick_lbls[selected_idx].set_color("#111827")
        tick_lbls[selected_idx].set_fontweight("700")
    ax.yaxis.set_visible(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.5, color="#F3F4F6", alpha=1.0, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)
    annot = ax.annotate(
        "", xy=(0, 0), xytext=(0, 16), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.5", fc="#111827", ec="none", alpha=0.96),
        arrowprops=dict(arrowstyle="-", color="#111827", lw=0),
        color="#FFFFFF", fontsize=10, fontweight="700", zorder=10,
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
        for (bx, by, idx) in bar_hits:
            if abs(event.xdata - bx) <= w / 2 + 0.06 and 0 <= event.ydata <= by * 1.12:
                annot.xy = (bx, by)
                lbl = labels[idx] if idx < len(labels) else str(idx + 1)
                annot.set_text(f"  {lbl}: ${by:,.2f}  ")
                annot.set_visible(True)
                canvas.draw_idle()
                found = True
                break
        if not found and vis:
            annot.set_visible(False)
            canvas.draw_idle()

    canvas.mpl_connect("motion_notify_event", _hover)
    return canvas


def make_line_chart_single(
    labels: list[str],
    values: list[int],
    color: str = "#2563EB",
) -> FigureCanvasQTAgg:
    bg = "#ffffff"
    fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.12)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    xi = list(range(len(labels)))
    ax.plot(xi, values, color=color, linewidth=2.2,
            marker="o", markerfacecolor="#fff", markeredgecolor=color,
            markersize=5, zorder=4)
    ax.fill_between(xi, values, alpha=0.12, color=color, zorder=1)
    ax.set_xticks(xi)
    ax.set_xticklabels(labels, fontsize=9, color="#6B7280")
    ax.yaxis.set_tick_params(labelsize=9, labelcolor="#9CA3AF")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.20, color="#E5E7EB")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)
    return FigureCanvasQTAgg(fig)


def make_bar_chart(
    labels: list[str],
    values: list[int | float],
    color: str = "#6366f1",
    dark: bool = False,
) -> FigureCanvasQTAgg:
    bg = "#1E1E2E" if dark else "#FFFFFF"
    txt_color = "#E5E7EB" if dark else "#6B7280"
    grid_color = "#374151" if dark else "#E5E7EB"

    fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.18)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)

    x = np.arange(len(labels))
    ax.bar(x, values, color=color, linewidth=0, zorder=2, alpha=0.85, width=0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9, color=txt_color)
    ax.yaxis.set_tick_params(labelsize=9, labelcolor=txt_color)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.20, color=grid_color)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)
    return FigureCanvasQTAgg(fig)

def make_line_chart(
    labels: list[str],
    series_a: list[int],
    series_b: list[int],
) -> FigureCanvasQTAgg:
    bg = "#ffffff"
    fig = Figure(figsize=(8, 3.5), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.12)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    xi = list(range(len(labels)))
    ax.plot(xi, series_a, color=ADMIN_ACCENT, linewidth=2.2,
            marker="o", markerfacecolor="#fff", markeredgecolor=ADMIN_ACCENT,
            markersize=5, zorder=4)
    ax.fill_between(xi, series_a, alpha=0.10, color=ADMIN_ACCENT, zorder=1)
    ax.plot(xi, series_b, color=USER_ACCENT, linewidth=2.0,
            marker="o", markerfacecolor="#fff", markeredgecolor=USER_ACCENT,
            markersize=5, zorder=4)
    ax.fill_between(xi, series_b, alpha=0.10, color=USER_ACCENT, zorder=1)
    ax.set_xticks(xi)
    ax.set_xticklabels(labels, fontsize=9, color="#6B7280")
    ax.yaxis.set_tick_params(labelsize=9, labelcolor="#9CA3AF")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.20, color="#E5E7EB")
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", length=0)
    return FigureCanvasQTAgg(fig)


def make_revenue_trend_chart(
    labels: list[str],
    hr_values: list[float],
    candidate_values: list[float],
) -> FigureCanvasQTAgg:
    """Revenue trend: HR Invoices (blue solid) + Candidate Pro (gray dashed)."""
    bg = "#FFFFFF"
    C_HR  = "#2563EB"
    C_CAN = "#9CA3AF"

    fig = Figure(figsize=(8, 3.0), dpi=100, facecolor=bg)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.92, bottom=0.18)
    ax = fig.add_subplot(111)
    ax.set_facecolor(bg)
    xi = list(range(len(labels)))

    def _fmt_y(val, _):
        if val >= 1_000_000_000:
            return f"{val/1_000_000_000:.1f}B"
        if val >= 1_000_000:
            return f"{val/1_000_000:.0f}M"
        return str(int(val))

    # HR Invoices — solid blue with fill
    ax.plot(xi, hr_values, color=C_HR, linewidth=2.5,
            marker="o", markerfacecolor="#fff", markeredgecolor=C_HR,
            markersize=6, zorder=4)
    ax.fill_between(xi, hr_values, alpha=0.10, color=C_HR, zorder=1)

    # Candidate Pro — dashed gray with dots
    ax.plot(xi, candidate_values, color=C_CAN, linewidth=1.8,
            linestyle="--", marker="o",
            markerfacecolor="#fff", markeredgecolor=C_CAN,
            markersize=5, zorder=4)
    ax.fill_between(xi, candidate_values, alpha=0.06, color=C_CAN, zorder=1)

    import matplotlib.ticker as ticker
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_y))
    ax.set_xticks(xi)
    ax.set_xticklabels(labels, color="#6B7280", fontsize=9)
    ax.tick_params(axis="both", length=0, labelsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.yaxis.grid(True, linestyle="--", alpha=0.18, color="#E5E7EB")
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    ax.yaxis.tick_left()

    # Hover annotation
    annot = ax.annotate(
        "", xy=(0, 0), xytext=(0, 14), textcoords="offset points",
        bbox=dict(boxstyle="round,pad=0.4", fc="#1F2937", ec="none", alpha=0.95),
        color="#FFFFFF", fontsize=9, fontweight="600", zorder=10,
    )
    annot.set_visible(False)
    canvas = FigureCanvasQTAgg(fig)

    def _hover(event):
        if event.inaxes != ax:
            annot.set_visible(False)
            canvas.draw_idle()
            return
        for i, (x, hr, can) in enumerate(zip(xi, hr_values, candidate_values)):
            if abs(event.xdata - x) < 0.4:
                def _f(v): return f"{v/1_000_000:.0f}M" if v >= 1_000_000 else str(int(v))
                annot.xy = (x, max(hr, can))
                annot.set_text(f"{labels[i]}: HR {_f(hr)} | Pro {_f(can)}")
                annot.set_visible(True)
                canvas.draw_idle()
                return
        annot.set_visible(False)
        canvas.draw_idle()

    canvas.mpl_connect("motion_notify_event", _hover)
    return canvas
