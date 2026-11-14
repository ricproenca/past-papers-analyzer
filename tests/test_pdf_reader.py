import fitz
import pytest

from src import pdf_reader as pr


# --- _annotate_anchors -------------------------------------------------------

def test_callout_line_becomes_labelled_part_response():
    out = pr._annotate_anchors("a ..... b ..... c .....")
    assert out.startswith("[LAYOUT:LabelledPartResponse labels=a,b,c]\n")
    assert out.count("[blank]") == 3 and "...." not in out


def test_labeled_block_lists_unique_labels():
    out = pr._annotate_anchors("Justification ......\nExplanation ......\n")
    assert "[LAYOUT:MultiPartLabeledBlock labels=Justification,Explanation]" in out


def test_numbered_block_counts_slots():
    out = pr._annotate_anchors("1 ......\n2 ......\n3 ......\n")
    assert "[LAYOUT:NumberedMultiList count=3]" in out


def test_inline_cloze_counts_gaps():
    out = pr._annotate_anchors("A computer uses ........ to store ........ data.")
    assert "[LAYOUT:InlineCloze gap_count=2]" in out


def test_each_cloze_passage_gets_its_own_annotation():
    page = ("2 Complete the sentence.\nA computer uses ........ to store data.\n[1]\n"
            "3 Complete the table.\nThe first section is called the ........ and has ........ bits.\n[2]\n")
    out = pr._annotate_anchors(page)
    assert out.count("[LAYOUT:InlineCloze") == 2
    assert out.index("gap_count=1]") < out.index("3 Complete the table.") < out.index("gap_count=2]")


def test_cloze_passage_wrapped_over_dotless_lines_is_one_block():
    page = ("The CPU ........ instructions and\nthen it ........ the result\nbefore the ........ is read. [3]\n")
    out = pr._annotate_anchors(page)
    assert out.count("[LAYOUT:InlineCloze") == 1 and "gap_count=3]" in out


def test_cloze_without_trailing_mark_is_still_annotated():
    out = pr._annotate_anchors("Intro.\nUses ........ here.\nUses ........ there.\n")
    assert out.count("[LAYOUT:InlineCloze gap_count=2]") == 1


def test_table_cell_next_to_answer_dots_is_not_a_cloze():
    cells = pr._table_cell_texts([[["", "The surface of each platter is divided into tracks and sectors."]]])
    line = "........ sectors."
    assert pr._is_table_fragment(line, cells)
    assert "InlineCloze" not in pr._annotate_anchors(line, cells)
    assert "InlineCloze" in pr._annotate_anchors(line)                      # without table info it still looks like one
    assert "InlineCloze" in pr._annotate_anchors("Uses ........ here.", cells)   # real cloze text is unaffected


def test_table_cell_texts_skips_blank_and_dotted_cells():
    cells = pr._table_cell_texts([[["Term", "...."], [" a\n b ", None]], None])
    assert cells == ["Term", "a b"]


def test_consecutive_dot_lines_are_a_single_block():
    out = pr._annotate_anchors("Explain.\n.....\n.....\n.....\n")
    assert "[LAYOUT:SimpleSingleBlock line_count=3]" in out
    assert "InlineCloze" not in out


def test_text_without_answer_dots_is_untouched():
    text = "Describe the fetch stage.\n[2]"
    assert pr._annotate_anchors(text) == text


# --- table helpers -----------------------------------------------------------

@pytest.mark.parametrize("cell,expected", [
    ("....", ""), ("\u2026\u2026", ""), (None, ""), ("  ", ""),
    ("two\nlines", "two lines"), ("  keep  ", "keep"),
])
def test_clean_cell(cell, expected):
    assert pr._clean_cell(cell) == expected


@pytest.mark.parametrize("table,expected", [
    ([], "MatrixGrid"),
    ([["Term", "Definition"], ["a", ""]], "TermDefinitionGrid"),
    ([["Function name", "Description"], ["a", ""]], "TermDefinitionGrid"),
    ([["PC", "ACC", "IX"], ["", "", ""]], "ValueTraceMatrix"),
    ([["Statement", "True", "False"], ["a", "", ""]], "MatrixGrid"),
    ([["Code", "City"], ["A1", "Paris"], ["B2", "Rome"]], "DataReferenceTable"),
    ([[""] * 8], "FixedRegisterArray register_size=8"),
    ([["b%d" % i for i in range(16)], [""] * 16], "FixedRegisterArray register_size=16"),
])
def test_classify_table(table, expected):
    assert pr._classify_table(table) == expected


def test_table_to_markdown_blanks_answer_cells():
    md = pr._table_to_markdown([["A", "B"], ["x", "...."]])
    assert md.splitlines() == ["| A | B |", "|---|---|", "| x |  |"]


