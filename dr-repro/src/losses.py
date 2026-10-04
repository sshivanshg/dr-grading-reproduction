"""Loss functions. Cross-entropy reproduces the paper; the rest are held for the Stage 4/5 hypothesis."""
import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, weight: torch.Tensor | None = None):
        super().__init__()
        self.gamma, self.weight = gamma, weight

    def forward(self, logits, target):
        logp = F.log_softmax(logits, dim=1)
        ce = F.nll_loss(logp, target, weight=self.weight, reduction="none")
        pt = logp.gather(1, target[:, None]).squeeze(1).exp()
        return ((1 - pt) ** self.gamma * ce).mean()


def build_loss(name: str, class_counts: torch.Tensor) -> nn.Module:
    if name == "ce":
        return nn.CrossEntropyLoss()
    inv = class_counts.sum() / (len(class_counts) * class_counts.float())
    if name == "wce":
        return nn.CrossEntropyLoss(weight=inv)
    if name == "focal":
        return FocalLoss(gamma=2.0)
    raise ValueError(name)
