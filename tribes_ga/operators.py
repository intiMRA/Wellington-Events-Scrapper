"""GA operators over binary-mask genomes: uniform crossover, batch-relative
fitness-scaled mutation (bit flips; the anti-collapse trick from DataCreator),
tournament selection, elitism, and ring migration."""
from __future__ import annotations

from typing import Callable, List

import numpy as np

from tribes_ga.config import TribesConfig
from tribes_ga.genome import Individual, genome_length

Evaluator = Callable[[Individual], float]


def crossover(p1: Individual, p2: Individual, rng: np.random.Generator, cfg: TribesConfig) -> Individual:
    if rng.random() >= cfg.crossover_prob:
        return p1.copy()
    if p1.diploid:
        assert p1.a0 is not None and p2.a0 is not None
        length = p1.a0.shape[0]
        take = rng.random(length) < 0.5
        child = Individual(diploid=True)
        assert p1.a1 is not None and p2.a1 is not None and p1.dominance is not None and p2.dominance is not None
        child.a0 = np.where(take, p1.a0, p2.a0).astype(np.int8)
        child.a1 = np.where(take, p2.a1, p1.a1).astype(np.int8)   # other allele from the other parent
        child.dominance = np.where(take, p1.dominance, p2.dominance)
        return child
    assert p1.mask is not None and p2.mask is not None
    take = rng.random(p1.mask.shape[0]) < 0.5
    child = Individual(diploid=False)
    child.mask = np.where(take, p1.mask, p2.mask).astype(np.int8)
    return child


def _flip(ind: Individual, k: int, rng: np.random.Generator) -> None:
    length = genome_length(ind)
    k = min(max(1, k), length)
    pos = rng.choice(length, size=k, replace=False)
    if not ind.diploid:
        assert ind.mask is not None
        ind.mask[pos] = 1 - ind.mask[pos]
        return
    assert ind.a0 is not None and ind.a1 is not None and ind.dominance is not None
    silent = rng.random(k) < 0.5   # silent flip = hidden allele (genotype diversity, no phenotype change)
    for j, p in enumerate(pos):
        express_a0 = ind.dominance[p] >= 0.5
        if silent[j]:
            if express_a0:
                ind.a1[p] = 1 - ind.a1[p]
            else:
                ind.a0[p] = 1 - ind.a0[p]
        else:   # loud flip = expressed allele, plus a small dominance nudge
            if express_a0:
                ind.a0[p] = 1 - ind.a0[p]
            else:
                ind.a1[p] = 1 - ind.a1[p]
            ind.dominance[p] = float(np.clip(ind.dominance[p] + rng.uniform(-0.2, 0.2), 0.0, 1.0))


def mutate_batch(offspring: List[Individual], evaluate: Evaluator, cfg: TribesConfig,
                 rng: np.random.Generator) -> None:
    """Flip a batch-relative number of bits per offspring: the fittest in the batch
    flips `mut_genes_min`, the worst `mut_genes_max` (scaled to this batch's fitness
    range), so the best candidates fine-tune while the rest explore. In place."""
    if not offspring:
        return
    fits = np.array([evaluate(o) for o in offspring], dtype=np.float64)
    fits = np.where(np.isfinite(fits), fits, fits[np.isfinite(fits)].min() if np.any(np.isfinite(fits)) else 0.0)
    hi, lo = float(fits.max()), float(fits.min())
    span = hi - lo
    for i, o in enumerate(offspring):
        frac = 0.0 if span == 0.0 else (hi - float(fits[i])) / span
        k = cfg.mut_genes_min + int(round(frac * (cfg.mut_genes_max - cfg.mut_genes_min)))
        _flip(o, k, rng)


def tournament_select(pop: List[Individual], k: int, rng: np.random.Generator) -> Individual:
    idx = rng.integers(0, len(pop), size=min(k, len(pop)))
    best = pop[int(idx[0])]
    for j in idx[1:]:
        if pop[int(j)].fitness > best.fitness:
            best = pop[int(j)]
    return best


def elites(pop: List[Individual], n: int) -> List[Individual]:
    return [ind.copy() for ind in sorted(pop, key=lambda x: x.fitness, reverse=True)[:n]]


def migrate_ring(islands: List[List[Individual]], k: int) -> None:
    """Copy the top `k` of each island into the next island (ring), replacing its
    worst `k`. In place."""
    if len(islands) < 2:
        return
    senders = [sorted(isl, key=lambda x: x.fitness, reverse=True)[:k] for isl in islands]
    for i, isl in enumerate(islands):
        incoming = senders[(i - 1) % len(islands)]
        isl.sort(key=lambda x: x.fitness)   # worst first
        for j, migrant in enumerate(incoming):
            if j < len(isl):
                isl[j] = migrant.copy()
