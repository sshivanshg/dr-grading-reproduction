"""Re-score a faithful-split run on test images that have no byte-identical copy in the training set."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import ROOT  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.train import majority_vote  # noqa: E402


def main(run: str):
    d = ROOT / "runs" / run
    split = pd.read_csv(d / "split.csv")
    train_imgs = set(split.loc[split["split"] == "train", "image"])
    z = np.load(d / "snapshot_probs.npz", allow_pickle=True)
    y, names, snaps = z["test_y"], z["test_images"], z["test"]
    best = np.load(d / "best_test_probs.npy")
    keep = ~np.isin(names, list(train_imgs))
    preds = {"final_epoch": (snaps[-1].argmax(1), snaps[-1]), "best_val": (best.argmax(1), best),
             "ensemble_vote": (majority_vote(snaps), snaps.mean(0))}
    out = {"n_test": int(len(y)), "n_leaked": int((~keep).sum())}
    for k, (p, pr) in preds.items():
        allm, cleanm = compute_metrics(y, p, pr), compute_metrics(y[keep], p[keep], pr[keep])
        leak_acc = float((p[~keep] == y[~keep]).mean()) if (~keep).any() else float("nan")
        out[k] = {"qwk_all": allm["qwk"], "qwk_no_leak": cleanm["qwk"], "acc_all": allm["accuracy"],
                  "acc_no_leak": cleanm["accuracy"], "acc_on_leaked": leak_acc}
    print(json.dumps(out, indent=2))
    (ROOT / "results" / f"leakage_{run}.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
