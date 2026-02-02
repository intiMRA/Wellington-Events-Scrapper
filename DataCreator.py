import math
import TextClassifier
import random
import pygad
from typing import List, Dict, Tuple
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical, set_random_seed
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, GlobalAveragePooling1D, Dense
from tensorflow.config.experimental import enable_op_determinism
from keras.callbacks import EarlyStopping
import os
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer

MODEL_CHOICE = 'LR'

ga_test_file_name = "ga_test.json"
ga_training_choices_file_name = "ga_training_choices.json"
ga_output_file_name = "ga_output.json"
ga_output_file_combined_name = "ga_output_combined.json"
ga_balanced_individual_file_name = "ga_balanced_individual.json"

def load_data_initial_data(load_ai) -> List[Dict]:
    data = []
    file_names = ["training_data.json", "unclassified_data.json"]
    if load_ai:
        file_names.append("ai_generates.json")
    for file_name in file_names:
        try:
            with open(file_name, mode="r") as f:
                data.extend(json.loads(f.read()))
        except FileNotFoundError:
            print(f"Warning: File not found: {file_name}")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_name}")

    new_data = []
    desc_titles = set()
    for d in data:
        description: str = d["description"]
        if d.get("skip", False) or "label" not in d:
            continue

        title = description.split(",")[0]

        if description in desc_titles or title in desc_titles:
            continue

        desc_titles.add(description)
        desc_titles.add(title)
        new_data.append(d)

    return new_data


def count_min_classes(data: List[Dict]) -> int:
    counts = {}
    for d in data:
        label = d["label"]
        counts[label] = counts.get(label, 0) + 1
    print(counts)
    smallest = math.inf
    for count in counts.values():
        if count < smallest:
            smallest = count

    return smallest


def generate_files():
    data = load_data_initial_data(load_ai=False)

    counts = count_min_classes(data)
    test_num = int(counts * 0.4)
    random.shuffle(data)

    classes = {}
    for d in data:
        label = d["label"]
        classes.setdefault(label, []).append(d)
    test = []
    for c in classes.keys():
        test.extend(classes[c][0:test_num])

    test_set = set(id(d) for d in test)
    data = load_data_initial_data(load_ai=True)
    training = [d for d in data if id(d) not in test_set]

    training_classes = {}
    for d in training:
        label = d["label"]
        training_classes.setdefault(label, []).append(d)

    min_training_count = min(len(v) for v in training_classes.values()) if training_classes else 0

    individual_indices = []
    for c in training_classes.keys():
        sub_set = training_classes[c][0:min_training_count]
        for s in sub_set:
            individual_indices.append(training.index(s))

    with open(ga_training_choices_file_name, mode="w") as ga_training_file:
        json.dump(training, ga_training_file, indent=2)

    with open(ga_test_file_name, mode="w") as ga_test_file:
        json.dump(test, ga_test_file, indent=2)

    with open(ga_balanced_individual_file_name, mode="w") as ga_balanced_individual_file:
        json.dump(individual_indices, ga_balanced_individual_file, indent=2)

def get_training() -> Tuple[np.ndarray, np.ndarray, int, LabelEncoder, object]:
    if not os.path.exists(ga_training_choices_file_name):
        raise FileNotFoundError(
            f"Training file '{ga_training_choices_file_name}' not found. Run generate_files() first.")

    with open(ga_training_choices_file_name, mode="r") as ga_training_file:
        classified_data = json.loads(ga_training_file.read())

    descriptions = [value["description"] for value in classified_data]
    labels = [value["label"] for value in classified_data]

    label_encoder = LabelEncoder()
    encoded_labels_all = label_encoder.fit_transform(labels)
    num_classes = len(np.unique(encoded_labels_all))
    one_hot_labels = to_categorical(encoded_labels_all, num_classes=num_classes)
    Y_pool = np.array(one_hot_labels)

    if MODEL_CHOICE == 'NN':
        # NN: Use Keras Tokenizer and Pad Sequences
        model_prep = Tokenizer(num_words=TextClassifier.num_words, oov_token="<unk>")
        model_prep.fit_on_texts(descriptions)
        sequences = model_prep.texts_to_sequences(descriptions)
        X_pool = np.array(pad_sequences(sequences, maxlen=TextClassifier.max_sequence_length, padding='post'))

    else:
        model_prep = TfidfVectorizer(max_features=TextClassifier.num_words)
        X_pool = model_prep.fit_transform(descriptions)  # X_pool is a sparse matrix

    return X_pool, Y_pool, num_classes, label_encoder, model_prep


def get_test(model_prep: object, label_encoder: LabelEncoder, num_classes: int) -> Tuple[np.ndarray, np.ndarray]:
    if not os.path.exists(ga_test_file_name):
        raise FileNotFoundError(f"Test file '{ga_test_file_name}' not found. Run generate_files() first.")

    with open(ga_test_file_name, mode="r") as ga_test_file:
        test_data = json.loads(ga_test_file.read())

    descriptions = [value["description"] for value in test_data]
    labels = [value["label"] for value in test_data]

    encoded_labels = label_encoder.transform(labels)
    one_hot_labels = to_categorical(encoded_labels, num_classes=num_classes)
    Y_test_processed = np.array(one_hot_labels)

    if MODEL_CHOICE == 'NN':
        # NN: Tokenize and Pad Sequences
        sequences = model_prep.texts_to_sequences(descriptions)
        X_test_processed = np.array(pad_sequences(sequences, maxlen=TextClassifier.max_sequence_length, padding='post'))

    else:  # MODEL_CHOICE == 'LR'
        # LR: Transform using fitted TF-IDF Vectorizer
        X_test_processed = model_prep.transform(descriptions)  # X_test_processed is a sparse matrix

    return X_test_processed, Y_test_processed


