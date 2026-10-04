"""Download APTOS 2019 (full-resolution HF mirror) shard-by-shard, downsize, and write a labels CSV.

Disk is tight, so each ~500 MB parquet shard is deleted right after its images are re-encoded
at a 512 px longest side (aspect ratio preserved). Training-time resizing happens later.
"""
import hashlib
import io
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from PIL import Image

REPO = "sngsfydy/aptos"
ROOT = Path(__file__).resolve().parents[1]
OUT_IMG = ROOT / "data" / "aptos512"
TMP = ROOT / "data" / "_tmp"
MAX_SIDE = 512


def list_shards():
    url = f"https://huggingface.co/api/datasets/{REPO}/tree/main/data"
    with urllib.request.urlopen(url) as r:
        files = json.load(r)
    return sorted(f["path"] for f in files if f["path"].endswith(".parquet"))


def main():
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    rows_path = ROOT / "data" / "labels.csv"
    rows = pd.read_csv(rows_path).to_dict("records") if rows_path.exists() else []
    done_shards = {r["shard"] for r in rows}

    for shard in list_shards():
        name = Path(shard).name
        if name in done_shards:
            print("skip", name, flush=True)
            continue
        local = TMP / name
        url = f"https://huggingface.co/datasets/{REPO}/resolve/main/{shard}"
        print("download", name, flush=True)
        subprocess.run(["curl", "-sSL", "--retry", "5", "-C", "-", "-o", str(local), url], check=True)

        pf = pq.ParquetFile(local)
        idx_in_shard = 0
        for rg in range(pf.num_row_groups):
            tbl = pf.read_row_group(rg).to_pydict()
            for img, label in zip(tbl["image"], tbl["label"]):
                raw = img["bytes"]
                sha = hashlib.sha1(raw).hexdigest()[:16]
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                w, h = im.size
                s = MAX_SIDE / max(w, h)
                im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
                fname = f"{sha}.jpg"
                im.save(OUT_IMG / fname, quality=95)
                rows.append({"image": fname, "label": int(label), "orig_w": w, "orig_h": h,
                             "shard": name, "idx": idx_in_shard})
                idx_in_shard += 1
        local.unlink()
        pd.DataFrame(rows).to_csv(rows_path, index=False)
        print(f"  {name}: {idx_in_shard} images, total {len(rows)}", flush=True)

    df = pd.DataFrame(rows)
    print("total", len(df), "unique files", df["image"].nunique())
    print(df["label"].value_counts().sort_index().to_string())
    TMP.rmdir()


if __name__ == "__main__":
    sys.exit(main())
