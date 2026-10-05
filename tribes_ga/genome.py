"""Genome: a variable-size binary in/out mask over a set of pool samples.

Two representations, chosen per individual:

* Haploid — a single int8 mask; phenotype = the mask itself.
* Diploid (adaptive-dominance) — two allele masks (a0, a1) plus a continuous
  per-gene dominance d in [0, 1]. The expressed phenotype bit is a0 where d >= 0.5
  else a1 (or, with stochastic dominance, a0 with probability d). The hidden allele
  is latent diversity: a "silent" mutation flips it without changing the phenotype,
  so the population can cheaply revert a gene later (noise/optimum-spike hedging)
  instead of rediscovering it. This is the redesigned, ablatable recessive-gene idea.

A "gene" is a position in the mask; the tribe orchestrator maps mask positions to
global pool indices (identity for island masks, per-class for coevolution tribes).
"""
from __future__ import annotations

from typing import Optional

import numpy as np


class Individual:
    def __init__(self, diploid: bool) -> None:
        self.diploid = diploid
        self.mask: Optional[np.ndarray] = None          # haploid genotype/phenotype
        self.a0: Optional[np.ndarray] = None            # diploid allele A
        self.a1: Optional[np.ndarray] = None            # diploid allele B
        self.dominance: Optional[np.ndarray] = None     # diploid per-gene dominance in [0, 1]
        self.fitness: float = float("-inf")

    def express(self, stochastic: bool = False, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        """The phenotype mask (int8) actually seen by the fitness function."""
        if not self.diploid:
            assert self.mask is not None
            return self.mask
        assert self.a0 is not None and self.a1 is not None and self.dominance is not None
        if stochastic:
            assert rng is not None
            take_a0 = rng.random(self.dominance.shape[0]) < self.dominance
        else:
            take_a0 = self.dominance >= 0.5
        return np.where(take_a0, self.a0, self.a1).astype(np.int8)

    def selected_indices(self) -> np.ndarray:
        """Local mask positions that are switched on (variable count)."""
        return np.where(self.express() == 1)[0]

    def copy(self) -> "Individual":
        clone = Individual(self.diploid)
        clone.fitness = self.fitness
        if self.diploid:
            assert self.a0 is not None and self.a1 is not None and self.dominance is not None
            clone.a0 = self.a0.copy()
            clone.a1 = self.a1.copy()
            clone.dominance = self.dominance.copy()
        else:
            assert self.mask is not None
            clone.mask = self.mask.copy()
        return clone


def haploid_from_mask(mask: np.ndarray) -> Individual:
    ind = Individual(diploid=False)
    ind.mask = mask.astype(np.int8)
    return ind


def diploid_from_mask(mask: np.ndarray) -> Individual:
    """Seed a diploid individual that initially expresses `mask` (both alleles equal
    the mask, dominance = 1.0), so warm starts express the seed exactly. Silent
    mutations then diversify the hidden allele over time."""
    ind = Individual(diploid=True)
    m = mask.astype(np.int8)
    ind.a0 = m.copy()
    ind.a1 = m.copy()
    ind.dominance = np.ones(m.shape[0], dtype=np.float64)
    return ind


def from_mask(mask: np.ndarray, diploid: bool) -> Individual:
    return diploid_from_mask(mask) if diploid else haploid_from_mask(mask)


def genome_length(ind: Individual) -> int:
    arr = ind.a0 if ind.diploid else ind.mask
    assert arr is not None
    return int(arr.shape[0])
