"""Coevolution's genome-to-global-mask bridge.

A cooperative-coevolution tribe owns one class's samples, so its genome is a mask
over just that class's slice of the pool. To be scored, a tribe genome must be
*stitched* into a full-pool mask alongside the other tribes' current champions.
This is the only place that mapping lives.
"""
from __future__ import annotations

from typing import List

import numpy as np

from tribes_ga.genome import Individual


def stitch(members: List[Individual], class_idx: List[np.ndarray], pool_size: int) -> np.ndarray:
    """Combine one champion per class into a single global-pool mask."""
    full = np.zeros(pool_size, dtype=np.int8)
    for c, ind in enumerate(members):
        full[class_idx[c]] = ind.express()
    return full


def stitch_with(candidate: Individual, c: int, bests: List[Individual],
                class_idx: List[np.ndarray], pool_size: int) -> np.ndarray:
    """Global mask using `candidate` for class `c` and the current best for every
    other class — the cooperative evaluation context for one tribe's individual."""
    full = np.zeros(pool_size, dtype=np.int8)
    for t in range(len(class_idx)):
        full[class_idx[t]] = (candidate if t == c else bests[t]).express()
    return full
