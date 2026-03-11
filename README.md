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
- [Genetic Algorithm Optimization](#genetic-algorithm-optimization-datacreatorpy)
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
| Conservation & Environment | Music & Concerts |
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

- Python 3.8+
- Chrome/Chromium (for Selenium-based scrapers)
- ChromeDriver matching your Chrome version

### Install Dependencies

```bash
pip install tensorflow keras scikit-learn numpy pygad joblib selenium beautifulsoup4
```

### Optional: GPU Support

For faster training with GPU:
```bash
pip install tensorflow-gpu
```

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
train_from_manual_training_files(use_ai_data=False)
```

### 4. Classify Events

```python
labels = predict_from_file("unclassified_data.json", update_labels=True)
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
│              ┌─────────────┼─────────────┐                              │
│              ▼             ▼             ▼                              │
│     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│     │training_data │ │ unclassified │ │ ai_generates │                  │
│     │    .json     │ │  _data.json  │ │    .json     │                  │
│     └──────┬───────┘ └──────────────┘ └──────┬───────┘                  │
│            │                                 │                          │
│            └─────────────┬───────────────────┘                          │
│                          ▼                                              │
│                 ┌─────────────────┐                                     │
│                 │  DataCreator    │ (Optional GA Optimization)          │
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

**Individual scrapper:**
```python
import EventbriteScrapper
scrapper = EventbriteScrapper.EventbriteScrapper()
events = scrapper.fetch_events([], [])
```

### Scraper Output

Each scraper generates three files:
- `{Source}Events.json` - Scraped event data
- `{Source}Urls.json` - Processed URLs (for deduplication)
- `{Source}Banned.json` - Blocked/invalid URLs

## Data Generation (`GenerateData.py`)

The data generation module prepares training data from scraped events.

### Key Functions

#### `generate_data()`
Processes events from `events.json` and updates the training dataset:
1. Reads events with valid descriptions (excluding "Other" category)
2. Cleans descriptions by removing boilerplate text like "You may also like..." sections
3. Deduplicates entries by checking against existing training and unclassified data
4. Creates training entries with format: `{description: "Event Name, Long Description", label: "Category"}`
5. Marks short entries (<110 characters) as `skip: true` to exclude from training

#### `generate_unclassified_data()`
Handles events marked as "Other" that need manual classification:
1. Filters events without proper categorization
2. Adds them to `unclassified_data.json` for later labeling

#### `clean_data(key, events)`
Removes noise from event descriptions by stripping:
- "You may also like the following events from..."
- "Also check out other..."

#### `count_categories()`
Displays category distribution with color-coded output to identify imbalanced classes.

#### `move_top_n_shortest()` / `move_top_n_largest()`
Rebalances the dataset by moving entries between training and unclassified sets based on description length.

### Data Files
- `training_data.json` - Labeled training examples
- `unclassified_data.json` - Events pending classification
- `ai_generates.json` - AI-generated training examples for augmentation

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
train_from_manual_training_files(use_ai_data=False)

# Prediction
labels = predict_from_file("unclassified_data.json", update_labels=True)
```

## Genetic Algorithm Optimization (`DataCreator.py`)

Uses a genetic algorithm (via PyGAD) to find the optimal subset of training data that maximizes model accuracy.

### How It Works

1. **Data Preparation**: Splits all labeled data into training pool and test set
2. **Fitness Function**: Trains a model on selected subset and evaluates on test set
3. **Evolution**: GA optimizes which training samples to include
4. **Output**: Best training subset saved to `ga_output_combined.json`

### GA Parameters

| Parameter | Value |
|-----------|-------|
| Population Size | 100 |
| Generations | 100 |
| Parent Selection | Steady-State Selection |
| Crossover | Scattered |
| Mutation Rate | 20% of genes |

### Model Options

- `NN` - Neural network with embedding + pooling
- `LR` - Logistic Regression with TF-IDF (faster for GA iterations)

## Project Structure

```
Wellington-Events-Scrapper/
├── MainScrapper.py              # Orchestrates all scrapers
├── ScrapperFactory.py           # Factory pattern for scraper instantiation
├── ScrapperNames.py             # Scraper name constants
│
├── # Individual Scrapers
├── AllEventsInScrapper.py       # allevents.in
├── EventbriteScrapper.py        # Eventbrite
├── EventFinderScrapper.py       # EventFinder
├── FacebookScrapper.py          # Facebook Events
├── FringeScrapper.py            # Fringe Festival
├── HumanitixScrapper.py         # Humanitix
├── RoxyScrapper.py              # Roxy Cinema
├── SanFranScrapper.py           # San Fran venue
├── TicketekScrapper.py          # Ticketek
├── TicketmasterScrapper.py      # Ticketmaster
├── UnderTheRaderScrapper.py     # Under The Radar
├── ValhallaScrapper.py          # Valhalla
├── WellingtonHeritageFestivalScrapper.py
├── WellingtonHighschoolScrapper.py
├── WellingtonNZScrapper.py      # Wellington.govt.nz
├── WoapScrapper.py              # WOAP
├── RougueScrapper.py            # Rogue & Vagabond
│
├── # ML Pipeline
├── GenerateData.py              # Data preparation and cleaning
├── TextClassifier.py            # CNN classifier training and prediction
├── DataCreator.py               # Genetic algorithm for data optimization
│
├── # Utilities
├── CategoryMapping.py           # Source-to-standard category mapping
├── CoordinatesMapper.py         # Geographic coordinate mapping
├── DateFormatting.py            # Date parsing utilities
├── EventInfo.py                 # Event data class
├── FileNames.py                 # File path constants
├── FileUtils.py                 # File I/O operations
│
├── # Data Files
├── events.json                  # Aggregated scraped events
├── training_data.json           # Labeled training examples
├── unclassified_data.json       # Events pending classification
├── ai_generates.json            # AI-augmented training data
├── ga_output_combined.json      # GA-optimized training set
│
├── # Model Artifacts
├── trained_model/               # Saved Keras model
├── tokenizer_config.json        # Tokenizer configuration
├── label_encoder.joblib         # Saved label encoder
│
├── # Output
├── predictions_log.txt          # Detailed prediction results
└── README.md
```

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

### Training Entry (`training_data.json`)

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

### DataCreator Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MODEL_CHOICE` | 'LR' | 'LR' (Logistic Regression) or 'NN' (Neural Network) |
| `pop_size` | 100 | GA population size |
| `num_generations` | 100 | GA generations to run |
| `mutation_percent_genes` | 20 | Mutation rate (%) |

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
│ STEP 2: GENERATE TRAINING DATA                                  │
│ $ python GenerateData.py                                        │
│ Output: training_data.json, unclassified_data.json              │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: (OPTIONAL) OPTIMIZE TRAINING SET                        │
│ $ python DataCreator.py                                         │
│ Output: ga_output_combined.json                                 │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: TRAIN CLASSIFIER                                        │
│ In TextClassifier.py:                                           │
│   should_train = True                                           │
│   train_from_manual_training_files(use_ai_data=False)           │
│ Output: trained_model/, tokenizer_config.json, label_encoder    │
└─────────────────────────────┬───────────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: CLASSIFY EVENTS                                         │
│ In TextClassifier.py:                                           │
│   predict_from_file("unclassified_data.json", update_labels=True)│
│ Output: predictions_log.txt, updated labels in source file      │
└─────────────────────────────────────────────────────────────────┘
```

### Manual Labeling Workflow

1. Run `GenerateData.py` to populate `unclassified_data.json`
2. Open `unclassified_data.json` and manually update `label` fields
3. Move labeled entries to `training_data.json`
4. Re-train the model with new data

### Using AI-Generated Data

1. Create synthetic training examples in `ai_generates.json`
2. Train with augmentation:
   ```python
   train_from_manual_training_files(use_ai_data=True)
   ```

## Troubleshooting

### Common Issues

**"Test file not found" when running DataCreator:**
```
Run generate_files() first before calling run()
```

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
