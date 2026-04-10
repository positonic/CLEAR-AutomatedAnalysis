"""Draw a clean, analyst-facing pipeline diagram for CLEAR Stage 1."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ── Palette ───────────────────────────────────────────────────────────────────
C_DARK_BLUE  = "#1A3A5C"
C_MID_BLUE   = "#235A8C"
C_ACCENT     = "#007AB5"
C_LIGHT_BLUE = "#D6EAF8"
C_LIGHT_GREY = "#F4F6F7"
C_BORDER     = "#AEC6CF"
C_ORANGE     = "#E8873A"
C_ORANGE_LT  = "#FDE9D9"
C_GREEN      = "#2E7D54"
C_GREEN_LT   = "#D5EFE0"
C_PURPLE     = "#6C4B8E"
C_PURPLE_LT  = "#EAE1F4"
C_WHITE      = "#FFFFFF"
C_TEXT_DARK  = "#1A1A2E"
C_TEXT_MID   = "#2C3E50"
C_ARROW      = "#5D7A96"

fig, ax = plt.subplots(figsize=(14, 17))
ax.set_xlim(0, 14)
ax.set_ylim(0, 17)
ax.axis("off")
fig.patch.set_facecolor(C_WHITE)

# ── Helper: rounded box ───────────────────────────────────────────────────────
def box(ax, x, y, w, h, label, sublabel=None,
        fc=C_LIGHT_BLUE, ec=C_ACCENT, tc=C_TEXT_DARK,
        fontsize=10.5, bold=True, radius=0.25):
    patch = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=1.6, zorder=3
    )
    ax.add_patch(patch)
    weight = "bold" if bold else "normal"
    ya = y + (0.18 if sublabel else 0)
    ax.text(x, ya, label, ha="center", va="center", fontsize=fontsize,
            color=tc, fontweight=weight, zorder=4, wrap=True,
            multialignment="center")
    if sublabel:
        ax.text(x, y - 0.28, sublabel, ha="center", va="center", fontsize=8.5,
                color=tc, fontstyle="italic", zorder=4, alpha=0.85,
                multialignment="center")


def arrow(ax, x1, y1, x2, y2, color=C_ARROW, lw=2.0, style="->"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=lw, connectionstyle="arc3,rad=0.0"),
                zorder=2)


def section_label(ax, x, y, text):
    ax.text(x, y, text, ha="left", va="center", fontsize=8,
            color=C_ACCENT, fontweight="bold", alpha=0.9,
            bbox=dict(fc="none", ec="none"))


# ── STEP 1 — Source documents ─────────────────────────────────────────────────
box(ax, 7, 16.2, 5.5, 0.8,
    "Humanitarian Documents",
    sublabel="Reports, situation reports, assessments (ReliefWeb)",
    fc="#EAF4FB", ec=C_MID_BLUE, tc=C_DARK_BLUE, fontsize=11)

arrow(ax, 7, 15.8, 7, 15.15)

# ── STEP 2 — Text extraction ──────────────────────────────────────────────────
box(ax, 7, 14.85, 5.0, 0.7,
    "Text Extraction",
    sublabel="Each document is read and its content made accessible",
    fc=C_LIGHT_GREY, ec=C_BORDER, tc=C_TEXT_MID, fontsize=10.5)

arrow(ax, 7, 14.5, 7, 13.85)

# ── STEP 3 — Entry segmentation ───────────────────────────────────────────────
box(ax, 7, 13.55, 5.5, 0.7,
    "Entry Segmentation",
    sublabel="Text is split into focused, self-contained analytical excerpts",
    fc=C_LIGHT_GREY, ec=C_BORDER, tc=C_TEXT_MID, fontsize=10.5)

arrow(ax, 7, 13.2, 7, 12.55)

# ── STEP 4 — Classification ───────────────────────────────────────────────────
box(ax, 7, 12.25, 6.0, 0.7,
    "Automated Classification",
    sublabel="Each excerpt tagged by pillar, sub-pillar, and sector",
    fc=C_LIGHT_BLUE, ec=C_ACCENT, tc=C_DARK_BLUE, fontsize=10.5)

# small tag pills
pill_y = 11.6
pills = [
    ("Displacement", C_PURPLE_LT, C_PURPLE),
    ("Shock & Hazards", "#FDE9D9", C_ORANGE),
    ("Humanitarian Access", C_GREEN_LT, C_GREEN),
    ("Impact & Conditions", C_LIGHT_BLUE, C_MID_BLUE),
    ("Sectors (10)", C_LIGHT_GREY, "#555"),
]
pill_xs = [2.6, 4.9, 7.2, 9.5, 11.7]
for (label, fc, ec), px in zip(pills, pill_xs):
    patch = FancyBboxPatch(
        (px - 1.05, pill_y - 0.22), 2.1, 0.44,
        boxstyle="round,pad=0,rounding_size=0.15",
        facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=3
    )
    ax.add_patch(patch)
    ax.text(px, pill_y, label, ha="center", va="center", fontsize=7.8,
            color=ec, fontweight="bold", zorder=4)

# thin connector from classification box bottom to pill row
ax.annotate("", xy=(7, pill_y + 0.22), xytext=(7, 11.9),
            arrowprops=dict(arrowstyle="-", color=C_BORDER, lw=1.2), zorder=1)

arrow(ax, 7, 11.38, 7, 10.75)

# ── STEP 5 — Divider label ────────────────────────────────────────────────────
ax.text(7, 10.55, "For each country — three parallel analyses",
        ha="center", va="center", fontsize=9.5,
        color=C_MID_BLUE, fontweight="bold",
        bbox=dict(fc="#EAF4FB", ec=C_ACCENT, boxstyle="round,pad=0.3", lw=1.2))

arrow(ax, 7, 10.3, 7, 9.9)

# split arrow to three branches
# left branch
ax.annotate("", xy=(2.8, 9.6), xytext=(7, 9.9),
            arrowprops=dict(arrowstyle="-", color=C_ARROW, lw=1.6), zorder=2)
arrow(ax, 2.8, 9.9, 2.8, 9.55)
# centre branch stays straight
arrow(ax, 7, 9.9, 7, 9.55)
# right branch
ax.annotate("", xy=(11.2, 9.6), xytext=(7, 9.9),
            arrowprops=dict(arrowstyle="-", color=C_ARROW, lw=1.6), zorder=2)
arrow(ax, 11.2, 9.9, 11.2, 9.55)

# ── Three parallel boxes ───────────────────────────────────────────────────────
# Left: narrative analysis
box(ax, 2.8, 9.0, 4.0, 1.0,
    "Narrative Analysis",
    sublabel="Risks · Needs · Priority actions\nper pillar and sector",
    fc=C_LIGHT_BLUE, ec=C_ACCENT, tc=C_DARK_BLUE, fontsize=10)

# Centre: figures extraction
box(ax, 7, 9.0, 4.0, 1.0,
    "Figures Extraction",
    sublabel="Displaced · Killed · Injured\nkey statistics with source",
    fc=C_ORANGE_LT, ec=C_ORANGE, tc="#7A3B00", fontsize=10)

# Right: context generation
box(ax, 11.2, 9.0, 4.0, 1.0,
    "Context Generation",
    sublabel="Background via live web search:\nDemographics · Economy · Security…",
    fc=C_GREEN_LT, ec=C_GREEN, tc="#1A4A2E", fontsize=10)

# converge arrows down
arrow(ax, 2.8, 8.5, 2.8, 8.05)
arrow(ax, 7,   8.5, 7,   8.05)
arrow(ax, 11.2, 8.5, 11.2, 8.05)

ax.annotate("", xy=(2.8, 8.05), xytext=(7, 7.75),
            arrowprops=dict(arrowstyle="-", color=C_ARROW, lw=1.6), zorder=2)
ax.annotate("", xy=(11.2, 8.05), xytext=(7, 7.75),
            arrowprops=dict(arrowstyle="-", color=C_ARROW, lw=1.6), zorder=2)
arrow(ax, 7, 8.05, 7, 7.75)
arrow(ax, 7, 7.75, 7, 7.3)

# ── STEP 6 — Severity filtering ───────────────────────────────────────────────
box(ax, 7, 7.0, 5.5, 0.65,
    "Severity Filtering",
    sublabel="Only the most critical information is kept (scored 0–10)",
    fc=C_LIGHT_GREY, ec=C_BORDER, tc=C_TEXT_MID, fontsize=10.5)

arrow(ax, 7, 6.67, 7, 6.05)

# ── STEP 7 — Dashboard ────────────────────────────────────────────────────────
box(ax, 7, 5.65, 6.5, 0.8,
    "Interactive Situation Analysis Dashboard",
    sublabel=None,
    fc="#D5EFE0", ec=C_GREEN, tc=C_GREEN, fontsize=11.5, bold=True)

# three dashboard tab pills
tab_y = 4.95
tab_labels = ["Overview & KPIs", "Sectors & Severity Matrix", "Response Planning"]
tab_xs     = [3.0, 7.0, 11.0]
tab_colors = [
    (C_LIGHT_BLUE, C_ACCENT),
    (C_ORANGE_LT, C_ORANGE),
    (C_GREEN_LT, C_GREEN),
]
for (label, (fc, ec)), tx in zip(zip(tab_labels, tab_colors), tab_xs):
    patch = FancyBboxPatch(
        (tx - 1.5, tab_y - 0.26), 3.0, 0.52,
        boxstyle="round,pad=0,rounding_size=0.15",
        facecolor=fc, edgecolor=ec, linewidth=1.2, zorder=3
    )
    ax.add_patch(patch)
    ax.text(tx, tab_y, label, ha="center", va="center", fontsize=8.5,
            color=ec, fontweight="bold", zorder=4)

ax.annotate("", xy=(7, tab_y + 0.26), xytext=(7, 5.25),
            arrowprops=dict(arrowstyle="-", color=C_BORDER, lw=1.2), zorder=1)

# export note
ax.text(7, 4.42, "Exportable as PDF  ·  No technical setup required  ·  Multi-country",
        ha="center", va="center", fontsize=8.5,
        color="#555", fontstyle="italic")

# ── Title ─────────────────────────────────────────────────────────────────────
ax.text(7, 17.5, "CLEAR — How Automated Situation Analysis Works",
        ha="center", va="center", fontsize=14,
        color=C_DARK_BLUE, fontweight="bold")
ax.text(7, 17.1, "From raw humanitarian documents to structured, interactive analysis",
        ha="center", va="center", fontsize=10,
        color=C_MID_BLUE)

# thin top rule
ax.plot([0.5, 13.5], [16.75, 16.75], color=C_ACCENT, lw=1.5, alpha=0.4)

# ── Step number badges ─────────────────────────────────────────────────────────
steps = [
    (7, 16.2, "1"),
    (7, 14.85, "2"),
    (7, 13.55, "3"),
    (7, 12.25, "4"),
    (2.8, 9.0, "5a"),
    (7,   9.0, "5b"),
    (11.2, 9.0, "5c"),
    (7, 7.0, "6"),
    (7, 5.65, "7"),
]
for (bx, by, num) in steps:
    cx = bx - 3.2 if bx == 7 else bx - 2.15
    circle = plt.Circle((cx, by), 0.22, color=C_ACCENT, zorder=5)
    ax.add_patch(circle)
    ax.text(cx, by, num, ha="center", va="center", fontsize=7.5,
            color=C_WHITE, fontweight="bold", zorder=6)

plt.tight_layout(pad=0)
out = "/Users/sfekih/Documents/MMP/CLEAR-AutomatedAnalysis/CLEAR_pipeline_diagram.png"
fig.savefig(out, dpi=300, bbox_inches="tight",
            facecolor=C_WHITE, edgecolor="none")
plt.close()
print(f"Saved: {out}")
