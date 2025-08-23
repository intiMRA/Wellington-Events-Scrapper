import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense
from keras.callbacks import EarlyStopping

training_data_file_name = "training_data.json"
ai_data_file_name = "ai_generates.json"
max_sequence_length = 1500
num_words = 2000
embedding_dim = 400
tokenizer = Tokenizer(num_words=num_words, oov_token="<unk>")
label_encoder = LabelEncoder()

def get_data(file_name: str):
    texts = []
    labels = []
    with open(file_name, mode="r") as f:
        dictionary = json.loads(f.read())
        for value in dictionary:
            description = value["description"]
            label = value["label"]
            texts.append(description)
            labels.append(label)

        tokenizer.fit_on_texts(texts)
        sequences = tokenizer.texts_to_sequences(texts)

        padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

        encoded_labels = label_encoder.fit_transform(labels)

        number_of_classes = len(np.unique(encoded_labels))

        one_hot_labels = to_categorical(encoded_labels, num_classes=number_of_classes)

        x_train, x_test, y_train, y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.2,
                                                                random_state=42)
        return x_train, x_test, y_train, y_test, number_of_classes
def predict_from_file(classification_model, file_name):
    """
    Predicts the labels for descriptions in a given file.
    """
    with open(file_name, mode="r") as f:
        data = json.loads(f.read())
        texts_to_predict = [item["description"] for item in data]
        given_labels = []
        for item in data:
            if "new" in item.keys():
                given_labels.append(item["label"] + "\nnew")
            else:
                given_labels.append(item["label"])

    sequences = tokenizer.texts_to_sequences(texts_to_predict)
    padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

    predictions = classification_model.predict(padded_sequences)

    predicted_labels = []
    for predictions_array in predictions:
        indecies = np.argpartition(predictions_array, -2)[-2:]
        indecies = indecies[np.argsort(-predictions_array[indecies])]
        if indecies[0] < 0.18:
            indecies = []
        elif predictions_array[indecies[1]] < predictions_array[indecies[0]] * 0.5:
            indecies = [indecies[0]]

        if len(indecies) == 0:
            predicted_labels.append([{"label": None, "confidence": f"Confidence 0%"}])
        else:
            label_dict = [{"label": label, "confidence": f"Confidence: {predictions_array[index] * 100:.2f}%"} for label, index in zip(label_encoder.inverse_transform(indecies), indecies)]
            predicted_labels.append(label_dict)

    print("\n--- Predictions for unclassified data ---")
    for i, text in enumerate(texts_to_predict):
        print(f"Text: '{text}'")
        print(f"Predicted Labels: {predicted_labels[i]}")
        print(f"given Label: {given_labels[i]}")
        print("-" * 20)
    return predicted_labels

X_train, X_test, Y_train, Y_test, num_classes = get_data(training_data_file_name)

X_train, X_val, Y_train, Y_val = train_test_split(X_train, Y_train, test_size=0.2, random_state=42)

X_train_ai, X_test_ai, Y_train_ai, Y_test_ai, num_classes_ai = get_data(ai_data_file_name)
for v in X_train_ai:
    np.append(X_train, v)

for v in Y_train_ai:
    np.append(Y_train, v)

for v in X_test_ai:
    np.append(X_val, v)

for v in Y_test_ai:
    np.append(Y_val, v)


model = Sequential()
model.add(Embedding(input_dim=num_words, output_dim=embedding_dim, input_length=max_sequence_length))
model.add(Conv1D(filters=512, kernel_size=3, activation='relu'))
model.add(GlobalMaxPooling1D())
model.add(Dense(units=64, activation='relu'))
model.add(Dense(units=num_classes, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

early_stopping_callback = EarlyStopping(
    monitor='val_loss',
    patience=10,
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

labels_out = predict_from_file(
    model,
    "unclassified_data.json"
)
model.save('trained_model')