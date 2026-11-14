import re
from pathlib import Path

import pdfplumber
from typing import List, Dict, Any, Iterable

_REGISTER_NAMES = frozenset({'PC', 'ACC', 'IX', 'MAR', 'MDR', 'CIR', 'IR', 'SR'})
_TERM_DEF_HEADERS = frozenset({'TERM', 'DEFINITION'})
# Right-column header signatures that identify a TermDefinitionGrid even when the
# left header isn't literally "Term" (e.g. "Function name | Description").
_TERM_DEF_RIGHT_RE = re.compile(r"descrip|defin", re.IGNORECASE)
# Characters that make up a Cambridge "blank-line" cell when nothing else is printed:
# unicode horizontal ellipsis, ASCII dot/period, whitespace.
_TICK_MARKS = frozenset({"\u2713", "\u2714", "x", "X"})
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


_RE_MARK_AT_END = re.compile(r'\[\d+\][ \t]*$')


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _table_cell_texts(tables: list) -> list[str]:
    """Normalised text of every fully printed (dot-free, non-blank) table cell."""
    cells = []
    for table in tables or []:
        for row in table or []:
            for cell in row or []:
                t = _norm(str(cell or ""))
                if t and "...." not in t and "\u2026" not in t:
                    cells.append(t)
    return cells


def _is_table_fragment(line: str, cell_texts: list[str]) -> bool:
    """True when `line` is just a printed table cell sharing a text line with an
    answer-dot run in the next column (e.g. '........ sectors.') — not a cloze."""
    rest = _norm(re.sub(r"\.{4,}", " ", line))
    return len(rest) >= 4 and any(rest in cell for cell in cell_texts)


_RE_GAP = re.compile(r'\.{4,}')
_RE_ADJACENT_GAPS = re.compile(r'\.{4,}(?:[ \t]+\.{4,})+')


def normalise_gaps(text: str) -> str:
    """Make every printed answer gap a single run of dots.

    Some papers print gaps with the ellipsis character (U+2026) instead of dots, and a
    long gap is often printed as two dotted runs side by side ("........ ........"),
    which is one answer, not two (the marks confirm it)."""
    text = text.replace("\u2026", "...")
    return _RE_ADJACENT_GAPS.sub("." * 8, text)


def _annotate_cloze_blocks(text: str, cell_texts: list[str] = ()) -> str:
    """Insert `[LAYOUT:InlineCloze gap_count=N]` before each fill-in-the-gap passage.

    A passage starts at its first cloze line (dots mid-sentence) — or at the prose
    lines just above it that END in a gap — and runs up to and including the line
    that carries the question's mark "[n]". Every gap inside the passage counts,
    including one at the end of a line ("... sent to the ........ ."). Wrapped lines
    without dots belong to the same passage; text after a mark starts a new one."""
    lines = text.split("\n")

    def gaps(line: str) -> int:
        return len(_RE_GAP.findall(line))

    def words_outside_gaps(line: str) -> int:
        return len(re.findall(r"[A-Za-z]{2,}", _RE_GAP.sub(" ", line)))

    def is_cloze(line: str) -> bool:
        return bool(_RE_INLINE_CLOZE_LINE.fullmatch(line)) and not _is_table_fragment(line, cell_texts)

    def is_prose_ending_in_gap(line: str) -> bool:
        return gaps(line) > 0 and words_outside_gaps(line) >= 3 and not _is_table_fragment(line, cell_texts)

    def has_text(line: str) -> bool:
        return bool(_RE_GAP.sub("", line).strip())       # anything besides the dots ("........ ." counts)

    blocks = []                # [(index of first line, [indexes of its gap lines])]
    current = None             # [first_index, [gap line indexes]]
    for i, line in enumerate(lines):
        if current is None and is_cloze(line):
            # Walk back over the wrapped lines of the same paragraph (at most 6) to
            # the earliest one that ends in a gap; stop at a mark, a blank line or
            # another annotation.
            first = i
            for j in range(i - 1, max(i - 7, -1), -1):
                prev = lines[j]
                if not prev.strip() or prev.startswith("[LAYOUT:") or _RE_MARK_AT_END.search(prev):
                    break
                if is_prose_ending_in_gap(prev):
                    first = j
            current = [first, [k for k in range(first, i) if gaps(lines[k])]]
        if current is not None and gaps(line) and has_text(line) and not _is_table_fragment(line, cell_texts):
            current[1].append(i)
        if current is not None and _RE_MARK_AT_END.search(line):
            blocks.append(tuple(current))
            current = None
    if current is not None:
        blocks.append(tuple(current))
    for first, gap_lines in reversed(blocks):
        # Write the gaps as [blank] here, so the answer-label rules that run later
        # cannot mistake a line ending in a gap for a label and strip it.
        for k in gap_lines:
            lines[k] = _RE_GAP.sub("[blank]", lines[k])
        gap_count = sum(lines[k].count("[blank]") for k in gap_lines)
        lines.insert(first, f'[LAYOUT:InlineCloze gap_count={gap_count}]')
    return "\n".join(lines)


