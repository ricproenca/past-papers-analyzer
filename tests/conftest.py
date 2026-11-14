import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JSON_DIR = ROOT / "output" / "json"
HTML_DIR = ROOT / "output" / "html"
PAPER_PATHS = sorted(JSON_DIR.glob("*.json"))


def make_question(qid="Q1", **overrides):
    q = {
        "id": qid, "text": "State one use of RAM.", "command": "State", "objective": "AO1",
        "marks": 1, "visuals": [], "page": 2, "layout_type": "SimpleSingleBlock",
        "structure_data": {"line_count": 1}, "topic": "3.3", "topic_name": "Data Storage",
    }
    q.update(overrides)
    return q


def make_paper(questions=None, **overrides):
    qs = questions if questions is not None else [make_question("Q1"), make_question("Q2", marks=2)]
    p = {
        "board": "CIE", "level": "IGCSE", "subject_code": "0478", "subject_name": "Computer Science",
        "variant": "12", "qp": "0478_m25_qp_12.pdf", "ms": None, "total_marks": sum(q["marks"] for q in qs),
        "questions": qs,
    }
    p.update(overrides)
    return p


def make_answer(**overrides):
    a = {"type": "text", "visuals": [], "scoring_rule": "Any one from", "marking_points": [{"text": "x", "marks": 1}]}
    a.update(overrides)
    return a


@pytest.fixture
def paper():
    return make_paper()


@pytest.fixture(params=PAPER_PATHS, ids=lambda p: p.stem)
def real_paper(request):
    """Every extracted paper committed under output/json/."""
    return json.loads(request.param.read_text(encoding="utf-8"))


@pytest.fixture
def debug_dir(tmp_path, monkeypatch):
    d = tmp_path / "debug"
    monkeypatch.setenv("CLAUDE_DEBUG_DIR", str(d))
    return d
