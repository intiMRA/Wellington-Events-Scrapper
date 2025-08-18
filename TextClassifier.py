from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report
from sklearn.preprocessing import MultiLabelBinarizer
from skmultilearn.problem_transform import BinaryRelevance

# Sample data
texts = ["This is a positive review.", "Bad movie, not recommended.", "Great experience, loved it!", "Terrible service, very disappointed."]
labels = [["positive", "awesome"], ["negative", "bad"], ["positive", "great"], ["negative"]]

mlb = MultiLabelBinarizer()
binary_labels = mlb.fit_transform(labels)
print("Binary Labels (y):")
print(binary_labels)
print("Classes:", mlb.classes_)
print("-" * 30)


vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(texts)

X_train, X_test, y_train, y_test = train_test_split(X, binary_labels, test_size=0.2, random_state=42)

model = BinaryRelevance(classifier=MultinomialNB())


model.fit(X_train, y_train)


y_pred = model.predict(X_test)
print("Classification Report:")
print(classification_report(y_test, y_pred, target_names=mlb.classes_))