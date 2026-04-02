"""ML lead-scoring service — loads the trained model and runs inference."""

import os
import logging

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "model.pkl")
_model = None


def _load_model():
    global _model
    if _model is None:
        path = os.path.normpath(_MODEL_PATH)
        if os.path.exists(path):
            _model = joblib.load(path)
            logger.info("Lead-scoring model loaded from %s", path)
        else:
            logger.warning("No model found at %s — scoring will return defaults", path)
    return _model


def _engineer_features(contact: dict) -> pd.DataFrame:
    """Mirror the feature engineering used during training."""
    features = pd.DataFrame([{
        "has_company": 1 if contact.get("company") else 0,
        "has_phone": 1 if contact.get("phone") else 0,
        "has_email": 1 if contact.get("email") else 0,
        "tag_count": len(contact.get("tags", [])),
        "notes_length": len(contact.get("notes", "")),
        "activity_count": contact.get("activity_count", 0),
        "days_since_last_activity": contact.get("days_since_last_activity", 30),
    }])
    return features


def score_contact(contact: dict) -> dict:
    """Return a lead-score dict {score: int, label: str}."""
    model = _load_model()
    if model is None:
        return {"score": 0, "label": "unknown"}

    X = _engineer_features(contact)
    label = model.predict(X)[0]
    probas = model.predict_proba(X)[0]
    score = int(round(max(probas) * 100))

    return {"score": score, "label": str(label)}
