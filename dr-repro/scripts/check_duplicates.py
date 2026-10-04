"""Exact-duplicate audit for APTOS 2019 under the faithful (naive random) split.

Perceptual hashes are unreliable here (every fundus photo is a bright disc on black, so a 64-bit
dHash flags thousands of false pairs); byte-identical images are unambiguous.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import ROOT, make_split  # noqa: E402


def main():
    df = make_split(42, "faithful")
    groups = df.groupby("image")
    dup = groups.filter(lambda g: len(g) > 1)
    conflicting = dup.groupby("image")["label"].nunique().gt(1)
    test = df[df["split"] == "test"]
    train_imgs = set(df.loc[df["split"] == "train", "image"])
    leaked = test[test["image"].isin(train_imgs)]
    leaked_conf = leaked["image"].map(conflicting).fillna(False).sum()
    clean = make_split(42, "clean")
    report = {
        "rows": len(df), "unique_images": int(df["image"].nunique()),
        "duplicate_groups": int(dup["image"].nunique()), "extra_duplicate_rows": int(len(dup) - dup["image"].nunique()),
        "groups_with_conflicting_grades": int(conflicting.sum()),
        "faithful_test_rows": len(test), "faithful_test_rows_with_identical_image_in_train": len(leaked),
        "of_which_conflicting_grade": int(leaked_conf),
        "clean_protocol_rows": len(clean), "clean_class_counts": clean["label"].value_counts().sort_index().tolist(),
    }
    print(json.dumps(report, indent=2))
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "duplicates.json").write_text(json.dumps(report, indent=2))
    dup.sort_values("image").to_csv(ROOT / "results" / "duplicate_rows.csv", index=False)


if __name__ == "__main__":
    main()
