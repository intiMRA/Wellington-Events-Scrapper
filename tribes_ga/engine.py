"""The generic genetic-algorithm engine shared by every tribe strategy.

A "tribe" is one population of mask genomes. These helpers initialise a population
from a warm-start seed and advance it a single generation; they know nothing about
islands, coevolution, or global-pool geometry — the strategies in
``tribes_ga.strategies`` compose them.
"""
from __future__ import annotations

from typing import Callable, List, Optional

import numpy as np

from tribes_ga import genome, operators, warmstart
from tribes_ga.config import TribesConfig
from tribes_ga.genome import Individual

Evaluator = Callable[[Individual], float]


def make_population(length: int, size: int, base_mask: Optional[np.ndarray],
                    cfg: TribesConfig, rng: np.random.Generator, evaluate: Evaluator) -> List[Individual]:
    """Build and score one population of `size` genomes over a mask of `length` genes.

    Warm start clones the seed once and fills the rest with near-seed perturbations
    (the initialisation that stopped DataCreator collapsing onto its seed); otherwise
    every genome is random.
    """
    pop: List[Individual] = []
    if cfg.warm_start and base_mask is not None:
        pop.append(genome.from_mask(base_mask, cfg.diploid))
        for _ in range(size - 1):
            pop.append(genome.from_mask(
                warmstart.perturbed(base_mask, rng, cfg.perturb_min, cfg.perturb_max), cfg.diploid))
    else:
        for _ in range(size):
            pop.append(genome.from_mask(warmstart.random_mask(length, rng), cfg.diploid))
    for ind in pop:
        ind.fitness = evaluate(ind)
    return pop


def evolve(pop: List[Individual], evaluate: Evaluator, cfg: TribesConfig,
           rng: np.random.Generator) -> List[Individual]:
    """Advance one population by a single generation: elitism carried over, the rest
    filled by tournament-selected crossover then batch-relative fitness-scaled
    mutation. Returns the next population (same size)."""
    keep = min(cfg.elitism, len(pop))
    next_gen = operators.elites(pop, keep)
    offspring: List[Individual] = []
    for _ in range(len(pop) - keep):
        p1 = operators.tournament_select(pop, cfg.tournament_k, rng)
        p2 = operators.tournament_select(pop, cfg.tournament_k, rng)
        offspring.append(operators.crossover(p1, p2, rng, cfg))
    operators.mutate_batch(offspring, evaluate, cfg, rng)
    for o in offspring:
        o.fitness = evaluate(o)
    return next_gen + offspring


def print_gen(gen: int, fits: List[float]) -> None:
    print(f"  gen {gen + 1:>3}  top: " + ", ".join(f"{f:.6f}" for f in fits))