def test_term_def_data_is_authoritative():
    data = pr._term_def_data([["Term", "Description"], ["cpu", "...."], ["", "stores data"]])
    assert data == {"headers": ["Term", "Description"],
                    "rows": [{"term": "cpu", "definition": None}, {"term": None, "definition": "stores data"}]}


# --- boilerplate cleaning ------------------------------------------------------

def test_clean_page_text_drops_boilerplate_only():
    raw = "\n".join([
        "(cid:44)(cid:1)(cid:1)(cid:9)",                 # glyph-id noise only -> dropped
        "* 0000800000006 *",
        "NIGRAM", "SIHT", "NI", "ETIRW", "TON", "OD",
        "1 (a) State what ROM(cid:12) stands for.",       # content with a stray glyph id -> kept, cleaned
        "BLANK PAGE",
        "\u00a9 UCLES 2025 0478/13/O/N/25 [Turn over",
        "\u00a9 Cambridge University Press & Assessment 2025 Page 3 of 9",
        "PUBLISHED",
        "Explain why OD and NI are not abbreviations here.",   # contains the tokens inside a sentence -> kept
        "Permission to reproduce items where third-party owned material...",
        "This text after the copyright notice is dropped.",
    ])
    assert pr.clean_page_text(raw).split("\n") == [
        "1 (a) State what ROM stands for.",
        "Explain why OD and NI are not abbreviations here.",
    ]


def test_clean_page_text_handles_empty():
    assert pr.clean_page_text("") == "" and pr.clean_page_text(None) == ""


@pytest.mark.parametrize("text,curves,page,expected", [
    ("Draw a logic circuit.", 0, 5, True),
    ("Complete the flowchart shown below.", 0, 3, True),
    ("State one use of RAM.", 0, 4, False),
    ("State one use of RAM.", 40, 4, True),            # an illustration made of many curves
    ("Draw on the cover page", 0, 1, False),            # cover page never counts
])
def test_has_diagram(text, curves, page, expected):
    assert pr._has_diagram(text, curves, page) is expected


def test_drop_ms_preamble_keeps_pages_from_the_answer_table():
    pages = [{"page": 1, "text": "MARK SCHEME"}, {"page": 2, "text": "Generic Marking Principles"},
             {"page": 3, "text": "Question Answer Marks\n1(a) ..."}, {"page": 4, "text": "2(a) ..."}]
    assert [p["page"] for p in pr.drop_ms_preamble(pages)] == [3, 4]
    no_table = [{"page": 1, "text": "x"}]
    assert pr.drop_ms_preamble(no_table) == no_table


# --- extract_pages / render_pages_to_pngs on a generated PDF -----------------

@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "sample.pdf"
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 100), "1 (a) Describe RAM.")
    p1.insert_text((72, 130), "...........................................................")
    p1.insert_text((72, 160), "...........................................................")
    p1.insert_text((72, 190), "A computer stores ............ data. [2]")
    doc.new_page().insert_text((72, 100), "Second page")
    doc.save(path)
    return path


def test_extract_pages_annotates_and_strips_dots(sample_pdf):
    pages = pr.extract_pages(str(sample_pdf))
    assert [p["page"] for p in pages] == [1, 2]
    t = pages[0]["text"]
    assert "[LAYOUT:SimpleSingleBlock line_count=2]" in t
    assert "[LAYOUT:InlineCloze gap_count=1]" in t
    assert "...." not in t and "[blank]" in t
    assert pages[0]["has_table"] is False and pages[0]["has_image"] is False
    assert pages[1]["text"].strip() == "Second page"


def test_render_pages_to_pngs(sample_pdf, tmp_path):
    out = tmp_path / "png"
    result = pr.render_pages_to_pngs(sample_pdf, [2, 1, 2, 99, 0], out)
    assert sorted(result) == [1, 2]                       # dedup'd, out-of-range skipped
    assert all(p.exists() and p.stat().st_size > 0 for p in result.values())
    mtime = result[1].stat().st_mtime_ns
    pr.render_pages_to_pngs(sample_pdf, [1], out)
    assert result[1].stat().st_mtime_ns == mtime           # idempotent: existing PNG kept


def test_extract_pages_exposes_flags_and_term_def_tables(sample_pdf):
    pages = pr.extract_pages(str(sample_pdf))
    assert all({"has_table", "has_image", "has_diagram", "term_def_tables"} <= p.keys() for p in pages)
    assert pages[0]["term_def_tables"] == []


def test_render_pages_to_png_bytes(sample_pdf):
    out = pr.render_pages_to_png_bytes(sample_pdf, [2, 1, 99, 0])
    assert sorted(out) == [1, 2] and all(b.startswith(b"\x89PNG") for b in out.values())
