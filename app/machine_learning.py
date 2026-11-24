"""Local TF-IDF + LogisticRegression classifier for AI Support Engine V2."""
import argparse
import csv
from functools import lru_cache
import json
from pathlib import Path
import time
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.rules import build_result, classify_traditional, detect_security_priority
from app.schemas import AnalysisResult, Category, Mode

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT_DIR / "data" / "tickets.csv"
BENCHMARK_CASES_FILE = ROOT_DIR / "data" / "benchmark_cases.json"
REPORTS_DIR = ROOT_DIR / "reports"
LOW_CONFIDENCE_THRESHOLD = 0.45
CLASS_ORDER = [Category.ACCESS.value, Category.BUG.value, Category.FEATURE.value, Category.SECURITY.value]


def load_and_validate_dataset(csv_path: Path = DATA_FILE) -> pd.DataFrame:
    """Load and validate the tickets dataset, preventing duplicates and invalid labels."""
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
    if "split" in data.columns:
        splits = set(data["split"].astype(str).str.strip().str.lower())
        if splits != {"train", "test"}:
            raise ValueError("La columna split debe contener únicamente 'train' y 'test'.")
    return data


def split_dataset(data: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Use fixed train/test split when provided, otherwise stratified 80/20 split."""
    if "split" in data.columns:
        split_col = data["split"].astype(str).str.strip().str.lower()
        train_df = data[split_col == "train"]
        test_df = data[split_col == "test"]
        return train_df["message"], test_df["message"], train_df["category"], test_df["category"]
    return train_test_split(
        data["message"],
        data["category"],
        test_size=0.2,
        stratify=data["category"],
        random_state=42,
    )


def evaluate_model(csv_path: Path = DATA_FILE) -> tuple[Pipeline, dict[str, Any]]:
    """Train the TF-IDF + LogisticRegression pipeline strictly on train and evaluate on test."""
    data = load_and_validate_dataset(csv_path)
    X_train, X_test, y_train, y_test = split_dataset(data)

    model = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
    ])
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    report_text = classification_report(y_test, predictions, labels=CLASS_ORDER, zero_division=0)
    report_dict = classification_report(
        y_test, predictions, labels=CLASS_ORDER, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(y_test, predictions, labels=CLASS_ORDER)

    sec_idx = CLASS_ORDER.index(Category.SECURITY.value)
    sec_fn = int(sum(matrix[sec_idx]) - matrix[sec_idx][sec_idx])
    sec_fp = int(sum(matrix[row][sec_idx] for row in range(len(CLASS_ORDER))) - matrix[sec_idx][sec_idx])

    metrics = {
        "dataset_path": str(csv_path.name),
        "total_records": int(len(data)),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "classes": CLASS_ORDER,
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "security_recall": round(float(report_dict["SECURITY"]["recall"]), 4),
        "security_precision": round(float(report_dict["SECURITY"]["precision"]), 4),
        "security_false_negatives": sec_fn,
        "security_false_positives": sec_fp,
        "confusion_matrix": matrix.tolist(),
        "classification_report_text": report_text,
        "classification_report": report_dict,
    }
    return model, metrics


def train_model(csv_path: Path = DATA_FILE) -> tuple[Pipeline, str]:
    """Train and return the pipeline and formatted classification report."""
    model, metrics = evaluate_model(csv_path)
    return model, metrics["classification_report_text"]


@lru_cache(maxsize=1)
def get_model() -> Pipeline:
    model, _ = train_model()
    return model


def predict_with_confidence(message: str) -> tuple[Category, float]:
    """Predict category and approximate confidence score from predict_proba."""
    model = get_model()
    category = Category(model.predict([message])[0])
    confidence = float(model.predict_proba([message]).max())
    return category, round(confidence, 4)


def analyze_machine_learning(
    message: str,
    confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> AnalysisResult:
    """Classify a ticket locally with ML, applying security guardrails and low-confidence review."""
    text = message.strip()
    if not text:
        raise ValueError("message must not be blank")

    category, confidence = predict_with_confidence(text)
    if detect_security_priority(text) is not None:
        category = Category.SECURITY

    result = build_result(text, category, Mode.MACHINE_LEARNING)
    if confidence < confidence_threshold and not result.requires_human_review:
        result = result.model_copy(update={"requires_human_review": True})
    return result


def _percentile_95(values_ms: list[float]) -> float:
    if not values_ms:
        return 0.0
    ordered = sorted(values_ms)
    idx = min(len(ordered) - 1, max(0, int(round(0.95 * len(ordered))) - 1))
    return round(ordered[idx], 2)


def build_three_engine_comparison() -> dict[str, Any]:
    """Compare traditional, machine_learning, and saved generative results on benchmark_cases.json."""
    cases = json.loads(BENCHMARK_CASES_FILE.read_text(encoding="utf-8"))
    # Warm up cached ML model before timing inference.
    get_model()

    comparison: dict[str, dict[str, Any]] = {}
    for mode_name, runner in (
        ("traditional", classify_traditional),
        ("machine_learning", analyze_machine_learning),
    ):
        cat_hits = 0
        sec_total = 0
        sec_hits = 0
        review_count = 0
        latencies_ms: list[float] = []
        for case in cases:
            start = time.perf_counter()
            res = runner(case["message"])
            latencies_ms.append((time.perf_counter() - start) * 1000.0)
            if res.category.value == case["expected_category"]:
                cat_hits += 1
            if case["expected_category"] == "SECURITY":
                sec_total += 1
                if res.category.value == "SECURITY":
                    sec_hits += 1
            if res.requires_human_review:
                review_count += 1
        comparison[mode_name] = {
            "cases": len(cases),
            "category_accuracy_pct": round(100.0 * cat_hits / len(cases), 1),
            "security_recall_pct": round(100.0 * sec_hits / sec_total, 1) if sec_total else 100.0,
            "latency_p95_ms": _percentile_95(latencies_ms),
            "cost_per_100_queries": "$0.00 (local)",
            "human_review_pct": round(100.0 * review_count / len(cases), 1),
        }

    # Include saved generative results from reports/results.csv without extra API calls.
    saved_csv = REPORTS_DIR / "results.csv"
    if saved_csv.is_file():
        with saved_csv.open(encoding="utf-8-sig", newline="") as stream:
            gen_rows = [row for row in csv.DictReader(stream) if row["mode"] == "generative"]
        if gen_rows:
            cat_hits = sum(row["category_correct"] == "True" for row in gen_rows)
            sec_rows = [row for row in gen_rows if row["expected_category"] == "SECURITY"]
            sec_hits = sum(row["category"] == "SECURITY" for row in sec_rows)
            review_count = sum(row["requiresHumanReview"] == "True" for row in gen_rows)
            comparison["generative"] = {
                "cases": len(gen_rows),
                "category_accuracy_pct": round(100.0 * cat_hits / len(gen_rows), 1),
                "security_recall_pct": round(100.0 * sec_hits / len(sec_rows), 1) if sec_rows else 100.0,
                "latency_p95_ms": "N/A (API externa)",
                "cost_per_100_queries": "Cuota API / Variable",
                "human_review_pct": round(100.0 * review_count / len(gen_rows), 1),
            }

    return comparison


def export_evaluation_reports(csv_path: Path = DATA_FILE) -> tuple[Path, Path]:
    """Export ML evaluation metrics, confusion matrix, and 3-engine comparison to reports/."""
    _, metrics = evaluate_model(csv_path)
    comparison = build_three_engine_comparison()
    payload = {
        "ml_test_evaluation": {k: v for k, v in metrics.items() if k != "classification_report_text"},
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "three_engine_comparison": comparison,
    }

    json_path = REPORTS_DIR / "ml_evaluation.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    labels = metrics["classes"]
    matrix_lines = ["| Real \\ Predicción | " + " | ".join(labels) + " |", "|---|" + "---:|" * len(labels)]
    for label, row in zip(labels, metrics["confusion_matrix"]):
        matrix_lines.append(f"| **{label}** | " + " | ".join(str(val) for val in row) + " |")

    comp_lines = [
        "| Motor | Accuracy categoría | Recall en SECURITY | Latencia p95 | Costo / 100 consultas | Revisión humana |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for mode_key, label in (
        ("traditional", "Tradicional (Reglas)"),
        ("machine_learning", "Machine Learning (TF-IDF)"),
        ("generative", "Generativo (LLM)"),
    ):
        row = comparison.get(mode_key)
        if not row:
            continue
        lat = f"{row['latency_p95_ms']} ms" if isinstance(row["latency_p95_ms"], (int, float)) else row["latency_p95_ms"]
        comp_lines.append(
            f"| {label} | {row['category_accuracy_pct']}% | {row['security_recall_pct']}% | "
            f"{lat} | {row['cost_per_100_queries']} | {row['human_review_pct']}% |"
        )

    md = "\n".join([
        "# Evaluación de Machine Learning — AI Support Engine V2",
        "",
        "## 1. Evaluación del modelo en conjunto `test` aislado",
        "",
        f"- **Dataset:** `data/{metrics['dataset_path']}` ({metrics['total_records']} registros únicos: {metrics['train_size']} `train` / {metrics['test_size']} `test`, sin duplicados ni fuga de datos).",
        "- **Pipeline:** `TfidfVectorizer(ngram_range=(1, 2))` + `LogisticRegression(max_iter=1000, random_state=42)`.",
        f"- **Accuracy global en `test`:** **{metrics['accuracy'] * 100:.1f}%**",
        f"- **Recall en `SECURITY`:** **{metrics['security_recall'] * 100:.1f}%** (Falsos negativos de seguridad: {metrics['security_false_negatives']}, Falsos positivos: {metrics['security_false_positives']}).",
        f"- **Umbral de confianza para revisión humana:** `{LOW_CONFIDENCE_THRESHOLD}` (si `predict_proba.max() < {LOW_CONFIDENCE_THRESHOLD}`, se activa `requiresHumanReview: true`).",
        "",
        "### Matriz de confusión (`test` = 40 tickets)",
        "",
        *matrix_lines,
        "",
        "### Reporte por clase",
        "",
        "```text",
        metrics["classification_report_text"].strip(),
        "```",
        "",
        "## 2. Comparativa de los 3 motores (`data/benchmark_cases.json` — 12 casos)",
        "",
        *comp_lines,
        "",
        "## 3. Análisis de decisiones: ¿cuándo elegir cada motor?",
        "",
        "- **Tradicional (Reglas):** Ideal para reglas invariables, guardarraíles de seguridad y prioridades estrictas con costo cero y latencia sub-milisegundo.",
        "- **Machine Learning (TF-IDF + LogisticRegression):** Ideal para clasificar tickets con redacción variada o sinónimos sin escribir regex por cada frase, manteniéndose local, gratuito y reproducible; respaldado por umbral de confianza y reglas de seguridad para evitar falsos negativos críticos.",
        "- **Generativo (LLM):** Ideal cuando se requiere comprender contexto ambiguo y redactar respuestas empáticas personalizadas, asumiendo mayor latencia y necesidad de validaciones estrictas de formato y seguridad.",
        "",
    ])

    md_path = REPORTS_DIR / "ml_evaluation.md"
    md_path.write_text(md, encoding="utf-8")
    return json_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Entrena y evalúa el clasificador local de ML.")
    parser.add_argument("--csv", type=Path, default=DATA_FILE)
    parser.add_argument("--export-report", action="store_true", help="Guarda reports/ml_evaluation.{json,md}")
    args = parser.parse_args()

    model, metrics = evaluate_model(args.csv)
    print("=== Classification Report (test aislado) ===")
    print(metrics["classification_report_text"])
    print("=== Confusion Matrix (ACCESS, BUG, FEATURE, SECURITY) ===")
    print(metrics["confusion_matrix"])
    print("\n=== Pruebas de inferencia en frases nuevas ===")
    samples = [
        "Mi cuenta fue bloqueada tras varios intentos",
        "La pantalla desaparece al confirmar una compra",
        "Puedo abrir información de usuarios ajenos",
    ]
    for sample in samples:
        pred = model.predict([sample])[0]
        score = float(model.predict_proba([sample]).max())
        print(f"- {sample!r} -> {pred} (score aprox: {score:.3f})")

    if args.export_report:
        json_path, md_path = export_evaluation_reports(args.csv)
        print(f"\nReportes guardados en: {json_path} y {md_path}")


if __name__ == "__main__":
    main()
