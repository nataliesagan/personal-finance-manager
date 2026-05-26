from pathlib import Path
import joblib
import re

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'models' / 'expense_classifier.joblib'

_model = None


def _load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f'Model file not found: {MODEL_PATH}. '
                f'Please run training script: python -m expenses.ml.train_classifier'
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def _preprocess_text(text: str) -> str:
    text = str(text).lower()
    text = re.sub(r'[^a-zа-яіїєґ0-9\s]+', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def predict_category(text: str) -> tuple[str, float]:
    model = _load_model()
    text_proc = _preprocess_text(text)
    probs = None

    if hasattr(model.named_steps['clf'], "predict_proba"):
        probs = model.predict_proba([text_proc])[0]
        classes = model.classes_
        best_idx = probs.argmax()
        return classes[best_idx], float(probs[best_idx])
    else:
        pred = model.predict([text_proc])[0]
        return pred, 1.0
