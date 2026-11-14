"""Render a single question card."""

import re
from html import escape

from .text import (
    _badge,
    _strip_pipe_tables,
    _strip_trailing_partial_mockup,
    _render_prose_paragraphs,
)
from .matching import (
    _is_line_match,
)
from .layouts import (
    _render_simple_single_block,
    _LAYOUT_RENDERERS,
)



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
        paper_num = (source.get("variant") or "")[:1]
        if paper_num:
            header_badges.append(_badge(f"Paper {paper_num}", "badge-paper-num"))
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
    elif layout_type == "AnnotatedDiagram" and \
            (structure_data.get("diagram_type") or "").strip().lower() == "circuit":
        # The JointJS canvas labels A/B/C/Z as actual pads — drop the trailing
        # textual mockup of the partial circuit that Claude leaves in the JSON.
        text = _strip_trailing_partial_mockup(text, structure_data.get("partial_elements") or [])
    elif layout_type == "AnnotatedDiagram" and _is_line_match(q, text):
        # The matcher owns the pipe-table; strip it from the prose so it doesn't
        # render as a duplicate ref-table above the interactive matcher.
        text = _strip_pipe_tables(text)
    visual_html = ""
    visual_image = q.get("visual_image")
    if visual_image:
        caption = ", ".join(str(v) for v in visuals) if visuals else "visual"
        m = re.search(r"page-(\d+)\.png$", str(visual_image))
        visual_page = m.group(1) if m else page
        page_label = f"Source: page {visual_page} &middot; " if visual_page else ""
        visual_html = (
            f'<figure class="q-figure">'
            f'<img class="q-visual-image" src="{escape(str(visual_image))}" '
            f'alt="{escape(caption)}" loading="lazy">'
            f'<figcaption>{page_label}<em>{escape(caption)}</em></figcaption>'
            f'</figure>'
        )
    elif visuals:
        visual_html = f'<p class="q-visual">[Contains: {escape(", ".join(str(v) for v in visuals))}]</p>'
    renderer = _LAYOUT_RENDERERS.get(layout_type)
    if renderer is None:
        print(
            f"[!] New question type detected: {layout_type!r} "
            f"(question {q.get('id', '?')}). Known types: {sorted(_LAYOUT_RENDERERS)}. "
            f"Falling back to SimpleSingleBlock."
        )
        renderer = _render_simple_single_block
    # Pages that mix papers (topic pages) hold several "Q1a"s: give inputs and the card
    # a paper-qualified id so radio groups and anchors do not collide across papers.
    dom_qid = f"{source['paper']}-{qid}" if source and source.get("paper") else qid
    input_html = renderer(dict(q, id=dom_qid) if dom_qid != qid else q, structure_data)

    if layout_type == "InlineCloze":
        # Cloze renderer owns the text — replaces the standard q-text paragraph
        body_inner = input_html
    elif visual_image:
        # Insert the figure between the first paragraph (typically the diagram
        # intro, e.g. "This flowchart represents an algorithm.") and the rest
        # of the question text, so the image sits in context, not at the end.
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if paragraphs:
            first_html = _render_prose_paragraphs(paragraphs[0])
            rest_html = _render_prose_paragraphs("\n\n".join(paragraphs[1:]))
            body_inner = first_html + visual_html + rest_html + input_html
        else:
            body_inner = visual_html + input_html
        visual_html = ""  # consumed; don't re-append at end-of-body
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
        f'id="{escape(dom_qid)}" '
        f'data-topic="{escape(topic or "")}" '
        f'data-subtopic="{escape(topic or "")}" '
        f'data-difficulty="{escape(q.get("difficulty", "") or "")}" '
        f'data-objective="{escape(obj)}" '
        f'data-bloom="{escape(q.get("bloom_level", "") or "")}" '
        f'data-command="{escape(command or "")}" '
        f'data-marks="{escape(str(marks))}" '
        f'data-layout="{escape(layout_type)}"'
    )
    if source:
        v = source.get("variant") or ""
        paper_num = v[:1]
        variant_num = v[1:2]
        data_attrs += (
            f' data-year="{escape(source["year"])}"'
            f' data-session="{escape(source["session"])}"'
            f' data-paper="{escape(source["paper"])}"'
            f' data-variant="{escape(v)}"'
            f' data-variant-num="{escape(variant_num)}"'
            f' data-paper-num="{escape(paper_num)}"'
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
