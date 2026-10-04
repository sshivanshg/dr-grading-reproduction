"""Overlay validation QWK of the four strategy-2 runs: results/figures/val_qwk_compare.{png,pdf}."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import ROOT  # noqa: E402

RUNS = [("s2_paper300", "300 px / 60 ep, lr 1e-3", "C3", "-"),
        ("s2_paper300_lr1e4", "300 px / 60 ep, lr 1e-4", "C0", "-"),
        ("s2_faithful", "224 px / 30 ep, lr 1e-3", "C3", ":"),
        ("s2_lr1e4", "224 px / 30 ep, lr 1e-4", "C0", ":")]

fig, ax = plt.subplots(figsize=(6.4, 3.6))
for run, label, color, ls in RUNS:
    log = pd.read_json(ROOT / "runs" / run / "log.jsonl", lines=True).drop_duplicates("epoch", keep="last")
    ax.plot(log["epoch"], log["val_qwk"], color=color, ls=ls, lw=1.4, label=label)
ax.axhline(0.954, color="k", lw=0.8, ls="--")
ax.text(1, 0.958, "paper (test, 0.954)", fontsize=8, va="bottom")
ax.set(xlabel="epoch", ylabel="validation QWK", ylim=(0.5, 1.0))
ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)
fig.tight_layout()
out = ROOT / "results" / "figures" / "val_qwk_compare"
for ext in ("png", "pdf"):
    fig.savefig(f"{out}.{ext}", dpi=200)
print("wrote", out)
