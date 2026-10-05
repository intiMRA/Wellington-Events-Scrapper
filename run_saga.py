"""Surrogate-assisted GA (SAGA) — DIPLOID COEVOLUTION + CNN-elite archive + WARM-START from prev curation.

A fast class-weighted linear surrogate ranks candidates inside each generation; a 10-epoch steering CNN
(fixed (mask,seed,epochs) cache) scores the stitched champion and two alternates; an archive keeps the best
CNN-scored subsets. On top of that sits the continual-loop piece: inject the previous best curation
(`ga_output.json`, the last DEPLOYED subset) into the search so the run can only IMPROVE on it. Two injection
points, both cheap and complementary:
  * PREV-CURATION ANCHORS: CNN-evaluate each prior subset (deployed + backup) up front so they live in the archive,
    define the CNN-side recall floor, and are forced finalists — the run can only replace the deployed subset by
    beating it. (14 Sep: the full pool is no longer tracked as an anchor/reference; it is only the tribes' gen-0
    base genome and the fallback floor for a first run with nothing deployed.)
  * POPULATION SEED: each tribe's gen-0 population gets the prior curation's per-class slice as one individual
    (next to the full-pool clone + perturbations). Elitism then guarantees the run ends >= max(full_pool,
    prev_curation); crossover/mutation can refine it. The no-regression FLOOR is still measured against the FULL
    pool seed, so the design's safety net is intact (this is why we ADD a seed individual rather than swap the
    base_mask to the subset).
Also persists the champion (mask .npy + deployable rows json) so this run is materialisable AND the NEXT loop can
warm-start from it. Honest: surrogate & CNN fit on TRAIN subset, selected on VAL, TEST touched once.

Launch with RICH_FEATURES=0 and PYTHONPATH=<repo>. Env: SAGA_VOCAB/POP/GEN/TOPK/FOLDS/CNN_EPOCHS/FINAL_EPOCHS/
FINAL_SEEDS/SEED/ANCHOR_SEEDS/OUT, plus SAGA_WARMSTART_FROM (comma list, default "ga_output,ga_output_backup" = the deployed
curation AND the one before it; "none" disables warm-start), SAGA_SEED_ONLY_FROM (comma list, default empty: subsets that
seed the gen-0 populations but are NOT anchors and NOT forced finalists, so they cannot raise the CNN floor) and SAGA_DEPLOY (default 1: at the end run
deploy_champion.py, rotating ga_output*.json -> *_backup.json and writing the champion into ga_output*.json).
Prior curations are always finalists, so the deployed subset is only replaced if the 3-seed re-check beats it.
"""
from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.metrics import accuracy_score

from classification import Dataset as ds
from tribes_ga import engine, fitness, genome, stitch, warmstart
from tribes_ga.config import TribesConfig
from util import paths

PREFIX = os.environ.get("SAGA_PREFIX", "saga")   # artifact name prefix (use e.g. saga_smoke for test runs)
OUT = os.environ.get("SAGA_OUT", paths.data_path(f"training/{PREFIX}_results.json"))
CHAMP_MASK_OUT = paths.data_path(f"training/{PREFIX}_champion_mask.npy")
CHAMP_ROWS_OUT = paths.data_path(f"training/{PREFIX}_champion_rows.json")
CKPT_OUT = paths.data_path(f"training/{PREFIX}_archive_ckpt.npz")   # per-gen top-10 masks

