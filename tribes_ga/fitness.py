"""Shaped cross-validated fitness over the shared training pool.

Data (pool, labels, folds, per-fold trainer) comes from ``classification.Dataset`` — the
single source of truth shared with the incumbent DataCreator GA. The scoring itself is
reimplemented here so a tribes run owns its own baseline / tolerance / reward weights.

fold_score = mean_c(recall_c)   # balanced accuracy (surrogate trains class-weighted)
           - penalty_weight * sum_c max(0, (baseline_recall_c - floor_tolerance) - recall_c)

`selected` are GLOBAL training-pool indices (into Dataset.X_pool / pool_labels).
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
from sklearn.metrics import recall_score

from classification import Dataset as ds

# Per-fold per-class recall of the warm-start seed; the no-regression floor is
# measured against it. None until set_baseline() runs (then the floor is inactive
# and fitness is just overall_acc + reward — used while measuring the seed itself).
_baseline_fold_recall: Optional[List[np.ndarray]] = None

# CV folds used for fitness (a prefix of Dataset's fixed training folds). set_folds() lets a
# run trade fold count for speed; baseline and fitness must use the same folds.
_folds: List[np.ndarray] = list(ds.POOL_FOLDS)


def set_folds(n: int) -> None:
    global _folds
    _folds = list(ds.POOL_FOLDS)[:n] if n else list(ds.POOL_FOLDS)


def set_baseline(seed_indices: np.ndarray) -> None:
    """Record the seed subset's per-fold per-class recall as the no-regression floor."""
    global _baseline_fold_recall
    recalls: List[np.ndarray] = []
    for train_fold, val_fold in _folds:
        train_idx = np.intersect1d(seed_indices, train_fold)
        preds = ds.fit_predict(train_idx, val_fold)
        if preds is None:
            raise ValueError("Seed subset covers <2 classes in a training fold; cannot set baseline.")
        recalls.append(recall_score(ds.pool_labels[val_fold], preds, labels=ds.ALL_LABELS,
                                    average=None, zero_division=0))
    _baseline_fold_recall = recalls


def set_baseline_multi(subsets: List[np.ndarray]) -> None:
    """No-regression floor = per-fold, per-class ELEMENTWISE MAX of recall over several reference
    subsets (e.g. the full pool AND each previously deployed curation). A candidate is then penalised
    for dropping any class below the best recall any reference achieved on it — i.e. gated to the
    previous best, not just to all-data (added 14 Sep 2026)."""
    global _baseline_fold_recall
    per_subset: List[List[np.ndarray]] = []
    for sub in subsets:
        set_baseline(sub)
        per_subset.append(list(_baseline_fold_recall))  # type: ignore[arg-type]
    _baseline_fold_recall = [np.max([ps[f] for ps in per_subset], axis=0) for f in range(len(_folds))]


def baseline_min_recall() -> float:
    assert _baseline_fold_recall is not None
    return float(np.mean(_baseline_fold_recall, axis=0).min())


def cv_fitness(selected: np.ndarray, floor_tolerance: float, reward_weight: float,
               penalty_weight: float) -> float:
    """Mean shaped fitness of a subset over Dataset's fixed training-pool folds. Trains on
    the subset's samples outside each fold, validates on the whole fold."""
    if selected.shape[0] < 2:
        return float("-inf")
    scores: List[float] = []
    for fold, (train_fold, val_fold) in enumerate(_folds):
        train_idx = np.intersect1d(selected, train_fold)
        preds = ds.fit_predict(train_idx, val_fold)
        if preds is None:
            return 0.0
        y_true = ds.pool_labels[val_fold]
        recalls = recall_score(y_true, preds, labels=ds.ALL_LABELS, average=None, zero_division=0)
        # BALANCED accuracy (mean per-class recall), not raw accuracy: the surrogate now trains
        # class-weighted (Dataset.fit_predict), so raw accuracy would let the 3k-row classes
        # dominate the ruler. reward_weight is retained in the signature but folded in here.
        balanced = float(recalls.mean())
        if _baseline_fold_recall is None:
            scores.append(balanced)
        else:
            deficit = float(np.maximum(0.0, (_baseline_fold_recall[fold] - floor_tolerance) - recalls).sum())
            scores.append(balanced - penalty_weight * deficit)
    return float(np.mean(scores))
