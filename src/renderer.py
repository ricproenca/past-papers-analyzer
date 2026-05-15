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
.q-text { white-space: pre-wrap; line-height: 1.65; font-size: .9375rem; }
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
"""

_JS = """
document.querySelectorAll('.q-header').forEach(h => {
    h.addEventListener('click', () => h.closest('.card').classList.toggle('open'));
});
"""


def _badge(text, cls):
    return f'<span class="badge {cls}">{escape(str(text))}</span>'


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
        f'<div class="q-body"><p class="q-text">{text_html}</p>{visual_html}</div>'
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
