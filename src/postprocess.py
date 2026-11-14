"""Deterministic clean-up of the model's Phase 1+2 output.

The model is asked to write only what needs judgement. Everything that is a pure
function of its output or of the PDF is filled in here, for free and without
transcription errors:
    - topic names come from src/syllabus.py
    - command words are reduced to their canonical form
    - TermDefinitionGrid contents are copied from the PDF tables
"""

from collections import defaultdict

from .enricher import canonical_command
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


def postprocess_phase12(data: dict, pages: list[dict]) -> list[str]:
    """Run every step; returns ids of TermDefinitionGrid questions that could not be paired."""
    fill_topic_names(data)
    canonicalise_commands(data)
    return fill_term_def_grids(data, pages)
