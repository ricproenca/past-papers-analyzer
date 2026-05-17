import json
import re

import pdfplumber
from typing import List, Dict, Any

_REGISTER_NAMES = frozenset({'PC', 'ACC', 'IX', 'MAR', 'MDR', 'CIR', 'IR', 'SR'})
_TERM_DEF_HEADERS = frozenset({'TERM', 'DEFINITION'})
# Right-column header signatures that identify a TermDefinitionGrid even when the
# left header isn't literally "Term" (e.g. "Function name | Description").
_TERM_DEF_RIGHT_RE = re.compile(r"descrip|defin", re.IGNORECASE)
# Characters that make up a Cambridge "blank-line" cell when nothing else is printed:
# unicode horizontal ellipsis, ASCII dot/period, whitespace.
_BLANK_CELL_RE = re.compile(r"^[\s.…]*$")

# Generic labeled answer slots: 2+ consecutive lines like "Label ....." or "Label: ....."
# The label is a capitalized word or short phrase (Justification, Primary storage, Input, etc.).
_RE_LABELED_BLOCK = re.compile(
    r'(?:^[A-Z][a-zA-Z][a-zA-Z\- ]{0,30}?\s*:?[ \t]+\.{4,}[ \t]*$\n?){2,}',
    re.MULTILINE,
)
_RE_LABEL_EXTRACT = re.compile(
    r'^([A-Z][a-zA-Z][a-zA-Z\- ]{0,30}?)\s*:?[ \t]+\.{4,}',
    re.MULTILINE,
)

# Numbered answer slots: "1 ....." / "2 ....." etc. (supports 1- or 2-digit indices)
_RE_NUMBERED_BLOCK = re.compile(
    r'(?:^\d{1,2}[ \t]+\.{4,}[ \t]*$\n?)+',
    re.MULTILINE,
)

# Dots mid-sentence: text before AND meaningful text (letters) after the dots
_RE_INLINE_CLOZE_LINE = re.compile(
    r'^(?![ \t]*\.{4,}[ \t]*(?:\[\d+\])?[ \t]*$)'  # exclude dot-only lines
    r'.*\.{4,}.*[a-zA-Z].*$',
    re.MULTILINE,
)

# Two or more consecutive dot-only lines (SimpleSingleBlock)
_RE_CONSEC_DOTS = re.compile(
    r'(?:^[ \t]*\.{4,}[ \t]*$\n?){2,}',
    re.MULTILINE,
)

# Inline callout slots: "a ..... b ..... c ....." — alphanumeric tokens each followed by dots on one line
_RE_CALLOUT_LINE = re.compile(
    r'(?m)^[A-Za-z0-9][ \t]+\.{4,}(?:[ \t]+[A-Za-z0-9][ \t]+\.{4,}){1,}[ \t]*$'
)


def _annotate_anchors(raw_text: str) -> str:
    """Insert [LAYOUT:TYPE ...] tokens inline before answer-space patterns.

    Runs before the dot-stripping regex so structural signals are preserved
    for Claude. Order matters: callout > labeled > numbered > cloze > simple.
    LabelledPartResponse runs first because its single-line "a ..... b ....."
    pattern could otherwise be partially consumed by InlineCloze.
    """
    text = raw_text

    # Pass 1 — LabelledPartResponse: "a ..... b ..... c ....." on one line.
    # Pre-strip the dots so subsequent passes (especially InlineCloze) don't double-match.
    def _replace_callout(m: re.Match) -> str:
        line = m.group(0)
        labels = re.findall(r'(?<!\w)([A-Za-z0-9])(?=[ \t]+\.{4,})', line)
        cleaned = re.sub(r'\.{4,}', '[blank]', line)
        return f'[LAYOUT:LabelledPartResponse labels={",".join(labels)}]\n' + cleaned

    text = _RE_CALLOUT_LINE.sub(_replace_callout, text)

    # Pass 2 — MultiPartLabeledBlock: 2+ consecutive "Label ....." lines (generic)
    def _replace_labeled(m: re.Match) -> str:
        block = m.group(0)
        raw_labels = _RE_LABEL_EXTRACT.findall(block)
        unique = list(dict.fromkeys(lbl.strip() for lbl in raw_labels))
        return f'[LAYOUT:MultiPartLabeledBlock labels={",".join(unique)}]\n' + block

    text = _RE_LABELED_BLOCK.sub(_replace_labeled, text)

    # Pass 3 — NumberedMultiList: "1 ....." / "2 ....."
    def _replace_numbered(m: re.Match) -> str:
        block = m.group(0)
        count = len(re.findall(r'(?m)^\d', block))
        return f'[LAYOUT:NumberedMultiList count={count}]\n' + block

    text = _RE_NUMBERED_BLOCK.sub(_replace_numbered, text)

    # Pass 4 — InlineCloze: dots mid-sentence with letters after
    cloze_lines = _RE_INLINE_CLOZE_LINE.findall(text)
    if cloze_lines:
        gap_count = sum(len(re.findall(r'\.{4,}', ln)) for ln in cloze_lines)
        first = _RE_INLINE_CLOZE_LINE.search(text)
        if first:
            annotation = f'[LAYOUT:InlineCloze gap_count={gap_count}]\n'
            text = text[: first.start()] + annotation + text[first.start() :]

    # Pass 5 — SimpleSingleBlock: 2+ consecutive dot-only lines not yet annotated
    def _replace_consec(m: re.Match) -> str:
        block = m.group(0)
        line_count = block.count('\n') or 1
        return f'[LAYOUT:SimpleSingleBlock line_count={line_count}]\n' + block

    text = _RE_CONSEC_DOTS.sub(_replace_consec, text)

    return text


