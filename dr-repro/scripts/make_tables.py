"""Turn runs/*/results.json into LaTeX tables included by reports/stage2_3_report.tex."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data import CLASS_NAMES, ROOT  # noqa: E402

GEN = ROOT / "reports" / "generated"
RUNS = [("s2_paper300", r"300\,px/60 ep, lr $10^{-3}$ (paper)"),
        ("s2_paper300_lr1e4", r"300\,px/60 ep, lr $10^{-4}$"),
        ("s2_faithful", r"224\,px/30 ep, lr $10^{-3}$ (M2)"),
        ("s2_lr1e4", r"224\,px/30 ep, lr $10^{-4}$ (M2)")]
VARIANTS = [("final_epoch", "final epoch"), ("best_val", "best val QWK"),
            ("ensemble_vote", "snapshot vote"), ("ensemble_mean", "snapshot mean")]


def load(run):
    p = ROOT / "runs" / run / "results.json"
    return json.loads(p.read_text()) if p.exists() else None


def main_table():
    lines = [r"\begin{table*}[t]", r"\centering",
             r"\caption{Reproduced test-set results on APTOS 2019 (550 test images, faithful split). Paper: QWK 0.954 "
             r"(single model, ImageNet init) and 0.967 (EyePACS init + snapshot ensemble).}",
             r"\label{tab:main}", r"\footnotesize",
             r"\begin{tabular}{llcccccc}", r"\toprule",
             r"Configuration & Prediction & QWK & Acc. & Macro-F1 & Macro AUC & Minority recall & $|\Delta|\geq2$ errors \\",
             r"\midrule"]
    for run, label in RUNS:
        res = load(run)
        if res is None:
            continue
        for i, (key, vlabel) in enumerate(VARIANTS):
            r = res[key]
            lines.append(f"{label if i == 0 else ''} & {vlabel} & {r['qwk']:.3f} & {r['accuracy']:.3f} & "
                         f"{r['macro_f1']:.3f} & {r['macro_auc_ovr']:.3f} & {r['minority_recall']:.3f} & "
                         f"{r['large_errors']} \\\\")
        lines.append(r"\midrule")
    lines[-1] = r"\bottomrule"
    lines += [r"\end{tabular}", r"\end{table*}"]
    (GEN / "main_table.tex").write_text("\n".join(lines) + "\n")


def per_class_table(run="s2_paper300", key="ensemble_vote"):
    res = load(run)
    if res is None:
        return
    rows = []
    for k, vlabel in [("best_val", "best val"), (key, "snapshot vote")]:
        pc = res[k]["per_class"]
        for c in CLASS_NAMES:
            d = pc[c]
            rows.append(f"{c} & {vlabel} & {d['precision']:.2f} & {d['recall']:.2f} & {d['f1']:.2f} & {d['support']} \\\\")
        rows.append(r"\midrule")
    rows[-1] = r"\bottomrule"
    body = "\n".join(rows)
    (GEN / "per_class_table.tex").write_text(
        r"\begin{table}[t]" "\n" r"\centering" "\n"
        r"\caption{Per-class test metrics, exact paper protocol (300\,px, 60 epochs, lr $10^{-3}$).}" "\n" r"\label{tab:perclass}" "\n"
        r"\footnotesize" "\n" r"\begin{tabular}{llcccc}" "\n" r"\toprule" "\n"
        r"Grade & Model & Prec. & Recall & F1 & $n$ \\" "\n" r"\midrule" "\n" + body + "\n"
        r"\end{tabular}" "\n" r"\end{table}" "\n")


def macros():
    """Key numbers as LaTeX macros so prose never drifts from the tables."""
    out = []
    names = {"s2_faithful": "SII", "s2_lr1e4": "SIIlow", "s2_paper300": "Full", "s2_paper300_lr1e4": "Fulllow"}
    for run, tag in names.items():
        res = load(run)
        if res is None:
            continue
        for key, ktag in [("final_epoch", "Final"), ("best_val", "Best"), ("ensemble_vote", "Vote"),
                          ("ensemble_mean", "Mean")]:
            r = res[key]
            out.append(f"\\newcommand{{\\{tag}{ktag}QWK}}{{{r['qwk']:.3f}}}")
            out.append(f"\\newcommand{{\\{tag}{ktag}Acc}}{{{r['accuracy']:.3f}}}")
            out.append(f"\\newcommand{{\\{tag}{ktag}MF}}{{{r['macro_f1']:.3f}}}")
            out.append(f"\\newcommand{{\\{tag}{ktag}MinRec}}{{{r['minority_recall']:.3f}}}")
            pc = r["per_class"]
            out.append(f"\\newcommand{{\\{tag}{ktag}SevRec}}{{{pc['Severe']['recall']:.2f}}}")
            out.append(f"\\newcommand{{\\{tag}{ktag}PDRRec}}{{{pc['PDR']['recall']:.2f}}}")
            out.append(f"\\newcommand{{\\{tag}{ktag}MildRec}}{{{pc['Mild']['recall']:.2f}}}")
    (GEN / "numbers.tex").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    GEN.mkdir(parents=True, exist_ok=True)
    main_table()
    per_class_table()
    macros()
    print("tables written to", GEN)
