from pathlib import Path
import re

from expenses.services.category_engine import (
    CategoryDecision,
    choose_best_decision,
    normalize_text,
    predict_by_keywords,
)

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
        import joblib
        _model = joblib.load(MODEL_PATH)
    return _model


def _preprocess_text(text: str) -> str:
    text = normalize_text(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _predict_by_ml(text: str) -> tuple[str, float]:
    model = _load_model()
    text_proc = _preprocess_text(text)

    if hasattr(model, 'named_steps') and 'clf' in model.named_steps and hasattr(model.named_steps['clf'], 'predict_proba'):
        probs = model.predict_proba([text_proc])[0]
        classes = model.classes_
        best_idx = probs.argmax()
        return classes[best_idx], float(probs[best_idx])

    pred = model.predict([text_proc])[0]
    return pred, 1.0


def predict_category_detailed(text: str) -> CategoryDecision:
    """Return a category decision with source and explanation.

    The keyword layer is used first because it is deterministic and covers the
    basic cases users usually test manually: кава, торт, сукня, таксі, аптека.
    The ML model remains an optional fallback for less obvious texts.
    """
    keyword_decision = predict_by_keywords(text)

    if keyword_decision.category != 'other':
        return keyword_decision

    try:
        ml_category, ml_confidence = _predict_by_ml(text)
    except Exception:
        ml_category, ml_confidence = 'other', 0.0

    return choose_best_decision(keyword_decision, ml_category, ml_confidence)


def predict_category(text: str) -> tuple[str, float]:
    decision = predict_category_detailed(text)
    return decision.category, decision.confidence
