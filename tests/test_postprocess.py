
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
