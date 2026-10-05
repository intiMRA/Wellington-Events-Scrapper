#!/bin/zsh
# One SAGA curation cycle: search the labelled pool for the training subset the CNN learns best from,
# warm-started from the subsets already deployed so the cycle can only move forward. ~18 h, ~114 CNN
# trainings, 30 generations.
#
#   caffeinate -i -m ./run_saga.sh 2>&1 | tee saga_$(date +%d%b).log
#
# WARM-START (anchor + forced finalist + gen-0 injection) — the subsets protected against regression:
#   ga_output        = the deployed curation
#   ga_output_backup = the one deploy rotated out
# Each is mapped onto the current pool by (description,label), so a file holding stale holdout rows is
# harmless here — build_prev_masks drops anything not in the pool. It is NOT harmless for
# cnn_eval_subset.py, which aborts on such a file; re-filter before any eval.
#
# SEED-ONLY sources get gen-0 injection ONLY. A warm-start entry is three things at once, and the anchor
# role is not free: the CNN floor is the ELEMENTWISE MAX of the anchors' per-class recall, so every extra
# anchor can only RAISE the floor and silently tighten the gate. Use SAGA_SEED_ONLY_FROM for subsets you
# want the search to explore FROM rather than ones you are protecting.
#
# GEN=30 IS DELIBERATE — do not cut it to save wall-clock. Across three cycles the winning generation was
# 0, then 23, then none at all. One cycle's champion was displaced into the archive only at gen 23 and
# then won the final re-check, so a GEN=10 run would have ended "KEPT" and that subset would never have
# existed. The arrival time of a winner is not predictable from the run so far.
#
# DEPLOY is gated on `replaced`: if the champion is a prev_* subset the run prints ROLLBACK CANDIDATE and
# writes nothing, because rotating a backup into place is a rollback and that is a human decision.
#
# AFTER THE RUN: SAGA's own end-of-run TEST= is a SINGLE measurement and its finalist ordering is a
# shortlist, not a result — twice now a 3-seed val ranking has failed to reproduce on 5-seed test. Confirm
# with ./run_cnn_eval.sh before believing or deploying anything.
cd "$(dirname "$0")"
export PYTHONPATH=$PWD RICH_FEATURES=0
export SAGA_POP=40 SAGA_GEN=30 SAGA_CNN_EPOCHS=10
export SAGA_WARMSTART_FROM=ga_output,ga_output_backup
export SAGA_ANCHOR_SEEDS=42,7,123   # anchors seed-averaged so the floor is not one noisy run
export SAGA_DEPLOY=1                # gated on `replaced`: a prev_* champion writes nothing
echo "=== SAGA start $(date '+%d/%m %H:%M') ==="
.venv/bin/python -u run_saga.py
echo "=== SAGA end $(date '+%d/%m %H:%M') ==="
