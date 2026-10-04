"""APTOS 2019 data: splitting, paper-faithful preprocessing, and a cached uint8 tensor dataset."""
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
IMG_DIR = DATA / "aptos512"
CACHE = DATA / "cache"
CLASS_NAMES = ["No DR", "Mild", "Moderate", "Severe", "PDR"]
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def make_split(seed: int = 42, protocol: str = "faithful", val_frac: float = 0.15,
               test_frac: float = 0.15) -> pd.DataFrame:
    """Stratified 70/15/15 split, the same proportions the paper used for EyePACS.

    APTOS ships 128 byte-identical duplicate rows (30 groups with conflicting grades).
    "faithful" keeps every row, as a naive reproduction would; "clean" drops conflicting groups and
    keeps one copy of each consistent group so no image appears in two splits.
    """
    df = pd.read_csv(DATA / "labels.csv")[["image", "label"]]
    if protocol == "clean":
        conflicting = df.groupby("image")["label"].transform("nunique") > 1
        df = df[~conflicting].drop_duplicates("image")
    elif protocol != "faithful":
        raise ValueError(protocol)
    df = df.reset_index(drop=True)
    trval, test = train_test_split(df, test_size=test_frac, stratify=df["label"], random_state=seed)
    train, val = train_test_split(trval, test_size=val_frac / (1 - test_frac), stratify=trval["label"],
                                  random_state=seed)
    df["split"] = "train"
    df.loc[val.index, "split"] = "val"
    df.loc[test.index, "split"] = "test"
    return df


def preprocess(path: Path, size: int, clahe_blur: bool) -> np.ndarray:
    """Paper strategy 2: CLAHE (on LAB luminance) then Gaussian blur, then a plain square resize."""
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if clahe_blur:
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[..., 0] = clahe.apply(lab[..., 0])
        bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        bgr = cv2.GaussianBlur(bgr, (5, 5), 0)
    bgr = cv2.resize(bgr, (size, size), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def load_cached(size: int, clahe_blur: bool) -> tuple[np.ndarray, dict[str, int]]:
    """Preprocessing is deterministic, so every unique image is processed once and memory-mapped.

    Returns the array and a map from image filename to its row in the array.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    tag = f"{size}_{'clahe' if clahe_blur else 'plain'}"
    arr_path, idx_path = CACHE / f"{tag}.npy", CACHE / f"{tag}.csv"
    if not arr_path.exists():
        names = pd.read_csv(DATA / "labels.csv")["image"].drop_duplicates().tolist()
        arr = np.lib.format.open_memmap(arr_path, mode="w+", dtype=np.uint8, shape=(len(names), size, size, 3))
        for i, name in enumerate(names):
            arr[i] = preprocess(IMG_DIR / name, size, clahe_blur)
        arr.flush()
        pd.DataFrame({"image": names}).to_csv(idx_path, index=False)
    names = pd.read_csv(idx_path)["image"]
    return np.load(arr_path, mmap_mode="r"), {n: i for i, n in enumerate(names)}


class CachedDataset(Dataset):
    def __init__(self, arr: np.ndarray, indices: np.ndarray, labels: np.ndarray, hflip: bool = False):
        self.arr, self.indices, self.labels, self.hflip = arr, indices, labels, hflip

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, i):
        x = torch.from_numpy(np.ascontiguousarray(self.arr[self.indices[i]])).permute(2, 0, 1)
        if self.hflip and torch.rand(1).item() < 0.5:
            x = x.flip(-1)
        return x, int(self.labels[i])


def normalize_on_device(x: torch.Tensor) -> torch.Tensor:
    """uint8 NCHW -> normalized float, done on the accelerator to keep the loader cheap."""
    mean = torch.tensor(IMAGENET_MEAN, device=x.device).view(1, 3, 1, 1)
    std = torch.tensor(IMAGENET_STD, device=x.device).view(1, 3, 1, 1)
    return ((x.float() / 255.0 - mean) / std).contiguous(memory_format=torch.channels_last)
