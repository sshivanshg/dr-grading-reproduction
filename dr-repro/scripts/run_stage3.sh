#!/usr/bin/env bash
# Stage 3 baseline queue, sized for an 8 GB Apple M2 (one run at a time, B3 at 224px/bs8 fits in ~2.8 GB).
# Runs resume from runs/<name>/last.pt if interrupted. Launch detached with scripts/launch.py.
# On a CUDA GPU (Colab/Kaggle) the exact paper protocol is: --size 300 --epochs 60 --bs 16.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p logs

run() {
  local name=$1; shift
  if [[ -f runs/$name/results.json ]]; then echo "skip $name"; return; fi
  echo "=== $name $(date)"
  caffeinate -i python -u -m src.train --run "$name" "$@" 2>&1 | grep --line-buffered -v MallocStack >> "logs/$name.log"
  python scripts/analyze.py "$name" 2>&1 | grep -v MallocStack
}

# Paper strategy 2 with the paper's hyper-parameters (headline reproduction).
run s2_faithful --size 224 --bs 8 --epochs 30 --snapshots 10 --protocol faithful
# Diagnostic: identical protocol with lr 1e-4, to test whether lr 1e-3 explains the gap.
run s2_lr1e4 --size 224 --bs 8 --epochs 30 --snapshots 10 --lr 1e-4 --protocol faithful
echo "=== all done $(date)"
