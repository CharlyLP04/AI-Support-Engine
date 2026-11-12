import json
from pathlib import Path

import pytest

from app.rules import classify_traditional


CASES = json.loads((Path(__file__).parents[1] / "data" / "benchmark_cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_traditional_engine_matches_reference(case):
    result = classify_traditional(case["message"])

    assert result.category == case["expected_category"]
    assert result.priority == case["expected_priority"]
    assert result.response.strip()
    assert result.requires_human_review is (case["expected_category"] == "SECURITY")
    assert result.mode == "traditional"
