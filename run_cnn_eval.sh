#!/bin/zsh
# Honest multi-seed CNN check of one or more curated subsets against the clean holdout.
#
#   ./run_cnn_eval.sh data/training/ga_output.json data/training/splits/training.json
#   CNN_EVAL_SEEDS=13453379,42,7,123,999 CNN_EVAL_OUT_SUFFIX=_5seed ./run_cnn_eval.sh <files...>
#
# With no arguments it measures the deployed curation, the rotated previous one, and the full pool —
# the standing three-row comparison.
#
# READ THE RESULTS THIS WAY:
#   * Judge on the SINGLE-MODEL per-seed mean. That is what production ships. The probability-averaged
#     ensemble column overstates it by ~4 points and has twice reversed a ranking.
#   * 5 seeds is the floor for any deploy decision: single-seed TEST for ONE fixed subset spans ~0.035
#     (about 12 test rows), so a 3-seed gap is usually smaller than its own noise.
#   * Check a paired t before calling a winner. At n=5 you need |t| >= 2.78; no pairwise comparison in
#     this project has ever reached it, so expect "no significant difference" and rank on size and
#     minority-class recall instead.
#   * One holdout example is ~2.6 points of class recall. Read per-class deltas in EXAMPLES, not percent.
#
# LEAK: a subset file is a frozen row list, not a view over the pool, so one written before a split
# rebuild can hold rows that are now val/test. cnn_eval_subset.py ABORTS on that rather than warning.
# The fix is to re-filter the file against data/training/splits/training.json, not to override the guard.
#
# Output per subset: data/training/cnn_eval_<tag><CNN_EVAL_OUT_SUFFIX>.json. Set the suffix when running
# a different seed count so results from other runs are not overwritten.
cd "$(dirname "$0")"
export PYTHONPATH=$PWD RICH_FEATURES=0
files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  files=(data/training/ga_output.json data/training/ga_output_backup.json data/training/splits/training.json)
fi
for f in $files; do
  echo "=== $f  $(date '+%d/%m %H:%M') ==="
  .venv/bin/python -u cnn_eval_subset.py "$f" 2>&1 | grep --line-buffered -v "warn\|Warning"
done
echo "ALL EVALS DONE $(date '+%d/%m %H:%M')"