VOCAB        = int(os.environ.get("SAGA_VOCAB", "20000"))
POP          = int(os.environ.get("SAGA_POP", "40"))
GEN          = int(os.environ.get("SAGA_GEN", "30"))
TOPK         = int(os.environ.get("SAGA_TOPK", "3"))
FOLDS        = int(os.environ.get("SAGA_FOLDS", "3"))
CNN_EPOCHS   = int(os.environ.get("SAGA_CNN_EPOCHS", "10"))   # in-loop = steering signal only
FINAL_EPOCHS = int(os.environ.get("SAGA_FINAL_EPOCHS", "100"))
FINAL_SEEDS  = [int(s) for s in os.environ.get("SAGA_FINAL_SEEDS", "42,7,123").split(",")]
FINAL_TOPN   = int(os.environ.get("SAGA_FINAL_TOPN", "4"))    # leaves room for the forced prev_curation finalists
SEED         = int(os.environ.get("SAGA_SEED", "42"))
ANCHOR_SEEDS = [int(s) for s in os.environ.get("SAGA_ANCHOR_SEEDS", "42,7,123").split(",")]
# Comma-separated list of data/training/<name>.json subsets to inject (14 Sep: BOTH the deployed curation and
# the previous one, which deploy_champion.py rotates into *_backup). "none" disables warm-start.
WARMSTART_FROM = os.environ.get("SAGA_WARMSTART_FROM", "ga_output,ga_output_backup")
WARMSTART_SOURCES = [w.strip() for w in WARMSTART_FROM.split(",") if w.strip() and w.strip() != "none"]
# 19 Sep: SEED-ONLY sources. A SAGA_WARMSTART_FROM entry is three things at once — (a) an individual injected into
# every tribe's gen-0 population, (b) a CNN ANCHOR, and (c) a forced finalist. (b) is not free: the CNN floor is the
# ELEMENTWISE MAX of the anchors' per-class recall, so every extra anchor can only RAISE the floor, never lower it —
# which would undo the 17 Sep seed-averaging fix that was loosening it. Sources listed here get (a) ONLY: they seed
# the search and can win on their merits, but they do not define the floor and are not forced into the final.
# Use for exploratory seeds we want the search to explore FROM, not subsets we are protecting against regression.
SEED_ONLY_FROM = os.environ.get("SAGA_SEED_ONLY_FROM", "")
SEED_ONLY_SOURCES = [w.strip() for w in SEED_ONLY_FROM.split(",") if w.strip() and w.strip() != "none"]
DEPLOY = os.environ.get("SAGA_DEPLOY", "1") == "1"   # run deploy_champion at the end (prev -> *_backup, champ -> main)
# CNN-side no-regression gate (14 Sep): archive/steering/final scores are BALANCED val accuracy minus a penalty
# for every class whose CNN val recall falls more than FLOOR_TOL below the best recall any prior curation
# achieved on it (elementwise max over prev_* anchors; full pool if there are none). 0.03 ≈ one val example.
CNN_FLOOR_TOL = float(os.environ.get("SAGA_CNN_FLOOR_TOL", "0.03"))
CNN_FLOOR_PEN = float(os.environ.get("SAGA_CNN_FLOOR_PEN", "2.0"))
# 17 Sep: the anchors define the floor, so a single noisy run makes the floor unbeatable. Evidence: on 14 Sep the
# floor was built from one 10-epoch run per anchor, and the DEPLOYED subset then scored -0.53 against it at the
# 3-seed re-check — i.e. the floor encoded seed noise, not data quality, and the run ended in a 16h no-op. Anchors
# are now averaged over these seeds (per-class recalls averaged, then the elementwise max across anchors is taken
# as before). Candidates are still scored single-seed IN-LOOP: 3x-ing every generation would turn a 16h run into
# ~48h, and finalists get a multi-seed re-check.
#
# 5 Oct: the finalists' multi-seed re-check was averaging in the WRONG PLACE, and it cost us the best subset of
# the 3-4 Oct cycle. It computed mean_s[ shaped(r_s) ] — penalty applied per seed, then averaged — instead of
# shaped over the seed-averaged recall vector. The penalty contains max(0, .), which is CONVEX, so by Jensen
# E[max(0, X)] >= max(0, E[X]): a class sitting near the floor is charged on every seed that dips below it and
# gets NO credit on the seeds above it. The penalty is one-sided, so the estimator is biased against any subset
# whose per-class recall is merely NOISY, independently of whether its mean recall is actually worse. Concrete
# damage: `g1_champ` lost the 4 Oct final to the backup on a 3-seed val min-recall gap of 0.509 vs 0.518, and on
# the 5-seed TEST that ordering inverted (g1_champ min class 0.579, backup 0.526) with g1_champ the best arm
# measured on every axis. FIX: average the per-class recalls across FINAL_SEEDS first, then apply shaped() once
# — exactly the treatment the anchors have had since 17 Sep. Costs nothing: the same trainings, scored once.
# Rejected: widening TOL (weakens the gate everywhere instead of making the estimator unbiased); rejected:
# dropping the penalty (it is the no-regression guarantee); rejected: seed-averaging the IN-LOOP steering score
# too (that is the 3x cost the 17 Sep note rules out, and it is a separate defect — see the notes).

