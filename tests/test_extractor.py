import json

import pytest

from src import extractor as ex
from conftest import make_paper, make_question, make_answer


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


# --- post-processing through the whole pipeline ---------------------------------------

def test_pipeline_fills_topic_names_and_canonicalises_commands(pipeline):
    responses, run = pipeline
    claude = json.loads(_claude_extraction())
    claude["questions"] = [make_question("Q3a", text="Part a.", command="Complete and annotate the diagram"),
                           make_question("Q3b", text="Part b.", topic="3.1")]
    claude["total_marks"] = 2
    for q in claude["questions"]:
        del q["topic_name"]                       # the model no longer writes it
    responses.append(json.dumps(claude))
    data, _ = run(ms=False)
    qa, qb = data["questions"]
    assert (qa["topic_name"], qb["topic_name"]) == ("Data Storage", "Computer Architecture")
    assert qa["command"] == "Complete" and qa["text"] == "Part a."


def test_pipeline_rejects_an_unknown_topic_and_saves_the_response(pipeline, debug_dir):
    responses, run = pipeline
    bad = json.loads(_claude_extraction())
    bad["questions"][0]["topic"] = "42.1"
    responses.append(json.dumps(bad))
    with pytest.raises(ValueError, match="unknown topic"):
        run(ms=False)
    assert list(debug_dir.glob("*Phase_1_2.txt"))


# --- batch driver -------------------------------------------------------------------------

@pytest.fixture
def batch_env(monkeypatch, tmp_path):
    monkeypatch.setattr(ex.pdf_reader, "extract_pages", lambda p: [{"page": 1, "text": "t", "has_table": False, "has_image": False}])
    monkeypatch.setattr(ex.visuals, "attach_visual_images", lambda *a, **k: 0)
    batches = []

    def fake_call_batch(requests, label="", poll_seconds=0):
        batches.append((label, list(requests)))
        return fake_call_batch.reply(label, requests)
    monkeypatch.setattr(ex.claude_client, "call_batch", fake_call_batch)
    return fake_call_batch, batches, tmp_path


def test_extract_batch_two_stages_and_failure_isolation(batch_env):
    fake, batches, tmp = batch_env

    def reply(label, requests):
        if label.startswith("Phase 1+2"):
            good = _claude_extraction()
            return {"good_qp_1": good, "nomarks_qp_2": good, "boom_qp_3": RuntimeError("batch request expired: x")}
        return {"good_qp_1": json.dumps({"Q1": make_answer(), "Q2": make_answer()})}
    fake.reply = reply

    papers = [(f"{n}.pdf", str(tmp / "json" / f"{n}.json"), ms) for n, ms in
              (("good_qp_1", "good_ms_1.pdf"), ("nomarks_qp_2", None), ("boom_qp_3", None))]
    failures = ex.extract_batch(papers)

    assert [(label.split(" batch")[0], ids) for label, ids in batches] == [
        ("Phase 1+2", ["good_qp_1", "nomarks_qp_2", "boom_qp_3"]), ("Phase 3", ["good_qp_1"])]
    assert [(n, type(e).__name__) for n, e in failures] == [("boom_qp_3.pdf", "RuntimeError")]
    good = json.loads((tmp / "json" / "good_qp_1.json").read_text())
    assert good["questions"][0]["answers"]["type"] == "text" and good["ms"] == "good_ms_1.pdf"
    assert "answers" not in json.loads((tmp / "json" / "nomarks_qp_2.json").read_text())["questions"][0]
    assert not (tmp / "json" / "boom_qp_3.json").exists()


def test_extract_batch_phase3_failure_does_not_write_a_half_paper(batch_env):
    fake, _, tmp = batch_env
    fake.reply = lambda label, reqs: ({"p_qp_1": _claude_extraction()} if label.startswith("Phase 1+2")
                                      else {"p_qp_1": ValueError("Claude returned invalid JSON")})
    failures = ex.extract_batch([("p_qp_1.pdf", str(tmp / "json" / "p_qp_1.json"), "p_ms_1.pdf")])
    assert [n for n, _ in failures] == ["p_qp_1.pdf"] and not (tmp / "json" / "p_qp_1.json").exists()


