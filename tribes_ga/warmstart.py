"""Warm-start helpers: turn the shared class-balanced seed into masks, and make
near-seed perturbations (the initialisation that stopped the search collapsing)."""
from __future__ import annotations

from typing import List

import numpy as np

from classification import Dataset as ds


def pool_size() -> int:
    return int(ds.X_pool.shape[0])


def class_indices(c: int) -> np.ndarray:
    """Global pool indices whose label is class `c`."""
    return np.where(ds.pool_labels == c)[0]


def all_class_indices() -> List[np.ndarray]:
    return [class_indices(c) for c in range(ds.num_classes)]


def seed_mask() -> np.ndarray:
    """Full training-pool binary mask seeded from ALL rows (start-from-everything). The mask
    GA then curates by REMOVING redundant / noisy rows, rather than growing from a tiny
    balanced seed. Class imbalance is handled by the class-weighted surrogate
    (Dataset.fit_predict) and the per-class no-regression floor (measured against this full
    seed), so removals that would drop any class's recall are penalised — the search prunes
    only rows it can drop safely. Set env TRIBES_SEED_BALANCED=1 to restore the old balanced
    seed (grow-from-small)."""
    import os
    if os.environ.get("TRIBES_SEED_BALANCED") == "1":
        mask = np.zeros(pool_size(), dtype=np.int8)
        mask[np.asarray(ds.balanced_seed, dtype=int)] = 1
        return mask
    return np.ones(pool_size(), dtype=np.int8)


def perturbed(mask: np.ndarray, rng: np.random.Generator, pmin: float, pmax: float) -> np.ndarray:
    """A near-seed copy of `mask` with a random pmin..pmax fraction of bits flipped."""
    out = mask.copy()
    n = out.shape[0]
    lo = max(1, int(n * pmin))
    hi = max(lo, int(n * pmax))
    k = int(rng.integers(lo, hi + 1))
    pos = rng.choice(n, size=k, replace=False)
    out[pos] = 1 - out[pos]
    return out


def random_mask(length: int, rng: np.random.Generator, density: float = 0.5) -> np.ndarray:
    return (rng.random(length) < density).astype(np.int8)