if ds.RICH_FEATURES:
    print("[saga] WARNING: RICH_FEATURES is ON — coev surrogate will be slow. Launch with RICH_FEATURES=0.", flush=True)

y_tr, y_va, y_te = ds.pool_labels, ds.val_labels, ds.test_labels
POOL_N = warmstart.pool_size()
NC = len(ds._label_encoder.classes_)

# ---- CNN token sequences (tokenizer fit on TRAIN only), padded once; subsets index in ----
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical, set_random_seed
from tensorflow.keras import backend as K
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense
from tensorflow.keras.callbacks import EarlyStopping
from classification import TextClassifier as TC
from sklearn.utils.class_weight import compute_class_weight

TC.num_words = VOCAB
MAXLEN, EDIM = TC.max_sequence_length, TC.embedding_dim
_tok = Tokenizer(num_words=VOCAB, oov_token="<unk>"); _tok.fit_on_texts(list(ds._train_desc))
def _pad(d): return np.array(pad_sequences(_tok.texts_to_sequences(d), maxlen=MAXLEN, padding="post"))
S_tr, S_va, S_te = _pad(list(ds._train_desc)), _pad(list(ds._val_desc)), _pad(list(ds._test_desc))
Y_va1 = to_categorical(y_va, NC)
_cnn_cache: Dict[Tuple[bytes, int, int], Dict] = {}   # key = (mask, seed, epochs)
_cnn_floor: Optional[np.ndarray] = None                 # per-class CNN val recall floor (set after anchors)
from sklearn.metrics import recall_score


def shaped(r: Dict) -> float:
    """Gated CNN score: balanced val acc − PEN·Σ_c max(0, floor_c − TOL − recall_c). Plain balanced acc
    until the floor is set (i.e. while scoring the anchors themselves)."""
    if _cnn_floor is None:
        return r["bal"]
    deficit = float(np.maximum(0.0, (_cnn_floor - CNN_FLOOR_TOL) - r["recalls"]).sum())
    return r["bal"] - CNN_FLOOR_PEN * deficit


def _cnn(sel, epochs, seed=SEED, want_test=False) -> Dict:
    """Train the steering/final CNN on `sel`; returns {"acc","bal","recalls","min_recall"[, "test"]}."""
    key = (sel.tobytes(), seed, epochs)
    if not want_test and key in _cnn_cache:
        return _cnn_cache[key]
    set_random_seed(seed); K.clear_session()
    m = Sequential([
        Embedding(input_dim=VOCAB, output_dim=EDIM, input_length=MAXLEN),
        Conv1D(filters=512, kernel_size=3, activation="relu"),
        GlobalMaxPooling1D(),
        Dense(units=64, activation="relu"),
        Dense(units=NC, activation="softmax"),
    ])
    m.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
    es = EarlyStopping(monitor="val_loss", patience=3, mode="min", restore_best_weights=True, min_delta=1e-4)
    ysel = y_tr[sel]
    present = np.unique(ysel)
    _w = compute_class_weight("balanced", classes=present, y=ysel)
    _wmap = {int(c): float(wi) for c, wi in zip(present, _w)}
    sw = np.array([_wmap[int(c)] for c in ysel], dtype="float32")
    m.fit(S_tr[sel], to_categorical(ysel, NC), validation_data=(S_va, Y_va1),
          epochs=epochs, batch_size=32, callbacks=[es], sample_weight=sw, verbose=0)
    pv = m.predict(S_va, verbose=0).argmax(1)
    recalls = recall_score(y_va, pv, labels=np.arange(NC), average=None, zero_division=0)
    r = {"acc": float(accuracy_score(y_va, pv)), "bal": float(recalls.mean()),
         "recalls": recalls, "min_recall": float(recalls.min())}
    if want_test:
        pt = m.predict(S_te, verbose=0).argmax(1)
        r["test"] = float(accuracy_score(y_te, pt))
        r["test_bal"] = float(recall_score(y_te, pt, labels=np.arange(NC), average=None, zero_division=0).mean())
    K.clear_session(); del m
    _cnn_cache[key] = {k: v for k, v in r.items() if k not in ("test", "test_bal")}
    return r