def test_phase3_failure_keeps_the_paid_extraction(batch_env, debug_dir, capsys):
    fake, _, tmp = batch_env
    fake.reply = lambda label, reqs: ({"p_qp_1": _claude_extraction()} if label.startswith("Phase 1+2")
                                      else {"p_qp_1": ValueError("Claude returned invalid JSON")})
    ex.extract_batch([("p_qp_1.pdf", str(tmp / "json" / "p_qp_1.json"), "p_ms_1.pdf")])
    kept = json.loads((debug_dir / "p_qp_1.phase12.json").read_text())
    assert kept["qp"] == "p_qp_1.pdf" and kept["questions"] and "answers" not in kept["questions"][0]
    assert "python answers.py" in capsys.readouterr().out


def test_extract_batch_passes_resume_ids(batch_env, monkeypatch):
    fake, _, tmp = batch_env
    seen = []

    def call_batch(requests, label="", poll_seconds=0, batch_id=None):
        seen.append((label, batch_id))
        return {"p_qp_1": _claude_extraction()} if label.startswith("Phase 1+2") else {
            "p_qp_1": json.dumps({"Q1": make_answer(), "Q2": make_answer()})}
    monkeypatch.setattr(ex.claude_client, "call_batch", call_batch)
    failures = ex.extract_batch([("p_qp_1.pdf", str(tmp / "json" / "p_qp_1.json"), "p_ms_1.pdf")],
                                resume={"phase12": "batch_A", "phase3": "batch_B"})
    assert failures == [] and seen == [("Phase 1+2 batch", "batch_A"), ("Phase 3 batch", "batch_B")]


def test_batch_ids_are_sanitised():
    assert ex._batch_id("/x/0478 m25 (qp)_12.pdf") == "0478_m25__qp__12"


# --- Phase 3 payload and answers-only refresh -------------------------------------------

def test_phase3_payload_sends_only_what_matching_needs(paper):
    payload = json.loads(ex.phase3_payload(paper))
    assert list(payload) == ["questions"]
    assert all(set(q) == {"id", "marks", "layout_type", "text"} for q in payload["questions"])


def test_refresh_answers_replaces_answers_only(monkeypatch, tmp_path):
    src = make_paper([make_question("Q1"), make_question("Q10", marks=15)], ms=None)
    src["questions"][0]["answers"] = make_answer(type="MCQ")
    path = tmp_path / "json" / "0478_m25_qp_12.json"
    path.parent.mkdir()
    path.write_text(json.dumps(src))
    ms = tmp_path / "0478_m25_ms_12.pdf"
    monkeypatch.setattr(ex.pdf_reader, "extract_pages", lambda p: [{"page": 1, "text": "Question Answer Marks", "has_table": False, "has_image": False}])
    monkeypatch.setattr(ex.visuals, "find_source_pdf", lambda name, root="input": None)
    replies = [json.dumps({"Q1": make_answer(type="text"),
                           "Q10": make_answer(scoring_rule="AO2 (maximum 9 marks); AO3 (maximum 6 marks)",
                                              marking_points=[{"text": "band", "marks": 15}])})]
    monkeypatch.setattr(ex.claude_client, "call", lambda *a, **k: replies.pop(0))
    data = ex.refresh_answers(str(path), str(ms))
    saved = json.loads(path.read_text())
    assert saved["ms"] == "0478_m25_ms_12.pdf" and saved["questions"][0]["answers"]["type"] == "text"
    assert saved["questions"][1]["objective_marks"] == {"AO2": 9, "AO3": 6}
    assert saved["statistics"]["marks_by_objective"]["AO3"] == 6 and data["questions"][0]["topic"] == "3.3"
    assert (tmp_path / "html" / "0478_m25_qp_12.html").exists()


def test_refresh_answers_needs_a_marking_scheme(monkeypatch, tmp_path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps(make_paper()))
    monkeypatch.setattr(ex.visuals, "find_source_pdf", lambda name, root="input": None)
    with pytest.raises(FileNotFoundError, match="no marking scheme"):
        ex.refresh_answers(str(path))
