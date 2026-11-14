
from src import postprocess as pp
from conftest import make_paper, make_question


def test_fill_topic_names_and_unknown_topics():
    d = make_paper([make_question("Q1", topic="3.3", topic_name="WRONG"), make_question("Q2", topic="99.9", topic_name="keep")])
    del d["questions"][0]["topic_name"]
    pp.fill_topic_names(d)
    assert d["questions"][0]["topic_name"] == "Data Storage" and d["questions"][1]["topic_name"] == "keep"


def test_canonicalise_commands():
    d = make_paper([make_question("Q1", command="Complete and annotate the diagram"), make_question("Q2", command="give"),
                    make_question("Q3", command="Zzz")])
    pp.canonicalise_commands(d)
    assert [q["command"] for q in d["questions"]] == ["Complete", "Give", "Zzz"]


def _td_pages():
    t1 = {"headers": ["Term", "Description"], "rows": [{"term": "cpu", "definition": None}, {"term": None, "definition": "stores"}]}
    t2 = {"headers": ["Name", "Use"], "rows": [{"term": None, "definition": "x"}]}
    return [{"page": 4, "term_def_tables": [t1, t2]}, {"page": 5, "term_def_tables": [t1]}], t1, t2


def test_fill_term_def_grids_pairs_by_page_and_order():
    pages, t1, t2 = _td_pages()
    qs = [make_question("Q1", page=4, layout_type="TermDefinitionGrid", structure_data={}),
          make_question("Q2", page=4, layout_type="TermDefinitionGrid", structure_data={"rows": ["junk"]}),
          make_question("Q3", page=5, layout_type="TermDefinitionGrid", structure_data={}),
          make_question("Q4", page=5, layout_type="SimpleSingleBlock")]
    assert pp.fill_term_def_grids(make_paper(qs), pages) == []
    assert qs[0]["structure_data"] == {"row_count": 2, "rows": t1["rows"], "headers": ["Term", "Description"]}
    assert qs[1]["structure_data"]["headers"] == ["Name", "Use"] and qs[2]["structure_data"]["row_count"] == 2
    assert qs[3]["structure_data"] == {"line_count": 1}                                # other layouts untouched
    qs[0]["structure_data"]["rows"][0]["term"] = "changed"
    assert t1["rows"][0]["term"] == "cpu"                                              # source tables are copied, not shared


def test_fill_term_def_grids_leaves_ambiguous_pages_alone():
    pages, _, _ = _td_pages()
    qs = [make_question("Q1", page=5, layout_type="TermDefinitionGrid", structure_data={"rows": ["model"]}),
          make_question("Q2", page=5, layout_type="TermDefinitionGrid", structure_data={}),
          make_question("Q9", page=7, layout_type="TermDefinitionGrid", structure_data={})]
    assert pp.fill_term_def_grids(make_paper(qs), pages) == ["Q1", "Q2", "Q9"]
    assert qs[0]["structure_data"] == {"rows": ["model"]}


def test_postprocess_phase12_runs_everything():
    pages, _, _ = _td_pages()
    d = make_paper([make_question("Q3a", text="own", command="Give", page=5, layout_type="TermDefinitionGrid", structure_data={})])
    del d["questions"][0]["topic_name"]
    assert pp.postprocess_phase12(d, pages) == []
    q = d["questions"][0]
    assert q["text"] == "own" and q["topic_name"] == "Data Storage" and q["structure_data"]["headers"] == ["Term", "Description"]


def test_paper_identity_comes_from_the_file_name():
    d = make_paper(qp="0478_w25_qp_12.pdf", subject_code="0478", variant="21")
    assert pp.fill_paper_identity(d) == ["variant: model wrote '21', file name says '12'"]
    assert (d["subject_code"], d["variant"]) == ("0478", "12")
    d2 = make_paper(qp="0478_w25_qp_12.pdf", variant=None)
    assert pp.fill_paper_identity(d2) == [] and d2["variant"] == "12"         # filled silently when missing
    d3 = make_paper(qp="some_other_name.pdf", variant="99")
    assert pp.fill_paper_identity(d3) == [] and d3["variant"] == "99"         # unknown naming: leave alone


