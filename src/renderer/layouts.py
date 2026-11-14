"""One renderer per answer layout (layout_type), plus the _LAYOUT_RENDERERS dispatch table."""

import re
from html import escape

from .text import (
    _render_prose_paragraphs,
)
from .matching import (
    _extract_line_match_columns,
    _render_line_matching,
)



def _as_int(value, default: int) -> int:
    """structure_data comes from the model: a count may be missing or not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _render_simple_single_block(q, sd):
    qid = escape(q.get("id", ""))
    rows = max(_as_int(sd.get("line_count"), 3) or 3, 2)
    return (
        f'<div class="q-input">'
        f'<textarea class="answer-textarea" rows="{rows}" '
        f'name="{qid}_a" placeholder="Write your answer..."></textarea>'
        f'</div>'
    )


_CODE_LANGUAGE_LABELS = {"pseudocode": "Pseudocode", "sql": "SQL", "code": "Code"}


def _render_code_block_response(q, sd):
    qid = escape(q.get("id", ""))
    try:
        marks = int(q.get("marks") or 0)
    except (TypeError, ValueError):
        marks = 0
    raw_lc = sd.get("line_count")
    try:
        lc = int(raw_lc) if raw_lc is not None else None
    except (TypeError, ValueError):
        lc = None
    # Cap at min(lc, 30) so an over-eager line_count doesn't produce a 50+ row
    # textarea; floor at max(marks * 2, 4) so very high-mark questions still
    # get reasonable room when the model omits line_count.
    rows = min(lc, 30) if (lc and lc >= 4) else max(marks * 2, 4)
    lang = (sd.get("language") or "pseudocode").lower()
    label = _CODE_LANGUAGE_LABELS.get(lang, "Code")
    return (
        f'<div class="q-input code-block-input">'
        f'<div class="code-block-language">{escape(label)}</div>'
        f'<textarea class="code-textarea" rows="{rows}" '
        f'name="{qid}_code" placeholder="Write your {escape(label.lower())}..."></textarea>'
        f'</div>'
    )


_SHORT_LABEL_RE = re.compile(r"\b(line number|number|code|mark)\b", re.IGNORECASE)


def _render_multi_part_labeled(q, sd):
    qid = escape(q.get("id", ""))
    labels = sd.get("labels") or []
    if not labels:
        return _render_simple_single_block(q, sd)
    slots = []
    for i, label in enumerate(labels):
        label_str = str(label)
        if _SHORT_LABEL_RE.search(label_str):
            field = f'<input type="text" class="answer-input" name="{qid}_l{i}">'
        else:
            field = f'<textarea class="answer-textarea" rows="2" name="{qid}_l{i}"></textarea>'
        slots.append(
            f'<div class="labeled-slot">'
            f'<label class="slot-label">{escape(label_str)}</label>'
            f'{field}'
            f'</div>'
        )
    return f'<div class="q-input">{"".join(slots)}</div>'


def _render_numbered_multi_list(q, sd):
    qid = escape(q.get("id", ""))
    count = max(_as_int(sd.get("list_count"), 1), 1)
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
        return max(_as_int(fallback, 1), 1)
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

    row_header = sd.get("row_header") or "Step"
    head_cells = ([f'<th>{escape(row_header)}</th>'] if has_step_col else []) + [
        f'<th>{escape(str(h))}</th>' for h in headers
    ]

    row_labels = rows if rows else [""] * max(_as_int(sd.get("row_count"), 3), 1)
    body_rows = []
    for r, row_label in enumerate(row_labels):
        cells = []
        if has_step_col:
            if row_label is None or row_label == "":
                cells.append(
                    f'<td><input type="text" class="trace-cell" name="{qid}_r{r}"></td>'
                )
            else:
                cells.append(f'<td class="prefilled">{escape(str(row_label))}</td>')
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
    n = _as_int(sd.get("register_size"), 8)
    if n not in (8, 16):
        n = 8
    boxes = "".join(
        f'<input type="text" class="bit-box" maxlength="1" '
        f'pattern="[01]" name="{qid}_b{i}">'
        for i in range(n)
    )
    return f'<div class="q-input"><div class="bit-row">{boxes}</div></div>'


def _extract_term_def_headers(q, sd=None):
    """Column headers: stored in structure_data["headers"] by the pipeline, else
    pulled from the first `X | Y` row in the question text (older JSONs).
    Cambridge papers use varied headers (Function name / Component / Internet term / ...);
    only the data row's column *positions* are conventionally term-on-left, definition-on-right.
    Falls back to ('Term', 'Description') when no header row exists in the text."""
    headers = (sd or {}).get("headers")
    if isinstance(headers, list) and len(headers) == 2 and all(isinstance(h, str) and h for h in headers):
        return headers[0], headers[1]
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

    col1, col2 = _extract_term_def_headers(q, sd)

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


_CIRCUIT_GATES = ("AND", "OR", "NOT", "NAND", "NOR", "XOR")


def _render_circuit_editor(q, sd):
    """Interactive JointJS canvas for AnnotatedDiagram questions whose
    `diagram_type == "circuit"`. Inputs/output come from `partial_elements`,
    with single-letter input labels routed left and the output (Z) routed right."""
    qid = escape(q.get("id", ""))
    partial = [str(p).strip() for p in (sd.get("partial_elements") or []) if str(p).strip()]
    # Treat the last item as the output (Cambridge convention: A, B, C, …, Z);
    # everything else is inputs. Fall back to A,B / Z when none provided.
    if len(partial) >= 2:
        inputs = partial[:-1]
        output = partial[-1]
    elif len(partial) == 1:
        inputs, output = [], partial[0]
    else:
        inputs, output = ["A", "B"], "Z"

    palette = "".join(
        f'<button type="button" class="circuit-gate" data-gate="{g}">{g}</button>'
        for g in _CIRCUIT_GATES
    )
    return (
        f'<div class="q-input">'
        f'<div class="circuit-editor" '
        f'data-qid="{qid}" '
        f'data-inputs="{escape(",".join(inputs))}" '
        f'data-output="{escape(output)}">'
        f'<div class="circuit-palette">{palette}</div>'
        f'<div class="circuit-paper" tabindex="0"></div>'
        f'<div class="circuit-toolbar">'
        f'<button type="button" class="circuit-reset">Reset</button>'
        f'<span class="circuit-hint">Drag a gate onto the canvas; drag from a green port to wire it.</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def _render_annotated_diagram(q, sd):
    if (sd.get("diagram_type") or "").strip().lower() == "circuit":
        return _render_circuit_editor(q, sd)

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


def _render_line_matching_layout(q, sd):
    """LineMatching: columns from structure_data (filled by postprocess), else from the
    pipe table in the text; without either it falls back to an open answer."""
    keys = ("left_header", "right_header", "left_items", "right_items")
    if all(sd.get(k) for k in keys):
        columns = tuple(sd[k] for k in keys)
    else:
        columns = _extract_line_match_columns(q.get("text") or "")
    if not columns:
        return _render_simple_single_block(q, sd)
    return _render_line_matching(q, columns)


def _render_working_answer(q, sd):
    """WorkingAnswer: an optional working area, then one labelled answer line per
    value asked for ("429", "1A3", "Denary value"), with the printed unit after it."""
    qid = escape(q.get("id", ""))
    try:
        marks = int(q.get("marks") or 1)
    except (TypeError, ValueError):
        marks = 1
    working = ""
    if sd.get("working_space", True):
        working = (
            f'<label class="slot-label working-label">Working space</label>'
            f'<textarea class="answer-textarea working-area" rows="{max(marks * 2, 3)}" '
            f'name="{qid}_work"></textarea>'
        )
    labels = [str(l) for l in (sd.get("answer_labels") or []) if str(l).strip()] or ["Answer"]
    unit = sd.get("unit")
    unit_html = f'<span class="answer-unit">{escape(str(unit))}</span>' if unit else ""
    rows = "".join(
        f'<div class="labeled-slot working-answer-row">'
        f'<label class="slot-label">{escape(label)}</label>'
        f'<input type="text" class="answer-input" name="{qid}_ans{i}">{unit_html}'
        f'</div>'
        for i, label in enumerate(labels)
    )
    return f'<div class="q-input working-answer">{working}{rows}</div>'


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
    "CodeBlockResponse":      _render_code_block_response,
    "LineMatching":           _render_line_matching_layout,
    "WorkingAnswer":          _render_working_answer,
}
