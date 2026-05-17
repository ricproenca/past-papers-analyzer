"""Render extracted JSON data as a self-contained HTML review page."""

import re
from html import escape
from pathlib import Path

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; background: #f3f4f6; color: #1f2937; }
.page { max-width: 900px; margin: 0 auto; padding: 2rem 1rem 4rem; }
.paper-header {
    background: #1e3a5f; color: #fff; border-radius: 10px;
    padding: 1.25rem 1.5rem; margin-bottom: 2rem;
}
.paper-header h1 { font-size: 1.25rem; font-weight: 700; margin-bottom: .35rem; }
.paper-header p { font-size: .875rem; opacity: .8; }
.card {
    background: #fff; border-radius: 10px; margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.1); overflow: hidden;
}
.q-header {
    display: flex; align-items: center; flex-wrap: wrap; gap: .5rem;
    padding: .875rem 1.25rem; cursor: pointer; user-select: none;
    border-bottom: 1px solid #e5e7eb;
}
.q-header:hover { background: #f9fafb; }
.q-id { font-weight: 700; font-size: 1rem; margin-right: .25rem; }
.badge {
    display: inline-block; font-size: .75rem; font-weight: 600;
    padding: .2rem .55rem; border-radius: 999px; color: #fff;
}
.badge-marks { background: #6b7280; }
.badge-obj { background: #6b7280; }
.badge-obj[data-obj=AO1] { background: #3b82f6; }
.badge-obj[data-obj=AO2] { background: #22c55e; }
.badge-obj[data-obj=AO3] { background: #f97316; }
.badge-cmd { background: #8b5cf6; }
.badge-topic { background: #0891b2; }
.badge-page { background: #d1d5db; color: #374151; }
.badge-paper { background: #1e3a5f; text-decoration: none; }
.badge-paper:hover { background: #2d4f7a; }
.chevron { margin-left: auto; font-size: .9rem; transition: transform .2s; }
.card.open .chevron { transform: rotate(180deg); }
.q-body { padding: 1.25rem; border-bottom: 1px solid #e5e7eb; }
.q-text { white-space: pre-wrap; line-height: 1.65; font-size: .9375rem; margin-bottom: 1rem; }
.q-visual { font-size: .8rem; color: #6b7280; margin-top: .5rem; font-style: italic; }
.answers {
    display: none; padding: 1.25rem; background: #f9fafb;
}
.card.open .answers { display: block; }
.answers-title {
    font-size: .7rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #6b7280; margin-bottom: .75rem;
}
.scoring-rule { font-size: .875rem; color: #374151; font-style: italic; margin-bottom: .75rem; }
.mp-list { list-style: none; display: flex; flex-direction: column; gap: .4rem; }
.mp-item {
    display: flex; align-items: baseline; gap: .6rem;
    font-size: .875rem; line-height: 1.5;
}
.mp-item::before { content: "•"; color: #9ca3af; flex-shrink: 0; }
.mp-text { flex: 1; }
.mp-marks {
    flex-shrink: 0; font-size: .75rem; font-weight: 600;
    color: #6b7280; white-space: nowrap;
}

/* === Form input styles (layout-specific inputs) === */
.q-input { margin-top: .25rem; }
.answer-textarea, .answer-input {
    width: 100%; font-family: inherit; font-size: .9rem; line-height: 1.5;
    padding: .5rem .65rem; border: 1px solid #d1d5db; border-radius: 6px;
    background: #fff; color: #1f2937; resize: vertical;
}
.answer-textarea:focus, .answer-input:focus, .cloze-blank:focus, .bit-box:focus,
.trace-cell:focus, .term-input:focus {
    outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, .15);
}

/* Labeled / numbered slots */
.labeled-slot, .numbered-slot {
    display: flex; align-items: flex-start; gap: .75rem; margin-bottom: .6rem;
}
.slot-label, .slot-number {
    flex-shrink: 0; font-weight: 600; font-size: .875rem; color: #374151;
    padding-top: .55rem; min-width: 2rem;
}
.slot-label { min-width: 8rem; }
.labeled-slot .answer-textarea, .numbered-slot .answer-input { flex: 1; }

/* InlineCloze */
.cloze-body { line-height: 2.2; font-size: .9375rem; }
.cloze-blank {
    display: inline-block; width: 8em; margin: 0 .25em; padding: .15rem .4rem;
    font-family: inherit; font-size: .9rem;
    border: none; border-bottom: 2px solid #6b7280; background: transparent;
}
.word-bank-note {
    margin-top: .75rem; font-size: .8rem; color: #6b7280; font-style: italic;
}
.word-bank {
    display: flex; flex-wrap: wrap; gap: .4rem;
    padding: .75rem .9rem; margin: .85rem 0;
    background: #f0f7ff; border: 1px solid #c7dcf6; border-radius: 8px;
}
.word-bank-label {
    width: 100%; font-size: .7rem; font-weight: 700; letter-spacing: .06em;
    text-transform: uppercase; color: #3b5b85; margin-bottom: .15rem;
}
.word-chip {
    background: #fff; border: 1px solid #c7dcf6; border-radius: 999px;
    padding: .25rem .7rem; font-size: .85rem; color: #1e3a5f; font-weight: 500;
}

/* Tables (MatrixGrid, ValueTraceMatrix, TermDefinitionGrid, embedded reference) */
.matrix-table, .trace-table, .term-def-table, .ref-table {
    width: 100%; border-collapse: collapse; font-size: .875rem;
    border: 1px solid #d1d5db; border-radius: 6px; overflow: hidden;
}
.matrix-table th, .trace-table th, .term-def-table th, .ref-table th {
    background: #f3f4f6; padding: .5rem .75rem; text-align: left;
    font-weight: 600; border-bottom: 1px solid #d1d5db;
}
.matrix-table td, .trace-table td, .term-def-table td, .ref-table td {
    padding: .5rem .75rem; border-bottom: 1px solid #e5e7eb;
    vertical-align: middle;
}
.matrix-table tbody tr:last-child td,
.trace-table tbody tr:last-child td,
.term-def-table tbody tr:last-child td,
.ref-table tbody tr:last-child td { border-bottom: none; }
.ref-table { margin: .75rem 0 1rem; }
.matrix-table td:not(:first-child) { text-align: center; }
.matrix-table input[type=radio] { transform: scale(1.2); cursor: pointer; }

/* Single-select MCQ option list (Tick one/N boxes) */
.option-table {
    width: 100%; border-collapse: collapse; font-size: .9rem;
    border: 1px solid #d1d5db; border-radius: 6px; overflow: hidden;
}
.option-table tr { border-bottom: 1px solid #e5e7eb; }
.option-table tr:last-child { border-bottom: none; }
.option-table tr:hover { background: #f9fafb; }
.option-table td { padding: .55rem .75rem; vertical-align: middle; }
.option-table td.opt-letter {
    width: 2.25rem; font-weight: 700; color: #1e3a5f; text-align: center;
}
.option-table td.opt-text { line-height: 1.5; }
.option-table td.opt-input {
    width: 3rem; text-align: center;
}
.option-table td.opt-input input { transform: scale(1.2); cursor: pointer; }
.tick-hint {
    font-size: .8rem; color: #6b7280; font-style: italic;
    margin-bottom: .5rem;
}
.trace-cell {
    width: 100%; padding: .3rem .5rem; font-family: ui-monospace, monospace;
    font-size: .85rem; border: 1px solid #d1d5db; border-radius: 4px; background: #fff;
}
.term-def-table td.prefilled { background: #f9fafb; color: #4b5563; }
.trace-table td.prefilled {
    background: #f9fafb; color: #1f2937;
    font-family: ui-monospace, monospace; text-align: center;
}
.term-def-table .term-input, .term-def-table textarea {
    width: 100%; font-family: inherit; font-size: .875rem;
    padding: .35rem .5rem; border: 1px solid #d1d5db; border-radius: 4px; background: #fff;
}

/* FixedRegisterArray */
.bit-row { display: flex; gap: .35rem; flex-wrap: wrap; margin-top: .5rem; }
.bit-box {
    width: 2.4rem; height: 2.4rem; text-align: center; font-size: 1rem;
    font-family: ui-monospace, monospace; font-weight: 600;
    border: 1.5px solid #6b7280; border-radius: 4px; background: #fff;
}

/* LabelledPartResponse */
.reference {
    font-family: ui-monospace, monospace; font-size: .9rem;
    background: #f3f4f6; padding: .65rem .85rem; border-radius: 6px;
    border-left: 3px solid #3b82f6; margin-bottom: .85rem; overflow-x: auto;
}
.callout-row { display: flex; gap: .75rem; flex-wrap: wrap; align-items: center; }
.callout-item {
    display: flex; align-items: center; gap: .35rem; flex: 1; min-width: 10rem;
}
.callout-letter {
    font-weight: 700; color: #3b82f6; font-size: .95rem; min-width: 1.2rem;
}

/* AnnotatedDiagram */
.diagram-context {
    background: #f9fafb; border: 1px dashed #d1d5db; border-radius: 6px;
    padding: .75rem 1rem; margin-bottom: .75rem;
}
.diagram-type-label { font-size: .85rem; color: #4b5563; margin-bottom: .4rem; }
.partial-elements {
    list-style: disc; padding-left: 1.4rem; font-size: .85rem; color: #1f2937;
}
.partial-elements li { margin-bottom: .15rem; }
"""

_JS = """
document.querySelectorAll('.q-header').forEach(h => {
    h.addEventListener('click', () => h.closest('.card').classList.toggle('open'));
});
"""


def _badge(text, cls):
    return f'<span class="badge {cls}">{escape(str(text))}</span>'


# ============================================================================
# Layout-specific input renderers
# ============================================================================

def _pipe_table_lines(lines: list[str]) -> list[str] | None:
    """If `lines` (non-empty, already-stripped) form a valid pipe-table —
    2+ rows, every row contains '|', all rows have the same '|'-separated
    column count, ≥2 columns — return the same list. Otherwise None.

    Single source of truth for pipe-table detection. Used by both:
    - `_maybe_pipe_table` to render genuine reference tables in prose stems
    - `_strip_pipe_tables` to remove pipe-mirrors of tables already rendered
      by a structured layout renderer (MatrixGrid / ValueTraceMatrix /
      TermDefinitionGrid)."""
    if len(lines) < 2:
        return None
    if not all("|" in ln for ln in lines):
        return None
    col_counts = [len(ln.split("|")) for ln in lines]
    if len(set(col_counts)) != 1 or col_counts[0] < 2:
        return None
    return lines


def _find_pipe_table_blocks(text: str) -> list[tuple[int, int]]:
    """Scan `text` line-by-line and return [(start, end_exclusive), ...] index
    ranges of every contiguous pipe-table run, where a run is the maximal
    sequence of non-blank '|'-containing lines that share the same column
    count. Runs shorter than 2 lines, or with fewer than 2 columns, are
    skipped — matching the `_pipe_table_lines` predicate."""
    raw_lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(raw_lines):
        if "|" not in raw_lines[i] or not raw_lines[i].strip():
            i += 1
            continue
        start = i
        first_cols = len(raw_lines[i].split("|"))
        j = i + 1
        while (
            j < len(raw_lines)
            and raw_lines[j].strip()
            and "|" in raw_lines[j]
            and len(raw_lines[j].split("|")) == first_cols
        ):
            j += 1
        if j - start >= 2 and first_cols >= 2:
            blocks.append((start, j))
        i = max(j, i + 1)
    return blocks


def _strip_pipe_tables(text: str) -> str:
    """Drop every detected pipe-table run from `text`. Used by layouts that
    own a structured table renderer so the model's pipe-mirror in the text
    field doesn't render as a duplicate `ref-table` above the real one."""
    if not text or "|" not in text:
        return text
    blocks = _find_pipe_table_blocks(text)
    if not blocks:
        return text
    raw_lines = text.splitlines()
    drop = [False] * len(raw_lines)
    for start, end in blocks:
        for k in range(start, end):
            drop[k] = True
    return "\n".join(ln for ln, d in zip(raw_lines, drop) if not d).strip()


def _maybe_pipe_table(paragraph: str) -> str | None:
    """If `paragraph` is a pipe-separated reference table, return rendered
    <table class="ref-table"> HTML. Otherwise return None.

    First line is treated as the header row. This handles reference tables
    embedded in question stems (e.g. Q2a's "Letter | Statement" lookup
    table) that aren't part of the answer structure."""
    lines = [ln.strip() for ln in paragraph.splitlines() if ln.strip()]
    if _pipe_table_lines(lines) is None:
        return None

    def _cells(ln: str) -> list[str]:
        return [c.strip() for c in ln.split("|")]

    th_html = "".join(f"<th>{escape(c)}</th>" for c in _cells(lines[0]))
    body_html = "".join(
        "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in _cells(ln)) + "</tr>"
        for ln in lines[1:]
    )
    return (
        f'<table class="ref-table"><thead><tr>{th_html}</tr></thead>'
        f'<tbody>{body_html}</tbody></table>'
    )


def _render_prose_paragraphs(text: str, css_class: str = "q-text") -> str:
    """Split prose on blank lines and emit one <p class="..."> per paragraph.

    Paragraphs that look like a pipe-separated reference table are rendered as
    <table> instead. Returns '' for empty/whitespace text."""
    if not text or not text.strip():
        return ""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    parts = []
    for p in paragraphs:
        table_html = _maybe_pipe_table(p)
        if table_html:
            parts.append(table_html)
        else:
            parts.append(f'<p class="{css_class}">{escape(p)}</p>')
    return "".join(parts)


def _render_simple_single_block(q, sd):
    qid = escape(q.get("id", ""))
    rows = max(int(sd.get("line_count") or 3), 2)
    return (
        f'<div class="q-input">'
        f'<textarea class="answer-textarea" rows="{rows}" '
        f'name="{qid}_a" placeholder="Write your answer..."></textarea>'
        f'</div>'
    )


def _render_multi_part_labeled(q, sd):
    qid = escape(q.get("id", ""))
    labels = sd.get("labels") or []
    if not labels:
        return _render_simple_single_block(q, sd)
    slots = []
    for i, label in enumerate(labels):
        slots.append(
            f'<div class="labeled-slot">'
            f'<label class="slot-label">{escape(str(label))}</label>'
            f'<textarea class="answer-textarea" rows="2" name="{qid}_l{i}"></textarea>'
            f'</div>'
        )
    return f'<div class="q-input">{"".join(slots)}</div>'


def _render_numbered_multi_list(q, sd):
    qid = escape(q.get("id", ""))
    count = max(int(sd.get("list_count") or 1), 1)
    slots = []
    for i in range(count):
        slots.append(
            f'<div class="numbered-slot">'
            f'<span class="slot-number">{i + 1}</span>'
            f'<input type="text" class="answer-input" name="{qid}_n{i}">'
            f'</div>'
        )
    return f'<div class="q-input">{"".join(slots)}</div>'


_WORD_BANK_RE = re.compile(r"^\s*\[word bank:\s*(.+?)\]\s*$", re.IGNORECASE)
_ELLIPSIS_RUN_RE = re.compile(r"[…]{2,}|\.{3,}")
_PROSE_END_RE = re.compile(r"[.!?]\s*$")


def _tokenize_bank_line(text: str):
    """Split a word-bank line into items. Uses 2+ spaces if present
    (preserves multi-word terms), otherwise single whitespace."""
    if re.search(r"\s{2,}", text):
        return [t.strip() for t in re.split(r"\s{2,}", text) if t.strip()]
    return text.split()


def _parse_cloze_text(text: str):
    """Split a cloze question's text into (intro, word_bank_items, cloze_paragraph).

    PDF-extracted gap placeholders that came through as runs of `…` (U+2026) or
    `...` are normalized to `[blank]` first.

    The cloze paragraph is everything from the first line containing `[blank]`.
    The word bank is detected by:
      (A) An explicit `[word bank: a, b, c]` line — split on commas (preserves
          multi-word terms like "central processing unit (CPU)").
      (B) Walking backward from just before the cloze paragraph, collecting
          consecutive non-empty lines that don't end with sentence-final
          punctuation. Multi-line banks are joined and re-tokenized.
    """
    text = _ELLIPSIS_RUN_RE.sub("[blank]", text)
    lines = text.splitlines()
    cloze_start = next((i for i, ln in enumerate(lines) if "[blank]" in ln), None)
    if cloze_start is None:
        return text, None, ""

    pre = list(lines[:cloze_start])
    cloze = "\n".join(lines[cloze_start:]).strip()

    word_bank = None

    # Pattern A — explicit marker, comma-separated
    for i, line in enumerate(pre):
        m = _WORD_BANK_RE.match(line)
        if m:
            word_bank = [w.strip() for w in m.group(1).split(",") if w.strip()]
            del pre[i]
            break

    # Pattern B — walk backwards, collect consecutive non-prose lines
    if word_bank is None:
        bank_lines = []
        cut_idx = len(pre)
        for i in range(len(pre) - 1, -1, -1):
            s = pre[i].strip()
            if not s:
                if bank_lines:
                    cut_idx = i
                    break
                cut_idx = i
                continue
            if _PROSE_END_RE.search(s):
                cut_idx = i + 1
                break
            bank_lines.insert(0, s)
            cut_idx = i
        if bank_lines:
            joined = "  ".join(bank_lines) if any(re.search(r"\s{2,}", b) for b in bank_lines) else " ".join(bank_lines)
            word_bank = _tokenize_bank_line(joined)
            pre = pre[:cut_idx]

    intro = "\n".join(pre).strip()
    return intro, word_bank, cloze


def _render_inline_cloze(q, sd):
    qid = escape(q.get("id", ""))
    text = q.get("text", "")

    intro, word_bank, cloze_text = _parse_cloze_text(text)

    intro_html = _render_prose_paragraphs(intro)

    bank_html = ""
    if word_bank:
        chips = "".join(
            f'<span class="word-chip">{escape(w)}</span>' for w in word_bank
        )
        bank_html = (
            f'<div class="word-bank">'
            f'<span class="word-bank-label">Word bank</span>{chips}'
            f'</div>'
        )
    elif sd.get("has_word_bank"):
        bank_html = (
            '<p class="word-bank-note">(Word bank provided in the original paper)</p>'
        )

    parts = (cloze_text or text).split("[blank]")
    pieces = []
    for i, part in enumerate(parts):
        pieces.append(f'<span>{escape(part)}</span>')
        if i < len(parts) - 1:
            pieces.append(
                f'<input type="text" class="cloze-blank" name="{qid}_g{i}">'
            )
    cloze_html = f'<div class="cloze-body">{"".join(pieces)}</div>'

    return f'{intro_html}{bank_html}{cloze_html}'


_TICK_HEADER_RE = re.compile(r"^(tick|select|choose|mark)\b", re.IGNORECASE)
_TICK_COUNT_RE = re.compile(
    r"tick\s*(?:\(\s*✓\s*\))?\s*(one|two|three|four|five|six|\d+)\s+box",
    re.IGNORECASE,
)
_OPTION_LETTER_RE = re.compile(r"^\s*([A-Z]|\d{1,2})\b[\s\.\)]+(.+)$")
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def _detect_tick_count(text: str, fallback: int) -> int:
    m = _TICK_COUNT_RE.search(text or "")
    if not m:
        return max(int(fallback or 1), 1)
    w = m.group(1).lower()
    if w.isdigit():
        return int(w)
    return _NUM_WORDS.get(w, fallback)


def _split_option_row(row_text: str):
    """Split 'A bit' into ('A','bit'); return (None, row_text) if no letter prefix."""
    m = _OPTION_LETTER_RE.match(str(row_text or ""))
    if not m:
        return None, str(row_text or "")
    return m.group(1), m.group(2).strip()


def _render_matrix_grid(q, sd):
    qid = escape(q.get("id", ""))
    headers = sd.get("matrix_headers") or ["Statement"]
    rows = sd.get("rows") or []
    if not headers or not rows:
        return _render_simple_single_block(q, sd)

    option_headers = headers[1:]  # first column = statement, remaining = options

    # Single-select MCQ pattern: 2 headers AND (the right header reads like "Tick/Select/..."
    # OR every row begins with an A/B/C-style option letter AND the question text contains
    # "Tick (✓) N box(es)"). Render as: [letter] [statement] [radio/checkbox] per row, with
    # a SHARED input name for tick-one (mutually exclusive) and checkboxes for tick-N.
    qtext = q.get("text", "") or ""
    right_header = str(option_headers[0] or "").strip() if option_headers else ""
    all_rows_lettered = bool(rows) and all(
        _OPTION_LETTER_RE.match(str(r or "")) for r in rows
    )
    is_single_select = (
        len(option_headers) == 1
        and (
            bool(_TICK_HEADER_RE.match(right_header))
            or (all_rows_lettered and bool(_TICK_COUNT_RE.search(qtext)))
        )
    )

    if is_single_select:
        tick_count = _detect_tick_count(q.get("text", ""), q.get("marks", 1) or 1)
        input_type = "radio" if tick_count == 1 else "checkbox"
        body_rows = []
        for r, row_text in enumerate(rows):
            letter, statement = _split_option_row(row_text)
            letter_html = f'<td class="opt-letter">{escape(letter)}</td>' if letter else '<td class="opt-letter"></td>'
            statement_html = f'<td class="opt-text">{escape(statement)}</td>'
            name = f"{qid}_choice" if input_type == "radio" else f"{qid}_pick{r}"
            value = letter or str(r)
            input_html = (
                f'<td class="opt-input">'
                f'<input type="{input_type}" name="{name}" value="{escape(value)}">'
                f'</td>'
            )
            body_rows.append(f"<tr>{letter_html}{statement_html}{input_html}</tr>")
        note = ""
        if tick_count > 1:
            note = f'<p class="tick-hint">Tick {tick_count} boxes.</p>'
        return (
            f'<div class="q-input">'
            f'{note}'
            f'<table class="option-table">'
            f'<tbody>{"".join(body_rows)}</tbody>'
            f'</table>'
            f'</div>'
        )

    # Multi-option matrix comparison (e.g. ["Statement","True","False"]) — unchanged
    head = "".join(f'<th>{escape(str(h))}</th>' for h in headers)
    body_rows = []
    for r, row_text in enumerate(rows):
        cells = [f'<td>{escape(str(row_text))}</td>']
        for c, opt in enumerate(option_headers):
            cells.append(
                f'<td><input type="radio" name="{qid}_r{r}" '
                f'value="{escape(str(opt))}"></td>'
            )
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    return (
        f'<div class="q-input">'
        f'<table class="matrix-table">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
        f'</div>'
    )


def _render_value_trace_matrix(q, sd):
    qid = escape(q.get("id", ""))
    headers = list(sd.get("matrix_headers") or [])
    rows = sd.get("rows") or []
    row_values = sd.get("row_values") or []
    if not headers:
        return _render_simple_single_block(q, sd)

    has_step_col = bool(rows)

    # If a step column is going to be auto-prepended AND the data already supplied
    # an empty leading header (intended as a placeholder for that step column),
    # drop the duplicate so we don't render two leftmost columns.
    if has_step_col and headers and not str(headers[0]).strip():
        headers = headers[1:]

    head_cells = (['<th>Step</th>'] if has_step_col else []) + [
        f'<th>{escape(str(h))}</th>' for h in headers
    ]

    row_labels = rows if rows else [""] * max(int(sd.get("row_count") or 3), 1)
    body_rows = []
    for r, row_label in enumerate(row_labels):
        cells = []
        if has_step_col:
            cells.append(f'<td>{escape(str(row_label))}</td>')
        prefill = row_values[r] if r < len(row_values) else None
        for c in range(len(headers)):
            val = prefill[c] if (isinstance(prefill, list) and c < len(prefill)) else None
            if val is None or val == "":
                cells.append(
                    f'<td><input type="text" class="trace-cell" name="{qid}_t{r}_{c}"></td>'
                )
            else:
                cells.append(f'<td class="prefilled">{escape(str(val))}</td>')
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    return (
        f'<div class="q-input">'
        f'<table class="trace-table">'
        f'<thead><tr>{"".join(head_cells)}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
        f'</div>'
    )


def _render_fixed_register_array(q, sd):
    qid = escape(q.get("id", ""))
    n = int(sd.get("register_size") or 8)
    if n not in (8, 16):
        n = 8
    boxes = "".join(
        f'<input type="text" class="bit-box" maxlength="1" '
        f'pattern="[01]" name="{qid}_b{i}">'
        for i in range(n)
    )
    return f'<div class="q-input"><div class="bit-row">{boxes}</div></div>'


def _extract_term_def_headers(q):
    """Pull (col1, col2) from the first `X | Y` row in the question text.
    Cambridge papers use varied headers (Function name / Component / Internet term / ...);
    only the data row's column *positions* are conventionally term-on-left, definition-on-right.
    Falls back to ('Term', 'Description') when no header row exists in the text."""
    for line in q.get("text", "").splitlines():
        if " | " in line:
            parts = [p.strip() for p in line.split(" | ", 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]
    return "Term", "Description"


def _render_term_definition_grid(q, sd):
    qid = escape(q.get("id", ""))
    rows = sd.get("rows") or []
    if not rows:
        return _render_simple_single_block(q, sd)

    col1, col2 = _extract_term_def_headers(q)

    body_rows = []
    for i, row in enumerate(rows):
        term = row.get("term") if isinstance(row, dict) else None
        defn = row.get("definition") if isinstance(row, dict) else None

        term_cell = (
            f'<td class="prefilled">{escape(str(term))}</td>'
            if term
            else f'<td><input type="text" class="term-input" name="{qid}_t{i}"></td>'
        )
        def_cell = (
            f'<td class="prefilled">{escape(str(defn))}</td>'
            if defn
            else f'<td><textarea rows="2" name="{qid}_d{i}"></textarea></td>'
        )
        body_rows.append(f'<tr>{term_cell}{def_cell}</tr>')

    return (
        f'<div class="q-input">'
        f'<table class="term-def-table">'
        f'<thead><tr><th>{escape(col1)}</th><th>{escape(col2)}</th></tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
        f'</div>'
    )


def _render_labelled_part_response(q, sd):
    qid = escape(q.get("id", ""))
    labels = sd.get("labels") or []
    reference = sd.get("reference") or ""
    if not labels:
        return _render_simple_single_block(q, sd)

    ref_html = (
        f'<pre class="reference">{escape(str(reference))}</pre>'
        if reference else ""
    )
    items = []
    for i, label in enumerate(labels):
        items.append(
            f'<div class="callout-item">'
            f'<span class="callout-letter">{escape(str(label))}</span>'
            f'<input type="text" class="answer-input" name="{qid}_c{i}">'
            f'</div>'
        )
    return (
        f'<div class="q-input">'
        f'{ref_html}'
        f'<div class="callout-row">{"".join(items)}</div>'
        f'</div>'
    )


def _render_annotated_diagram(q, sd):
    qid = escape(q.get("id", ""))
    diagram_type = sd.get("diagram_type") or "diagram"
    partial = sd.get("partial_elements") or []

    elements_html = ""
    if partial:
        items = "".join(f'<li>{escape(str(p))}</li>' for p in partial)
        elements_html = (
            f'<p class="diagram-type-label">Pre-drawn elements:</p>'
            f'<ul class="partial-elements">{items}</ul>'
        )

    return (
        f'<div class="q-input">'
        f'<div class="diagram-context">'
        f'<p class="diagram-type-label">Diagram type: <strong>{escape(str(diagram_type))}</strong></p>'
        f'{elements_html}'
        f'</div>'
        f'<textarea class="answer-textarea" rows="5" name="{qid}_diag" '
        f'placeholder="Describe your additions to the diagram (or sketch in your answer book)..."></textarea>'
        f'</div>'
    )


_LAYOUT_RENDERERS = {
    "SimpleSingleBlock":      _render_simple_single_block,
    "MultiPartLabeledBlock":  _render_multi_part_labeled,
    "NumberedMultiList":      _render_numbered_multi_list,
    "InlineCloze":            _render_inline_cloze,
    "MatrixGrid":             _render_matrix_grid,
    "ValueTraceMatrix":       _render_value_trace_matrix,
    "FixedRegisterArray":     _render_fixed_register_array,
    "TermDefinitionGrid":     _render_term_definition_grid,
    "LabelledPartResponse":   _render_labelled_part_response,
    "AnnotatedDiagram":       _render_annotated_diagram,
}


def _render_question(q, source: dict | None = None):
    obj = q.get("objective", "")
    obj_badge = f'<span class="badge badge-obj" data-obj="{escape(obj)}">{escape(obj)}</span>'

    qid = q.get("id", "")
    marks = q.get("marks", "?")
    topic = q.get("topic")
    topic_name = q.get("topic_name")
    command = q.get("command")
    page = q.get("page")
    visuals = q.get("visuals") or []
    answers = q.get("answers")

    header_badges = [
        f'<span class="q-id">{escape(qid)}</span>',
        _badge(f"{marks} mark{'s' if marks != 1 else ''}", "badge-marks"),
        obj_badge,
    ]
    if command:
        header_badges.append(_badge(command, "badge-cmd"))
    if topic and topic_name:
        header_badges.append(_badge(f"{topic} {topic_name}", "badge-topic"))
    if page:
        header_badges.append(_badge(f"p.{page}", "badge-page"))
    if source:
        href = f'{escape(source["paper"])}.html#{escape(qid)}'
        label = f'{source["session"]} · QP{source["variant"]} · {qid}'
        header_badges.append(
            f'<a class="badge badge-paper" href="{href}" '
            f'onclick="event.stopPropagation()">{escape(label)}</a>'
        )

    header_inner = "\n".join(header_badges)
    chevron = '<span class="chevron">▾</span>'

    layout_type = q.get("layout_type") or "SimpleSingleBlock"
    structure_data = q.get("structure_data") or {}

    text = q.get("text", "")
    if layout_type != "InlineCloze":
        text = text.replace("[blank]", "").strip()
    if layout_type in ("MatrixGrid", "ValueTraceMatrix", "TermDefinitionGrid"):
        # These layouts own a structured table renderer. The model frequently
        # mirrors that table into the text field as pipe-separated lines (a
        # human-readable mirror it was told to write). Strip all such runs so
        # they don't render as a duplicate `ref-table` above the real one.
        text = _strip_pipe_tables(text)
    if layout_type in ("MatrixGrid", "ValueTraceMatrix"):
        # Belt-and-braces: also drop any lingering bare row-label / single-row
        # header lines that survived pipe-table stripping (e.g. a "byte 1"
        # standing alone on its own line outside the table block, or a
        # "Option | Tick" 1-row pipe stub that didn't trigger the ≥2-line
        # pipe-table detector).
        rows = structure_data.get("rows") or []
        strip_set = {row.strip() for row in rows if isinstance(row, str)}
        headers = structure_data.get("matrix_headers") or []
        header_tokens = [h.strip() for h in headers if isinstance(h, str) and h.strip()]
        if header_tokens:
            def _is_header_pipe_line(line: str) -> bool:
                parts = [p.strip() for p in line.split("|")]
                return parts == header_tokens
            text = "\n".join(
                line for line in text.splitlines() if not _is_header_pipe_line(line)
            ).strip()
        if strip_set:
            text = "\n".join(
                line for line in text.splitlines() if line.strip() not in strip_set
            ).strip()
        if strip_set and layout_type == "MatrixGrid":
            # Normalised chunk-strip: handles every (rows-prefix × text-prefix)
            # corner of MatrixGrid duplication with one principled comparison.
            #
            # Drop any line whose 2+-space-separated chunks are ALL row labels,
            # where "is a row label" tolerates a short letter/number prefix on
            # EITHER side. This covers:
            #   - s24/11 Q5b: flow-list,    unprefixed rows  → chunks ∈ strip_set
            #   - m25/12 Q1c: per-line "A …", unprefixed rows → _norm(chunk) ∈ strip_set_norm
            #   - m24/12 Q1a: per-line "A …", prefixed   rows → chunks ∈ strip_set
            #   - s24/13 Q6a: flow-list,    prefixed   rows → _norm(chunk) ∈ strip_set_norm
            #                                                  (rows normalised too)
            _PREFIX_RE = re.compile(r"^(?:[A-Za-z]|\d{1,2}\.?)\s+(.+)$")
            def _norm(s: str) -> str:
                m = _PREFIX_RE.match(s.strip())
                return m.group(1).strip() if m else s.strip()
            strip_set_norm = {_norm(r) for r in rows if isinstance(r, str)}
            def _is_row_token(token: str) -> bool:
                s = token.strip()
                return s in strip_set or _norm(s) in strip_set_norm
            def _all_chunks_are_options(line: str) -> bool:
                chunks = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip()]
                return bool(chunks) and all(_is_row_token(c) for c in chunks)
            text = "\n".join(
                line for line in text.splitlines() if not _all_chunks_are_options(line)
            ).strip()
    elif layout_type == "MultiPartLabeledBlock":
        labels = structure_data.get("labels") or []
        strip_set = {l.strip() for l in labels if isinstance(l, str)}
        if strip_set:
            text = "\n".join(
                line for line in text.splitlines() if line.strip() not in strip_set
            ).strip()
    elif layout_type == "NumberedMultiList":
        count = max(int(structure_data.get("list_count") or 1), 1)
        expected = [str(i) for i in range(1, count + 1)]
        lines = text.splitlines()
        trailing, tail_start = [], len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip():
                trailing.insert(0, lines[i].strip())
                if len(trailing) == count:
                    tail_start = i
                    break
        if trailing == expected:
            text = "\n".join(lines[:tail_start]).strip()
    visual_html = ""
    if visuals:
        visual_html = f'<p class="q-visual">[Contains: {escape(", ".join(str(v) for v in visuals))}]</p>'
    renderer = _LAYOUT_RENDERERS.get(layout_type)
    if renderer is None:
        print(
            f"[!] New question type detected: {layout_type!r} "
            f"(question {q.get('id', '?')}). Known types: {sorted(_LAYOUT_RENDERERS)}. "
            f"Falling back to SimpleSingleBlock."
        )
        renderer = _render_simple_single_block
    input_html = renderer(q, structure_data)

    if layout_type == "InlineCloze":
        # Cloze renderer owns the text — replaces the standard q-text paragraph
        body_inner = input_html
    else:
        body_inner = _render_prose_paragraphs(text) + input_html

    answers_html = ""
    if answers:
        rule = answers.get("scoring_rule")
        rule_html = f'<p class="scoring-rule">{escape(rule)}</p>' if rule else ""
        mps = answers.get("marking_points") or []
        mp_items = []
        for mp in mps:
            mp_marks = mp.get("marks", "")
            mp_text = escape(mp.get("text", ""))
            mark_label = f"[{mp_marks}]" if mp_marks != "" else ""
            mp_items.append(
                f'<li class="mp-item">'
                f'<span class="mp-text">{mp_text}</span>'
                f'<span class="mp-marks">{mark_label}</span>'
                f'</li>'
            )
        mp_list = f'<ul class="mp-list">{"".join(mp_items)}</ul>' if mp_items else ""
        ans_visuals = answers.get("visuals") or []
        ans_visual_html = (
            f'<p class="q-visual">[Answer visual: {escape(", ".join(str(v) for v in ans_visuals))}]</p>'
            if ans_visuals else ""
        )
        answers_html = (
            f'<div class="answers">'
            f'<p class="answers-title">Marking scheme</p>'
            f'{rule_html}{mp_list}{ans_visual_html}'
            f'</div>'
        )

    data_attrs = (
        f'id="{escape(qid)}" '
        f'data-topic="{escape(topic or "")}" '
        f'data-subtopic="{escape(topic or "")}" '
        f'data-difficulty="{escape(q.get("difficulty", "") or "")}" '
        f'data-objective="{escape(obj)}" '
        f'data-bloom="{escape(q.get("bloom_level", "") or "")}" '
        f'data-command="{escape(command or "")}" '
        f'data-marks="{escape(str(marks))}"'
    )
    if source:
        data_attrs += (
            f' data-year="{escape(source["year"])}"'
            f' data-session="{escape(source["session"])}"'
            f' data-paper="{escape(source["paper"])}"'
        )

    return (
        f'<div class="card" {data_attrs}>'
        f'<div class="q-header">{header_inner}{chevron}</div>'
        f'<div class="q-body" data-layout="{escape(layout_type)}">{body_inner}{visual_html}</div>'
        f'{answers_html}'
        f'</div>'
    )


# Public alias for cross-module callers (e.g. generate_topics.py)
render_question_card = _render_question


def render_html(data: dict) -> str:
    board = escape(data.get("board", ""))
    level = escape(data.get("level", ""))
    subject = escape(data.get("subject_name", ""))
    code = escape(data.get("subject_code", ""))
    variant = escape(str(data.get("variant", "")))
    total = data.get("total_marks", "?")
    qp = escape(data.get("qp", ""))

    title = f"{board} {level} {subject} ({code}) Variant {variant}"
    questions = data.get("questions", [])
    q_cards = "\n".join(_render_question(q) for q in questions)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="paper.css">
</head>
<body>
<div class="page">
  <div class="paper-header">
    <h1>{title}</h1>
    <p>{qp} &nbsp;·&nbsp; {len(questions)} questions &nbsp;·&nbsp; {total} marks total</p>
  </div>
  {q_cards}
</div>
<script src="paper.js"></script>
</body>
</html>"""


def _write_assets(directory: Path) -> None:
    (directory / "paper.css").write_text(_CSS, encoding="utf-8")
    (directory / "paper.js").write_text(_JS, encoding="utf-8")


def render(data: dict, output_path: str | Path) -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _write_assets(out.parent)
    out.write_text(render_html(data), encoding="utf-8")
