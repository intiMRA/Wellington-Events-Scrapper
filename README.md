# Wellington Events Scrapper

A comprehensive event aggregation and classification system for Wellington, New Zealand. This project combines web scraping from multiple event sources with machine learning-based automatic categorization using neural networks and genetic algorithm optimization.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Web Scraping](#web-scraping)
- [Data Generation](#data-generation-generatedatapy)
- [Text Classifier](#text-classifier-textclassifierpy)
- [Training-Set Curation: SAGA](#training-set-curation-saga-run_sagapy)
- [Project Structure](#project-structure)
- [Data Formats](#data-formats)
- [Configuration](#configuration)
- [Workflow](#workflow)
- [Troubleshooting](#troubleshooting)

## Overview

This project scrapes event data from various Wellington event sources and classifies them into 16 categories:

| Category | Category |
|----------|----------|
| Arts & Theatre | Health & Wellness |
| Business & Networking | Hobbies & Interests |
| Classes & Workshops | Kids & Parents |
| Community & Culture | Markets & Fairs |
| Conservation & Nature | Music & Concerts |
| Festivals | Religion & Spirituality |
| Film & Media | Sports & Fitness |
| Food & Drink | Government & Politics |

## Features

- **Multi-source Scraping**: Aggregates events from 18+ Wellington event platforms
- **Automatic Classification**: CNN-based text classifier with ~85%+ accuracy
- **Data Augmentation**: AI-generated synthetic training data support
- **Genetic Algorithm Optimization**: Finds optimal training data subsets
- **Duplicate Detection**: Identifies and handles duplicate events across sources
- **Auto-labeling**: High-confidence predictions automatically update labels

## Installation

### Prerequisites

- **Python 3.11** (required: `StrEnum` needs ≥3.11, and the pinned TensorFlow 2.15 supports up to 3.11). The version is pinned in `.python-version` and `pyproject.toml` (`requires-python`).
- Chrome/Chromium (for Selenium-based scrapers)

### Set up the environment

Create a 3.11 virtual environment at `.venv` and install the pinned dependencies:

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

**PyCharm:** on first open it detects `requirements.txt` / `pyproject.toml` and offers to create the `.venv` and install everything automatically — just accept the prompt (it reads `requires-python` to pick 3.11). Run scripts **from the repo root**; auxiliary scripts run as modules, e.g. `python -m classification.TextClassifier`.

Dependencies are pinned in `requirements.txt` (the single source; `pyproject.toml` reads from it). ChromeDriver is managed automatically by `webdriver-manager`.

## Quick Start

### 1. Scrape Events

```bash
python MainScrapper.py
```

This runs all scrapers and aggregates events into `events.json`.

### 2. Generate Training Data

```bash
python GenerateData.py
```

Processes scraped events into training and unclassified datasets.

### 3. Train the Classifier

```python
# In TextClassifier.py, set:
should_train = True
train_from_manual_training_files()
```

### 4. Classify Events

```python
labels = predict_from_file("generated_data.json", update_labels=True)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Wellington Events Scrapper                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Eventbrite  │    │   Facebook   │    │  EventFinder │   ...18+     │
│  │   Scrapper   │    │   Scrapper   │    │   Scrapper   │   sources    │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              │
│         │                   │                   │                       │
│         └───────────────────┼───────────────────┘                       │
│                             ▼                                           │
│                    ┌────────────────┐                                   │
│                    │  MainScrapper  │                                   │
│                    │  (Aggregator)  │                                   │
│                    └───────┬────────┘                                   │
│                            ▼                                            │
│                    ┌────────────────┐                                   │
│                    │  events.json   │                                   │
│                    └───────┬────────┘                                   │
│                            ▼                                            │
│                    ┌────────────────┐                                   │
│                    │ GenerateData   │                                   │
│                    └───────┬────────┘                                   │
│                            │                                            │
│                            ▼                                            │
│                    ┌────────────────┐                                   │
│                    │ generated_data │                                   │
│                    │     .json      │                                   │
│                    └───────┬────────┘                                   │
│                            ▼                                            │
│                 ┌─────────────────┐                                     │
│                 │    run_saga     │ (GA training-set curation)          │
│                 └────────┬────────┘                                     │
│                          ▼                                              │
│                 ┌─────────────────┐                                     │
│                 │ TextClassifier  │                                     │
│                 │   (CNN Model)   │                                     │
│                 └────────┬────────┘                                     │
│                          │                                              │
│            ┌─────────────┼─────────────┐                                │
│            ▼             ▼             ▼                                │
│     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│     │trained_model/│ │  tokenizer_  │ │label_encoder │                  │
│     │              │ │ config.json  │ │   .joblib    │                  │
│     └──────────────┘ └──────────────┘ └──────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Web Scraping

### Supported Event Sources

| Scrapper | Source | Notes |
|----------|--------|-------|
| `AllEventsInScrapper` | allevents.in | General events |
| `EventbriteScrapper` | Eventbrite | Major event platform |
| `EventFinderScrapper` | EventFinder | NZ events |
| `FacebookScrapper` | Facebook Events | Social events |
| `FringeScrapper` | Fringe Festival | Arts festival |
| `HumanitixScrapper` | Humanitix | Charity events |
| `RoxyScrapper` | Roxy Cinema | Film screenings |
| `SanFranScrapper` | San Fran venue | Live music |
| `TicketekScrapper` | Ticketek | Major ticketing |
| `TicketmasterScrapper` | Ticketmaster | Major ticketing |
| `UnderTheRaderScrapper` | Under The Radar | Indie events |
| `ValhallaScrapper` | Valhalla | Venue events |
| `WellingtonHeritageFestivalScrapper` | Heritage Festival | Cultural events |
| `WellingtonHighschoolScrapper` | WHS Events | School events |
| `WellingtonNZScrapper` | Wellington.govt.nz | City events |
| `WoapScrapper` | WOAP | Food & wine festival |
| `RougueScrapper` | Rogue & Vagabond | Venue events |

### Running Scrapers

**All scrapers:**
```bash
python MainScrapper.py
```

**Individual scrapper** (run from the repo root):
```python
from scrapers import EventbriteScrapper
scrapper = EventbriteScrapper.EventbriteScrapper()
events = scrapper.fetch_events([], [])
```

**Auxiliary pipeline scripts** run as modules from the repo root, e.g.:
```bash
python -m classification.TextClassifier
python -m classification.GenerateData
```

### Scraper Output

Each scraper keeps its files in its own folder, `data/scrapers/{Source}/`:
- `data/scrapers/{Source}/events.json` - Scraped event data
- `data/scrapers/{Source}/urls.json` - Processed URLs (for deduplication)
- `data/scrapers/{Source}/banned.json` - Blocked/invalid URLs

## Data Generation (`GenerateData.py`)

The data generation module prepares training data from scraped events.

### Key Functions

#### `generate_data()`
Ingests new events from `events.json` into the single dataset `generated_data.json`:
1. Reads events with a valid `long_description` (any `eventType`)
2. Cleans descriptions by removing boilerplate ("You may also like...", "Also check out other...")
3. Deduplicates by description against the existing dataset
4. Appends new entries as `{description: "Event Name, Long Description", label: eventType}` — uncategorised events come in as `Other` for later labeling
5. Marks short entries (<110 characters) as `skip: true` to exclude from training

#### `clean_data(key, events)`
Removes noise from event descriptions by stripping:
- "You may also like the following events from..."
- "Also check out other..."

#### `count_categories()`
Prints the label distribution of `generated_data.json` to spot class imbalance.

### Data File
- `generated_data.json` - The single labeled dataset (both categorised and `Other` entries)

## Text Classifier (`TextClassifier.py`)

A CNN-based text classifier using TensorFlow/Keras.

### Architecture

```
Embedding Layer (400 dimensions)
    ↓
Conv1D (512 filters, kernel size 3, ReLU)
    ↓
GlobalMaxPooling1D
    ↓
Dense (64 units, ReLU)
    ↓
Dense (16 units, Softmax) → Category Prediction
```

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Max Sequence Length | 1500 tokens |
| Vocabulary Size | 2000 words |
| Embedding Dimension | 400 |
| Batch Size | 32 |
| Early Stopping Patience | 5 epochs |

### Training (`train_from_manual_training_files()`)

1. Loads training data from JSON files
2. Tokenizes text using Keras `Tokenizer` with OOV token handling
3. Encodes labels using `LabelEncoder`
4. Splits data: 80% train, 20% validation
5. Trains with early stopping based on validation loss
6. Saves model artifacts:
   - `trained_model/` - Keras model
   - `tokenizer_config.json` - Tokenizer configuration
   - `label_encoder.joblib` - Label encoder

### Prediction (`predict_from_file()`)

Predicts categories for events in a file:
1. Loads trained model, tokenizer, and label encoder
2. Returns top 2 predictions if confidence is similar (within 50%)
3. Auto-updates labels for high-confidence predictions in select categories:
   - Music & Concerts
   - Markets & Fairs
   - Classes & Workshops
   - Arts & Theatre
4. Logs predictions to `predictions_log.txt`

### Usage

```python
# Training
should_train = True
train_from_manual_training_files()

# Prediction
labels = predict_from_file("generated_data.json", update_labels=True)
```

## Training-Set Curation: SAGA (`run_saga.py`)

SAGA (surrogate-assisted genetic algorithm) searches for the subset of labelled rows that the CNN
trains best on, without regressing any single class. It is the one GA in the repo; the older
PyGAD `DataCreator.py` and the standalone `tribes_ga` runner were removed in Sep 2026.

### How It Works

1. **Split** (`classification/Dataset.py`): one canonical, group-aware, append-stable
   train / validation / test split. Near-duplicate rows are clustered and kept in one split, and
   held-out rows never migrate as the pool grows. Rebuild after labelling with
   `python -m classification.Dataset --rebuild`.
2. **Warm start**: the deployed subset (`ga_output.json`) *and* the one before it
   (`ga_output_backup.json`) are mapped onto the pool and injected into every tribe's starting
   population, and both are forced into the final re-check, so each run can only improve on the last.
3. **Tribes** (`tribes_ga/`): one diploid population per class (cooperative coevolution). A fast
   class-weighted linear surrogate scores candidates with a shaped fitness: balanced accuracy minus a
   penalty for any class whose recall drops below the **previous-best floor**, the per-class max over
   the prior curations (deployed + backup). The full pool is not tracked as a reference; it is only the
   tribes' starting genome, and the fallback floor on a first run with nothing deployed.
4. **CNN in the loop**: each generation the stitched champion plus a few alternates are trained
   with a short CNN run. Candidates are scored with the same gate on the CNN side: balanced validation
   accuracy minus a penalty for any class whose CNN recall falls below the prior curations' recall
   (`SAGA_CNN_FLOOR_TOL`, default 0.03 ≈ one validation example). The archive keeps the best gated score.
5. **Final pick**: top archive entries plus the prior curations are re-checked with the full CNN across
   3 seeds and ranked by mean gated score; the winner is tested once and persisted as
   `saga_champion_rows.json` + `saga_champion_mask.npy`. If nothing beats the deployed curation,
   the champion *is* the deployed curation and deploy is a no-op.
6. **Deploy** (`deploy_champion.py`, run automatically at the end unless `SAGA_DEPLOY=0`): rotates the
   current `ga_output.json` / `ga_output_combined.json` to `*_backup.json`, then writes the champion as
   `ga_output.json` (next warm start) and `ga_output_combined.json` (champion + validation + test, what
   `TextClassifier` trains on).

### Running it

```bash
cd Wellington-Events-Scrapper
python -m classification.Dataset --rebuild
nohup caffeinate -i -m ./run_saga.sh > saga_run.log 2>&1 &
# ~18h later the log prints "SAGA DONE" and ga_output*.json already hold the new champion.
# Then retrain the CNN (TextClassifier, use_ga=True) on ga_output_combined.json.
```

`run_saga.sh` sets the parameters below and documents why each is what it is; override any of them by
exporting the env var before calling it. Progress is checkpointed every generation to
`data/training/saga_archive_ckpt.npz` (top-10 masks), which is how a crashed run still leaves a
materialisable subset behind.

Before deploying or believing any champion, confirm it with `./run_cnn_eval.sh`: SAGA's end-of-run
`TEST=` is a SINGLE measurement, and its finalist ordering is a shortlist, not a result.

### SAGA Parameters (env vars)

| Variable | Default | Description |
|-----------|---------|-------------|
| `SAGA_POP` | 40 | Population per class tribe |
| `SAGA_GEN` | 30 | Generations |
| `SAGA_FOLDS` | 3 | Surrogate CV folds |
| `SAGA_CNN_EPOCHS` | 10 | In-loop steering CNN epochs |
| `SAGA_FINAL_EPOCHS` / `SAGA_FINAL_SEEDS` | 100 / 42,7,123 | Final re-check |
| `SAGA_VOCAB` | 20000 | CNN vocabulary |
| `SAGA_WARMSTART_FROM` | `ga_output,ga_output_backup` | Prior subsets to inject, comma list (`none` to disable) |
| `SAGA_DEPLOY` | 1 | Run `deploy_champion.py` at the end (`0` to only persist the champion files) |
| `SAGA_CNN_FLOOR_TOL` / `SAGA_CNN_FLOOR_PEN` | 0.03 / 2.0 | CNN-side per-class recall gate vs prior curations |
| `SAGA_PREFIX` | `saga` | Artifact filename prefix (use another value for test runs) |
| `RICH_FEATURES` | 1 | Set `0` for the fast word-2000 surrogate |

## Project Structure

```
Wellington-Events-Scrapper/
├── MainScrapper.py              # Entry point: runs all scrapers -> events.json
├── RecoverFromLast.py           # Resume a scrape from the last-run source
│
├── scrapers/                    # One module per event source + factory/registry
│   ├── ScrapperFactory.py       # Maps a source name to its scraper class
│   ├── ScrapperNames.py         # Source name constants + active-source list
│   ├── AllEventsInScrapper.py   # allevents.in
│   ├── EventbriteScrapper.py    # Eventbrite
│   ├── EventFinderScrapper.py   # EventFinder
│   ├── FacebookScrapper.py      # Facebook Events
│   ├── FringeScrapper.py        # Fringe Festival
│   ├── HumanitixScrapper.py     # Humanitix
│   ├── RoxyScrapper.py          # Roxy Cinema
│   ├── RougueScrapper.py        # Rogue & Vagabond
│   ├── SanFranScrapper.py       # San Fran venue
│   ├── TicketekScrapper.py      # Ticketek
│   ├── TicketmasterScrapper.py  # Ticketmaster
│   ├── UnderTheRaderScrapper.py # Under The Radar
│   ├── ValhallaScrapper.py      # Valhalla
│   ├── WellingtonHeritageFestivalScrapper.py
│   ├── WellingtonHighschoolScrapper.py
│   ├── WellingtonNZScrapper.py  # Wellington.govt.nz
│   └── WoapScrapper.py          # WOAP
│
├── model/                       # Domain data models
│   ├── EventInfo.py             # Event data class
│   ├── Buger.py                 # Burger data class (Wellington on a Plate)
│   └── CategoryMapping.py       # Source-to-standard category mapping
│
├── classification/              # ML pipeline (run as: python -m classification.<name>)
│   ├── TextClassifier.py        # CNN event-type classifier (train/predict)
│   ├── KidFriendlyClassifier.py # Kid-friendly binary classifier
│   ├── GenerateData.py          # Build/clean training + unclassified datasets
│   ├── Dataset.py               # Canonical group-aware train/val/test split
│   └── LabelEvents.py           # Label events with the trained model
│
├── run_saga.py                  # SAGA: CNN-in-the-loop GA training-set curation
├── run_saga.sh                  # One curation cycle, with the rationale for each setting
├── deploy_champion.py           # Champion rows -> ga_output*.json
├── cnn_eval_subset.py           # Multi-seed CNN score of a subset on the clean holdout
├── run_cnn_eval.sh              # Run that eval over several subsets, with how to read it
├── tribes_ga/                   # GA library used by SAGA (genome, engine, fitness, stitch)
│
├── util/                        # Shared helpers and I/O
│   ├── paths.py                 # Central data/ & models/ path resolution
│   ├── FileNames.py             # Canonical file paths
│   ├── FileUtils.py             # Event file I/O
│   ├── CurrentFestivals.py      # Active festival registry
│   ├── DateFormatting.py        # Date parsing utilities
│   ├── CoordinatesMapper.py     # Geographic coordinate mapping
│   ├── Summarizer.py            # Description summarisation
│   └── tryAddLocation.py        # One-off location backfill utility
│
├── data/
│   ├── scrapers/<Source>/       # Per-scraper checkpoints: events.json, urls.json, banned.json
│   ├── training/                # Training/GA datasets (generated_data, ga_*, ...)
│   └── logs/                    # Prediction/debug logs
├── models/                      # Saved Keras models, tokenizers, label encoder
│
├── events.json                  # Published feed (aggregated events), read via raw URL
├── events_filtered.json         # Published filtered feed
├── currentFestivals.json        # Published active-festival list
├── currentFestivalDetails.json  # Published festival details (carries per-festival URLs)
├── burgers.json                 # Published feed consumed directly by the iOS client
├── wellington-fringe.json       # Published festival feed (linked from festival details)
├── heritage-festival.json       #   "
├── *-film-festival*.json         # Published Roxy festival feeds (linked from festival details)
│
├── requirements.txt
└── README.md
```

> **Published feeds stay at the repo root.** The iOS client
> (`WellingtonEventsApp`) fetches these by `raw.githubusercontent.com/.../main/<file>` URL —
> directly (`events.json`, `currentFestivals.json`, `currentFestivalDetails.json`,
> `burgers.json`) or via the `url` fields inside `currentFestivalDetails.json`. Do not move
> them into `data/`; only internal working data lives there.

## Data Formats

### Event Entry (`events.json`)

```json
{
  "id": "unique_event_id",
  "name": "Event Name",
  "venue": "Venue Name, Wellington",
  "dates": ["2026-03-15-19:30"],
  "url": "https://source.com/event",
  "source": "Eventbrite",
  "eventType": "Music & Concerts",
  "long_description": "Full event description text...",
  "imageUrl": "https://..."
}
```

### Data Entry (`generated_data.json`)

```json
{
  "description": "Event Name, Full event description text...",
  "label": "Music & Concerts",
  "skip": false,
  "new": true
}
```

**Field descriptions:**
- `description`: Concatenation of event name and long description
- `label`: One of 16 category labels
- `skip`: If `true`, excluded from training (e.g., too short)
- `new`: If `true`, newly added entry

## Configuration

### TextClassifier Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_sequence_length` | 1500 | Maximum tokens per input |
| `num_words` | 2000 | Vocabulary size |
| `embedding_dim` | 400 | Embedding vector dimensions |
| `batch_size` | 32 | Training batch size |
| `patience` | 5 | Early stopping patience |

### GenerateData Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_description_length` | 110 | Minimum characters (shorter = skipped) |
| `skip_strings` | [...] | Boilerplate text to remove |

## Workflow

### Complete Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: SCRAPE EVENTS                                           │
│ $ python MainScrapper.py                                        │
│ Output: events.json                                             │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: GENERATE / INGEST DATA                                  │
│ $ python -m classification.GenerateData                         │
│ Output: generated_data.json                                     │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: CURATE TRAINING SET (SAGA)                              │
│ $ python -m classification.Dataset --rebuild                    │
│ $ ./run_saga.sh       (see "Training-Set Curation")             │
│ $ python deploy_champion.py                                     │
│ Output: ga_output.json, ga_output_combined.json                 │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: TRAIN CLASSIFIER                                        │
│ In TextClassifier.py:                                           │
│   should_train = True                                           │
│   train_from_manual_training_files()           │
│ Output: trained_model/, tokenizer_config.json, label_encoder    │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: CLASSIFY EVENTS                                         │
│ In TextClassifier.py:                                           │
│   predict_from_file("generated_data.json", update_labels=True)│
│ Output: predictions_log.txt, updated labels in source file      │
└─────────────────────────────────────────────────────────────────┘
```

### Manual Labeling Workflow

1. Run `python -m classification.GenerateData` to ingest new events into `generated_data.json`
2. Open `generated_data.json` and set/correct `label` fields (uncategorised events come in as `Other`)
3. Re-train the model with the updated data

## Troubleshooting

### Common Issues

**SAGA / Dataset import errors:**
Run from the repo root (or set `PYTHONPATH` to it) and rebuild the split first with
`python -m classification.Dataset --rebuild`.

**Low classifier accuracy:**
- Check category balance with `count_categories()` in GenerateData
- Add more training examples for underrepresented categories
- Try GA optimization to find better training subsets

**Scraper timeouts:**
- Check your internet connection
- Verify ChromeDriver version matches Chrome
- Some sites may have rate limiting

**Memory issues during training:**
- Reduce `num_words` vocabulary size
- Reduce `embedding_dim`
- Use smaller batch size

### Checking Training Data Quality

```python
# In GenerateData.py
count_categories()  # Shows category distribution with color coding
print_duplicates()  # Identifies conflicting labels
```

**Color codes in count_categories:**
- Green: Balanced (150 samples)
- Cyan: Below target
- Red/Yellow: Above target

### Model Not Learning

1. Verify training data is not too short (< 110 chars)
2. Check for label conflicts with `print_duplicates()`
3. Ensure sufficient examples per category (aim for 150+)
4. Review `skip` flags in training data
