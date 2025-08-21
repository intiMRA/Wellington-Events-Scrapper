import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense, MaxPooling1D
from keras.callbacks import EarlyStopping

training_data_file_name = "training_data.json"
ai_data_file_name = "ai_generates.json"
def get_data(file_name: str, max_sequence_length: int, tokenizer, lable_encoder):
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

        num_classes = len(np.unique(encoded_labels))

        one_hot_labels = to_categorical(encoded_labels, num_classes=num_classes)

        X_train, X_test, y_train, y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.2,
                                                                random_state=42)
        return X_train, X_test, y_train, y_test, num_classes

max_sequence_length = 1500
num_words = 2000
tokenizer = Tokenizer(num_words=num_words, oov_token="<unk>")
label_encoder = LabelEncoder()
X_train, X_test, y_train, y_test, num_classes = get_data(training_data_file_name, max_sequence_length, tokenizer, label_encoder)

X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.1, random_state=42)

X_train_ai, X_test_ai, y_train_ai, y_test_ai, num_classes_ai = get_data(ai_data_file_name, max_sequence_length, tokenizer, label_encoder)
for v in X_train_ai:
    np.append(X_train, v)

for v in y_train_ai:
    np.append(y_train, v)

for v in X_test_ai:
    np.append(X_test, v)

for v in y_test_ai:
    np.append(y_test, v)

embedding_dim = 100

model = Sequential()
model.add(Embedding(input_dim=num_words, output_dim=embedding_dim, input_length=max_sequence_length))
model.add(Conv1D(filters=512, kernel_size=1, activation='relu'))
model.add(GlobalMaxPooling1D())
model.add(Dense(units=64, activation='relu'))
model.add(Dense(units=num_classes, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

early_stopping_callback = EarlyStopping(
    monitor='val_loss',
    patience=15,
    mode='min',
    restore_best_weights=True,
    min_delta=0.0001,
    start_from_epoch=30
)

model.fit(
    X_train, y_train,
    epochs=100,
    batch_size=32,
    validation_data=(X_val, y_val),
    callbacks=[early_stopping_callback],
    verbose=1
)

loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")

# {'score': 0.6477272510528564, 'max_sequence_length': 1500, 'num_words': 2000}

def predict_from_file(model, file_name, tokenizer, label_encoder, max_sequence_length):
    """
    Predicts the labels for descriptions in a given file.
    """
    with open(file_name, mode="r") as f:
        data = json.loads(f.read())
        texts_to_predict = [item["description"] for item in data]

    # Preprocess the new texts using the same tokenizer
    sequences = tokenizer.texts_to_sequences(texts_to_predict)
    padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

    # Make predictions
    predictions = model.predict(padded_sequences)

    # Convert predictions back to labels
    predicted_labels = label_encoder.inverse_transform(np.argmax(predictions, axis=1))

    # Display results
    print("\n--- Predictions for unclassified data ---")
    for i, text in enumerate(texts_to_predict):
        print(f"Text: '{text}'")
        print(f"Predicted Label: {predicted_labels[i]}")
        print("-" * 20)

    return predicted_labels


# Make predictions on the unclassified file
predicted_labels = predict_from_file(
    model,
    "unclassified_data.json",
    tokenizer,
    label_encoder,
    max_sequence_length
)