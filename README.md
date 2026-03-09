# Wellington Events Scrapper - Text Classification

A machine learning pipeline for classifying Wellington events into categories using neural networks and genetic algorithm optimization.

## Overview

This project scrapes event data from various Wellington event sources and classifies them into 16 categories:

- Arts & Theatre
- Business & Networking
- Classes & Workshops
- Community & Culture
- Conservation & Environment
- Festivals
- Film & Media
- Food & Drink
- Government & Politics
- Health & Wellness
- Hobbies & Interests
- Kids & Parents
- Markets & Fairs
- Music & Concerts
- Religion & Spirituality
- Sports & Fitness

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

## Installation

```bash
pip install tensorflow keras scikit-learn numpy pygad joblib
```

## Project Structure

```
├── GenerateData.py          # Data preparation and cleaning
├── TextClassifier.py        # CNN classifier training and prediction
├── DataCreator.py           # Genetic algorithm for data optimization
├── training_data.json       # Labeled training examples
├── unclassified_data.json   # Events pending classification
├── ai_generates.json        # AI-augmented training data
├── ga_output_combined.json  # GA-optimized training set
├── trained_model/           # Saved Keras model
├── tokenizer_config.json    # Tokenizer configuration
└── label_encoder.joblib     # Saved label encoder
```

## Workflow

1. **Scrape Events** → `events.json`
2. **Generate Data** → Run `GenerateData.py` to populate training files
3. **Optimize Training Set** → Run `DataCreator.py` to find optimal subset
4. **Train Classifier** → Run `TextClassifier.py` with `should_train = True`
5. **Classify Events** → Run `TextClassifier.py` to predict categories
