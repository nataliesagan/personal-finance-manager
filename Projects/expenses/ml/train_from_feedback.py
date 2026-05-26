import os

import django
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

from .train_classifier import preprocess_text, select_best_model, MODEL_PATH, MODEL_DIR

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_manager.settings')
django.setup()

from expenses.models import Expense, CategoryFeedback  # noqa: E402


def build_dataset_from_db():
    rows = []

    for e in Expense.objects.all():
        rows.append({
            'text': e.description,
            'category': e.category,
        })

    for fb in CategoryFeedback.objects.select_related('expense'):
        rows.append({
            'text': fb.expense.description,
            'category': fb.corrected_category,
        })

    if not rows:
        print("No expenses or feedback found in DB. Nothing to retrain on.")
        empty = pd.Series([], dtype=str)
        return empty, empty

    df = pd.DataFrame(rows)
    df['text'] = df['text'].apply(preprocess_text)
    return df['text'], df['category']


def train_from_feedback():
    X, y = build_dataset_from_db()

    if len(X) < 10:
        print(f"Too few examples from DB (n={len(X)}), skipping retrain.")
        return

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    best_pipeline = select_best_model(X_train, y_train)
    best_pipeline.fit(X_train, y_train)

    y_pred = best_pipeline.predict(X_test)
    print('Classification report on feedback-based dataset:')
    print(classification_report(y_test, y_pred))

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(best_pipeline, MODEL_PATH)
    print(f'Updated model saved to {MODEL_PATH}')


if __name__ == '__main__':
    train_from_feedback()
