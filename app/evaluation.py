from collections import defaultdict
from typing import Any


_CATEGORIES = {"ACCESS", "BUG", "FEATURE", "SECURITY"}
_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
_RESPONSE_KEYS = {"category", "priority", "response", "requiresHumanReview", "mode"}


def evaluate_case(case: dict[str, Any], mode: str, payload: Any, error: str | None = None) -> dict[str, Any]:
    valid = (
        isinstance(payload, dict)
        and set(payload) == _RESPONSE_KEYS
        and isinstance(payload.get("category"), str)
        and payload.get("category") in _CATEGORIES
        and isinstance(payload.get("priority"), str)
        and payload.get("priority") in _PRIORITIES
        and isinstance(payload.get("response"), str)
        and bool(payload.get("response", "").strip())
        and isinstance(payload.get("requiresHumanReview"), bool)
        and (payload.get("category") != "SECURITY" or payload.get("requiresHumanReview") is True)
        and payload.get("mode") == mode
    )
    category = payload.get("category") if isinstance(payload, dict) else None
    priority = payload.get("priority") if isinstance(payload, dict) else None
    category_correct = bool(valid and category == case["expected_category"])
    priority_correct = bool(valid and priority == case["expected_priority"])
    return {
        "id": case["id"],
        "scenario": case["scenario"],
        "mode": mode,
        "expected_category": case["expected_category"],
        "category": category,
        "expected_priority": case["expected_priority"],
        "priority": priority,
        "format_valid": bool(valid),
        "category_correct": category_correct,
        "priority_correct": priority_correct,
        "exact_correct": category_correct and priority_correct,
        "requiresHumanReview": payload.get("requiresHumanReview") if isinstance(payload, dict) else None,
        "response": payload.get("response", "") if isinstance(payload, dict) else "",
        "error": error or "",
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["mode"]].append(row)

    summary: dict[str, dict[str, float | int]] = {}
    for mode, mode_rows in grouped.items():
        total = len(mode_rows)
        summary[mode] = {
            "cases": total,
            "format_compliance_pct": round(100 * sum(r["format_valid"] for r in mode_rows) / total, 1),
            "category_accuracy_pct": round(100 * sum(r["category_correct"] for r in mode_rows) / total, 1),
            "priority_accuracy_pct": round(100 * sum(r["priority_correct"] for r in mode_rows) / total, 1),
            "exact_accuracy_pct": round(100 * sum(r["exact_correct"] for r in mode_rows) / total, 1),
        }
    return summary
