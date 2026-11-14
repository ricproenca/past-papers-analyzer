import json

import pytest

from src import extractor as ex
from conftest import make_paper, make_answer


def test_reorder_puts_known_keys_first_and_drops_unknown():
    out = ex._reorder({"questions": [], "zzz": 1, "board": "CIE", "qp": "x"})
    assert list(out) == ["board", "qp", "questions"]


def test_merge_answers_attaches_without_touching_questions(paper):
    before = json.dumps([{k: v for k, v in q.items()} for q in paper["questions"]], sort_keys=True)
    a1, a2 = make_answer(type="MCQ"), make_answer()
    ex._merge_answers(paper, {"Q1": a1, "Q2": a2})
    assert [q["answers"] for q in paper["questions"]] == [a1, a2]
    for q in paper["questions"]:
        q.pop("answers")
    assert json.dumps(paper["questions"], sort_keys=True) == before


def test_merge_answers_fills_missing_and_ignores_unknown(paper, capsys):
    ex._merge_answers(paper, {"Q1": make_answer(), "ZZ": make_answer()})
    assert paper["questions"][1]["answers"] == ex._EMPTY_ANSWER
    out = capsys.readouterr().out
    assert "no answer for 1 question(s): ['Q2']" in out and "unknown ids (ignored): ['ZZ']" in out
    assert all("ZZ" != q["id"] for q in paper["questions"])


def test_merge_answers_missing_entries_are_independent_copies(paper):
    ex._merge_answers(paper, {})
    paper["questions"][0]["answers"]["marking_points"].append("x")
    assert ex._EMPTY_ANSWER["marking_points"] == []


def test_merge_answers_rejects_non_mapping(paper):
    with pytest.raises(ValueError, match="mapping question id"):
        ex._merge_answers(paper, [])


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    """Run extract() with the PDF reader and Claude stubbed out; returns (responses, run)."""
    responses = []
    monkeypatch.setattr(ex.pdf_reader, "extract_pages", lambda p: [{"page": 1, "text": "t", "has_table": False, "has_image": False}])
    monkeypatch.setattr(ex.claude_client, "call", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(ex.visuals, "attach_visual_images", lambda *a, **k: 0)

    def run(ms=True):
        out = tmp_path / "json" / "0478_m25_qp_12.json"
        out.parent.mkdir(exist_ok=True)
        ex.extract("0478_m25_qp_12.pdf", str(out), ms_path="0478_m25_ms_12.pdf" if ms else None)
        return json.loads(out.read_text(encoding="utf-8")), tmp_path / "html" / "0478_m25_qp_12.html"
    return responses, run


def _claude_extraction():
    p = make_paper()
    for k in ("qp", "ms"):
        p.pop(k)                      # injected by the pipeline, not by Claude
    return json.dumps(p)


def test_full_pipeline_with_marking_scheme(pipeline):
    responses, run = pipeline
    responses += [_claude_extraction(), json.dumps({"Q1": make_answer(type="MCQ"), "Q2": make_answer()})]
    data, html = run()
    assert (data["qp"], data["ms"]) == ("0478_m25_qp_12.pdf", "0478_m25_ms_12.pdf")
    assert list(data)[:2] == ["board", "level"] and "summary" in data and "statistics" in data
    q1 = data["questions"][0]
    assert q1["answers"]["type"] == "MCQ" and q1["difficulty"] == "Low" and q1["bloom_level"] == "Remember"
    assert data["statistics"]["count_by_answer_type"] == {"MCQ": 1, "text": 1}
    assert html.exists() and "Q1" in html.read_text(encoding="utf-8")


def test_pipeline_without_marking_scheme_makes_one_call(pipeline):
    responses, run = pipeline
    responses.append(_claude_extraction())
    data, _ = run(ms=False)
    assert data["ms"] is None and "answers" not in data["questions"][0] and responses == []


def test_validation_failure_saves_raw_response(pipeline, debug_dir):
    responses, run = pipeline
    bad = json.loads(_claude_extraction())
    bad["questions"][0]["objective"] = "AO9"
    responses.append(json.dumps(bad))
    with pytest.raises(ValueError, match="invalid objective"):
        run(ms=False)
    (saved,) = debug_dir.glob("*Phase_1_2.txt")
    assert "AO9" in saved.read_text()
