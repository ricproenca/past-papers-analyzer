"""Render extracted JSON data as a self-contained HTML review page."""

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

/* Tables (MatrixGrid, ValueTraceMatrix, TermDefinitionGrid) */
.matrix-table, .trace-table, .term-def-table {
    width: 100%; border-collapse: collapse; font-size: .875rem;
    border: 1px solid #d1d5db; border-radius: 6px; overflow: hidden;
}
.matrix-table th, .trace-table th, .term-def-table th {
    background: #f3f4f6; padding: .5rem .75rem; text-align: left;
    font-weight: 600; border-bottom: 1px solid #d1d5db;
}
.matrix-table td, .trace-table td, .term-def-table td {
    padding: .5rem .75rem; border-bottom: 1px solid #e5e7eb;
    vertical-align: middle;
}
.matrix-table tbody tr:last-child td,
.trace-table tbody tr:last-child td,
.term-def-table tbody tr:last-child td { border-bottom: none; }
.matrix-table td:not(:first-child) { text-align: center; }
.matrix-table input[type=radio] { transform: scale(1.2); cursor: pointer; }
.trace-cell {
    width: 100%; padding: .3rem .5rem; font-family: ui-monospace, monospace;
    font-size: .85rem; border: 1px solid #d1d5db; border-radius: 4px; background: #fff;
}
.term-def-table td.prefilled { background: #f9fafb; color: #4b5563; }
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


def _render_inline_cloze(q, sd):
    qid = escape(q.get("id", ""))
    text = q.get("text", "")
    parts = text.split("[blank]")
    pieces = []
    for i, part in enumerate(parts):
        pieces.append(f'<span>{escape(part)}</span>')
        if i < len(parts) - 1:
            pieces.append(
                f'<input type="text" class="cloze-blank" name="{qid}_g{i}">'
            )
    word_bank = (
        '<p class="word-bank-note">(Word bank provided in the original paper)</p>'
        if sd.get("has_word_bank") else ""
    )
    return f'<div class="cloze-body">{"".join(pieces)}</div>{word_bank}'


def _render_matrix_grid(q, sd):
    qid = escape(q.get("id", ""))
    headers = sd.get("matrix_headers") or ["Statement"]
    rows = sd.get("rows") or []
    if not headers or not rows:
        return _render_simple_single_block(q, sd)

    head = "".join(f'<th>{escape(str(h))}</th>' for h in headers)
    option_headers = headers[1:]  # first column = statement, remaining = options

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
    headers = sd.get("matrix_headers") or []
    rows = sd.get("rows") or []
    if not headers:
        return _render_simple_single_block(q, sd)

    # Step column on the left if rows are given; otherwise headers stand alone
    has_step_col = bool(rows)
    head_cells = (['<th>Step</th>'] if has_step_col else []) + [
        f'<th>{escape(str(h))}</th>' for h in headers
    ]

    row_labels = rows if rows else [""] * max(int(sd.get("row_count") or 3), 1)
    body_rows = []
    for r, row_label in enumerate(row_labels):
        cells = []
        if has_step_col:
            cells.append(f'<td>{escape(str(row_label))}</td>')
        for c, _ in enumerate(headers):
            cells.append(
                f'<td><input type="text" class="trace-cell" name="{qid}_t{r}_{c}"></td>'
            )
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


def _render_term_definition_grid(q, sd):
    qid = escape(q.get("id", ""))
    rows = sd.get("rows") or []
    if not rows:
        return _render_simple_single_block(q, sd)

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
        f'<thead><tr><th>Term</th><th>Definition</th></tr></thead>'
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


def _render_question(q):
    obj = q.get("objective", "")
    obj_badge = f'<span class="badge badge-obj" data-obj="{escape(obj)}">{escape(obj)}</span>'

    marks = q.get("marks", "?")
    topic = q.get("topic")
    topic_name = q.get("topic_name")
    command = q.get("command")
    page = q.get("page")
    visuals = q.get("visuals") or []
    answers = q.get("answers")

    header_badges = [
        f'<span class="q-id">{escape(q.get("id", ""))}</span>',
        _badge(f"{marks} mark{'s' if marks != 1 else ''}", "badge-marks"),
        obj_badge,
    ]
    if command:
        header_badges.append(_badge(command, "badge-cmd"))
    if topic and topic_name:
        header_badges.append(_badge(f"{topic} {topic_name}", "badge-topic"))
    if page:
        header_badges.append(_badge(f"p.{page}", "badge-page"))

    header_inner = "\n".join(header_badges)
    chevron = '<span class="chevron">▾</span>'

    text_html = escape(q.get("text", ""))
    visual_html = ""
    if visuals:
        visual_html = f'<p class="q-visual">[Contains: {escape(", ".join(str(v) for v in visuals))}]</p>'

    layout_type = q.get("layout_type", "SimpleSingleBlock")
    structure_data = q.get("structure_data") or {}
    renderer = _LAYOUT_RENDERERS.get(layout_type, _render_simple_single_block)
    input_html = renderer(q, structure_data)

    if layout_type == "InlineCloze":
        # Cloze renderer owns the text — replaces the standard q-text paragraph
        body_inner = input_html
    else:
        body_inner = f'<p class="q-text">{text_html}</p>{input_html}'

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

    return (
        f'<div class="card">'
        f'<div class="q-header">{header_inner}{chevron}</div>'
        f'<div class="q-body" data-layout="{escape(layout_type)}">{body_inner}{visual_html}</div>'
        f'{answers_html}'
        f'</div>'
    )


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
