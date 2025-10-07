import numpy as np
from keras.preprocessing.text import tokenizer_from_json
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical,set_random_seed
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense
from tensorflow.config.experimental import enable_op_determinism
from keras.callbacks import EarlyStopping
from tensorflow.keras.models import load_model
import joblib

max_sequence_length = 1500
num_words = 2000
embedding_dim = 400
def train_from_manual_training_files(load_ai):
    use_ga = True
    training_data_file_name = "ga_output_combined.json" if use_ga else "training_data.json"
    ai_data_file_name = "ai_generates.json"

    all_texts = []
    with open(training_data_file_name, mode="r") as f:
        data = json.loads(f.read())
        all_texts.extend([item["description"] for item in data if not item["skip"]])
    if load_ai:
        with open(ai_data_file_name, mode="r") as f:
            data = json.loads(f.read())
            all_texts.extend([item["description"] for item in data if not item["skip"]])

    tokenizer = Tokenizer(num_words=num_words, oov_token="<unk>")
    tokenizer.fit_on_texts(all_texts)
    label_encoder = LabelEncoder()
    set_random_seed(13453379)
    enable_op_determinism()
    X_train, X_test, Y_train, Y_test, num_classes = get_data(training_data_file_name, label_encoder, tokenizer)

    X_train, X_val, Y_train, Y_val = train_test_split(X_train, Y_train, test_size=0.2, random_state=42)

    if load_ai:
        X_train_ai, X_test_ai, Y_train_ai, Y_test_ai, num_classes_ai = get_data(ai_data_file_name, label_encoder, tokenizer)
        for v in X_train_ai:
            np.append(X_train, v)

        for v in Y_train_ai:
            np.append(Y_train, v)

        for v in X_test_ai:
            np.append(X_train, v)

        for v in Y_test_ai:
            np.append(Y_train, v)
    train(num_classes, X_train, Y_train, X_val, Y_val, X_test, Y_test, label_encoder, tokenizer)

def train(num_classes, X_train, Y_train, X_val, Y_val, X_test, Y_test, label_encoder=None, tokenizer=None, epochs=100, verbose=1) -> float:
    model = Sequential()
    model.add(Embedding(input_dim=num_words, output_dim=embedding_dim, input_length=max_sequence_length))
    model.add(Conv1D(filters=512, kernel_size=3, activation='relu'))
    model.add(GlobalMaxPooling1D())
    model.add(Dense(units=64, activation='relu'))
    model.add(Dense(units=num_classes, activation='softmax'))

    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    early_stopping_callback = EarlyStopping(
        monitor='val_loss',
        patience=5,
        mode='min',
        restore_best_weights=True,
        min_delta=0.0001
    )

    model.fit(
        X_train, Y_train,
        epochs=epochs,
        batch_size=32,
        validation_data=(X_val, Y_val),
        callbacks=[early_stopping_callback],
        verbose=verbose
    )

    loss, accuracy = model.evaluate(X_test, Y_test)
    print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")
    if not label_encoder and not tokenizer:
        return accuracy
    model.save('trained_model')
    tokenizer_json = tokenizer.to_json()
    with open('tokenizer_config.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(tokenizer_json, ensure_ascii=False))
    joblib.dump(label_encoder, 'label_encoder.joblib')
    return accuracy

def get_data(file_name: str, label_encoder, tokenizer):
    texts = []
    labels = []
    with open(file_name, mode="r") as f:
        dictionary = json.loads(f.read())
        for value in dictionary:
            if value["skip"]:
                continue
            description = value["description"]
            label = value["label"]
            texts.append(description)
            labels.append(label)

        sequences = tokenizer.texts_to_sequences(texts)

        padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

        encoded_labels = label_encoder.fit_transform(labels)

        number_of_classes = len(np.unique(encoded_labels))

        one_hot_labels = to_categorical(encoded_labels, num_classes=number_of_classes)

        x_train, x_test, y_train, y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.2,
                                                                random_state=42)
        return x_train, x_test, y_train, y_test, number_of_classes
def predict_from_file(file_name):
    """
    Predicts the labels for descriptions in a given file.
    """
    classification_model, loaded_tokenizer, loaded_label_encoder = load_models_from_file()
    with open(file_name, mode="r") as f:
        data = json.loads(f.read())
        texts_to_predict = []
        given_labels = []
        for item in data:
            if item["skip"]:
                continue
            texts_to_predict.append(item["description"])
            if "new" in item.keys():
                given_labels.append(item["label"] + "\nnew")
            else:
                given_labels.append(item["label"])

    sequences = loaded_tokenizer.texts_to_sequences(texts_to_predict)
    padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

    predictions = classification_model.predict(padded_sequences)

    predicted_labels = []
    for predictions_array in predictions:
        indecies = np.argpartition(predictions_array, -2)[-2:]
        indecies = indecies[np.argsort(-predictions_array[indecies])]

        if predictions_array[indecies[1]] < predictions_array[indecies[0]] * 0.2:
            indecies = [indecies[0]]

        if len(indecies) == 0:
            predicted_labels.append([{"label": None, "confidence": f"Confidence 0%"}])
        else:
            label_dict = [{"label": label, "confidence": f"Confidence: {predictions_array[index] * 100:.2f}%"} for label, index in zip(loaded_label_encoder.inverse_transform(indecies), indecies)]
            predicted_labels.append(label_dict)

    with open("predictions_log.txt", mode="w") as f:
        correct_labels = 0
        for i, text in enumerate(texts_to_predict):
            f.write(f"Text: {text}\n")
            f.write(f"Predicted Labels: {predicted_labels[i]}\n")
            f.write(f"given Label: {given_labels[i]}\n")
            found = False
            for item in predicted_labels[i]:
                if given_labels[i] == item["label"]:
                    found = True
                    break
            f.write(f"prediction correct: {found}\n")
            if found:
                correct_labels+=1
            f.write("-" * 100)
            f.write("\n")
            f.write("\n")
        f.write(f"correct: {correct_labels} of {len(texts_to_predict)} {(correct_labels/len(texts_to_predict)) * 100}%\n")
    return predicted_labels

def load_models_from_file():
    classification_model = load_model("trained_model")
    with open('tokenizer_config.json', 'r', encoding='utf-8') as f:
        tokenizer_config_string = json.loads(f.read())
    loaded_tokenizer = tokenizer_from_json(tokenizer_config_string)

    loaded_label_encoder = joblib.load('label_encoder.joblib')
    return classification_model, loaded_tokenizer, loaded_label_encoder

use_ai_data = False
should_train = True

if should_train:
    train_from_manual_training_files(use_ai_data)

training_data_file = "training_data.json"
unclassified_data_file = "unclassified_data.json"

labels_out = predict_from_file(
    training_data_file
)