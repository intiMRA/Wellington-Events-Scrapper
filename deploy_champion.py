"""Deploy a SAGA champion: turn `saga_champion_rows.json` (written by run_saga.py) into the
files the CNN trains on and the next SAGA loop warm-starts from.

    data/training/ga_output.json           = champion rows (training-pool subset)     -> SAGA_WARMSTART_FROM=ga_output
    data/training/ga_output_combined.json  = champion rows + validation + test rows   -> TextClassifier(use_ga=True)

Previous versions are rotated to `ga_output_backup.json` / `ga_output_combined_backup.json` first.
Replaces the writer that lived in classification/DataCreator.py (deleted 13 Sep 2026).

Usage (repo root):
    .venv/bin/python deploy_champion.py                 # from saga_champion_rows.json
    .venv/bin/python deploy_champion.py --from-mask     # rebuild rows from saga_champion_mask.npy instead
"""
from __future__ import annotations

import json
import os
import shutil
import sys

from classification import Dataset as ds
from util import paths

CHAMP_ROWS = paths.data_path("training/saga_champion_rows.json")
CHAMP_MASK = paths.data_path("training/saga_champion_mask.npy")
GA_OUTPUT = paths.data_path("training/ga_output.json")
GA_OUTPUT_BACKUP = paths.data_path("training/ga_output_backup.json")
GA_COMBINED = paths.data_path("training/ga_output_combined.json")
GA_COMBINED_BACKUP = paths.data_path("training/ga_output_combined_backup.json")


def _rotate_backup(path: str, backup_path: str) -> None:
    """Snapshot the previous deployment so the next loop can still warm-start from it."""
    if os.path.exists(path):
        shutil.copy(path, backup_path)


def load_champion_rows(from_mask: bool) -> list:
    if from_mask:
        import numpy as np
        mask = np.load(CHAMP_MASK)
        pool = ds.load_split(ds.training_file_name)
        if mask.shape[0] != len(pool):
            raise SystemExit(f"mask length {mask.shape[0]} != current training pool {len(pool)}; "
                             "the split was rebuilt since the run — use the rows file instead")
        return [pool[i] for i in np.where(mask == 1)[0].tolist()]
    with open(CHAMP_ROWS) as f:
        return json.load(f)


def main() -> None:
    rows = load_champion_rows("--from-mask" in sys.argv)
    _rotate_backup(GA_OUTPUT, GA_OUTPUT_BACKUP)
    _rotate_backup(GA_COMBINED, GA_COMBINED_BACKUP)
    with open(GA_OUTPUT, "w") as f:
        json.dump(rows, f, indent=2)
    combined = rows + ds.load_split(ds.validation_file_name) + ds.load_split(ds.test_file_name)
    with open(GA_COMBINED, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"[deploy] ga_output.json={len(rows)} rows  ga_output_combined.json={len(combined)} rows "
          f"(prev versions -> *_backup.json)")


if __name__ == "__main__":
    main()
