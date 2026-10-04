"""Evaluate a saved state_dict on a run's test split: python scripts/eval_ckpt.py <run_dir> <ckpt.pt>."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import CachedDataset, load_cached  # noqa: E402
from src.metrics import compute_metrics  # noqa: E402
from src.model import DRNet  # noqa: E402
from src.train import predict  # noqa: E402

run_dir, ckpt = Path(sys.argv[1]), Path(sys.argv[2])
cfg = json.loads((run_dir / "config.json").read_text())
arr, pos = load_cached(cfg["size"], not cfg["no_clahe"])
split = pd.read_csv(run_dir / "split.csv")
test = split[split["split"] == "test"]
dl = DataLoader(CachedDataset(arr, test["image"].map(pos).to_numpy(), test["label"].to_numpy()), batch_size=16)
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model = DRNet(cfg["backbone"], pretrained=False).to(device).to(memory_format=torch.channels_last)
model.load_state_dict(torch.load(ckpt, map_location=device))
probs, y = predict(model, dl, device, False)
res = compute_metrics(y, probs.argmax(1), probs)
np.save(run_dir / f"{ckpt.stem}_test_probs.npy", probs)
(run_dir / f"{ckpt.stem}_test_results.json").write_text(json.dumps(res, indent=2))
print(json.dumps({k: v for k, v in res.items() if k not in ("per_class", "confusion_matrix")}, indent=2))
print("per-class recall:", {k: round(v["recall"], 3) for k, v in res["per_class"].items()})
print("confusion:", res["confusion_matrix"])
