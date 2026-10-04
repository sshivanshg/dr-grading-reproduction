#!/usr/bin/env bash
# Exact paper protocol on a CUDA GPU (Colab T4): EfficientNet-B3, CLAHE + blur, 300 px, 60 epochs, batch 16,
# 10 snapshots. Re-running resumes unfinished runs from runs/<name>/last.pt and skips finished ones.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs

run() {
  local name=$1; shift
  if [[ -f runs/$name/results.json ]]; then echo "skip $name (already finished)"; return; fi
  echo "=== $name $(date)"
  python -u -m src.train --run "$name" "$@" 2>&1 | tee -a "logs/$name.log"
  if [[ -f runs/$name/results.json ]]; then
    python scripts/analyze.py "$name"
    python scripts/leakage_eval.py "$name"
    rm -f "runs/$name/last.pt"
  else
    echo "!!! $name did not finish; re-run this script to resume"
    exit 1
  fi
}

# 1. Paper hyper-parameters at the paper's resolution and schedule (the faithful reproduction).
run s2_paper300 --size 300 --bs 16 --epochs 60 --snapshots 10 --lr 1e-3 --protocol faithful
# 2. Same protocol with lr 1e-4 (does the learning-rate finding hold at 300 px / 60 epochs?).
run s2_paper300_lr1e4 --size 300 --bs 16 --epochs 60 --snapshots 10 --lr 1e-4 --protocol faithful
echo "=== all done $(date)"
