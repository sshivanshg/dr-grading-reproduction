"""Evaluation: QWK (primary), accuracy, macro-F1, per-class P/R/F1, macro OvR AUC, confusion matrix."""
import numpy as np
from sklearn.metrics import (accuracy_score, cohen_kappa_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support, roc_auc_score)

from .data import CLASS_NAMES


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, probs: np.ndarray | None = None) -> dict:
    labels = list(range(len(CLASS_NAMES)))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    out = {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "per_class": {CLASS_NAMES[i]: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]),
                                       "support": int(s[i])} for i in labels},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "minority_recall": float(np.mean([r[3], r[4]])),
        "large_errors": int(np.sum(np.abs(y_true - y_pred) >= 2)),
    }
    if probs is not None:
        out["macro_auc_ovr"] = float(roc_auc_score(y_true, probs, multi_class="ovr", average="macro"))
    return out