def _is_blank_cell(cell) -> bool:
    """A cell counts as 'blank' when its only content is a dotted answer line
    (Cambridge prints these as runs of '.' or U+2026 ellipsis) or pure whitespace."""
    return bool(_BLANK_CELL_RE.match(str(cell or "")))


def _clean_cell(cell) -> str:
    """Return the cell text with line-joining whitespace collapsed, or '' if blank."""
    if _is_blank_cell(cell):
        return ""
    return re.sub(r"\s+", " ", str(cell)).strip()


def _classify_table(table: list) -> str:
    """Return a TABLE_TYPE annotation string for a pdfplumber table."""
    if not table:
        return "MatrixGrid"

    first_row = table[0]
    ncols = len(first_row)

    # FixedRegisterArray: 8 or 16 columns with at least one fully-empty answer row
    # (the row of bit boxes); handles both single-row and header+data layouts
    if ncols in (8, 16):
        answer_rows = table if len(table) == 1 else table[1:]
        if answer_rows and all(
            not str(cell or "").strip()
            for row in answer_rows
            for cell in row
        ):
            return f"FixedRegisterArray register_size={ncols}"

    header_tokens = {str(cell or "").strip().upper() for cell in first_row}

    # TermDefinitionGrid: two columns, right header looks like "Description"/"Definition".
    # Covers literal "Term | Definition" AND variants like "Function name | Description",
    # "Component | Description", "Internet term | Description", etc.
    if ncols == 2 and _TERM_DEF_RIGHT_RE.search(str(first_row[1] or "")):
        return "TermDefinitionGrid"
    # Backward-compat fallback in case headers ever come through reordered.
    if _TERM_DEF_HEADERS <= header_tokens:
        return "TermDefinitionGrid"

    # ValueTraceMatrix: header row contains known register names
    if header_tokens & _REGISTER_NAMES:
        return "ValueTraceMatrix"

    return "MatrixGrid"


def _table_to_markdown(table: list) -> str:
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [_clean_cell(cell) for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


def _term_def_block(table: list) -> str:
    """Build the authoritative [TERM_DEF_TABLE_DATA] JSON block for a TermDefinitionGrid table.

    Every cell is either a verbatim string of the printed text OR "" for a blank
    answer line. The model is instructed (in prompts.py) to copy this verbatim into
    structure_data.rows, converting "" to null."""
    if not table or len(table) < 2:
        return ""
    header_row = table[0]
    headers = [_clean_cell(c) for c in header_row]
    rows = []
    for raw_row in table[1:]:
        if len(raw_row) < 2:
            continue
        left  = _clean_cell(raw_row[0])
        right = _clean_cell(raw_row[1])
        rows.append({"term": left, "definition": right})
    payload = {"headers": headers, "rows": rows}
    return (
        "[TERM_DEF_TABLE_DATA]\n"
        + json.dumps(payload, ensure_ascii=False)
        + "\n[/TERM_DEF_TABLE_DATA]"
    )


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw = page.extract_text() or ""
            text = _annotate_anchors(raw)
            text = re.sub(r'(?m)^\s*\.{4,}\s*(\[\d+\])\s*$', r'\1', text)
            text = re.sub(r'(?m)^\s*\.{4,}\s*$\n?', '', text)
            text = re.sub(r'(?m)^([A-Za-z0-9][A-Za-z0-9 \-]*?)\.{4,}\s*(\[\d+\])\s*$',
                          lambda m: f"{m.group(1).rstrip()} {m.group(2)}", text)
            text = re.sub(r'(?m)^([A-Za-z0-9][A-Za-z0-9 \-]*?)\.{4,}\s*$',
                          lambda m: m.group(1).rstrip(), text)
            text = re.sub(r'\.{4,}', '[blank]', text)
            text = re.sub(r'\n{3,}', '\n\n', text)

            tables = page.extract_tables()
            images = page.images

            if tables:
                table_parts = []
                for t in tables:
                    if not t:
                        continue
                    ttype = _classify_table(t)
                    md = _table_to_markdown(t)
                    if md:
                        part = f"[TABLE_TYPE:{ttype}]\n{md}"
                        if ttype == "TermDefinitionGrid":
                            block = _term_def_block(t)
                            if block:
                                part = part + "\n" + block
                        table_parts.append(part)
                if table_parts:
                    text = text + "\n\n[TABLES]\n" + "\n\n".join(table_parts)

            pages.append({
                "page": i,
                "text": text,
                "has_table": bool(tables),
                "has_image": bool(images),
            })
    return pages
