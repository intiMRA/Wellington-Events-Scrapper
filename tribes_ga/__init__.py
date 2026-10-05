"""tribes_ga — GA building blocks for training-subset selection.

Since 13 Sep 2026 this is a library only: the diploid genome, per-class (coevolution)
population engine, shaped no-regression fitness, stitch bridge and warm-start helpers used
by the CNN-in-the-loop driver ``run_saga.py`` in the repo root. The standalone runner,
the island/hybrid/pipeline strategies and the benchmark were removed once SAGA became the
one production path (see session notes / tribes_ga/README.md).
"""
from tribes_ga.config import TribesConfig, TribeMode

__all__ = ["TribesConfig", "TribeMode"]
