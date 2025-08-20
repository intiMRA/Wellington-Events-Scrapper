import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from keras.preprocessing.text import Tokenizer
from keras.utils import pad_sequences, to_categorical
import json
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, Conv1D, GlobalMaxPooling1D, Dense, MaxPooling1D
from keras.callbacks import EarlyStopping
import nlpaug.augmenter.word as naw
import nlpaug.augmenter.char as nac

training_data_file_name = "training_data.json"
ai_data_file_name = "ai_generates.json"
def get_data(file_name: str, max_sequence_length: int, num_words):
    texts = []
    labels = []
    with open(file_name, mode="r") as f:
        dictionary = json.loads(f.read())
        for value in dictionary:
            description = value["description"]
            label = value["label"]
            texts.append(description)
            labels.append(label)

            # aug = naw.synonym.SynonymAug(aug_src="wordnet")
            # augmented_text = aug.augment(description)
            # texts.append(augmented_text)
            # labels.append(label)

            # aug = nac.RandomCharAug(action="insert")
            # augmented_text = aug.augment(description)
            # texts.append(augmented_text)
            # labels.append(label)

            # aug = nac.RandomCharAug(action="delete")
            # augmented_text = aug.augment(description)
            # texts.append(augmented_text)
            # labels.append(label)
            #
            # aug = nac.RandomCharAug(action="substitute")
            # augmented_text = aug.augment(description)
            # texts.append(augmented_text)
            # labels.append(label)

        tokenizer = Tokenizer(num_words=num_words, oov_token="<unk>")
        tokenizer.fit_on_texts(texts)
        sequences = tokenizer.texts_to_sequences(texts)

        padded_sequences = pad_sequences(sequences, maxlen=max_sequence_length, padding='post')

        label_encoder = LabelEncoder()
        encoded_labels = label_encoder.fit_transform(labels)

        num_classes = len(np.unique(encoded_labels))

        one_hot_labels = to_categorical(encoded_labels, num_classes=num_classes)

        X_train, X_test, y_train, y_test = train_test_split(padded_sequences, one_hot_labels, test_size=0.2,
                                                                random_state=42)
        return X_train, X_test, y_train, y_test, num_classes
max_sequence_length = 100
num_words = 2000
X_train, X_test, y_train, y_test, num_classes = get_data(training_data_file_name, max_sequence_length, num_words)

X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=0.1, random_state=42)

X_train_ai, X_test_ai, y_train_ai, y_test_ai, num_classes_ai = get_data(ai_data_file_name, max_sequence_length, num_words)
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
# model.add(Conv1D(filters=256, kernel_size=5, activation='relu'))
# model.add(MaxPooling1D(pool_size=2))
model.add(Conv1D(filters=128, kernel_size=5, activation='relu'))
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
    batch_size=32,
    validation_data=(X_val, y_val)
)

loss, accuracy = model.evaluate(X_test, y_test)
print(f"Test Loss: {loss:.4f}, Test Accuracy: {accuracy:.4f}")