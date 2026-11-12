from app.evaluation import evaluate_case, summarize


def test_evaluate_case_checks_contract_and_reference_labels():
    case = {
        "id": "access-1",
        "scenario": "normal",
        "expected_category": "ACCESS",
        "expected_priority": "MEDIUM",
    }
    payload = {
        "category": "ACCESS",
        "priority": "MEDIUM",
        "response": "Prueba restablecer la contraseña.",
        "requiresHumanReview": False,
        "mode": "generative",
    }

    row = evaluate_case(case, "generative", payload)

    assert row["format_valid"] is True
    assert row["category_correct"] is True
    assert row["priority_correct"] is True
    assert row["exact_correct"] is True


def test_evaluate_case_rejects_incomplete_contract():
    case = {
        "id": "bug-1",
        "scenario": "normal",
        "expected_category": "BUG",
        "expected_priority": "LOW",
    }

    row = evaluate_case(case, "traditional", {"category": "BUG", "priority": "LOW"})

    assert row["format_valid"] is False
    assert row["category_correct"] is False
    assert row["exact_correct"] is False


def test_evaluate_case_handles_unhashable_fields_without_crashing():
    case = {
        "id": "malformed-1",
        "scenario": "normal",
        "expected_category": "BUG",
        "expected_priority": "LOW",
    }
    payload = {
        "category": ["BUG"],
        "priority": "LOW",
        "response": "Lo revisaremos.",
        "requiresHumanReview": False,
        "mode": "traditional",
    }

    row = evaluate_case(case, "traditional", payload)

    assert row["format_valid"] is False
    assert row["category_correct"] is False


def test_evaluate_case_rejects_security_result_without_human_review():
    case = {
        "id": "security-1",
        "scenario": "normal",
        "expected_category": "SECURITY",
        "expected_priority": "CRITICAL",
    }
    payload = {
        "category": "SECURITY",
        "priority": "CRITICAL",
        "response": "El equipo de seguridad debe revisar el incidente.",
        "requiresHumanReview": False,
        "mode": "generative",
    }

    row = evaluate_case(case, "generative", payload)

    assert row["format_valid"] is False
    assert row["category_correct"] is False


def test_summary_reports_category_priority_and_exact_accuracy():
    rows = [
        {"mode": "traditional", "format_valid": True, "category_correct": True, "priority_correct": True, "exact_correct": True},
        {"mode": "traditional", "format_valid": True, "category_correct": True, "priority_correct": False, "exact_correct": False},
        {"mode": "generative", "format_valid": True, "category_correct": False, "priority_correct": True, "exact_correct": False},
        {"mode": "generative", "format_valid": False, "category_correct": False, "priority_correct": False, "exact_correct": False},
    ]

    summary = summarize(rows)

    assert summary["traditional"]["category_accuracy_pct"] == 100.0
    assert summary["traditional"]["priority_accuracy_pct"] == 50.0
    assert summary["traditional"]["exact_accuracy_pct"] == 50.0
    assert summary["generative"]["format_compliance_pct"] == 50.0
