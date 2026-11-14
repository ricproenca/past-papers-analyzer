import re

import pytest

from src import renderer as r
from src.renderer import layouts, matching, page, question
from src.renderer import text as textmod
from conftest import HTML_DIR, PAPER_PATHS, make_paper, make_question

PIPE = "| A | B |\n| 1 | 2 |\n| 3 | 4 |"


# --- pipe tables -------------------------------------------------------------

def test_pipe_table_lines_requires_consistent_columns():
    assert textmod._pipe_table_lines(["a | b", "c | d"]) == ["a | b", "c | d"]
    assert textmod._pipe_table_lines(["a | b"]) is None                    # one row
    assert textmod._pipe_table_lines(["a | b", "c | d | e"]) is None      # ragged
    assert textmod._pipe_table_lines(["a | b", "no pipe"]) is None


def test_find_pipe_table_blocks():
    text = "intro\n" + PIPE + "\n\nmore\nx | y\nz | w"
    assert textmod._find_pipe_table_blocks(text) == [(1, 4), (6, 8)]
    assert textmod._find_pipe_table_blocks("just prose") == []


def test_strip_pipe_tables_removes_only_the_table():
    assert textmod._strip_pipe_tables("Intro.\n" + PIPE + "\nOutro.") == "Intro.\nOutro."
    assert textmod._strip_pipe_tables("plain") == "plain"


def test_maybe_pipe_table_renders_and_escapes():
    html = textmod._maybe_pipe_table("| H1 | H2 |\n| <b> | x & y |")
    assert html.startswith('<table class="ref-table">')
    assert "<th>H1</th>" in html and "<td>&lt;b&gt;</td>" in html and "x &amp; y" in html
    assert textmod._maybe_pipe_table("not a table") is None


def test_maybe_code_block():
    assert textmod._maybe_code_block("SELECT *\nFROM t\nWHERE x = 1").startswith('<pre class="code-stem">')
    assert textmod._maybe_code_block("01 DECLARE x\n02 x = 1").startswith('<pre class="code-stem">')
    assert textmod._maybe_code_block("Describe the process.") is None
    assert textmod._maybe_code_block("") is None


# --- cloze -------------------------------------------------------------------

def test_cloze_with_explicit_word_bank():
    text = "Complete the passage.\n[word bank: central processing unit (CPU), RAM, ROM]\nThe ... stores data."
    intro, bank, cloze = layouts._parse_cloze_text(text)
    assert intro == "Complete the passage."
    assert bank == ["central processing unit (CPU)", "RAM", "ROM"]
    assert cloze == "The [blank] stores data."


def test_cloze_with_implicit_word_bank_lines():
    text = "Choose words from the list.\nRAM  ROM  cache\nA computer uses [blank] to store data."
    intro, bank, cloze = layouts._parse_cloze_text(text)
    assert intro == "Choose words from the list." and bank == ["RAM", "ROM", "cache"]
    assert cloze.startswith("A computer uses [blank]")


def test_cloze_without_gaps_is_returned_unchanged():
    assert layouts._parse_cloze_text("Describe RAM.") == ("Describe RAM.", None, "")


# --- tick boxes / option rows -------------------------------------------------

@pytest.mark.parametrize("text,fallback,expected", [
    ("Tick (\u2713) one box to show the answer.", 5, 1),
    ("Tick two boxes.", 1, 2),
    ("tick 3 boxes", 1, 3),
    ("State the answer.", 4, 4),
    ("", 0, 1),
])
def test_detect_tick_count(text, fallback, expected):
    assert layouts._detect_tick_count(text, fallback) == expected


@pytest.mark.parametrize("row,expected", [
    ("A a bit", ("A", "a bit")), ("B. a byte", ("B", "a byte")), ("12) twelve", ("12", "twelve")),
    ("no letter prefix", (None, "no letter prefix")), (None, (None, "")),
])
def test_split_option_row(row, expected):
    assert layouts._split_option_row(row) == expected


# --- line matching -----------------------------------------------------------

MATCH_TEXT = ("Draw one line from each device to its use.\n"
              "| Device | Use |\n| Mouse | Pointing |\n| Speaker | Sound output |\n| Scanner | Digitising |")


