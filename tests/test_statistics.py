import json

import pytest

from src import enricher, statistics as st
from conftest import make_question, make_paper, make_answer, PAPER_PATHS


def test_marks_and_counts_by_axis():
    qs = [make_question("Q1", marks=1, topic="1.1"), make_question("Q2", marks=3, topic="1.1"),
          make_question("Q3", marks=2, topic="2.1")]
    s = st.compute_statistics(make_paper(qs))
    assert s["marks_by_topic"] == {"1.1": 4, "2.1": 2}
    assert s["count_by_topic"] == {"1.1": 2, "2.1": 1}
    assert len([k for k in s if k.startswith(("marks_by_", "count_by_"))]) == 16


def test_missing_axis_values_are_skipped():
    s = st.compute_statistics(make_paper([make_question(topic=None), make_question("Q2", topic="")]))
    assert s["marks_by_topic"] == {} and s["count_by_topic"] == {}


def test_answer_type_axis_uses_answers():
    qs = [make_question("Q1", answers=make_answer(type="MCQ")), make_question("Q2")]
    assert st.compute_statistics(make_paper(qs))["count_by_answer_type"] == {"MCQ": 1}


@pytest.mark.parametrize("values,expected", [([], 0), ([3], 3), ([1, 3, 2], 2), ([1, 2], 1.5), ([2, 4], 3)])
def test_median(values, expected):
    assert st._median(values) == expected


def test_summary():
    qs = [make_question("Q1", marks=1, answers=make_answer(type="MCQ")), make_question("Q2", marks=4, topic="1.1")]
    assert st.compute_summary(make_paper(qs)) == {
        "question_count": 2, "mcq_count": 1, "mean_marks_per_question": 2.5,
        "median_marks_per_question": 2.5, "max_marks_per_question": 4, "unique_topics_count": 2}


def test_summary_of_empty_paper():
    assert st.compute_summary(make_paper([]))["question_count"] == 0


def test_real_papers_marks_sum_per_axis(real_paper):
    total = sum(q["marks"] for q in real_paper["questions"])
    for axis in ("topic", "difficulty", "objective", "layout_type"):
        assert sum(real_paper["statistics"][f"marks_by_{axis}"].values()) == total, axis


def test_committed_enrichment_is_up_to_date(real_paper):
    """Fails if enricher/statistics changed without re-running backfill_enrichment.py."""
    fresh = json.loads(json.dumps(real_paper))
    enricher.enrich_paper(fresh)
    st.attach_statistics(fresh)
    assert fresh == real_paper