def build_prev_masks(sources: Optional[List[str]] = None,
                     seen: Optional[set] = None) -> List[Tuple[str, np.ndarray, int]]:
    """Map each subset named in `sources` (default: WARMSTART_SOURCES) onto the current pool by (description,label).
    Returns [(name, mask over POOL_N, n_hits)] for sources that exist and map at least one row; a source that is a
    duplicate of an earlier one (identical mask) is dropped so we don't inject the same individual twice.
    `seen` lets a second call (the seed-only sources) dedup against the masks the first call already produced."""
    sources = WARMSTART_SOURCES if sources is None else sources
    idx: Dict[Tuple[str, str], int] = {}
    for i, d in enumerate(ds._training):
        idx[(d["description"], d["label"])] = i
    out: List[Tuple[str, np.ndarray, int]] = []
    seen = set() if seen is None else seen
    for name in sources:
        path = paths.data_path(f"training/{name}.json")
        if not os.path.exists(path):
            print(f"[saga] warm-start: {name}.json not found, skipping", flush=True); continue
        m = np.zeros(POOL_N, np.int8); hit = 0
        for r in json.load(open(path)):
            k = (r.get("description"), r.get("label"))
            if k in idx:
                m[idx[k]] = 1; hit += 1
        if hit == 0 or m.tobytes() in seen:
            print(f"[saga] warm-start: {name}.json mapped {hit} rows / duplicate of earlier source, skipping", flush=True)
            continue
        seen.add(m.tobytes()); out.append((name, m, hit))
    return out


