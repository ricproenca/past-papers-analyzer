import json

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


def test_term_def_block_is_authoritative_json():
    block = pr._term_def_block([["Term", "Description"], ["cpu", "...."], ["", "stores data"]])
    payload = json.loads(block.removeprefix("[TERM_DEF_TABLE_DATA]\n").removesuffix("\n[/TERM_DEF_TABLE_DATA]"))
    assert payload == {"headers": ["Term", "Description"],
                       "rows": [{"term": "cpu", "definition": ""}, {"term": "", "definition": "stores data"}]}


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
