"""Check saved evidence consistency; these tests do not invoke a model."""
import csv
import json
from pathlib import Path

from app.evaluation import evaluate_case, summarize

ROOT = Path(__file__).resolve().parents[1]


def test_saved_comparison_matches_reference_and_summary():
    cases = json.loads((ROOT / "data/benchmark_cases.json").read_text(encoding="utf-8"))
    references = {case["id"]: case for case in cases}
    assert len(references) == len(cases) >= 10
    assert sum(c["scenario"] == "instruction_attack" for c in cases) >= 2
    assert any(c["scenario"] == "ambiguous" for c in cases)
    with (ROOT / "reports/results.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2 * len(cases)
    assert {(r["id"], r["mode"]) for r in rows} == {
        (c["id"], mode) for c in cases for mode in ("traditional", "generative")
    }
    evaluated = []
    for row in rows:
        case = references[row["id"]]
        assert row["expected_category"] == case["expected_category"]
        assert row["expected_priority"] == case["expected_priority"]
        payload = {key: row[key] for key in ("category", "priority", "response", "mode")}
        assert row["requiresHumanReview"] in ("True", "False")
        payload["requiresHumanReview"] = row["requiresHumanReview"] == "True"
        actual = evaluate_case(case, row["mode"], payload, row["error"])
        for key in ("format_valid", "category_correct", "priority_correct", "exact_correct"):
            assert row[key] == str(actual[key])
        evaluated.append(actual)
    report = json.loads((ROOT / "reports/summary.json").read_text(encoding="utf-8"))
    assert report["metrics"] == summarize(evaluated)
    assert report["total_requests"] == len(rows)
    assert report["cases_per_mode"] == len(cases)
    assert len((ROOT / "reports/conclusion.md").read_text(encoding="utf-8").split()) <= 150