def main():
    t0 = time.time()
    print(f"[saga] DIPLOID-COEV (warm-start={WARMSTART_FROM}) | VOCAB={VOCAB} pop={POP} gen={GEN} topk={TOPK} "
          f"folds={FOLDS} rich={ds.RICH_FEATURES} cnn_epochs={CNN_EPOCHS} final_epochs={FINAL_EPOCHS} "
          f"pool={POOL_N} nc={NC}", flush=True)
    rng = np.random.default_rng(SEED)
    cfg = TribesConfig(diploid=True, pop_per_tribe=POP, n_folds=FOLDS, elitism=2,
                       crossover_prob=0.7, tournament_k=3, mut_genes_min=5, mut_genes_max=400)
    fitness.set_folds(cfg.n_folds)
    seed = warmstart.seed_mask()                 # full pool (all ones) — the tribes' gen-0 base
    seed_sel = np.where(seed == 1)[0]
    class_idx = warmstart.all_class_indices()
    full_sel = np.arange(POOL_N)

    _seen: set = set()
    prevs = build_prev_masks(seen=_seen)
    # Seed-only sources: injected into the populations, but NOT anchors and NOT forced finalists (see
    # SEED_ONLY_FROM above). Deduped against `prevs` via the shared `_seen`, so naming the same subset in both
    # lists injects it once, as an anchor.
    seed_only = build_prev_masks(SEED_ONLY_SOURCES, seen=_seen) if SEED_ONLY_SOURCES else []
    prev_hit = sum(h for _, _, h in prevs)
    for name, m, hit in seed_only:
        print(f"[saga] seed-only: mapped {hit} rows from {name}.json into pool ({100*hit/POOL_N:.1f}% of {POOL_N}) "
              f"— seeds the search, NOT an anchor and NOT a forced finalist", flush=True)
    for name, m, hit in prevs:
        print(f"[saga] warm-start: mapped {hit} rows from {name}.json into pool ({100*hit/POOL_N:.1f}% of {POOL_N})",
              flush=True)
    # SURROGATE FLOOR (14 Sep): gated to the PREVIOUS BEST, not just all-data — per-class recall floor = elementwise
    # max over {full pool} ∪ {each prior curation}. A class may not drop below what any prior achieved (−tolerance).
    # (14 Sep, user) the full pool is no longer tracked: floor = prior curations only; full pool is the fallback
    # for a first run with nothing deployed yet.
    floor_sets = [np.where(pm == 1)[0] for _, pm, _ in prevs] or [seed_sel]
    fitness.set_baseline_multi(floor_sets)
    print(f"[saga] surrogate floor = max({', '.join(n for n, _, _ in prevs) or 'full_pool (no prior curation)'}); "
          f"min class recall floor={fitness.baseline_min_recall():.3f} tol={cfg.floor_tolerance}", flush=True)

    bests = [genome.from_mask(seed[class_idx[c]], True) for c in range(NC)]

    def make_eval(c):
        def _e(cand):
            full = stitch.stitch_with(cand, c, bests, class_idx, POOL_N)
            return fitness.cv_fitness(np.where(full == 1)[0], cfg.floor_tolerance,
                                      cfg.reward_weight, cfg.penalty_weight)
        return _e

    for c in range(NC):
        bests[c].fitness = make_eval(c)(bests[c])
    tribe_pops = [engine.make_population(len(class_idx[c]), POP, seed[class_idx[c]], cfg, rng, make_eval(c))
                  for c in range(NC)]

    # WARM-START SEED: drop EACH prior curation's per-class slice into each tribe's gen-0 population
    # (replace the last perturbations, keep the full-pool clone at index 0). Guarantees the prior bests are
    # in the search from the start; elitism keeps them if they aren't beaten.
    # Seed-only sources are injected here too — this is the ONLY place they are used.
    for j, (name, pm, _) in enumerate(prevs + seed_only):
        for c in range(NC):
            ind = genome.from_mask(pm[class_idx[c]], cfg.diploid)
            ind.fitness = make_eval(c)(ind)
            tribe_pops[c][-(1 + j)] = ind

    # Anchors = the prior curations only (14 Sep, user: stop tracking the full pool). Fallback for a first run
    # with nothing deployed: the full pool itself, so a floor and a forced finalist still exist.
    archive: List[Dict] = []
    anchors = [(f"prev_{name}", np.where(pm == 1)[0], pm.copy()) for name, pm, _ in prevs]
    if not anchors:
        anchors = [("prev_full_pool", full_sel, np.ones(POOL_N, np.int8))]
    def _rec(tag, gen, r, sel, msk):
        return {"tag": tag, "gen": gen, "val": r["acc"], "bal": r["bal"], "min_recall": r["min_recall"],
                "recalls": r["recalls"], "score": shaped(r), "size": int(sel.shape[0]), "mask": msk.copy()}

    global _cnn_floor
    for nm, sel, msk in anchors:
        # Seed-average the anchor: per-class recalls are averaged across ANCHOR_SEEDS, so the floor is an estimate
        # of what the prior curation actually achieves rather than its luckiest single run.
        rs = [_cnn(sel, CNN_EPOCHS, seed=s) for s in ANCHOR_SEEDS]
        recalls = np.mean([x["recalls"] for x in rs], axis=0)
        r = {"acc": float(np.mean([x["acc"] for x in rs])), "bal": float(np.mean([x["bal"] for x in rs])),
             "recalls": recalls, "min_recall": float(recalls.min())}
        archive.append(_rec(nm, -1, r, sel, msk))
        spread = [round(x["acc"], 4) for x in rs]
        print(f"[saga] anchor {nm:22} cnn_val={r['acc']:.4f} bal={r['bal']:.4f} min_recall={r['min_recall']:.3f} "
              f"size={sel.shape[0]} seeds={ANCHOR_SEEDS} per_seed_val={spread}", flush=True)
    # CNN FLOOR = elementwise max of per-class val recall over the prior curations (all anchors are prev_*).
    floor_src = list(archive)
    _cnn_floor = np.max([a["recalls"] for a in floor_src], axis=0)
    for a in archive:
        a["score"] = shaped(a)   # re-score anchors against the floor so they rank comparably
    print(f"[saga] CNN floor from {[a['tag'] for a in floor_src]}: min={_cnn_floor.min():.3f} "
          f"mean={_cnn_floor.mean():.3f} tol={CNN_FLOOR_TOL} pen={CNN_FLOOR_PEN}", flush=True)

    for gen in range(GEN):
        for c in range(NC):
            ev = make_eval(c)
            tribe_pops[c] = engine.evolve(tribe_pops[c], ev, cfg, rng)
            champ = max(tribe_pops[c], key=lambda x: x.fitness)
            if champ.fitness >= bests[c].fitness:
                bests[c] = champ.copy()

        champ_mask = stitch.stitch(bests, class_idx, POOL_N)
        cands = [("champ", champ_mask, None)]
        for c in rng.choice(NC, size=min(TOPK - 1, NC), replace=False):
            ranked = sorted(tribe_pops[c], key=lambda x: x.fitness, reverse=True)
            if len(ranked) > 1:
                alt = ranked[1]
                cands.append((f"alt_c{c}", stitch.stitch_with(alt, c, bests, class_idx, POOL_N), (c, alt)))

        champ_rec, best = None, None
        for desc, mask, adopt in cands:
            sel = np.where(mask == 1)[0]
            rec = _rec(f"g{gen}_{desc}", gen, _cnn(sel, CNN_EPOCHS), sel, mask)
            archive.append(rec)
            if desc == "champ":
                champ_rec = rec
            if best is None or rec["score"] > best[0]:
                best = (rec["score"], adopt)
        if best[1] is not None and best[0] > champ_rec["score"]:
            c, alt = best[1]
            bests[c] = alt.copy()
            bests[c].fitness = make_eval(c)(bests[c])

        ba = max(archive, key=lambda a: a["score"])
        print(f"[saga] gen {gen:2d}/{GEN} champ: val={champ_rec['val']:.4f} bal={champ_rec['bal']:.4f} "
              f"min={champ_rec['min_recall']:.3f} score={champ_rec['score']:.4f} | archive_best score={ba['score']:.4f} "
              f"val={ba['val']:.4f} (size {ba['size']}, {ba['tag']}) cache={len(_cnn_cache)} "
              f"t={(time.time()-t0)/60:.0f}m", flush=True)
        _KEYS = ('tag', 'gen', 'val', 'bal', 'min_recall', 'score', 'size')
        json.dump({"note": "SAGA (diploid-coev, warm-start, CNN-gated) in progress", "vocab": VOCAB,
                   "warmstart_from": WARMSTART_FROM, "seed_only_from": SEED_ONLY_FROM, "prev_hit": prev_hit,
                   "cnn_floor": {"tol": CNN_FLOOR_TOL, "pen": CNN_FLOOR_PEN, "min": float(_cnn_floor.min()),
                                 "anchor_seeds": ANCHOR_SEEDS},
                   "archive_top": sorted(({k: a[k] for k in _KEYS} for a in archive),
                                         key=lambda a: -a["score"])[:10]}, open(OUT, "w"), indent=2)
        # CHECKPOINT (added 13 Sep): persist the top-10 archive MASKS every generation so a crash/reboot
        # leaves a materialisable subset behind (the 9 Sep run died with val scores only, no masks).
        top10 = sorted(archive, key=lambda a: -a["score"])[:10]
        np.savez_compressed(CKPT_OUT, **{a["tag"]: a["mask"] for a in top10},
                            _vals=np.array([a["score"] for a in top10]),
                            _tags=np.array([a["tag"] for a in top10]))

    # ---- final: re-check top-N archive with full CNN (multi-seed val), TEST once on champion ----
    # The prior curations are ALWAYS finalists (14 Sep): the run may only replace the deployed subset if the
    # 3-seed re-check says the new champion beats it — otherwise the champion IS the prior and deploy is a no-op.
    uniq: Dict[bytes, Dict] = {}
    for a in archive:
        if a["tag"].startswith("prev_"):
            uniq.setdefault(a["mask"].tobytes(), a)
    for a in sorted(archive, key=lambda a: -a["score"]):
        if len(uniq) >= FINAL_TOPN + len(prevs):
            break
        uniq.setdefault(a["mask"].tobytes(), a)
    finalists = list(uniq.values())
    print(f"[saga] final re-check {len(finalists)} finalists @ {FINAL_EPOCHS}ep seeds {FINAL_SEEDS} "
          f"(ranked by gated score = balanced val − floor penalty, mean over seeds)", flush=True)
    for a in finalists:
        sel = np.where(a["mask"] == 1)[0]
        rs = [_cnn(sel, FINAL_EPOCHS, seed=s) for s in FINAL_SEEDS]
        a["final_val_mean"] = float(np.mean([r["acc"] for r in rs])); a["final_val_std"] = float(np.std([r["acc"] for r in rs]))
        a["final_bal_mean"] = float(np.mean([r["bal"] for r in rs]))
        # 5 Oct fix: average the per-class recall vector ACROSS SEEDS, then score once. Scoring per seed and
        # averaging the scores biases against noisy-but-equal subsets because the penalty's max(0, .) is convex
        # (see the CNN_FLOOR_* block above). `final_recalls` is the seed-averaged vector everything below reads.
        a["final_recalls"] = np.mean([r["recalls"] for r in rs], axis=0)
        a["final_min_recall"] = float(a["final_recalls"].min())
        a["final_score"] = shaped({"bal": a["final_bal_mean"], "recalls": a["final_recalls"]})
        # Kept for one cycle so the two estimators can be compared on the same run; drop once the fix is trusted.
        a["final_score_perseed"] = float(np.mean([shaped(r) for r in rs]))
        print(f"  finalist {a['tag']:22} size={a['size']:5d} inloop={a['score']:.4f} final: val={a['final_val_mean']:.4f}"
              f"±{a['final_val_std']:.4f} bal={a['final_bal_mean']:.4f} min={a['final_min_recall']:.3f} "
              f"SCORE={a['final_score']:.4f} (per-seed-penalty estimator: {a['final_score_perseed']:.4f})", flush=True)
    champ = max(finalists, key=lambda a: a["final_score"])
    champ_mask_final = champ["mask"]
    csel = np.where(champ_mask_final == 1)[0]
    _r = _cnn(csel, FINAL_EPOCHS, seed=SEED, want_test=True); fv, ft, ft_bal = _r["acc"], _r["test"], _r["test_bal"]

    # PERSIST champion so it's deployable AND the next loop can warm-start from it.
    np.save(CHAMP_MASK_OUT, champ_mask_final)
    champ_rows = [ds._training[i] for i in csel.tolist()]
    json.dump(champ_rows, open(CHAMP_ROWS_OUT, "w"), indent=2)

    prev_anchor = next((a for a in archive if a["tag"] == "prev_ga_output"), None)
    payload = {
        "note": "SAGA diploid-coev + CNN-elite archive + warm-start (deployed + backup curations). Surrogate floor "
                "= max recall over full pool and prior curations. CNN scores GATED: balanced val acc − penalty for "
                "classes below the prior curations' CNN recall floor. Prior curations always finalists; select by "
                "3-seed mean gated score; test once. champion mask/rows persisted.",
        "config": {"engine": "diploid_coevolution", "vocab": VOCAB, "pop": POP, "gen": GEN, "topk": TOPK,
                   "folds": FOLDS, "surrogate": "word-2000 shaped-CV (RICH_FEATURES=0)",
                   "cnn_epochs": CNN_EPOCHS, "final_epochs": FINAL_EPOCHS, "final_seeds": FINAL_SEEDS,
                   "warmstart_from": WARMSTART_FROM, "seed_only_from": SEED_ONLY_FROM, "prev_hit": prev_hit,
                   "cnn_floor_tol": CNN_FLOOR_TOL, "cnn_floor_pen": CNN_FLOOR_PEN, "anchor_seeds": ANCHOR_SEEDS,
                   "cnn_floor_per_class": {str(c): float(v) for c, v in zip(ds._label_encoder.classes_, _cnn_floor)}},
        "champion": {"tag": champ["tag"], "size": champ["size"], "final_val": champ["final_val_mean"],
                     "final_val_std": champ["final_val_std"], "final_bal": champ["final_bal_mean"],
                     "final_min_recall": champ["final_min_recall"], "final_score": champ["final_score"],
                     "test": ft, "test_bal": ft_bal, "mask_file": CHAMP_MASK_OUT, "rows_file": CHAMP_ROWS_OUT},
        # 5 Oct: record the seed-averaged PER-CLASS recall for every finalist. Two consecutive cycles ended with
        # a per-class question (did the champion's Gov & Politics cut cost anything?) that the run's own output
        # could not answer, because only `min_recall` was stored — forcing a separate 3h eval to settle it.
        "finalists": [{**{k: a.get(k) for k in ('tag', 'size', 'final_val_mean', 'final_bal_mean',
                                                 'final_min_recall', 'final_score', 'final_score_perseed')},
                       "final_per_class_recall": ({str(c): round(float(v), 4) for c, v
                                                   in zip(ds._label_encoder.classes_, a["final_recalls"])}
                                                  if a.get("final_recalls") is not None else None)}
                      for a in finalists],
        "prev_curation_ref": ({"inloop_val": prev_anchor["val"], "size": prev_anchor["size"],
                               "final_val": prev_anchor.get("final_val_mean"),
                               "final_score": prev_anchor.get("final_score")} if prev_anchor else None),
        "pool_size": int(POOL_N),
        "archive_top": sorted(({k: a.get(k) for k in ('tag', 'gen', 'val', 'bal', 'min_recall', 'score', 'size',
                                                       'final_score')} for a in archive),
                              key=lambda a: -a["score"])[:12],
        "cnn_trainings": len(_cnn_cache),
    }
    json.dump(payload, open(OUT, "w"), indent=2)
    replaced = not champ["tag"].startswith("prev_")
    if replaced:
        verdict = "NEW subset beats the deployed one"
    elif champ["tag"] == "prev_ga_output":
        verdict = "deployed curation KEPT (nothing beat it)"
    else:
        # 17 Sep: a prior OTHER than the deployed one won — i.e. the deployed subset is not the best thing we
        # have. Deploy still does nothing (rotating a *_backup into place is a rollback, which is the user's
        # call, not the GA's), so say so loudly instead of reporting a plain "KEPT".
        verdict = (f"ROLLBACK CANDIDATE: {champ['tag']} beat the deployed curation — nothing deployed, "
                   f"decide manually whether to promote it")
    print(f"\n[saga] CHAMPION tag={champ['tag']} size={champ['size']} final: val={champ['final_val_mean']:.4f}"
          f"±{champ['final_val_std']:.4f} bal={champ['final_bal_mean']:.4f} min={champ['final_min_recall']:.3f} "
          f"score={champ['final_score']:.4f} | TEST={ft:.4f} (bal {ft_bal:.4f}) | {verdict}", flush=True)
    print(f"[saga] champion persisted -> {CHAMP_MASK_OUT} + {CHAMP_ROWS_OUT}", flush=True)
    print(f"[saga] wrote {OUT} wall={(time.time()-t0)/3600:.1f}h trainings={len(_cnn_cache)}", flush=True)
    if DEPLOY and replaced:
        # prev ga_output*.json -> *_backup.json ; champion -> ga_output.json + ga_output_combined.json.
        # Next run's default warm-start injects both, so the loop can only move forward.
        import deploy_champion
        deploy_champion.main()
    elif DEPLOY:
        # 15 Sep: when the champion IS a prior curation there is nothing to deploy. Running the rotation anyway
        # copied ga_output -> ga_output_backup and destroyed the second warm-start anchor (the 8,521-row prior
        # curation was overwritten with a duplicate of the deployed one). Skip it.
        print(f"[deploy] skipped: champion is {champ['tag']}, deployed files unchanged", flush=True)
    print("SAGA DONE", flush=True)


if __name__ == "__main__":
    main()
