import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense, GlobalAvgPool1D
from keras.callbacks import EarlyStopping
# Sample data
texts = []
labels = []
with open("training_data.json", mode="r") as f:
    dictionary = json.loads(f.read())
    for value in dictionary:
        texts.append(value["description"])
        labels.append(value["label"])

num_words = 2000  # Number of words to keep
max_sequence_length = 100 # Max length of a sequence

tokenizer = Tokenizer(num_words=num_words, oov_token="<unk>")
tokenizer.fit_on_texts(texts)
sequences = tokenizer.texts_to_sequences(texts)

padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(labels)
num_classes = len(np.unique(encoded_labels))

one_hot_labels = to_categorical(encoded_labels, num_classes=num_classes)

X_train, X_test, y_train, y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.2, random_state=42)

X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.1, random_state=42)

embedding_dim = 100


model = Sequential()
model.add(Embedding(input_dim=num_words, output_dim=embedding_dim, input_length=max_sequence_length))
model.add(Conv1D(filters=256, kernel_size=5, activation='relu'))
model.add(GlobalMaxPooling1D())
model.add(Dense(units=64, activation='relu'))
model.add(Dense(units=num_classes, activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
model.summary()

early_stopping_callback = EarlyStopping(
    monitor='val_loss',
    patience=5,
    mode='min',
    restore_best_weights=True,
    min_delta=0.000001,
    start_from_epoch=30
)

model.fit(
    X_train, y_train,
    epochs=100,
    batch_size=2,
    validation_data=(X_val, y_val),
    callbacks=[early_stopping_callback]
)

loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")