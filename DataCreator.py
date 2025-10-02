import TextClassifier
import random
import pygad
from typing import List, Dict, Tuple
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical,set_random_seed
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense, GlobalAveragePooling1D
from tensorflow.config.experimental import enable_op_determinism
from keras.callbacks import EarlyStopping
def load_data_initial_data() -> List[Dict]:
    data = []
    file_names = ["training_data.json", "unclassified_data.json", "ai_generates.json"]
    for file_name in file_names:
        try:
            with open(file_name, mode="r") as f:
                data.extend(json.loads(f.read()))
        except FileNotFoundError:
            print(f"Warning: File not found: {file_name}")
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {file_name}")
    return data

def filter_classified_data(all_data: List[Dict]) -> List[Dict]:
    return [
        value for value in all_data
        if not value.get("skip", False) and "label" in value
    ]
def get_training(classified_data: List[Dict]) -> Tuple[
    np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, LabelEncoder, Tokenizer]:

    descriptions = [value["description"] for value in classified_data]
    labels = [value["label"] for value in classified_data]

    tokenizer = Tokenizer(num_words=TextClassifier.num_words, oov_token="<unk>")
    tokenizer.fit_on_texts(descriptions)

    label_encoder = LabelEncoder()

    sequences = tokenizer.texts_to_sequences(descriptions)
    padded_sequences = pad_sequences(sequences, maxlen=TextClassifier.max_sequence_length, padding='post')

    encoded_labels = label_encoder.fit_transform(labels)
    num_classes = len(np.unique(encoded_labels))
    one_hot_labels = to_categorical(encoded_labels, num_classes=num_classes)

    X_pool, X_test, Y_pool, Y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.3, random_state=42)

    return X_pool, X_test, Y_pool, Y_test, num_classes, label_encoder, tokenizer


def best_solution(solution: List[int]):
    selected_count = sum(solution)
    total_count = len(solution)
    print(f"\n--- Best Solution Found ---")
    print(f"Best subset mask identifies {selected_count} samples out of {total_count} in the training pool.")
    # Add logic here to save the best solution mask if needed
    pass


initial_data_all = load_data_initial_data()
classified_data = filter_classified_data(initial_data_all)

X_pool, X_test, Y_pool, Y_test, num_classes, label_encoder, tokenizer = get_training(classified_data)

num_genes = len(X_pool)

def fitness_func(ga_instance, solution: List[int], solution_idx) -> float:
    """Evaluates the fitness of a subset of training data."""
    set_random_seed(13453379)
    enable_op_determinism()

    solution_mask = np.array(solution, dtype=bool)

    new_x_train = X_pool[solution_mask]
    new_y_train = Y_pool[solution_mask]

    if len(new_x_train) < 2:
        return 0.0

    new_x_train_split, x_val, new_y_train_split, y_val = train_test_split(
        new_x_train, new_y_train, test_size=0.2, random_state=42
    )

    # 3. Train and evaluate the model
    # TextClassifier.train should return a single score (e.g., accuracy)
    model = Sequential()
    model.add(Embedding(input_dim=TextClassifier.num_words, output_dim=TextClassifier.embedding_dim, input_length=TextClassifier.max_sequence_length))
    model.add(GlobalAveragePooling1D())
    model.add(Dense(units=64, activation='relu'))
    model.add(Dense(units=num_classes, activation='softmax'))

    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    early_stopping_callback = EarlyStopping(
        monitor='val_loss',
        patience=5,
        mode='min',
        restore_best_weights=True,
        min_delta=0.001
    )

    model.fit(
        new_x_train_split, new_y_train_split,
        epochs=30,
        batch_size=32,
        validation_data=(x_val, y_val),
        callbacks=[early_stopping_callback],
        verbose=0
    )

    loss, accuracy = model.evaluate(X_test, Y_test)

    return accuracy

num_generations = 20
num_parents_mating = 2
init_range_low = 0
init_range_high = 1
parent_selection_type = "sss"
keep_parents = 1
crossover_type = "scattered"
mutation_type = "random"
mutation_percent_genes = 20

initial_population = []
for _ in range(10):
    initial_population.append([random.randint(init_range_low, init_range_high) for _ in range(num_genes)])

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
                       mutation_percent_genes=mutation_percent_genes)


print(f"Starting Genetic Algorithm with {num_genes} genes (training pool size).")
ga_instance.run()

solution, solution_fitness, solution_idx = ga_instance.best_solution()

best_solution(solution)

print(f"Final best solution fitness (Test Accuracy): {solution_fitness}")