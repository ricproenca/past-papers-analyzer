"""Deterministic clean-up of the model's Phase 1+2 output.

The model is asked to write only what needs judgement. Everything that is a pure
function of its output or of the PDF is filled in here, for free and without
transcription errors:
    - topic names come from src/syllabus.py
    - command words are reduced to their canonical form
    - TermDefinitionGrid contents are copied from the PDF tables
    - subject code and variant come from the Cambridge file name
    - line-matching questions get the layout the renderer draws them with
    - text the model wrote that is not on the paper (e.g. a flowchart summary) is removed
"""

import re
from collections import defaultdict

from .enricher import canonical_command
from .renderer.matching import _is_line_match
from .syllabus import TOPIC_NAMES

def fill_topic_names(data: dict) -> None:
    for q in data.get("questions", []):
        name = TOPIC_NAMES.get(q.get("topic"))
        if name:
            q["topic_name"] = name


def canonicalise_commands(data: dict) -> None:
    for q in data.get("questions", []):
        q["command"] = canonical_command(q.get("command"))


def fill_term_def_grids(data: dict, pages: list[dict]) -> list[str]:
    """Copy headers/rows of TermDefinitionGrid tables from the PDF into the questions.

    Tables and questions are paired by page and reading order. When the counts on
    a page differ the pairing is ambiguous, so those questions are left untouched
    and their ids are returned (the caller prints a warning)."""
    tables_by_page = {p["page"]: list(p.get("term_def_tables") or []) for p in pages}
    questions_by_page = defaultdict(list)
    for q in data.get("questions", []):
        if q.get("layout_type") == "TermDefinitionGrid":
            questions_by_page[q.get("page")].append(q)

    unmatched = []
    for page, qs in questions_by_page.items():
        tables = tables_by_page.get(page, [])
        if len(tables) != len(qs):
            unmatched += [q["id"] for q in qs]
            continue
        for q, table in zip(qs, tables):
            q["structure_data"] = {
                "row_count": len(table["rows"]),
                "rows": [dict(r) for r in table["rows"]],
                "headers": list(table["headers"]),
            }
    return unmatched


_QP_NAME_RE = re.compile(r"^(\d{4})_[a-z]\d{2}_qp_(\d{2})\.pdf$", re.IGNORECASE)


def fill_paper_identity(data: dict) -> list[str]:
    """Take subject_code/variant from a Cambridge file name (e.g. 0478_w25_qp_12.pdf).
    The name is authoritative; returns a note for every value the model got wrong."""
    m = _QP_NAME_RE.match(data.get("qp") or "")
    if not m:
        return []
    notes = []
    for key, value in (("subject_code", m.group(1)), ("variant", m.group(2))):
        if str(data.get(key) or "") != value:
            if data.get(key) not in (None, ""):
                notes.append(f"{key}: model wrote {data.get(key)!r}, file name says {value!r}")
            data[key] = value
    return notes


def fix_line_matching_layouts(data: dict) -> list[str]:
    """"Draw one line from each X to Y" questions are drawn with the interactive
    matcher, which belongs to AnnotatedDiagram; the model sometimes picks MatrixGrid
    because the two columns look like a table. Returns the ids it corrected."""
    fixed = []
    for q in data.get("questions", []):
        if q.get("layout_type") != "AnnotatedDiagram" and _is_line_match(q, q.get("text") or ""):
            q["layout_type"] = "AnnotatedDiagram"
            q["structure_data"] = {"diagram_type": "other", "partial_elements": []}
            fixed.append(q.get("id"))
    return fixed


_WORD_RE = re.compile(r"[a-z0-9]+")
_MARKER_RE = re.compile(r"\[blank\]|\[LAYOUT:[^\]]*\]|\[TABLE_TYPE:[^\]]*\]")
_SENTENCE_RE = re.compile(r"(?<=[.?!])\s+")


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(_MARKER_RE.sub(" ", (text or "").lower()))


def _trigrams(words: list[str]) -> set:
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


def _sourced(text: str, source: set, threshold: float) -> bool:
    grams = _trigrams(_words(text))
    return not grams or sum(1 for g in grams if g in source) / len(grams) >= threshold


def drop_unsourced_text(data: dict, pages: list[dict], min_words: int = 8, threshold: float = 0.5) -> list[tuple[str, str]]:
    """Remove prose the model wrote that is not printed on the paper.

    "text" must be verbatim, yet the model occasionally adds its own summary of a
    flowchart or diagram. A paragraph whose word trigrams mostly do not occur anywhere
    in the paper's extracted text is checked sentence by sentence and its unsourced
    sentences are dropped. Measured: 0 hits on 15 committed papers, every invented
    flowchart summary caught (coverage 0.02-0.08). Returns [(id, removed text)]."""
    source = _trigrams(_words(" ".join(p.get("text", "") for p in pages)))
    removed = []
    for q in data.get("questions", []):
        paragraphs = re.split(r"(\n\s*\n)", q.get("text") or "")
        changed = False
        for k in range(0, len(paragraphs), 2):
            para = paragraphs[k]
            if len(_words(para)) < min_words or _sourced(para, source, threshold):
                continue
            kept = [s for s in _SENTENCE_RE.split(para) if _sourced(s, source, threshold)]
            dropped = para if not kept else " ".join(s for s in _SENTENCE_RE.split(para) if s not in kept)
            removed.append((q.get("id"), dropped))
            paragraphs[k] = " ".join(kept)
            changed = True
        if changed:
            text = "".join(paragraphs)
            q["text"] = re.sub(r"(\n\s*\n){2,}", "\n\n", text).strip()
    return removed


def postprocess_phase12(data: dict, pages: list[dict]) -> list[str]:
    """Run every step; returns ids of TermDefinitionGrid questions that could not be paired."""
    for note in fill_paper_identity(data):
        print(f"[!] Paper identity corrected — {note}")
    fill_topic_names(data)
    canonicalise_commands(data)
    for qid, text in drop_unsourced_text(data, pages):
        print(f"[!] {qid}: removed text that is not on the paper: {text[:100]!r}")
    for qid in fix_line_matching_layouts(data):
        print(f"[!] {qid}: line-matching question re-labelled AnnotatedDiagram")
    return fill_term_def_grids(data, pages)
