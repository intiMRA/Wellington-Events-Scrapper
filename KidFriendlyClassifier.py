import numpy as np
from keras.preprocessing.text import tokenizer_from_json
from sklearn.model_selection import train_test_split
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical,set_random_seed
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense
from tensorflow.config.experimental import enable_op_determinism
from keras.callbacks import EarlyStopping
from tensorflow.keras.models import load_model

true = True
false = False

training_data_file_name = "training_data_kid_friendly.json"
unclassified_data_file_name = "unclassified_data.json"

should_train = true

max_sequence_length = 1500
num_words = 2000
embedding_dim = 400
tokenizer = Tokenizer(num_words=num_words, oov_token="<unk>")
all_texts = []

with open(training_data_file_name, mode="r") as f:
    data = json.loads(f.read())
    all_texts.extend([item["description"] for item in data if not item["skip"]])

tokenizer.fit_on_texts(all_texts)

def get_data(file_name: str):
    texts = []
    labels = []
    with open(file_name, mode="r") as f:
        dictionary = json.loads(f.read())
        for value in dictionary:
            if value["skip"]:
                continue
            description = value["description"]
            label = value["kid_friendly"]
            texts.append(description)
            labels.append(label)

        sequences = tokenizer.texts_to_sequences(texts)

        padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

        encoded_labels = [1 if label else 0 for label in labels]

        number_of_classes = len(np.unique(encoded_labels))

        one_hot_labels = to_categorical(encoded_labels, num_classes=number_of_classes)

        x_train, x_test, y_train, y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.2,
                                                                random_state=42)
        return x_train, x_test, y_train, y_test, number_of_classes
def predict_from_file(file_name):
    """
    Predicts the labels for descriptions in a given file.
    """
    classification_model, loaded_tokenizer = load_models_from_file()
    with open(file_name, mode="r") as f:
        data = json.loads(f.read())
        texts_to_predict = []
        given_labels = []
        for item in data:
            if item["skip"]:
                continue
            texts_to_predict.append(item["description"])
            given_labels.append(str(item["kid_friendly"]))

    sequences = loaded_tokenizer.texts_to_sequences(texts_to_predict)
    padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

    predictions = classification_model.predict(padded_sequences)

    predicted_labels = []
    for predictions_array in predictions:
        indecies = np.argpartition(predictions_array, -1)[-1:]
        indecies = indecies[np.argsort(-predictions_array[indecies])]

        if len(indecies) == 0:
            predicted_labels.append([{"label": None, "confidence": f"Confidence 0%"}])
        else:
            label_dict = [{"label": label, "confidence": f"Confidence: {predictions_array[index] * 100:.2f}%"} for label, index in zip([index == 1 for index in  indecies], indecies)]
            predicted_labels.append(label_dict)

    with open("kid_friendly_predictions_log.txt", mode="w") as f:
        correct_labels = 0
        for i, text in enumerate(texts_to_predict):
            f.write(f"Text: {text}\n")
            f.write(f"Predicted Labels: {predicted_labels[i]}\n")
            f.write(f"given Label: {given_labels[i]}\n")
            found = False
            for item in predicted_labels[i]:
                if given_labels[i] == str(item["kid_friendly"]):
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
    classification_model = load_model("trained_model_kid_friendly")
    with open('tokenizer_config_kid_friendly.json', 'r', encoding='utf-8') as f:
        tokenizer_config_string = json.loads(f.read())
    loaded_tokenizer = tokenizer_from_json(tokenizer_config_string)

    return classification_model, loaded_tokenizer

if should_train:
    set_random_seed(13453376)
    enable_op_determinism()
    X_train, X_test, Y_train, Y_test, num_classes = get_data(training_data_file_name)

    X_train, X_val, Y_train, Y_val = train_test_split(X_train, Y_train, test_size=0.2, random_state=42)

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
        epochs=100,
        batch_size=32,
        validation_data=(X_val, Y_val),
        callbacks=[early_stopping_callback],
        verbose=1
    )

    loss, accuracy = model.evaluate(X_test, Y_test)
    print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")

    model.save('trained_model_kid_friendly')
    tokenizer_json = tokenizer.to_json()
    with open('tokenizer_config_kid_friendly.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(tokenizer_json, ensure_ascii=False))

labels_out = predict_from_file(
    training_data_file_name
)