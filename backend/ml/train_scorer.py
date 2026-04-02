"""Train a RandomForest lead-scoring model and persist it as model.pkl."""

import os

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

DATA = os.path.join(os.path.dirname(__file__), "training_data.csv")
MODEL = os.path.join(os.path.dirname(__file__), "model.pkl")
FEATURES = [
    "has_company",
    "has_phone",
    "has_email",
    "tag_count",
    "notes_length",
    "activity_count",
    "days_since_last_activity",
]


def train():
    df = pd.read_csv(DATA)
    X = df[FEATURES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    preds = clf.predict(X_test)
    print(classification_report(y_test, preds))

    joblib.dump(clf, MODEL)
    print(f"✓ Model saved → {MODEL}")


if __name__ == "__main__":
    train()