_MATCH = ("Draw one line from each stage to the most appropriate description.\n"
          "Stage | Description\ntesting | finding errors\ncoding | writing code\ndesign | planning")


def test_line_matching_questions_get_their_own_layout_and_columns():
    qs = [make_question("Q3", command="Draw", text=_MATCH, layout_type="MatrixGrid", structure_data={"rows": []}),
          make_question("Q4", command="Draw", text="Draw a logic circuit.", layout_type="AnnotatedDiagram",
                        structure_data={"diagram_type": "circuit"}),
          make_question("Q5", command="Draw", text=_MATCH, layout_type="AnnotatedDiagram",
                        structure_data={"diagram_type": "other"})]
    assert pp.fix_line_matching_layouts(make_paper(qs)) == ["Q3", "Q5"]
    assert qs[0]["layout_type"] == qs[2]["layout_type"] == "LineMatching"
    assert qs[0]["structure_data"] == {"left_header": "Stage", "right_header": "Description",
                                       "left_items": ["testing", "coding", "design"],
                                       "right_items": ["finding errors", "writing code", "planning"]}
    assert qs[1]["structure_data"] == {"diagram_type": "circuit"}


def test_line_matching_columns_are_refreshed_and_idempotent():
    q = make_question("Q3", command="Draw", text=_MATCH, layout_type="LineMatching", structure_data={})
    paper = make_paper([q])
    assert pp.fix_line_matching_layouts(paper) == []                 # already LineMatching: not reported
    first = dict(q["structure_data"])
    pp.fix_line_matching_layouts(paper)
    assert first["left_items"] == ["testing", "coding", "design"] and q["structure_data"] == first


_PAGES = [{"page": 6, "text": "7 This flowchart represents an algorithm.\nSTART\nOUTPUT\n\"Continue?\"\nINPUT Answer\n"
                               "Complete the trace table for the input data:\nY, 7, S, 9, Y, 5"}]


def test_invented_diagram_summary_is_removed_but_printed_sentences_stay():
    invented = ("The flowchart shows a start node, then it outputs a prompt and reads the answer, "
                "then it decides whether the answer is yes and loops back to the start.")
    q = make_question("Q7a", text="This flowchart represents an algorithm. " + invented +
                      "\n\nComplete the trace table for the input data:\nY, 7, S, 9, Y, 5")
    removed = pp.drop_unsourced_text(make_paper([q]), _PAGES)
    assert [i for i, _ in removed] == ["Q7a"] and "start node" in removed[0][1]
    assert q["text"] == "This flowchart represents an algorithm.\n\nComplete the trace table for the input data:\nY, 7, S, 9, Y, 5"


def test_verbatim_and_short_text_is_untouched():
    q = make_question("Q7b", text="This flowchart represents an algorithm.\n\nState the purpose.")
    assert pp.drop_unsourced_text(make_paper([q]), _PAGES) == []
    assert q["text"] == "This flowchart represents an algorithm.\n\nState the purpose."


def test_whole_invented_paragraph_is_removed():
    q = make_question("Q7c", text=("Complete the trace table for the input data:\n\n"
                                   "It is a calculator that keeps asking the user for numbers and operators until they stop."))
    pp.drop_unsourced_text(make_paper([q]), _PAGES)
    assert q["text"] == "Complete the trace table for the input data:"


def _with_rule(rule, marks=15, **kw):
    return make_question("Q10", marks=marks, answers={"type": "pseudocode", "visuals": [], "scoring_rule": rule, "marking_points": []}, **kw)


def test_objective_split_is_read_from_the_marking_scheme():
    q = _with_rule("Marks are available for: AO2 (maximum 9 marks); AO3 (maximum 6 marks)")
    assert pp.fill_objective_marks(make_paper([q])) == ["Q10"] and q["objective_marks"] == {"AO2": 9, "AO3": 6}


def test_objective_split_needs_two_objectives_that_add_up():
    wrong_sum = _with_rule("AO2 (maximum 9 marks); AO3 (maximum 5 marks)", objective_marks={"AO1": 15})
    single = _with_rule("AO2 (maximum 15 marks)")
    none = _with_rule("Any three from", marks=3)
    assert pp.fill_objective_marks(make_paper([wrong_sum, single, none])) == []
    assert "objective_marks" not in wrong_sum                     # a stale split is removed