def _annotate_anchors(raw_text: str, cell_texts: list[str] = ()) -> str:
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

    # Pass 4 — InlineCloze: dots mid-sentence with letters after.
    # One annotation per cloze passage: a passage ends at the line carrying its
    # mark "[n]", so two cloze questions on one page get separate gap counts.
    text = _annotate_cloze_blocks(text, cell_texts)

    # Pass 5 — SimpleSingleBlock: 2+ consecutive dot-only lines not yet annotated
    # (WorkingAnswer when the lines follow a printed "Working space" label)
    def _replace_consec(m: re.Match) -> str:
        block = m.group(0)
        line_count = block.count('\n') or 1
        before = m.string[:m.start()].rstrip().rsplit("\n", 1)[-1].strip()
        if before.lower() == "working space":
            return '[LAYOUT:WorkingAnswer working_space=true]\n' + block
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

    body = [[_clean_cell(c) for c in row] for row in table[1:]]
    has_blank = any(not c for row in body for c in row)

    # TermDefinitionGrid by shape: two columns, some answer cells blank, and printed
    # text either in the right column or beside a blank left cell ("type | statement").
    # A tick-box MCQ (options left, empty tick column right) does not match.
    if ncols == 2 and body and has_blank and any(
        (len(row) > 1 and row[1] and row[1] not in _TICK_MARKS) or (row and not row[0])
        for row in body
    ):
        return "TermDefinitionGrid"

    # DataReferenceTable: a lookup/context table provided in the question where every
    # data cell is prefilled (no blank answer slots). These are NOT answer formats —
    # they appear before sub-questions to give students data to work with.
    if body and not has_blank:
        return "DataReferenceTable"

    # Fill-in grid: values already printed beside the blanks (parity bytes, truth
    # tables, conversion tables, test-data tables) — the student writes values, not ticks.
    if body and any(c and c not in _TICK_MARKS for row in body for c in row[1:]):
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


def _term_def_data(table: list) -> dict:
    """Headers and rows of a TermDefinitionGrid table. Each cell is the verbatim
    printed text, or None for a blank answer cell."""
    headers = [_clean_cell(c) for c in table[0]] if table else []
    rows = []
    for raw_row in table[1:]:
        if len(raw_row) < 2:
            continue
        rows.append({"term": _clean_cell(raw_row[0]) or None,
                     "definition": _clean_cell(raw_row[1]) or None})
    return {"headers": headers[:2], "rows": rows}


# --- page-text cleaning ---------------------------------------------------------
# Boilerplate that carries no exam content but costs tokens on every page.
_CID_RE = re.compile(r"\(cid:\d+\)")
_JUNK_LINE_RES = [re.compile(p) for p in (
    r"^\*\s*\d{6,}\s*\*$",                                  # barcode text: "* 0000800000006 *"
    r"^(?:NIGRAM|SIHT|NI|ETIRW|TON|OD)$",                       # mirrored "DO NOT WRITE IN THIS MARGIN"
    r"^BLANK PAGE$",
    r"^\[Turn over$",
    r"^\u00a9\s*UCLES\b.*$",                                     # question-paper footer
    r"^\u00a9\s*Cambridge University Press & Assessment\b.*$",   # mark-scheme footer
    r"^\d{4}/\d{2}\s+Cambridge IGCSE\s*\u2013\s*Mark Scheme.*$",  # mark-scheme running header
    r"^PUBLISHED$",
    r"^This document (?:consists of \d+ printed pages|has \d+ pages)\b.*$",
)]
# Everything from these lines to the end of the page is copyright boilerplate.
_BOILERPLATE_TAIL_RE = re.compile(
    r"^(?:Permission to reproduce items|To avoid the issue of disclosure|"
    r"Cambridge Assessment International Education is part of)", re.IGNORECASE)


def clean_page_text(raw: str) -> str:
    """Remove glyph-id noise, mirrored margin text, barcodes and footers from
    pdfplumber's raw page text. Exam content is never touched: every rule only
    matches whole lines of known boilerplate."""
    out = []
    for line in (raw or "").split("\n"):
        stripped = line.strip()
        if _BOILERPLATE_TAIL_RE.match(stripped):
            break
        if _CID_RE.search(line):
            line = _CID_RE.sub("", line)
            stripped = line.strip()
            if not stripped:
                continue
        if any(rx.match(stripped) for rx in _JUNK_LINE_RES):
            continue
        out.append(line)
    return "\n".join(out)


# --- diagram detection -------------------------------------------------------------
# Text cue for "a drawing is part of this question" (measured on 17 known diagram
# pages: 15 found, 1 false positive). Vector-shape counts were tried and rejected:
# furniture and tables produce the same counts as real diagrams.
_DIAGRAM_CUE_RE = re.compile(
    r"\b(diagram|flowchart|flow chart|draw|sketch|logic circuit|circuit|"
    r"complete and annotate|shown below|image below|picture)\b", re.IGNORECASE)
_MANY_CURVES = 20      # a page with this many curves holds an illustration (robot, network...)


