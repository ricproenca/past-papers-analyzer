import re

import pdfplumber
from typing import List, Dict, Any

_REGISTER_NAMES = frozenset({'PC', 'ACC', 'IX', 'MAR', 'MDR', 'CIR', 'SR'})
_TERM_DEF_HEADERS = frozenset({'TERM', 'DEFINITION'})

# Labeled answer slots: "Justification: ....." / "Benefit: ....." etc.
_RE_LABELED_BLOCK = re.compile(
    r'(?:^(?:Justification|Explanation|Benefit|Drawback|Advantage|Disadvantage)'
    r'\s*:[ \t]*\.{4,}[ \t]*$\n?)+',
    re.IGNORECASE | re.MULTILINE,
)

# Numbered answer slots: "1   ....." / "2   ....." etc.
_RE_NUMBERED_BLOCK = re.compile(
    r'(?:^\d[ \t]+\.{4,}[ \t]*$\n?)+',
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

# Inline callout slots: "a ..... b ..... c ....." — single letters each followed by dots on one line
_RE_CALLOUT_LINE = re.compile(
    r'(?m)^[a-zA-Z][ \t]+\.{4,}(?:[ \t]+[a-zA-Z][ \t]+\.{4,}){1,}[ \t]*$'
)


def _annotate_anchors(raw_text: str) -> str:
    """Insert [LAYOUT:TYPE ...] tokens inline before answer-space patterns.

    Runs before the dot-stripping regex so structural signals are preserved
    for Claude. Order matters: labeled > numbered > cloze > simple block.
    """
    text = raw_text

    # Pass 1 — LabelledPartResponse: "a ..... b ..... c ....." on one line
    def _replace_callout(m: re.Match) -> str:
        line = m.group(0)
        labels = re.findall(r'(?<!\w)([a-zA-Z])(?=[ \t]+\.{4,})', line)
        return f'[LAYOUT:LabelledPartResponse labels={",".join(labels)}]\n' + line

    text = _RE_CALLOUT_LINE.sub(_replace_callout, text)

    # Pass 3 — MultiPartLabeledBlock
    def _replace_labeled(m: re.Match) -> str:
        block = m.group(0)
        labels = re.findall(
            r'^(Justification|Explanation|Benefit|Drawback|Advantage|Disadvantage)\s*:',
            block, re.IGNORECASE | re.MULTILINE,
        )
        unique = list(dict.fromkeys(lbl.capitalize() for lbl in labels))
        return f'[LAYOUT:MultiPartLabeledBlock labels={",".join(unique)}]\n' + block

    text = _RE_LABELED_BLOCK.sub(_replace_labeled, text)

    # Pass 4 — NumberedMultiList
    def _replace_numbered(m: re.Match) -> str:
        block = m.group(0)
        count = len(re.findall(r'(?m)^\d', block))
        return f'[LAYOUT:NumberedMultiList count={count}]\n' + block

    text = _RE_NUMBERED_BLOCK.sub(_replace_numbered, text)

    # Pass 5 — InlineCloze (dots mid-sentence; after labeled/numbered passes so
    # those patterns don't interfere — label lines have no letters after dots)
    cloze_lines = _RE_INLINE_CLOZE_LINE.findall(text)
    if cloze_lines:
        gap_count = sum(len(re.findall(r'\.{4,}', ln)) for ln in cloze_lines)
        first = _RE_INLINE_CLOZE_LINE.search(text)
        if first:
            annotation = f'[LAYOUT:InlineCloze gap_count={gap_count}]\n'
            text = text[: first.start()] + annotation + text[first.start() :]

    # Pass 6 — SimpleSingleBlock (2+ consecutive dot-only lines not yet annotated)
    def _replace_consec(m: re.Match) -> str:
        block = m.group(0)
        line_count = block.count('\n') or 1
        return f'[LAYOUT:SimpleSingleBlock line_count={line_count}]\n' + block

    text = _RE_CONSEC_DOTS.sub(_replace_consec, text)

    return text


def _classify_table(table: list) -> str:
    """Return a TABLE_TYPE annotation string for a pdfplumber table."""
    if not table:
        return "MatrixGrid"

    first_row = table[0]
    ncols = len(first_row)

    # FixedRegisterArray: 8 or 16 columns, all data cells empty
    if ncols in (8, 16):
        data_rows = table[1:]
        if data_rows and all(
            not str(cell or "").strip()
            for row in data_rows
            for cell in row
        ):
            return f"FixedRegisterArray register_size={ncols}"

    header_tokens = {str(cell or "").strip().upper() for cell in first_row}

    # TermDefinitionGrid: exactly "Term" and "Definition" columns
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
        cells = [str(cell or "").strip() for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


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
                        table_parts.append(f"[TABLE_TYPE:{ttype}]\n{md}")
                if table_parts:
                    text = text + "\n\n[TABLES]\n" + "\n\n".join(table_parts)

            pages.append({
                "page": i,
                "text": text,
                "has_table": bool(tables),
                "has_image": bool(images),
            })
    return pages
