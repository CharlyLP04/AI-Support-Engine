import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.evaluation import evaluate_case, summarize


ROOT = Path(__file__).resolve().parents[1]
CASE_FILE = ROOT / "data" / "benchmark_cases.json"
REPORT_DIR = ROOT / "reports"
CSV_FIELDS = [
    "id", "scenario", "mode", "expected_category", "category", "expected_priority",
    "priority", "format_valid", "category_correct", "priority_correct", "exact_correct",
    "requiresHumanReview", "response", "error",
]


def run_benchmark(api_url: str, limit: int | None = None) -> dict[str, Any]:
    cases = json.loads(CASE_FILE.read_text(encoding="utf-8"))
    if limit is not None:
        cases = cases[:limit]
    rows: list[dict[str, Any]] = []

    with httpx.Client(timeout=150) as client:
        health = client.get(f"{api_url.rstrip('/')}/health")
        health.raise_for_status()
        for case in cases:
            for mode in ("traditional", "generative"):
                try:
                    response = client.post(
                        f"{api_url.rstrip('/')}/api/analyze",
                        json={"message": case["message"], "mode": mode},
                    )
                    if response.is_success:
                        payload: Any = response.json()
                        error = None
                    else:
                        payload = None
                        error = f"HTTP {response.status_code}"
                except httpx.HTTPError as exc:
                    payload = None
                    error = f"API connection failed: {type(exc).__name__}"
                rows.append(evaluate_case(case, mode, payload, error))

    summary = summarize(rows)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = REPORT_DIR / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cases_per_mode": len(cases),
        "total_requests": len(rows),
        "generative_model": os.getenv("HERMES_MODEL", "nous/welcome"),
        "metrics": summary,
        "results_csv": "reports/results.csv",
    }
    (REPORT_DIR / "summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 2-engine support classification comparison.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="Base URL of the running API")
    parser.add_argument("--limit", type=int, help="Run only the first N cases (for a quick smoke test)")
    args = parser.parse_args()
    report = run_benchmark(args.api_url, args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
