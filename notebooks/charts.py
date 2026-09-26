"""Chart style shared by every Step 4 notebook.

Palette: the validated categorical order from the dataviz reference palette (light
surface). Slots 1 to 3 (blue, orange, aqua) pass colour-blind separation checks as a
set; aqua is below 3:1 contrast on the light surface, so any chart using it carries
direct labels. Magnitude uses the single-hue blue ramp; polarity (increases against
decreases in a bridge) uses the blue/red diverging pair with a grey total.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from nb_utils import CHARTS  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
SERIES = [BLUE, ORANGE, AQUA]
INCREASE, DECREASE, TOTAL = "#2a78d6", "#e34948", "#8a8983"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ_CMAP = LinearSegmentedColormap.from_list("blue_ramp", BLUE_RAMP)

SOURCE = "Source: Northbridge data room (synthetic), invoice ledger after cleaning; analysis by buy-side Transaction Analytics."


def setup() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": TEXT_2,
        "axes.labelcolor": TEXT_2,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXT,
        "axes.titlelocation": "left",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": TEXT_2,
        "ytick.color": TEXT_2,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "lines.linewidth": 2,
        "savefig.dpi": 150,
    })


def gbp_m(dp: int = 1):
    """Axis formatter: £m."""
    return FuncFormatter(lambda v, _: f"£{v / 1e6:,.{dp}f}m")


def gbp_k():
    return FuncFormatter(lambda v, _: f"£{v / 1e3:,.0f}k")


def pct_fmt(dp: int = 0):
    return FuncFormatter(lambda v, _: f"{v:.{dp}f}%")


def save(fig, name: str, source: str = SOURCE) -> str:
    """Add the source note and save to outputs/charts/<name>.png."""
    # Placed just below the figure; bbox_inches="tight" extends the canvas to include it,
    # so it never collides with axis labels.
    fig.text(0.01, -0.01, source, fontsize=6.5, color=TEXT_2, ha="left", va="top")
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.15, metadata={"Software": None})
    plt.close(fig)
    return str(path.relative_to(CHARTS.parent.parent))


setup()
