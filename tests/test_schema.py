import pytest

from src.schema import validate_phase_output as validate
from conftest import make_paper, make_question, make_answer


def test_valid_phase2_passes(paper):
    validate(paper, phase=2)


def test_valid_phase3_passes():
    qs = [make_question(answers=make_answer())]
    validate(make_paper(qs), phase=3)


def test_missing_top_level_key(paper):
    del paper["board"]
    with pytest.raises(ValueError, match="top-level"):
        validate(paper, phase=2)


def test_questions_must_be_a_list(paper):
    paper["questions"] = {}
    with pytest.raises(ValueError, match="must be a list"):
        validate(paper, phase=2)


def test_missing_question_key(paper):
    del paper["questions"][0]["topic"]
    with pytest.raises(ValueError, match="'Q1' missing keys"):
        validate(paper, phase=2)


@pytest.mark.parametrize("bad", [None, "2", 2.0, True])
def test_marks_must_be_an_integer(paper, bad):
    paper["questions"][0]["marks"] = bad
    with pytest.raises(ValueError, match="'marks' must be an integer"):
        validate(paper, phase=2)


def test_invalid_objective(paper):
    paper["questions"][0]["objective"] = "AO9"
    with pytest.raises(ValueError, match="invalid objective"):
        validate(paper, phase=2)


def test_structure_data_must_be_dict(paper):
    paper["questions"][0]["structure_data"] = []
    with pytest.raises(ValueError, match="structure_data"):
        validate(paper, phase=2)


def test_unknown_layout_type_only_warns(paper, capsys):
    paper["questions"][0]["layout_type"] = "BrandNew"
    validate(paper, phase=2)
    assert "New question type detected" in capsys.readouterr().out


def test_phase3_answer_must_have_all_keys():
    a = make_answer(); del a["scoring_rule"]
    with pytest.raises(ValueError, match="answers missing keys"):
        validate(make_paper([make_question(answers=a)]), phase=3)


def test_phase3_marking_points_shape():
    with pytest.raises(ValueError, match="marking_point\\[0\\]"):
        validate(make_paper([make_question(answers=make_answer(marking_points=[{"text": "x"}]))]), phase=3)


def test_total_marks_mismatch_only_warns(paper, capsys):
    paper["total_marks"] = 99
    validate(paper, phase=2)
    assert "does not match total_marks" in capsys.readouterr().out


def test_real_papers_validate(real_paper):
    validate(real_paper, phase=3 if real_paper.get("ms") else 2)


def test_unknown_topic_is_rejected(paper):
    paper["questions"][0]["topic"] = "99.9"
    with pytest.raises(ValueError, match="unknown topic"):
        validate(paper, phase=2)


def test_unmapped_command_warns_but_canonical_forms_do_not(paper, capsys):
    paper["questions"][0]["command"] = "Complete and annotate the diagram"   # canonicalises to Complete
    paper["questions"][1]["command"] = "Frobnicate"
    validate(paper, phase=2)
    out = capsys.readouterr().out
    assert "Frobnicate" in out and "annotate" not in out


def test_consistency_warnings(capsys):
    qs = [make_question("Q1", layout_type="InlineCloze", structure_data={"inline_gap_count": 3}, text="a [blank] b"),
          make_question("Q2", marks=3, layout_type="SimpleSingleBlock", structure_data={"line_count": 1}),
          make_question("Q3", marks=2, layout_type="TermDefinitionGrid",
                        structure_data={"rows": [{"term": None, "definition": "x"}, {"term": "y", "definition": "z"}]})]
    validate(make_paper(qs), phase=2)
    out = capsys.readouterr().out
    assert "inline_gap_count=3 but text has 1" in out
    assert "3-mark question has a one-line answer space" in out
    assert "1 blank cell(s) but 2 mark(s)" in out


def test_consistent_questions_print_no_warnings(capsys):
    validate(make_paper(), phase=2)
    assert "[!]" not in capsys.readouterr().out


def test_topic_outside_the_papers_chapters_warns(capsys):
    validate(make_paper([make_question(topic="7.2")], variant="12"), phase=2)
    assert "topic 7.2 is outside Paper 1's chapters" in capsys.readouterr().out
