"""Tests for the demo value-point marking endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_lists_the_demo_scheme():
    response = client.get("/api/v2/questions")
    assert response.status_code == 200

    body = response.json()
    assert len(body["questions"]) == 4
    assert "NOT VALIDATED AGAINST HUMAN EXAMINERS" in body["disclaimer"]


def test_unknown_question_id_is_404_and_lists_valid_ids():
    response = client.post(
        "/api/v2/evaluate", json={"question_id": "nope", "answer_text": "x"}
    )
    assert response.status_code == 404
    assert "q1" in response.json()["detail"]


def test_full_marks_for_a_correct_answer():
    response = client.post(
        "/api/v2/evaluate",
        json={
            "question_id": "q1",
            "answer_text": "Plants absorb carbon dioxide from the atmosphere.",
        },
    )
    body = response.json()

    assert body["total"] == 1.0
    assert body["max_marks"] == 1.0


def test_the_atp_class_case_variant_is_credited():
    """A student writing the accepted variant must be credited.

    The old path scored a verbatim term at 0.651 against a 0.68 threshold and
    marked it missing. This is that failure, as an API assertion.
    """
    response = client.post(
        "/api/v2/evaluate",
        json={"question_id": "q1", "answer_text": "The gas taken in is CO2."},
    )
    body = response.json()

    assert body["total"] == 1.0
    assert body["awarded"][0]["evidence_span"] is not None


def test_wrong_but_topical_scores_zero():
    """The punchline: topical relatedness earns nothing on its own."""
    response = client.post(
        "/api/v2/evaluate",
        json={
            "question_id": "q2",
            "answer_text": (
                "Mitochondria are found inside cells. They are called the "
                "powerhouse and are very important organelles."
            ),
        },
    )
    body = response.json()

    assert body["total"] == 0.0
    assert all(not a["matched"] for a in body["not_awarded"])


def test_step_marks_survive_a_wrong_final_answer():
    response = client.post(
        "/api/v2/evaluate",
        json={
            "question_id": "q3",
            "answer_text": "2x + 5 = 15 so 2x = 10, then x = 10/2, therefore x = 7.",
        },
    )
    body = response.json()

    assert body["total"] == 2.0, "method marks must survive a wrong result"
    awarded_ids = {a["value_point_id"] for a in body["awarded"]}
    assert awarded_ids == {"3.1", "3.2"}
    assert [a["value_point_id"] for a in body["not_awarded"]] == ["3.3"]


def test_any_n_credits_only_two_of_three():
    response = client.post(
        "/api/v2/evaluate",
        json={
            "question_id": "q2",
            "answer_text": (
                "Mitochondria produce ATP, carry out cellular respiration, "
                "and release energy for the cell."
            ),
        },
    )
    body = response.json()

    assert body["total"] == 3.0
    assert len(body["awarded"]) == 2
    assert "outside the best 2" in body["not_awarded"][0]["reason"]


def test_response_is_a_complete_appeal_record():
    """Master spec rule 3: criterion id + evidence span + engine version."""
    response = client.post(
        "/api/v2/evaluate",
        json={"question_id": "q1", "answer_text": "It absorbs carbon dioxide."},
    )
    body = response.json()

    assert body["engine_version"]
    assert body["derivation"]
    for line in body["awarded"]:
        assert line["value_point_id"]
        assert line["evidence_span"] is not None
        assert line["method"]


def test_empty_answer_is_a_zero_not_an_error():
    response = client.post(
        "/api/v2/evaluate", json={"question_id": "q4", "answer_text": "   "}
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0.0


def test_disclaimer_is_on_every_response():
    response = client.post(
        "/api/v2/evaluate", json={"question_id": "q1", "answer_text": "anything"}
    )
    body = response.json()

    assert "NOT VALIDATED AGAINST HUMAN EXAMINERS" in body["disclaimer"]
    assert "NOT VALIDATED AGAINST HUMAN EXAMINERS" in body["derivation"]
