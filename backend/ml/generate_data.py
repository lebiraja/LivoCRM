"""Generate synthetic CRM data for training the lead-scoring model."""

import random
import pandas as pd

random.seed(42)
ROWS = 2000


def generate():
    records = []
    for _ in range(ROWS):
        has_company = random.choice([0, 1])
        has_phone = random.choice([0, 1])
        has_email = random.choice([0, 1])
        tag_count = random.randint(0, 5)
        notes_length = random.randint(0, 500)
        activity_count = random.randint(0, 20)
        days_since_last_activity = random.randint(0, 90)

        # Simple heuristic for labels
        score = (
            has_company * 15
            + has_phone * 10
            + has_email * 10
            + tag_count * 5
            + min(notes_length / 50, 10)
            + activity_count * 3
            - days_since_last_activity * 0.5
        )
        if score > 40:
            label = "hot"
        elif score > 20:
            label = "warm"
        else:
            label = "cold"

        records.append({
            "has_company": has_company,
            "has_phone": has_phone,
            "has_email": has_email,
            "tag_count": tag_count,
            "notes_length": notes_length,
            "activity_count": activity_count,
            "days_since_last_activity": days_since_last_activity,
            "label": label,
        })

    df = pd.DataFrame(records)
    df.to_csv("ml/training_data.csv", index=False)
    print(f"✓ Generated {ROWS} rows → ml/training_data.csv")
    print(df["label"].value_counts())


if __name__ == "__main__":
    generate()
