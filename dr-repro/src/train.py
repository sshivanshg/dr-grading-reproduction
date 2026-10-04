"""Train one configuration and evaluate single-model, best-val, and snapshot-ensemble predictions.

Snapshot ensembling follows the paper's strategies: predictions from weights at evenly spaced epochs
are combined by majority vote (strategy 2) or by averaging (strategy 1, two snapshots). Instead of
storing every snapshot's weights, val/test probabilities are recorded at those epochs, which gives
identical ensemble predictions at a fraction of the disk cost.
"""
import argparse
import json
import random
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from .data import ROOT, CachedDataset, load_cached, make_split, normalize_on_device
from .losses import build_loss
from .metrics import compute_metrics
from .model import DRNet


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--backbone", default="efficientnet_b3")
    p.add_argument("--size", type=int, default=300)
    p.add_argument("--no-clahe", action="store_true")
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--bs", type=int, default=16)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--wd", type=float, default=1e-4)
    p.add_argument("--clip", type=float, default=0.1)
    p.add_argument("--loss", default="ce", choices=["ce", "wce", "focal"])
    p.add_argument("--snapshots", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--split-seed", type=int, default=42)
    p.add_argument("--protocol", default="faithful", choices=["faithful", "clean"])
    p.add_argument("--hflip", action="store_true")
    p.add_argument("--amp", action="store_true")
    p.add_argument("--max-batches", type=int, default=0, help="smoke-test limit per epoch")
    return p.parse_args()


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


@torch.no_grad()
def predict(model, loader, device, amp):
    model.eval()
    probs, ys = [], []
    for x, y in loader:
        x = normalize_on_device(x.to(device, non_blocking=True))
        with torch.autocast(device.type, dtype=torch.float16, enabled=amp):
            logits = model(x)
        probs.append(torch.softmax(logits.float(), 1).cpu())
        ys.append(y)
    return torch.cat(probs).numpy(), torch.cat(ys).numpy()


def majority_vote(snap_probs: np.ndarray) -> np.ndarray:
    """Mode over snapshot argmax predictions; ties broken by mean probability."""
    votes = snap_probs.argmax(-1)  # (S, N)
    n_cls = snap_probs.shape[-1]
    counts = np.stack([(votes == c).sum(0) for c in range(n_cls)], 1).astype(float)
    counts += 1e-3 * snap_probs.mean(0)
    return counts.argmax(1)


def main():
    a = parse_args()
    seed_all(a.seed)
    device = torch.device("mps" if torch.backends.mps.is_available() else
                          "cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
        print("GPU:", torch.cuda.get_device_name(0), flush=True)
    out = ROOT / "runs" / a.run
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(vars(a), indent=2))

    arr, pos = load_cached(a.size, not a.no_clahe)
    split = make_split(a.split_seed, a.protocol)
    split.to_csv(out / "split.csv", index=False)
    cache_idx = split["image"].map(pos).to_numpy()
    labels = split["label"].to_numpy()
    sets = {s: np.where(split["split"].to_numpy() == s)[0] for s in ("train", "val", "test")}

    mk = lambda s, shuffle, flip: DataLoader(
        CachedDataset(arr, cache_idx[sets[s]], labels[sets[s]], hflip=flip), batch_size=a.bs, shuffle=shuffle,
        num_workers=2, persistent_workers=True, drop_last=shuffle)
    train_dl, val_dl, test_dl = mk("train", True, a.hflip), mk("val", False, False), mk("test", False, False)

    model = DRNet(a.backbone).to(device).to(memory_format=torch.channels_last)
    counts = torch.bincount(torch.from_numpy(labels[sets["train"]]), minlength=5)
    criterion = build_loss(a.loss, counts).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=a.lr, weight_decay=a.wd)

    snap_epochs = {round(a.epochs * k / a.snapshots) for k in range(1, a.snapshots + 1)}
    snaps = {"val": [], "test": [], "epochs": []}
    best_qwk, start = -2.0, 1
    ckpt = out / "last.pt"
    if ckpt.exists():
        state = torch.load(ckpt, map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        opt.load_state_dict(state["opt"])
        snaps, best_qwk, start = state["snaps"], state["best_qwk"], state["epoch"] + 1
        torch.set_rng_state(state["rng"].cpu())
        print(f"resumed from epoch {state['epoch']}", flush=True)
    elif (out / "log.jsonl").exists():
        (out / "log.jsonl").unlink()
    log = open(out / "log.jsonl", "a")
    for ep in range(start, a.epochs + 1):
        model.train()
        t0, tot, n = time.time(), 0.0, 0
        for b, (x, y) in enumerate(train_dl):
            if a.max_batches and b >= a.max_batches:
                break
            x, y = normalize_on_device(x.to(device, non_blocking=True)), y.to(device)
            with torch.autocast(device.type, dtype=torch.float16, enabled=a.amp):
                loss = criterion(model(x).float(), y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), a.clip)
            opt.step()
            tot += loss.item() * len(y)
            n += len(y)

        vp, vy = predict(model, val_dl, device, a.amp)
        vm = compute_metrics(vy, vp.argmax(1), vp)
        rec = {"epoch": ep, "train_loss": tot / max(n, 1), "val_qwk": vm["qwk"], "val_acc": vm["accuracy"],
               "val_macro_f1": vm["macro_f1"], "sec": round(time.time() - t0, 1)}
        print(json.dumps(rec), flush=True)
        log.write(json.dumps(rec) + "\n")
        log.flush()
        if vm["qwk"] > best_qwk:
            best_qwk = vm["qwk"]
            torch.save(model.state_dict(), out / "best.pt")
        if ep in snap_epochs:
            tp, ty = predict(model, test_dl, device, a.amp)
            snaps["val"].append(vp)
            snaps["test"].append(tp)
            snaps["epochs"].append(ep)
        try:
            torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "snaps": snaps, "best_qwk": best_qwk,
                        "epoch": ep, "rng": torch.get_rng_state()}, ckpt.with_suffix(".tmp"))
            ckpt.with_suffix(".tmp").replace(ckpt)
        except (RuntimeError, OSError) as e:
            ckpt.with_suffix(".tmp").unlink(missing_ok=True)
            print(f"warning: checkpoint save failed at epoch {ep}: {e}", flush=True)

    ty, vy = labels[sets["test"]], labels[sets["val"]]
    np.savez_compressed(out / "snapshot_probs.npz", val=np.stack(snaps["val"]), test=np.stack(snaps["test"]),
                        epochs=np.array(snaps["epochs"]), test_y=ty, val_y=vy,
                        test_images=split["image"].to_numpy()[sets["test"]])

    results = {"final_epoch": compute_metrics(ty, snaps["test"][-1].argmax(1), snaps["test"][-1])}
    model.load_state_dict(torch.load(out / "best.pt", map_location=device))
    bp, _ = predict(model, test_dl, device, a.amp)
    np.save(out / "best_test_probs.npy", bp)
    results["best_val"] = compute_metrics(ty, bp.argmax(1), bp)
    st = np.stack(snaps["test"])
    results["ensemble_vote"] = compute_metrics(ty, majority_vote(st), st.mean(0))
    results["ensemble_mean"] = compute_metrics(ty, st.mean(0).argmax(1), st.mean(0))
    results["best_val_qwk"] = best_qwk
    (out / "results.json").write_text(json.dumps(results, indent=2))
    for k in ("final_epoch", "best_val", "ensemble_vote", "ensemble_mean"):
        r = results[k]
        print(f"{k:14s} QWK={r['qwk']:.4f} acc={r['accuracy']:.4f} macroF1={r['macro_f1']:.4f} "
              f"AUC={r.get('macro_auc_ovr', float('nan')):.4f} minorityRecall={r['minority_recall']:.3f}")


if __name__ == "__main__":
    main()