# ----------------------------------------------------


def best_solution(solution: List[int]):
    selected_count = len(solution)
    print(f"\n--- Best Solution Found ---")
    print(f"Best subset identifies {selected_count} samples (fixed size) from the training pool.")

    with open(ga_training_choices_file_name, mode="r") as ga_training_file:
        training_list = json.loads(ga_training_file.read())

    training_array = np.array(training_list, dtype=object)

    data = training_array[solution].tolist()

    with open(ga_output_file_name, mode="w") as ga_output_file:
        json.dump(data, ga_output_file, indent=2)

    with open(ga_test_file_name, mode="r") as ga_test_file:
        data += json.loads(ga_test_file.read())

    with open(ga_output_file_combined_name, mode="w") as ga_output_file_combined:
        json.dump(data, ga_output_file_combined, indent=2)


generate_files()

X_pool, Y_pool, num_classes, label_encoder, model_prep = get_training()
X_test, Y_test = get_test(model_prep, label_encoder, num_classes)

def fitness_func(ga_instance, solution: List[int], solution_idx) -> float:
    """Evaluates the fitness of a subset of training data using the selected model."""
    nums = [234, 7383903, 134512449, 8475, 13453379]
    accs = []
    for num in nums:
        set_random_seed(num)
        enable_op_determinism()

        new_x_train = X_pool[solution]
        new_y_train = Y_pool[solution]

        if new_x_train.shape[0] < 2:
            return 0.0

        if MODEL_CHOICE == 'NN':
            new_x_train_split, x_val, new_y_train_split, y_val = train_test_split(
                new_x_train, new_y_train, test_size=0.2, random_state=num
            )

            model = Sequential()
            model.add(Embedding(input_dim=TextClassifier.num_words, output_dim=TextClassifier.embedding_dim,
                                input_length=TextClassifier.max_sequence_length))
            model.add(GlobalAveragePooling1D())
            model.add(Dense(units=num_classes, activation='softmax'))

            model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

            early_stopping_callback = EarlyStopping(
                monitor='val_loss', patience=5, mode='min', restore_best_weights=True, min_delta=0.001
            )

            model.fit(new_x_train_split, new_y_train_split, epochs=20, batch_size=32,
                      validation_data=(x_val, y_val), callbacks=[early_stopping_callback], verbose=0)

            loss, accuracy = model.evaluate(X_test, Y_test, verbose=0)
            accs.append(accuracy)

        else:
            labels_1d = np.argmax(new_y_train, axis=1)

            new_x_train_split, x_val, new_y_train_split, y_val = train_test_split(
                new_x_train, labels_1d, test_size=0.2, random_state=num
            )

            model = LogisticRegression(solver='liblinear', random_state=num, max_iter=100, multi_class='ovr')
            model.fit(new_x_train_split, new_y_train_split)

            Y_test_1d = np.argmax(Y_test, axis=1)
            accuracy = model.score(X_test, Y_test_1d)
            accs.append(accuracy)

    return sum(accs)/len(nums)


# ----------------------------------------------------

def on_generation_callback(ga_instance):
    if ga_instance.generations_completed > 0:
        current_best_fitness = ga_instance.best_solution()[1]
        print(f"\n--- Generation {ga_instance.generations_completed} ENDED ---")
        print(f"  Best Fitness (Overall): {current_best_fitness:.6f}")
        print("-" * 100)

    if ga_instance.generations_completed < ga_instance.num_generations:
        print(f"\n--- Generation {ga_instance.generations_completed + 1} STARTING ({MODEL_CHOICE} Model) ---")


def run():
    if not os.path.exists(ga_balanced_individual_file_name):
        raise FileNotFoundError("Balanced individual file not found. Run generate_files() first.")

    balanced_individual = []
    with open(ga_balanced_individual_file_name, mode="r") as ga_balanced_individual_file:
        balanced_individual = json.loads(ga_balanced_individual_file.read())

    num_genes = len(balanced_individual)

    init_range_high = X_pool.shape[0] - 1
    pop_size = 150
    num_generations = 150
    num_parents_mating = int(pop_size * 0.2)
    init_range_low = 0
    parent_selection_type = "sss"
    keep_parents = 1
    crossover_type = "scattered"
    mutation_type = "random"
    mutation_percent_genes = 20

    initial_population = []

    for _ in range(pop_size):
        initial_population.append([ gene if random.uniform(0,1) > 0.5 else random.randint(init_range_low, init_range_high) for gene in balanced_individual])

    initial_population.append(balanced_individual)

    ga_instance = pygad.GA(num_generations=num_generations,
                           num_parents_mating=num_parents_mating,
                           initial_population=initial_population,
                           fitness_func=fitness_func,
                           num_genes=num_genes,
                           init_range_low=init_range_low,
                           init_range_high=init_range_high,
                           gene_type=int,
                           parent_selection_type=parent_selection_type,
                           keep_parents=keep_parents,
                           crossover_type=crossover_type,
                           mutation_type=mutation_type,
                           mutation_percent_genes=mutation_percent_genes,
                           on_generation=on_generation_callback)

    print(f"Starting Genetic Algorithm with {num_genes} genes (fixed subset size) using the {MODEL_CHOICE} model.")

    ga_instance.run()

    solution, solution_fitness, solution_idx = ga_instance.best_solution()

    best_solution(solution)

    print(f"Final best solution fitness (Test Accuracy): {solution_fitness}")


if __name__ == "__main__":
    run()