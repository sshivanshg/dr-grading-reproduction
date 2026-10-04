"""Extra figures for the presentation: class distribution and per-snapshot test QWK."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import cohen_kappa_score  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import CLASS_NAMES, ROOT  # noqa: E402

FIG = ROOT / "results" / "figures"
NAVY, TEAL, CORAL = "#1F3A5F", "#2A9D8F", "#E76F51"
plt.rcParams.update({"font.size": 13, "axes.spines.top": False, "axes.spines.right": False})


def class_distribution():
    counts = [1805, 370, 999, 193, 295]
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    bars = ax.bar(CLASS_NAMES, counts, color=[NAVY, TEAL, NAVY, CORAL, CORAL])
    for b, c in zip(bars, counts):
        ax.text(b.get_x() + b.get_width() / 2, c + 25, f"{c}\n({c / 3662:.0%})", ha="center", va="bottom", fontsize=11)
    ax.set_ylim(0, 2200)
    ax.set_ylabel("images")
    ax.set_title("APTOS 2019 grade distribution (n = 3,662)")
    fig.tight_layout()
    fig.savefig(FIG / "class_distribution.png", dpi=200)
    plt.close(fig)


def snapshot_qwk():
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for run, label, color in [("s2_faithful", "lr 1e-3 (paper)", CORAL), ("s2_lr1e4", "lr 1e-4", TEAL)]:
        z = np.load(ROOT / "runs" / run / "snapshot_probs.npz")
        q = [cohen_kappa_score(z["test_y"], p.argmax(1), weights="quadratic") for p in z["test"]]
        ax.plot(z["epochs"], q, "o-", color=color, label=f"{label} snapshots", lw=2)
    ax.axhline(0.788, color=CORAL, ls="--", lw=1.5, label="lr 1e-3 vote = 0.788")
    ax.axhline(0.887, color=TEAL, ls="--", lw=1.5, label="lr 1e-4 vote = 0.887")
    ax.axhline(0.954, color=NAVY, ls=":", lw=2, label="paper = 0.954")
    ax.set(xlabel="snapshot epoch", ylabel="test QWK", ylim=(0.6, 1.0), xticks=range(3, 31, 3))
    ax.set_title("Test QWK of each saved snapshot")
    ax.legend(fontsize=9, loc="lower right", ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "snapshot_qwk.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    class_distribution()
    snapshot_qwk()
    print("done")
