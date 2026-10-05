"""The single, canonical train / validation / test split shared by every optimiser.

The SAGA driver (``run_saga.py``, built on the ``tribes_ga`` library) and every
evaluation script import their data from here, so they all see identical, *disjoint* splits. The
three sets are written to their own reusable files under ``data/training/splits/`` and
are pairwise-disjoint by description — no test/validation row ever appears in the
training pool (the leakage this module was created to eliminate).

Split protocol (fixed ``RANDOM_SEED``, balanced per class, group-aware + append-stable):
* filter rows to the 16 canonical ``EventCategory`` labels (drops junk like ``Ignore``),
* dedup by exact description/title,
* GROUP near-duplicates (same event scraped from multiple sources / recurring weekly
  events): rows with identical digit-masked signature OR char_wb(2,5) cosine >=
  ``NEAR_DUP_SIM`` are unioned into one group. Only rows with NO near-twin in the whole pool
  (singleton groups) are eligible for the held-out sets; every row that has a twin goes to
  the training pool. This kills the near-duplicate leak that exact-string dedup misses.
* carve ``TEST_FRACTION`` and ``VALIDATION_FRACTION`` of the smallest class per class from
  those singleton rows into balanced test/validation sets; the remainder is the training pool.
* APPEND-STABLE: assignments are persisted to ``assignment_manifest.json`` (signature ->
  split) and honoured on rebuild, so as the pool grows no held-out row ever migrates into
  training — the test set stays genuinely unseen across the continual retrain loop.

TF-IDF is fit on the training pool ONLY; validation/test are transformed with it. The
module builds the splits on first import (or when ``REGENERATE`` is set / files are
missing) and otherwise loads them.

Run ``python -m classification.Dataset --rebuild`` to force a rebuild.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from enum import StrEnum
from typing import Any, Dict, List, Optional

import numpy as np
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, set_random_seed, to_categorical
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import LabelEncoder, normalize
from sklearn.svm import LinearSVC
from tensorflow.config.experimental import enable_op_determinism
from tensorflow.keras.layers import Dense, Embedding, GlobalAveragePooling1D
from tensorflow.keras.models import Sequential

from classification import TextClassifier
from model.CategoryMapping import EventCategory
from util import paths

class ModelChoice(StrEnum):
    LR = "LR"    # TF-IDF + LogisticRegression
    NN = "NN"    # tokenizer + padded sequences + Keras


MODEL_CHOICE = ModelChoice.LR
# Rich surrogate features for the LR path: word (1,2)-grams + char_wb (2,5)-grams (sublinear, min_df=2)
# scored with a LinearSVC. On the clean split this lifts held-out accuracy from ~0.71 (word-2000 unigram +
# LogReg) to ~0.82 — i.e. the ~0.75 wall the GA plateaued at was the *representation*, not the data. The GA
# fitness surrogate uses fit_predict/X_pool, so this makes the GA curate the CNN's training data on a far
# stronger signal. Set False (or env RICH_FEATURES=0) to restore the legacy word-2000 unigram + LogReg
# surrogate — much faster, which the coevolution search (thousands of fitness calls) needs.
RICH_FEATURES = os.environ.get("RICH_FEATURES", "1") == "1"
RANDOM_SEED = 42
CV_SEED = 42
REGENERATE = False           # pass --rebuild to force a rebuild of the split files
N_FITNESS_FOLDS = 5          # stratified CV folds over the TRAINING pool (fitness)
TEST_FRACTION = 0.2          # per-class fraction (of the smallest class) held out for test
VALIDATION_FRACTION = 0.2    # per-class fraction held out for validation
# Near-duplicate leakage guard: rows whose char_wb(2,5) cosine >= this (or whose
# digit-masked signature is identical) are treated as the SAME event and forced into a
# single split so no near-twin ever straddles train/val/test. Only rows with NO near-twin
# anywhere in the pool are eligible for the held-out sets. See build_splits().
NEAR_DUP_SIM = 0.80

# The canonical training labels: every EventCategory except the OTHER catch-all. Rows
# whose label is not one of these (e.g. "Ignore") are dropped before splitting.
CANONICAL_LABELS = frozenset(c.value for c in EventCategory if c is not EventCategory.OTHER)

_splits_dir = paths.data_path("training/splits")
training_file_name = os.path.join(_splits_dir, "training.json")
validation_file_name = os.path.join(_splits_dir, "validation.json")
test_file_name = os.path.join(_splits_dir, "test.json")
balanced_seed_file_name = os.path.join(_splits_dir, "balanced_seed.json")
# Near-duplicate group id per training row (parallel to training.json order). Lets the GA
# build a redundancy-aware seed: keep one representative per group, dropping redundant twins.
training_groups_file_name = os.path.join(_splits_dir, "training_group_ids.json")
# Persisted signature -> split map. Makes the split append-stable across the continual
# retrain loop: a row already assigned to a split keeps that split when the pool grows, so
# the held-out set stays genuinely held out over time (no row migrates test -> train).
manifest_file_name = os.path.join(_splits_dir, "assignment_manifest.json")


def _load_labelled() -> List[Dict[str, Any]]:
    """Load generated_data.json, drop skipped/unlabelled rows and non-canonical labels,
    and dedup by description and by title (first comma-separated token)."""
    with open(paths.data_path("training/generated_data.json"), mode="r") as f:
        data = json.loads(f.read())

    kept: List[Dict[str, Any]] = []
    dropped: Dict[str, int] = {}
    seen: set = set()
    for d in data:
        if d.get("skip", False) or "label" not in d:
            continue
        label = d["label"]
        if label not in CANONICAL_LABELS:
            dropped[label] = dropped.get(label, 0) + 1
            continue
        description = d["description"]
        title = description.split(",")[0]
        if description in seen or title in seen:
            continue
        seen.add(description)
        seen.add(title)
        kept.append(d)

    if dropped:
        print(f"[dataset] dropped non-canonical labels: {dropped}")
    return kept


_RE_DIGIT = re.compile(r"\d+")
_RE_NONALNUM = re.compile(r"[^a-z0-9\s]+")
_RE_WS = re.compile(r"\s+")


def _signature(text: str) -> str:
    """Digit-masked, punctuation-stripped, whitespace-collapsed lowercase form. Recurring
    events that differ only by date collapse to the same signature."""
    t = _RE_DIGIT.sub("#", text.lower())
    t = _RE_NONALNUM.sub(" ", t)
    return _RE_WS.sub(" ", t).strip()


def _near_dup_groups(descs: List[str]) -> np.ndarray:
    """Union-find over the pool: rows are merged when their signatures match OR their
    char_wb(2,5) TF-IDF cosine >= NEAR_DUP_SIM. Returns a component id per row."""
    n = len(descs)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    # 1) identical digit-masked signatures (catches recurring events cheaply)
    first_by_sig: Dict[str, int] = {}
    for i, d in enumerate(descs):
        s = _signature(d)
        if s in first_by_sig:
            union(first_by_sig[s], i)
        else:
            first_by_sig[s] = i

    # 2) char_wb cosine >= NEAR_DUP_SIM (catches same event across sources / reworded copies)
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
    X = normalize(vec.fit_transform(descs))
    block = 512
    for b0 in range(0, n, block):
        b1 = min(b0 + block, n)
        sims = (X[b0:b1] @ X.T).tocsr()
        sims.data[sims.data < NEAR_DUP_SIM] = 0.0
        sims.eliminate_zeros()
        coo = sims.tocoo()
        for r, c in zip(coo.row.tolist(), coo.col.tolist()):
            i = b0 + r
            if c > i:  # upper triangle only; skips the self-match at c == i
                union(i, c)

    return np.array([find(i) for i in range(n)])


def build_splits() -> None:
    """Draw the balanced, group-aware, append-stable 3-way split and write the split files."""
    os.makedirs(_splits_dir, exist_ok=True)
    data = _load_labelled()
    comp = _near_dup_groups([d["description"] for d in data])
    group_size = Counter(comp.tolist())
    for d, c in zip(data, comp):
        d["_grp"] = int(c)
        d["_sig"] = _signature(d["description"])

    manifest: Dict[str, str] = {}
    if os.path.exists(manifest_file_name):
        with open(manifest_file_name, mode="r") as f:
            manifest = json.loads(f.read())

    random.seed(RANDOM_SEED)
    random.shuffle(data)

    by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in data:
        by_class[d["label"]].append(d)

    min_class = min(len(v) for v in by_class.values())
    test_n = int(min_class * TEST_FRACTION)
    val_n = int(min_class * VALIDATION_FRACTION)
    if test_n < 1 or val_n < 1:
        raise ValueError(f"smallest class has {min_class} rows; too few for a "
                         f"test/validation carve of {TEST_FRACTION}/{VALIDATION_FRACTION}")

    test: List[Dict[str, Any]] = []
    validation: List[Dict[str, Any]] = []
    training: List[Dict[str, Any]] = []
    short: Dict[str, int] = {}
    for label, rows in by_class.items():
        # Append-stability: rows whose signature was already assigned keep that split.
        forced_test = [d for d in rows if manifest.get(d["_sig"]) == "test"]
        forced_val = [d for d in rows if manifest.get(d["_sig"]) == "validation"]
        forced_ids = {id(d) for d in forced_test + forced_val}
        rest = [d for d in rows if id(d) not in forced_ids]
        # Only singletons (no near-twin anywhere in the pool) may enter the held-out sets;
        # any row that shares a near-duplicate group is routed to training.
        singles = [d for d in rest if group_size[d["_grp"]] == 1]
        grouped = [d for d in rest if group_size[d["_grp"]] > 1]

        need_t = max(0, test_n - len(forced_test))
        need_v = max(0, val_n - len(forced_val))
        take_t = singles[:need_t]
        take_v = singles[need_t:need_t + need_v]
        leftover = singles[need_t + need_v:]

        if len(take_t) < need_t or len(take_v) < need_v:
            short[label] = (need_t + need_v) - (len(take_t) + len(take_v))

        test.extend(forced_test + take_t)
        validation.extend(forced_val + take_v)
        training.extend(grouped + leftover)

    if short:
        print(f"[dataset] WARNING: too few singleton rows to fill held-out sets for: {short}")

    # Balanced seed: the smallest per-class count of training rows, as indices into training.
    min_train = min(sum(1 for d in training if d["label"] == c) for c in by_class)
    seed_indices: List[int] = []
    per_class_taken: Dict[str, int] = {}
    for i, d in enumerate(training):
        if per_class_taken.get(d["label"], 0) < min_train:
            seed_indices.append(i)
            per_class_taken[d["label"]] = per_class_taken.get(d["label"], 0) + 1

    # Refresh the append-stability manifest: held-out assignments are authoritative and
    # sticky; training rows only fill signatures not already claimed by a held-out row.
    for d in test:
        manifest[d["_sig"]] = "test"
    for d in validation:
        manifest[d["_sig"]] = "validation"
    for d in training:
        manifest.setdefault(d["_sig"], "training")

    def _clean(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{k: v for k, v in d.items() if k not in ("_grp", "_sig")} for d in rows]

    training_group_ids = [d["_grp"] for d in training]  # parallel to _clean(training) order
    for path, payload in ((training_file_name, _clean(training)),
                          (validation_file_name, _clean(validation)),
                          (test_file_name, _clean(test)), (balanced_seed_file_name, seed_indices),
                          (training_groups_file_name, training_group_ids),
                          (manifest_file_name, manifest)):
        with open(path, mode="w") as f:
            json.dump(payload, f, indent=2)

    multi = sum(1 for c in group_size.values() if c > 1)
    in_multi = sum(sz for sz in group_size.values() if sz > 1)
    print(f"[dataset] built splits — training={len(training)} validation={len(validation)} "
          f"test={len(test)} (test/val {test_n}/{val_n} per class over {len(by_class)} classes); "
          f"balanced seed={len(seed_indices)}")
    print(f"[dataset] near-dup groups: {multi} multi-row groups covering {in_multi} rows "
          f"(all routed to training); {len(group_size)} groups total over {len(data)} rows")


def load_split(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"split file '{path}' not found; run build_splits() first")
    with open(path, mode="r") as f:
        result: List[Dict[str, Any]] = json.loads(f.read())
    return result


if REGENERATE or not all(os.path.exists(p) for p in
                         (training_file_name, validation_file_name, test_file_name,
                          balanced_seed_file_name, training_groups_file_name)):
    build_splits()

_training = load_split(training_file_name)
_validation = load_split(validation_file_name)
_test = load_split(test_file_name)
with open(balanced_seed_file_name, mode="r") as _f:
    balanced_seed: List[int] = json.loads(_f.read())
with open(training_groups_file_name, mode="r") as _f:
    training_group_ids: List[int] = json.loads(_f.read())

_label_encoder = LabelEncoder()
_label_encoder.fit([d["label"] for d in _training])
num_classes = int(len(_label_encoder.classes_))
ALL_LABELS = list(range(num_classes))

_train_desc = [d["description"] for d in _training]
_val_desc = [d["description"] for d in _validation]
_test_desc = [d["description"] for d in _test]

if MODEL_CHOICE == ModelChoice.NN:
    _tokenizer = Tokenizer(num_words=TextClassifier.num_words, oov_token="<unk>")
    _tokenizer.fit_on_texts(_train_desc)

    def _pad(descs: List[str]) -> np.ndarray:
        seqs = _tokenizer.texts_to_sequences(descs)
        return np.array(pad_sequences(seqs, maxlen=TextClassifier.max_sequence_length, padding="post"))

    X_pool = _pad(_train_desc)
    X_val = _pad(_val_desc)
    X_test = _pad(_test_desc)
elif RICH_FEATURES:  # 'LR' path, rich features — word (1,2) + char_wb (2,5), fit on TRAINING pool ONLY
    _vec_word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2)
    _vec_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True, min_df=2)
    _Xw = _vec_word.fit_transform(_train_desc)
    _Xc = _vec_char.fit_transform(_train_desc)
    X_pool = hstack([_Xw, _Xc]).tocsr()
    X_val = hstack([_vec_word.transform(_val_desc), _vec_char.transform(_val_desc)]).tocsr()
    X_test = hstack([_vec_word.transform(_test_desc), _vec_char.transform(_test_desc)]).tocsr()
else:  # 'LR' legacy — word-2000 unigram TF-IDF fit on the training pool ONLY
    _vectorizer = TfidfVectorizer(max_features=TextClassifier.num_words)
    X_pool = _vectorizer.fit_transform(_train_desc)
    X_val = _vectorizer.transform(_val_desc)
    X_test = _vectorizer.transform(_test_desc)

pool_labels = _label_encoder.transform([d["label"] for d in _training])
val_labels = _label_encoder.transform([d["label"] for d in _validation])
test_labels = _label_encoder.transform([d["label"] for d in _test])

# Fixed stratified folds of the TRAINING pool. A subset's fitness trains on the subset's
# samples outside a fold and validates on the whole fold.
POOL_FOLDS = list(StratifiedKFold(n_splits=N_FITNESS_FOLDS, shuffle=True, random_state=CV_SEED)
                  .split(np.zeros(len(pool_labels)), pool_labels))


def fit_predict(train_idx: np.ndarray, eval_idx: np.ndarray) -> Optional[np.ndarray]:
    """Train on the given training-pool samples and predict `eval_idx` (also pool
    indices). Returns None if fewer than 2 classes are present to train on."""
    labels_1d = pool_labels[train_idx]
    if len(np.unique(labels_1d)) < 2:
        return None

    if MODEL_CHOICE == ModelChoice.NN:
        set_random_seed(CV_SEED)
        enable_op_determinism()
        model = Sequential()
        model.add(Embedding(input_dim=TextClassifier.num_words, output_dim=TextClassifier.embedding_dim,
                            input_length=TextClassifier.max_sequence_length))
        model.add(GlobalAveragePooling1D())
        model.add(Dense(units=num_classes, activation="softmax"))
        model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
        model.fit(X_pool[train_idx], to_categorical(labels_1d, num_classes=num_classes),
                  epochs=20, batch_size=32, verbose=0)
        return np.argmax(model.predict(X_pool[eval_idx], verbose=0), axis=1)

    # class_weight="balanced" makes the surrogate reweight the loss by inverse class
    # frequency, so the GA no longer has to achieve balance by DELETING majority rows (which
    # starves the model — the minority floor is ~100). The subset can stay large and merely
    # redundancy-trimmed; the model handles the 3k-vs-100 skew via weights.
    if RICH_FEATURES:
        model = LinearSVC(C=1.0, random_state=CV_SEED, class_weight="balanced")
    else:
        model = LogisticRegression(solver="liblinear", random_state=CV_SEED, max_iter=100,
                                   multi_class="ovr", class_weight="balanced")
    model.fit(X_pool[train_idx], labels_1d)
    return model.predict(X_pool[eval_idx])


def _report() -> None:
    print(f"[dataset] pool={X_pool.shape[0]} val={X_val.shape[0]} test={X_test.shape[0]} "
          f"classes={num_classes} balanced_seed={len(balanced_seed)}")


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        build_splits()
    _report()