def _has_diagram(text: str, curve_count: int, page_num: int) -> bool:
    if page_num == 1:                      # cover page: instructions only
        return False
    return bool(_DIAGRAM_CUE_RE.search(text)) or curve_count >= _MANY_CURVES


# Cover page: keep only what identifies the paper (title, code, session, duration,
# total marks). The candidate instructions and the empty name/number boxes are the
# same on every paper.
_COVER_KEEP_RE = re.compile(
    r"(Cambridge|COMPUTER SCIENCE|^Paper \d|hours?\b.*minutes|total mark for this paper)", re.IGNORECASE)


def clean_cover_text(text: str) -> str:
    return "\n".join(l for l in text.split("\n") if _COVER_KEEP_RE.search(l.strip()) and l.strip() != "\u2122")


_MS_TABLE_HEADER_RE = re.compile(r"^Question\s+Answer\s+Marks", re.MULTILINE)


def drop_ms_preamble(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Marking schemes open with generic marking principles, annotation guides and
    abbreviations (identical for every paper). Drop the pages before the first
    answer table; if no table header is found, keep everything."""
    for i, p in enumerate(pages):
        if _MS_TABLE_HEADER_RE.search(p["text"]):
            return pages[i:]
    return pages


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw = normalise_gaps(clean_page_text(page.extract_text() or ""))
            tables = page.extract_tables()
            if i == 1 and _COVER_KEEP_RE.search(raw) and "total mark for this paper" in raw:
                # question-paper cover: identity lines only, and its tables are the
                # candidate name/number boxes, not exam content
                raw, tables = clean_cover_text(raw), []
            text = _annotate_anchors(raw, _table_cell_texts(tables))
            text = re.sub(r'(?m)^\s*\.{4,}\s*(\[\d+\])\s*$', r'\1', text)
            text = re.sub(r'(?m)^\s*\.{4,}\s*$\n?', '', text)
            text = re.sub(r'(?m)^([A-Za-z0-9][A-Za-z0-9 \-]*?)\.{4,}\s*(\[\d+\])\s*$',
                          lambda m: f"{m.group(1).rstrip()} {m.group(2)}", text)
            text = re.sub(r'(?m)^([A-Za-z0-9][A-Za-z0-9 \-]*?)\.{4,}\s*$',
                          lambda m: m.group(1).rstrip(), text)
            text = re.sub(r'\.{4,}', '[blank]', text)
            text = re.sub(r'\n{3,}', '\n\n', text)

            images = page.images

            term_def_tables = []
            if tables:
                table_parts = []
                for t in tables:
                    if not t:
                        continue
                    ttype = _classify_table(t)
                    md = _table_to_markdown(t)
                    if md:
                        table_parts.append(f"[TABLE_TYPE:{ttype}]\n{md}")
                        if ttype == "TermDefinitionGrid":
                            term_def_tables.append(_term_def_data(t))
                if table_parts:
                    text = text + "\n\n[TABLES]\n" + "\n\n".join(table_parts)

            pages.append({
                "page": i,
                "text": text,
                "has_table": bool(tables),
                "has_image": bool(images),
                "has_diagram": _has_diagram(raw, len(page.curves), i),
                # Authoritative table contents, attached to the questions in code
                # (src/postprocess.py) instead of being re-typed by the model.
                "term_def_tables": term_def_tables,
            })
    return pages


def render_pages_to_pngs(
    pdf_path: str | Path,
    page_nums: Iterable[int],
    output_dir: str | Path,
    dpi: int = 180,
) -> Dict[int, Path]:
    """Render the given 1-based page numbers of `pdf_path` as PNGs into `output_dir`.

    Returns a {page_num: png_path} map. Skips pages whose PNG is at least as new as
    the PDF (idempotent). Page numbers outside the PDF range are silently skipped."""
    import fitz  # PyMuPDF — imported lazily so existing flows don't require it

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    result: Dict[int, Path] = {}
    targets = sorted({int(n) for n in page_nums if n})
    if not targets:
        return result

    with fitz.open(str(pdf_path)) as doc:
        n_pages = doc.page_count
        for page_num in targets:
            if page_num < 1 or page_num > n_pages:
                continue
            png_path = out_dir / f"page-{page_num}.png"
            result[page_num] = png_path
            if png_path.exists() and png_path.stat().st_mtime >= Path(pdf_path).stat().st_mtime:
                continue                      # up to date; a newer PDF is rendered again
            page = doc.load_page(page_num - 1)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(str(png_path))
    return result


def render_pages_to_png_bytes(pdf_path: str | Path, page_nums: Iterable[int], dpi: int = 110) -> Dict[int, bytes]:
    """Render 1-based pages as PNG bytes (for sending to the model as images)."""
    import fitz

    zoom = dpi / 72.0
    result: Dict[int, bytes] = {}
    with fitz.open(str(pdf_path)) as doc:
        for n in sorted({int(n) for n in page_nums if n}):
            if 1 <= n <= doc.page_count:
                result[n] = doc.load_page(n - 1).get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False).tobytes("png")
    return result
