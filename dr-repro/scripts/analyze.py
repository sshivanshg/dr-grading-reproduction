"""Figures and tables for a finished run: training curves, confusion matrices, per-class table, failures."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from PIL import Image  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import CLASS_NAMES, IMG_DIR, ROOT  # noqa: E402

FIG = ROOT / "results" / "figures"


def curves(run: str):
    log = pd.read_json(ROOT / "runs" / run / "log.jsonl", lines=True).drop_duplicates("epoch", keep="last")
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
    ax[0].plot(log["epoch"], log["train_loss"])
    ax[0].set(xlabel="epoch", ylabel="train loss", title="Training loss")
    ax[1].plot(log["epoch"], log["val_qwk"], label="val QWK")
    ax[1].plot(log["epoch"], log["val_acc"], label="val accuracy")
    ax[1].plot(log["epoch"], log["val_macro_f1"], label="val macro-F1")
    ax[1].set(xlabel="epoch", title="Validation metrics", ylim=(0, 1))
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / f"{run}_curves.pdf")
    fig.savefig(FIG / f"{run}_curves.png", dpi=150)
    plt.close(fig)


def confusion(run: str, key: str):
    res = json.loads((ROOT / "runs" / run / "results.json").read_text())[key]
    cm = np.array(res["confusion_matrix"])
    fig, ax = plt.subplots(figsize=(4.2, 3.6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    ax.set(xlabel="Predicted", ylabel="True", title=f"QWK={res['qwk']:.3f}")
    ax.tick_params(axis="x", labelrotation=30)
    fig.tight_layout()
    fig.savefig(FIG / f"{run}_{key}_cm.pdf")
    fig.savefig(FIG / f"{run}_{key}_cm.png", dpi=150)
    plt.close(fig)


def failures(run: str, n: int = 10):
    z = np.load(ROOT / "runs" / run / "snapshot_probs.npz", allow_pickle=True)
    probs = np.load(ROOT / "runs" / run / "best_test_probs.npy")
    y, names = z["test_y"], z["test_images"]
    pred = probs.argmax(1)
    err = np.abs(pred - y)
    order = np.argsort(-(err * 10 + probs.max(1)))[:n]
    fig, axes = plt.subplots(2, n // 2, figsize=(2.2 * n // 2, 5))
    for ax, i in zip(axes.flat, order):
        ax.imshow(Image.open(IMG_DIR / names[i]))
        ax.set_title(f"true {CLASS_NAMES[y[i]]}\npred {CLASS_NAMES[pred[i]]} ({probs[i].max():.2f})", fontsize=8)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(FIG / f"{run}_failures.pdf")
    fig.savefig(FIG / f"{run}_failures.png", dpi=120)
    plt.close(fig)


def main(run: str):
    FIG.mkdir(parents=True, exist_ok=True)
    curves(run)
    for key in ("final_epoch", "best_val", "ensemble_vote"):
        confusion(run, key)
    failures(run)
    print("figures written for", run)


if __name__ == "__main__":
    main(sys.argv[1])
