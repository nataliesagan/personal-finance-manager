import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report
import joblib
import re


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / 'data' / 'expenses_train.csv'
MODEL_DIR = BASE_DIR / 'models'
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / 'expense_classifier.joblib'


def preprocess_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'[^a-zа-яіїєґ0-9\s]+', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def load_data():
    df = pd.read_csv(DATA_PATH)
    df['text'] = df['text'].apply(preprocess_text)
    return df['text'], df['category']


def select_best_model(X, y):
    models = {
        'logreg': LogisticRegression(max_iter=1000),
        'nb': MultinomialNB(),
        'svm': LinearSVC()
    }

    value_counts = pd.Series(y).value_counts()
    min_per_class = int(value_counts.min())
    cv = min(5, min_per_class)

    best_name = None
    best_score = -1.0
    best_pipeline = None

    if cv < 2:
        print(
            f"Too few samples per class for cross-validation (min_per_class={min_per_class}). "
            f"Using LogisticRegression without CV."
        )
        best_pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('clf', LogisticRegression(max_iter=1000)),
        ])
        return best_pipeline

    print(f'Using {cv}-fold cross-validation (min samples per class = {min_per_class})')

    for name, clf in models.items():
        pipe = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2)
            )),
            ('clf', clf),
        ])
        scores = cross_val_score(pipe, X, y, cv=cv, scoring='f1_macro')
        mean_score = scores.mean()
        print(f'{name}: F1-macro={mean_score:.4f} (+/- {scores.std():.4f})')

        if mean_score > best_score:
            best_score = mean_score
            best_name = name
            best_pipeline = pipe

    print(f'Best model: {best_name} with F1-macro={best_score:.4f}')
    return best_pipeline


def train():
    X, y = load_data()

    y_series = pd.Series(y)
    min_per_class = int(y_series.value_counts().min())

    if min_per_class < 2:
        print(
            f"Too few samples in at least one class (min_per_class={min_per_class}). "
            f"Training on all data without stratified train/test split."
        )

        best_pipeline = select_best_model(X, y)
        best_pipeline.fit(X, y)

        print("Skipping hold-out test metrics due to too few samples per class.")

        joblib.dump(best_pipeline, MODEL_PATH)
        print(f'Model saved to {MODEL_PATH}')
        return

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    best_pipeline = select_best_model(X_train, y_train)

    best_pipeline.fit(X_train, y_train)

    y_pred = best_pipeline.predict(X_test)
    print('Classification report on hold-out test:')
    print(classification_report(y_test, y_pred))

    joblib.dump(best_pipeline, MODEL_PATH)
    print(f'Model saved to {MODEL_PATH}')


if __name__ == '__main__':
    train()
