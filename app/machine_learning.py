"""Local TF-IDF classifier trained on the synthetic tickets dataset."""
import argparse
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.rules import build_result, detect_security_priority
from app.schemas import AnalysisResult, Category, Mode

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "tickets.csv"


def train_model(csv_path: Path = DATA_FILE) -> tuple[Pipeline, str]:
    data = pd.read_csv(csv_path)
    if not {"message", "category"}.issubset(data.columns):
        raise ValueError("El CSV debe contener message y category.")
    if data[["message", "category"]].isna().any().any():
        raise ValueError("El CSV contiene campos vacíos.")
    if not data["message"].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
        raise ValueError("Cada mensaje debe ser texto con contenido.")
    if set(data["category"]) != set(Category):
        raise ValueError("El CSV debe incluir las cuatro categorías válidas.")
    normalized = data["message"].str.strip().str.casefold()
    if normalized.duplicated().any():
        raise ValueError("El CSV contiene mensajes duplicados.")
    if data.groupby("category").size().min() < 5:
        raise ValueError("Se requieren al menos cinco ejemplos por categoría.")
    X_train, X_test, y_train, y_test = train_test_split(
        data["message"], data["category"], test_size=0.2,
        stratify=data["category"], random_state=42,
    )
    model = Pipeline([
        ("vectorizer", TfidfVectorizer(ngram_range=(1, 2))),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(X_train, y_train)
    report = classification_report(y_test, model.predict(X_test), zero_division=0)
    return model, report


@lru_cache(maxsize=1)
def get_model() -> Pipeline:
    model, _ = train_model()
    return model


def analyze_machine_learning(message: str) -> AnalysisResult:
    if not message.strip():
        raise ValueError("message must not be blank")
    category = Category(get_model().predict([message])[0])
    if detect_security_priority(message) is not None:
        category = Category.SECURITY
    return build_result(message, category, Mode.MACHINE_LEARNING)


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena y evalúa el clasificador local.")
    parser.add_argument("--csv", type=Path, default=DATA_FILE)
    args = parser.parse_args()
    model, report = train_model(args.csv)
    print(report)
    print(model.predict(["Alguien entró a mi cuenta sin autorización"]))


if __name__ == "__main__":
    main()
