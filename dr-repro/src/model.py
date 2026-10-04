"""EfficientNet backbone with the paper's three-layer classifier head (Fig. 2 of Chilukoti et al. 2024)."""
import timm
import torch.nn as nn


class DRNet(nn.Module):
    def __init__(self, backbone: str = "efficientnet_b3", num_classes: int = 5, pretrained: bool = True):
        super().__init__()
        self.backbone = timm.create_model(backbone, pretrained=pretrained, num_classes=0, global_pool="avg")
        feat = self.backbone.num_features
        self.head = nn.Sequential(
            nn.Linear(feat, 512), nn.Dropout(0.5), nn.ReLU(inplace=True),
            nn.Linear(512, 512), nn.Dropout(0.25), nn.ReLU(inplace=True),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        return self.head(self.backbone(x))
