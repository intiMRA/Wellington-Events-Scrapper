"""Head-to-head: train the production CNN (classification.TextClassifier, unchanged code path) on two
curations and score each on generated_data.json exactly as `python -m classification.TextClassifier` does.

    prev = data/training/ga_output_combined.json        (currently deployed curation)
    saga = saga_champion_rows.json + validation + test  (what deploy_champion.py would write)

*** NOT the yardstick for choosing a subset — use cnn_eval_subset.py / run_cnn_eval.sh for that. ***
Roughly 60% of generated_data.json is each model's own training data, so the agreement rate this prints
is mostly memorisation and it is single-seed besides. What this script is actually good for is the one
thing the eval harness cannot do: it trains through the DEPLOYED code path, so it shows what production
would produce rather than what the harness measures. The two differ (vocabulary size and class
weighting), which is exactly why that is worth being able to see.

Models are saved under models/compare/<name>/ so the deployed models/trained_model is NOT touched.
Per-run prediction logs are copied to data/logs/predictions_log_<name>.txt.
Run from repo root:  .venv/bin/python -u compare_curations.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time

from classification import Dataset as ds
from classification import TextClassifier as TC
from util import paths

REPO = os.path.dirname(os.path.abspath(__file__))
PREV = paths.data_path("training/ga_output_combined.json")
CHAMP_ROWS = paths.data_path("training/saga_champion_rows.json")
SAGA_COMBINED = paths.data_path("training/compare_saga_combined.json")   # scratch input, same shape as prev
GENERATED = paths.data_path("training/generated_data.json")
LOG = paths.data_path("logs/predictions_log.txt")
OUT = paths.data_path("training/compare_curations_results.json")
MODEL_ROOT = os.path.join(REPO, "models", "compare")

_orig_model_path = paths.model_path


def _use_model_dir(name: str) -> None:
    d = os.path.join(MODEL_ROOT, name)
    os.makedirs(d, exist_ok=True)
    paths.model_path = lambda n, _d=d: os.path.join(_d, n)   # TC calls paths.model_path at call time


def build_saga_combined() -> int:
    rows = json.load(open(CHAMP_ROWS))
    combined = rows + ds.load_split(ds.validation_file_name) + ds.load_split(ds.test_file_name)
    json.dump(combined, open(SAGA_COMBINED, "w"), indent=2)
    return len(combined)


def train_on(file_name: str) -> float:
    """Same as TC.train_from_manual_training_files() but with the input file parameterised."""
    from keras.preprocessing.text import Tokenizer
    from keras.utils import set_random_seed
    from tensorflow.config.experimental import enable_op_determinism
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    data = json.load(open(file_name))
    all_texts = [it["description"] for it in data if not it["skip"]]
    tokenizer = Tokenizer(num_words=TC.num_words, oov_token="<unk>")
    tokenizer.fit_on_texts(all_texts)
    label_encoder = LabelEncoder()
    set_random_seed(13453379)
    enable_op_determinism()
    X_train, X_test, Y_train, Y_test, num_classes = TC.get_data(file_name, label_encoder, tokenizer)
    X_train, X_val, Y_train, Y_val = train_test_split(X_train, Y_train, test_size=0.2, random_state=42)
    return float(TC.train(num_classes, X_train, Y_train, X_val, Y_val, X_test, Y_test,
                          label_encoder, tokenizer, verbose=2))


def parse_log() -> dict:
    txt = open(LOG).read()
    m = re.search(r"correct: (\d+) of (\d+) ([\d.]+)%", txt)
    per_class = {}
    for blk in txt.split("-" * 100):
        g = re.search(r"given Label: (.*?)\nprediction correct: (True|False)", blk, re.S)
        if g:
            c = per_class.setdefault(g.group(1).strip(), {"count": 0, "correct": 0})
            c["count"] += 1; c["correct"] += g.group(2) == "True"
    return {"correct": int(m.group(1)), "total": int(m.group(2)), "acc": float(m.group(3)) / 100,
            "per_class": {k: round(v["correct"] / v["count"], 4) for k, v in sorted(per_class.items())}}


def main() -> None:
    n_saga = build_saga_combined()
    n_prev = len(json.load(open(PREV)))
    print(f"[compare] prev={PREV} ({n_prev} rows)  saga={SAGA_COMBINED} ({n_saga} rows)", flush=True)
    results = {}
    for name, fn in (("prev", PREV), ("saga", SAGA_COMBINED)):
        t0 = time.time()
        _use_model_dir(name)
        holdout_acc = train_on(fn)
        print(f"[compare] {name}: trained in {(time.time()-t0)/60:.1f}m, internal 20% holdout acc={holdout_acc:.4f}",
              flush=True)
        TC.predict_from_file(GENERATED, False)
        shutil.copy(LOG, paths.data_path(f"logs/predictions_log_{name}.txt"))
        r = parse_log(); r["train_rows"] = n_prev if name == "prev" else n_saga; r["holdout_acc"] = holdout_acc
        results[name] = r
        print(f"[compare] {name}: generated_data acc={r['acc']:.4f} ({r['correct']}/{r['total']})", flush=True)
        json.dump(results, open(OUT, "w"), indent=2)
    paths.model_path = _orig_model_path
    print("[compare] per-class (prev -> saga):")
    for c in sorted(results["saga"]["per_class"]):
        p, s = results["prev"]["per_class"].get(c), results["saga"]["per_class"][c]
        print(f"  {c:28} {p:.3f} -> {s:.3f}  ({(s - (p or 0))*100:+.1f})")
    print(f"[compare] wrote {OUT}\nCOMPARE DONE", flush=True)


if __name__ == "__main__":
    main()
