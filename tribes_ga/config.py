"""All knobs for a tribes_ga run in one place — flip experiments here."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Tuple


class TribeMode(StrEnum):
    # N independent island populations of full-pool masks + periodic migration
    # (and an optional global merge). Best at escaping local optima via diversity.
    ISLAND = "island"
    # One tribe per class evolves that class's samples; each tribe individual is
    # scored stitched with the current best of every OTHER tribe (cooperative
    # coevolution). Aligns with the per-class no-regression objective.
    CLASS_COEVOLUTION = "class_coevolution"
    # class_coevolution for the first `merge_at` of the run, then stitch the tribe
    # populations into full masks and finish as one global island population.
    HYBRID = "hybrid"
    # Run an arbitrary sequence of phases (see `pipeline`), each phase seeded from the
    # previous phase's best. Lets you chain any combination, e.g. island -> coev ->
    # island (a "full hybrid" using all the ideas).
    PIPELINE = "pipeline"


class Phase(StrEnum):
    """A stage in a PIPELINE run."""
    ISLAND = "I"   # global island evolution
    COEV = "C"     # per-class cooperative coevolution


@dataclass
class TribesConfig:
    mode: TribeMode = TribeMode.ISLAND
    # For mode=PIPELINE: the phase sequence to run (each seeded from the prior best).
    pipeline: Optional[Tuple[Phase, ...]] = None

    # --- diploidy (opt-in adaptive-dominance; see genome.py) ---
    diploid: bool = False
    stochastic_dominance: bool = False  # express a0 with prob=dominance vs a 0.5 threshold

    # --- population / run size ---
    num_tribes: int = 4          # islands (ISLAND/HYBRID); CLASS_COEVOLUTION uses one tribe per class
    pop_per_tribe: int = 60
    generations: int = 60

    # --- island migration / hybrid merge ---
    # Migration only applies between islands (ISLAND, and the island phases of
    # HYBRID/PIPELINE): they share one full-pool genome space. Coevolution tribes hold
    # per-class genomes of different lengths, so individuals cannot migrate between them.
    migration_interval: int = 5   # ISLAND: migrate every N generations (0 disables migration)
    migration_rate: float = 0.1   # ISLAND: fraction of each island migrated per event, ring topology
                                  # (floored to >=1 individual when active; 0.0 disables migration)
    merge_at: float = 0.5        # HYBRID: fraction of generations before merging to a global population

    # --- operators ---
    crossover_prob: float = 0.7
    tournament_k: int = 3
    elitism: int = 3
    # batch-relative fitness-scaled bit-flip mutation (the anti-collapse trick from
    # DataCreator): the fittest offspring in a batch flips `mut_genes_min` bits, the
    # worst flips `mut_genes_max`, linear between. Clamped to the genome length.
    mut_genes_min: int = 5
    mut_genes_max: int = 400

    # --- shaped fitness (borrowed from DataCreator) ---
    floor_tolerance: float = 0.03
    reward_weight: float = 0.25
    penalty_weight: float = 2.0
    n_folds: int = 5             # CV folds used for fitness (fewer = faster, noisier; max 5)

    # --- warm start (near-seed init that stabilised DataCreator) ---
    warm_start: bool = True
    perturb_min: float = 0.02    # per-individual init perturbation fraction (range)
    perturb_max: float = 0.20

    seed: int = 42
