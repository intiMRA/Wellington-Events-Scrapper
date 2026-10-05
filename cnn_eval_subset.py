"""CNN-check a curated subset on the clean holdout: num_words=20000 + class-weighted loss
(per-sample inverse-freq), trained once per seed on the subset and evaluated on val/test.

Reports BOTH a single-model per-seed mean (what production ships — judge subsets on this) and a
probability-averaged ensemble over the seeds (kept because ensembling is a real lever, but it
overstates the single model by ~4 points and has reversed rankings).

    .venv/bin/python cnn_eval_subset.py <subset.json>

Does NOT overwrite the deployed model."""
import os, sys, json
os.environ["RICH_FEATURES"] = "0"
import numpy as np
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical, set_random_seed
from keras.callbacks import EarlyStopping
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import balanced_accuracy_score
from tensorflow.config.experimental import enable_op_determinism
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense
from classification import Dataset as ds
from util import paths

NW, MAXLEN, EMB, NC = 20000, 1500, 400, ds.num_classes
# CNN_EVAL_SEEDS: comma list, default = the 3 seeds used for every result up to 14 Sep. CNN_EVAL_OUT_SUFFIX: appended to
# the output file name so a 5-seed run never overwrites a 3-seed result (e.g. "_5seed").
SEEDS = [int(s) for s in os.environ.get("CNN_EVAL_SEEDS", "13453379,42,7").split(",")]
OUT_SUFFIX = os.environ.get("CNN_EVAL_OUT_SUFFIX", "")
if len(sys.argv) < 2:
    sys.exit("usage: cnn_eval_subset.py <subset.json>   (e.g. data/training/ga_output.json, "
             "data/training/splits/training.json for the full pool)")
subset_path = sys.argv[1]
rows = json.load(open(subset_path))

# LEAK GUARD (19 Sep). A subset file written BEFORE a split rebuild can contain rows the rebuild has since moved
# into val/test — the file is a frozen row list, not a view over the pool, so it does not follow the split.
# This really happened: `ga_output_backup.json` (the 13 Sep curation, written pre-rebuild) held 12 of the current
# 592 TEST rows and 10 VAL rows, and its 17 Sep score of 0.7591 was inflated by roughly 5 test rows — enough to
# make it look like the best subset on record and to trigger a recovery effort built on a number that was not
# real. Training on holdout rows makes every number from this script invalid, silently and in the favourable
# direction, so this aborts rather than warns. Escape hatch for a deliberate diagnostic: CNN_EVAL_ALLOW_LEAK=1.
# The fix for a stale file is to re-filter it against the current pool, not to set the override.
_te = {(d, ds._label_encoder.classes_[i]) for d, i in zip(ds._test_desc, ds.test_labels)}
_va = {(d, ds._label_encoder.classes_[i]) for d, i in zip(ds._val_desc, ds.val_labels)}
_sub = {(r["description"], r["label"]) for r in rows}
_n_te, _n_va = len(_sub & _te), len(_sub & _va)
if _n_te or _n_va:
    msg = (f"[cnn-eval] LEAK: subset {os.path.basename(subset_path)} contains {_n_te} of {len(_te)} TEST rows and "
           f"{_n_va} of {len(_va)} VAL rows. Any score from it would be inflated and not comparable to clean runs. "
           f"Re-filter the file against data/training/splits/training.json, or set CNN_EVAL_ALLOW_LEAK=1 to "
           f"measure it anyway (and label the result as contaminated).")
    if os.environ.get("CNN_EVAL_ALLOW_LEAK") != "1":
        sys.exit(msg)
    print(msg.replace("LEAK:", "LEAK (ALLOWED, RESULT IS CONTAMINATED):"), flush=True)

sub_x = [r["description"] for r in rows]
ytr = ds._label_encoder.transform([r["label"] for r in rows])
print(f"[cnn-eval] subset={subset_path.split('/')[-1]} rows={len(sub_x)} classes={len(set(ytr.tolist()))} "
      f"holdout_leak=(test {_n_te}, val {_n_va})", flush=True)

tok = Tokenizer(num_words=NW, oov_token="<unk>"); tok.fit_on_texts(sub_x)
pad = lambda xs: np.array(pad_sequences(tok.texts_to_sequences(xs), maxlen=MAXLEN, padding="post"))
Xtr, Xva, Xte = pad(sub_x), pad(ds._val_desc), pad(ds._test_desc)
Ytr, Yva = to_categorical(ytr, NC), to_categorical(ds.val_labels, NC)
sw = compute_class_weight("balanced", classes=np.arange(NC), y=ytr)[ytr].astype("float32")