def test_extract_line_match_columns():
    assert matching._extract_line_match_columns(MATCH_TEXT) == (
        "Device", "Use", ["Mouse", "Speaker", "Scanner"], ["Pointing", "Sound output", "Digitising"])
    assert matching._extract_line_match_columns("| a | b |\n| c | d |") is None            # too few rows
    assert matching._extract_line_match_columns("| a | b | c |\n" * 4) is None            # 3 columns


def test_is_line_match_needs_draw_command_and_prompt():
    assert matching._is_line_match({"command": "Draw"}, MATCH_TEXT) is not None
    assert matching._is_line_match({"command": "Draw lines"}, MATCH_TEXT) is None
    assert matching._is_line_match({"command": "Draw"}, MATCH_TEXT.replace("Draw one line from each", "Link")) is None


def test_slug_key():
    assert matching._slug_key("Sound  output!") == "Sound_output"
    assert matching._slug_key("***") == "x"


def test_line_match_question_renders_matcher():
    html = question._render_question(make_question(command="Draw", text=MATCH_TEXT, layout_type="LineMatching",
                                                   structure_data={}))
    assert 'class="match-grid"' in html and html.count('class="match-box"') + html.count('match-box ') >= 6
    assert 'class="ref-table"' not in html                                   # the pipe table is not shown twice


def test_line_matching_uses_columns_from_structure_data():
    sd = {"left_header": "Stage", "right_header": "Task", "left_items": ["a", "b"], "right_items": ["x", "y", "z"]}
    html = question._render_question(make_question(command="Draw", text="Draw one line from each stage.",
                                                   layout_type="LineMatching", structure_data=sd))
    assert html.count('data-side="L"') == 2 and html.count('data-side="R"') == 3


def test_annotated_diagram_no_longer_turns_into_a_matcher():
    html = question._render_question(make_question(command="Draw", text=MATCH_TEXT, layout_type="AnnotatedDiagram",
                                                   structure_data={"diagram_type": "other"}))
    assert 'class="match-grid"' not in html


def test_working_answer_renders_working_area_labels_and_unit():
    text = ("Convert the two hexadecimal codes to 12-bit binary numbers.\n\n429\n1A3\n\nWorking space")
    sd = {"working_space": True, "answer_labels": ["429", "1A3"], "unit": None}
    html = question._render_question(make_question(text=text, marks=2, command="Convert",
                                                   layout_type="WorkingAnswer", structure_data=sd))
    assert 'name="Q1_work"' in html and 'name="Q1_ans0"' in html and 'name="Q1_ans1"' in html
    assert "Convert the two hexadecimal codes" in html
    body = html.split('<div class="q-input')[0]
    assert ">429<" not in body and "Working space" not in body                # label lines are drawn by the input, not repeated as prose


def test_working_answer_strips_answer_line_with_unit():
    text = "Calculate the file size in kibibytes (KiB). Show all your working.\n\nAnswer [blank] . KiB"
    html = question._render_question(make_question(text=text, marks=3, command="Calculate", layout_type="WorkingAnswer",
                                                   structure_data={"working_space": True, "answer_labels": [], "unit": "KiB"}))
    assert "[blank]" not in html and html.count('class="answer-unit">KiB<') == 1 and 'name="Q1_ans0"' in html


# --- session label -----------------------------------------------------------

@pytest.mark.parametrize("qp,expected", [
    ("0478_m25_qp_22.pdf", "March 2025"), ("0478_s24_qp_11.pdf", "Summer 2024"),
    ("0478_w24_qp_13.pdf", "Winter 2024"), ("weird.pdf", ""), (None, ""),
])
def test_parse_session_label(qp, expected):
    assert page._parse_session_label(qp) == expected


# --- whole pages -------------------------------------------------------------

def test_user_content_is_escaped():
    q = make_question(text='State <script>alert("x")</script> & more.')
    html = r.render_html(make_paper([q]))
    assert "<script>alert" not in html and "&lt;script&gt;" in html


def test_every_layout_type_renders():
    from src.schema import _VALID_LAYOUT_TYPES
    for layout in sorted(_VALID_LAYOUT_TYPES):
        html = r.render_html(make_paper([make_question(layout_type=layout, structure_data={})]))
        assert "Q1" in html, layout


@pytest.mark.parametrize("path", PAPER_PATHS, ids=lambda p: p.stem)
def test_committed_html_matches_renderer(path):
    """Golden test: fails if the renderer changed without re-running render.py
    (or if the JSON changed). Fix with `python render.py output/json`."""
    import json
    html_path = HTML_DIR / f"{path.stem}.html"
    assert html_path.exists(), f"missing {html_path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert r.render_html(data) == html_path.read_text(encoding="utf-8")


def test_real_paper_renders_every_question(real_paper):
    from html import escape
    html = r.render_html(real_paper)
    for q in real_paper["questions"]:
        assert escape(q["id"]) in html


def test_term_def_headers_prefer_structure_data_then_text():
    q = {"text": "Function | Description\nstem"}
    assert layouts._extract_term_def_headers(q, {"headers": ["Name", "Use"]}) == ("Name", "Use")
    assert layouts._extract_term_def_headers(q, {}) == ("Function", "Description")
    assert layouts._extract_term_def_headers({"text": "no table"}, {"headers": [""]}) == ("Term", "Description")


def test_term_def_grid_renders_headers_from_structure_data():
    sd = {"headers": ["Component", "Purpose"], "rows": [{"term": None, "definition": "stores data"}]}
    html = r.render_html(make_paper([make_question(layout_type="TermDefinitionGrid", structure_data=sd, text="Complete the table.")]))
    assert "<th>Component</th><th>Purpose</th>" in html and "stores data" in html


# --- page weight, CDN integrity, ids on mixed-paper pages ---------------------------------

def test_widget_scripts_load_only_when_needed():
    plain = r.render_html(make_paper())
    assert "joint.min.js" not in plain and "circuit.js" not in plain and "match.js" not in plain
    assert "joint.css" not in plain                       # that URL is a 404; never link it
    circuit = make_question(layout_type="AnnotatedDiagram", command="Draw", text="Draw a logic circuit for X = A AND B.",
                            structure_data={"diagram_type": "circuit", "partial_elements": ["A", "B", "X"]})
    html = r.render_html(make_paper([circuit]))
    assert 'class="circuit-editor"' in html and 'integrity="sha384-' in html and 'crossorigin="anonymous"' in html
    assert "circuit.js" in html and "match.js" not in html
    assert r.interactive_script_tags('<div class="match-grid">') == '<script src="match.js"></script>'
    assert r.interactive_script_tags("") == ""


def test_cards_from_different_papers_get_distinct_ids_and_input_names():
    q = make_question("Q1", layout_type="MatrixGrid", text="Tick one box.",
                      structure_data={"matrix_headers": ["Option", "Tick"], "row_count": 2, "rows": ["A one", "B two"]})
    a = r.render_question_card(q, source={"paper": "0478_m24_qp_12", "session": "m24", "variant": "12", "year": "2024"})
    b = r.render_question_card(q, source={"paper": "0478_s25_qp_11", "session": "s25", "variant": "11", "year": "2025"})
    assert 'id="0478_m24_qp_12-Q1"' in a and 'id="0478_s25_qp_11-Q1"' in b
    radios_a = set(re.findall(r'type="radio" name="([^"]+)"', a)); radios_b = set(re.findall(r'type="radio" name="([^"]+)"', b))
    assert radios_a and radios_b and not radios_a & radios_b
    assert '<span class="q-id">Q1</span>' in a and "0478_m24_qp_12.html#Q1" in a      # label and link keep the paper's id
    assert 'id="Q1"' in r.render_question_card(q)                                          # paper pages unchanged


# --- malformed model output never breaks a page -------------------------------

@pytest.mark.parametrize("layout,sd", [
    ("SimpleSingleBlock", {"line_count": "five"}), ("NumberedMultiList", {"list_count": "N"}),
    ("FixedRegisterArray", {"register_size": "8 bits"}), ("LabelledPartResponse", {"labels": 5}),
    ("CodeBlockResponse", {"language": 3}), ("ValueTraceMatrix", {"matrix_headers": ["A"], "row_count": "n"}),
    ("MatrixGrid", None),
])
def test_bad_structure_data_falls_back_instead_of_crashing(layout, sd):
    html = question._render_question(make_question(layout_type=layout, structure_data=sd))
    assert 'class="card"' in html and "<textarea" in html or "<input" in html


def test_bad_text_and_marking_points_do_not_crash():
    answers = {"type": "text", "visuals": [], "scoring_rule": 3, "marking_points": [{"text": None, "marks": 1}, "loose string"]}
    html = question._render_question(make_question(text=None, answers=answers))
    assert "loose string" in html and 'class="mp-item"' in html