def build():
    m = Sequential([Embedding(NW, EMB, input_length=MAXLEN), Conv1D(512, 3, activation='relu'),
                    GlobalMaxPooling1D(), Dense(64, activation='relu'), Dense(NC, activation='softmax')])
    m.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return m

from sklearn.metrics import recall_score

def _recalls(pred):
    return recall_score(ds.test_labels, pred, labels=np.arange(NC), average=None, zero_division=0)

Pv = np.zeros((len(ds.val_labels), NC)); Pt = np.zeros((len(ds.test_labels), NC))
per_seed_test, per_seed_recalls = [], []
for s in SEEDS:
    set_random_seed(s); enable_op_determinism()
    m = build()
    es = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, min_delta=0.0001)
    m.fit(Xtr, Ytr, epochs=100, batch_size=32, validation_data=(Xva, Yva), callbacks=[es], sample_weight=sw, verbose=0)
    pv, pt = m.predict(Xva, verbose=0), m.predict(Xte, verbose=0)
    Pv += pv; Pt += pt
    per_seed_test.append(float((pt.argmax(1) == ds.test_labels).mean()))
    # Per-SEED per-class recall, not just the ensemble's. Without this every per-class claim is
    # ensemble-derived and so has a single measurement per subset — it cannot carry a paired t, which
    # is exactly the test used to decide whether a per-class difference is real.
    per_seed_recalls.append(_recalls(pt.argmax(1)))
    print(f"[cnn-eval] seed={s} test={per_seed_test[-1]:.4f} min-class={per_seed_recalls[-1].min():.3f}", flush=True)
Pv /= len(SEEDS); Pt /= len(SEEDS)
vacc = float((Pv.argmax(1) == ds.val_labels).mean()); tacc = float((Pt.argmax(1) == ds.test_labels).mean())
pred_t = Pt.argmax(1)
per_class = {str(c): round(float(r), 4) for c, r in zip(ds._label_encoder.classes_, _recalls(pred_t))}
_R = np.array(per_seed_recalls)
single_per_class = {str(c): {"per_seed": [round(float(v), 4) for v in _R[:, i]],
                             "mean": round(float(_R[:, i].mean()), 4), "std": round(float(_R[:, i].std()), 4)}
                    for i, c in enumerate(ds._label_encoder.classes_)}
tag = os.path.splitext(os.path.basename(subset_path))[0]
n = len(SEEDS)
res = {"subset": os.path.basename(subset_path), "rows": len(sub_x), "seeds": SEEDS, "n_seeds": n,
       # Recorded on every result so a contaminated number can never be mistaken for a clean one later.
       # (0, 0) is the only value a comparable result may have; anything else means CNN_EVAL_ALLOW_LEAK was set.
       "holdout_leak": {"test_rows": _n_te, "val_rows": _n_va},
       "per_seed_test_acc": per_seed_test,
       "per_seed_test_mean": float(np.mean(per_seed_test)), "per_seed_test_std": float(np.std(per_seed_test)),
       # Single-model per-class recall, one value per seed — the per-class figures that may be compared
       # across subsets with a paired t. The ensemble's per_class_recall below is ONE measurement.
       "per_seed_test_per_class_recall": single_per_class,
       "per_seed_test_min_class_recall_mean": round(float(_R.min(axis=1).mean()), 4),
       f"cnn_{n}seed": {
        "val_acc": vacc, "test_acc": tacc,
        "test_balanced": float(balanced_accuracy_score(ds.test_labels, pred_t)),
        "test_min_class_recall": min(per_class.values()), "test_per_class_recall": per_class}}
out = paths.data_path(f"training/cnn_eval_{tag}{OUT_SUFFIX}.json")
json.dump(res, open(out, "w"), indent=2)
print(f"[cnn-eval] {n}-seed prob-avg  val={vacc:.4f}  TEST={tacc:.4f}  balanced={res[f'cnn_{n}seed']['test_balanced']:.4f}  "
      f"min-class-recall={res[f'cnn_{n}seed']['test_min_class_recall']:.3f}  | SINGLE-MODEL TEST mean={res['per_seed_test_mean']:.4f} "
      f"±{res['per_seed_test_std']:.4f} min-class={res['per_seed_test_min_class_recall_mean']:.3f}  -> {out}", flush=True)
print("[cnn-eval] judge subsets on the SINGLE-MODEL mean; the prob-avg column is an ensemble production "
      "does not ship.", flush=True)
print("CNN EVAL DONE", flush=True)
