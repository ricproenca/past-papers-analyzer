#!/usr/bin/env python3
"""Generate per-topic revision pages from all paper JSONs in output/json/.

Outputs to output/html/:
  - topics.html              landing index linking to the 6 topic pages
  - topic_1.html .. topic_6.html
  - topics.css, topics.js    filter-bar styling + filter logic
  - paper.css, paper.js      reused from src.renderer
"""

import glob
import json
import re
from html import escape
from pathlib import Path

from src.renderer import _CSS as PAPER_CSS, _JS as PAPER_JS, render_question_card


TOPIC_GROUPS = {
    "1": ("Data Representation",
          ["1.1", "1.2", "1.3"],
          "Number systems, text/sound/images, storage & compression"),
    "2": ("Data Transmission",
          ["2.1", "2.2", "2.3"],
          "Transmission methods, error detection, encryption"),
    "3": ("Hardware",
          ["3.1", "3.2", "3.3", "3.4"],
          "Architecture, I/O devices, storage, network hardware"),
    "4": ("Software",
          ["4.1", "4.2"],
          "Software types, programming languages & translators"),
    "5": ("Internet & Cyber",
          ["5.1", "5.2", "5.3"],
          "Web, digital currency, cyber security"),
    "6": ("Emerging Tech",
          ["6.1", "6.2", "6.3"],
          "Automated systems, robotics, AI"),
}

TOPIC_NAMES = {
    "1.1": "Number Systems",
    "1.2": "Text, Sound and Images",
    "1.3": "Data Storage and Compression",
    "2.1": "Types and Methods of Data Transmission",
    "2.2": "Methods of Error Detection",
    "2.3": "Encryption",
    "3.1": "Computer Architecture",
    "3.2": "Input and Output Devices",
    "3.3": "Data Storage",
    "3.4": "Network Hardware",
    "4.1": "Types of Software and Interrupts",
    "4.2": "Programming Languages, Translators and IDEs",
    "5.1": "The Internet and the World Wide Web",
    "5.2": "Digital Currency",
    "5.3": "Cyber Security",
    "6.1": "Automated Systems",
    "6.2": "Robotics",
    "6.3": "Artificial Intelligence",
}

BLOOM_ORDER = ["Remember", "Understand", "Apply", "Analyse", "Evaluate", "Create"]
DIFFICULTY_ORDER = ["Low", "Medium", "High"]
OBJECTIVE_ORDER = ["AO1", "AO2", "AO3"]
MARKS_BUCKETS = ["1", "2", "3", "4", "5+"]


def load_all_questions():
    """Return [(question, source)] across every paper JSON."""
    out = []
    for path in sorted(glob.glob("output/json/*.json")):
        stem = Path(path).stem
        m = re.match(r"0478_([a-z])(\d{2})_qp_(\d+)", stem)
        if not m:
            continue
        sess_letter, yr, variant = m.groups()
        source = {
            "paper":   stem,
            "session": f"{sess_letter}{yr}",
            "variant": variant,
            "year":    f"20{yr}",
        }
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            continue
        for q in data.get("questions", []):
            out.append((q, source))
    return out


def question_sort_key(q, src):
    return (
        q.get("topic", "") or "",
        src["year"],
        src["session"],
        src["variant"],
        q.get("id", "") or "",
    )


# ============================================================================
# CSS / JS
# ============================================================================

TOPICS_CSS = """
/* Extends paper.css for topic revision pages */
.topic-page-header {
    background: #1e3a5f; color: #fff;
    padding: 1.25rem 1.5rem; margin-bottom: 1rem;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 1rem;
}
.topic-page-header h1 { font-size: 1.4rem; font-weight: 700; }
.topic-page-header .crumbs { font-size: .85rem; opacity: .85; margin-top: .25rem; }
.topic-page-header a.back-link {
    color: #fff; text-decoration: none; font-size: .85rem;
    padding: .4rem .85rem; border: 1px solid rgba(255,255,255,.4); border-radius: 6px;
}
.topic-page-header a.back-link:hover { background: rgba(255,255,255,.1); }

.filter-bar {
    position: sticky; top: 0; z-index: 10;
    background: #fff;
    border: 1px solid #e5e7eb; border-radius: 10px;
    padding: .85rem 1rem; margin-bottom: 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,.05);
    display: flex; flex-direction: column; gap: .55rem;
}
.filter-row { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; }
.filter-label {
    font-size: .7rem; font-weight: 700; color: #6b7280;
    text-transform: uppercase; letter-spacing: .06em;
    width: 5.5rem; flex-shrink: 0;
}
.tab-group { display: flex; gap: .35rem; flex-wrap: wrap; }
.tab-btn {
    padding: .3rem .75rem; border-radius: 6px;
    border: 1.5px solid #e5e7eb; background: #fff;
    color: #4b5563; font-size: .8rem; font-weight: 500;
    cursor: pointer; transition: all .12s;
}
.tab-btn:hover:not(:disabled) { border-color: #1e3a5f; color: #1e3a5f; }
.tab-btn.active { background: #1e3a5f; color: #fff; border-color: #1e3a5f; }
.tab-btn:disabled { opacity: .35; cursor: not-allowed; }

.actions-row { display: flex; gap: .5rem; flex-wrap: wrap; padding-top: .25rem; }
.action-btn {
    padding: .35rem .85rem; border-radius: 6px;
    border: 1px solid #d1d5db; background: #fff;
    font-size: .8rem; font-weight: 500; cursor: pointer;
    color: #374151;
}
.action-btn:hover { background: #f3f4f6; border-color: #9ca3af; }
.action-btn.primary { background: #1e3a5f; color: #fff; border-color: #1e3a5f; }
.action-btn.primary:hover { background: #2d4f7a; }

.counter {
    font-size: .85rem; color: #6b7280; margin-bottom: 1rem; padding-left: .25rem;
}
.counter strong { color: #1e3a5f; }

.empty-state {
    background: #fff; border-radius: 10px; padding: 3rem 1.5rem;
    text-align: center; color: #6b7280; font-size: .9rem;
    border: 1px dashed #d1d5db;
}

/* === Index page (topics.html) === */
.topics-index-header {
    background: #1e3a5f; color: #fff;
    padding: 2rem 1.5rem; margin-bottom: 2rem; border-radius: 10px;
}
.topics-index-header h1 { font-size: 1.75rem; font-weight: 700; }
.topics-index-header p { font-size: .95rem; opacity: .8; margin-top: .35rem; }
.topics-index-header .links {
    margin-top: 1rem; display: flex; gap: .6rem; flex-wrap: wrap;
}
.topics-index-header .links a {
    color: #fff; text-decoration: none; font-size: .8rem;
    padding: .35rem .8rem; border: 1px solid rgba(255,255,255,.4); border-radius: 6px;
}
.topics-index-header .links a:hover { background: rgba(255,255,255,.12); }

.topic-index-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
}
.topic-card {
    background: #fff; border-radius: 10px; padding: 1.4rem 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,.08);
    text-decoration: none; color: inherit;
    border: 2px solid transparent; transition: all .15s;
    display: flex; flex-direction: column; gap: .6rem;
}
.topic-card:hover { border-color: #1e3a5f; transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,.08); }
.topic-card .topic-num {
    font-size: 2rem; font-weight: 700; color: #1e3a5f; line-height: 1;
}
.topic-card .topic-name {
    font-size: 1.05rem; font-weight: 600; color: #1f2937;
}
.topic-card .topic-desc {
    font-size: .825rem; color: #6b7280; line-height: 1.45;
}
.topic-card .topic-meta {
    margin-top: auto; padding-top: .65rem; border-top: 1px solid #f3f4f6;
    font-size: .75rem; color: #6b7280; display: flex; justify-content: space-between;
    flex-wrap: wrap; gap: .35rem;
}
.topic-card .topic-meta strong { color: #1e3a5f; font-weight: 700; }
.subtopic-chips { display: flex; gap: .25rem; flex-wrap: wrap; }
.subtopic-chip {
    font-size: .7rem; padding: .12rem .45rem; border-radius: 999px;
    background: #eff6ff; color: #1e3a5f; font-weight: 600;
}
"""

TOPICS_JS = """
const FILTERS = ['subtopic','difficulty','objective','bloom','command','marks','year'];
const state = Object.fromEntries(FILTERS.map(f => [f, 'all']));

function matchesMarks(card) {
    if (state.marks === 'all') return true;
    const m = parseInt(card.dataset.marks, 10);
    if (Number.isNaN(m)) return false;
    if (state.marks === '5+') return m >= 5;
    return m === parseInt(state.marks, 10);
}

function cardMatches(card) {
    for (const f of FILTERS) {
        if (f === 'marks') { if (!matchesMarks(card)) return false; continue; }
        if (state[f] !== 'all' && card.dataset[f] !== state[f]) return false;
    }
    return true;
}

function applyFilters() {
    const cards = document.querySelectorAll('.card');
    let shown = 0;
    cards.forEach(card => {
        const match = cardMatches(card);
        card.style.display = match ? '' : 'none';
        if (match) shown++;
    });
    document.getElementById('counter-shown').textContent = shown;
    document.getElementById('counter-total').textContent = cards.length;
    const empty = document.getElementById('empty-state');
    if (empty) empty.style.display = shown === 0 ? '' : 'none';
}

function bindFilterTabs() {
    document.querySelectorAll('.tab-group[data-filter]').forEach(group => {
        const filter = group.dataset.filter;
        group.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (btn.disabled) return;
                state[filter] = btn.dataset.value;
                group.querySelectorAll('.tab-btn').forEach(b =>
                    b.classList.toggle('active', b.dataset.value === state[filter])
                );
                applyFilters();
            });
        });
    });
}

function bindActions() {
    const expandAll = document.getElementById('btn-expand-all');
    const collapseAll = document.getElementById('btn-collapse-all');
    const reset = document.getElementById('btn-reset');

    if (expandAll) expandAll.addEventListener('click', () => {
        document.querySelectorAll('.card').forEach(c => {
            if (c.style.display !== 'none') c.classList.add('open');
        });
    });
    if (collapseAll) collapseAll.addEventListener('click', () => {
        document.querySelectorAll('.card').forEach(c => c.classList.remove('open'));
    });
    if (reset) reset.addEventListener('click', () => {
        FILTERS.forEach(f => state[f] = 'all');
        document.querySelectorAll('.tab-group[data-filter]').forEach(group => {
            group.querySelectorAll('.tab-btn').forEach(b =>
                b.classList.toggle('active', b.dataset.value === 'all')
            );
        });
        applyFilters();
    });
}

bindFilterTabs();
bindActions();
applyFilters();
"""


# ============================================================================
# HTML builders
# ============================================================================

def _tab_group(filter_key, options, present_values):
    """Build a single filter row. `options` is a list of (value, label) pairs.
    Buttons whose value isn't in `present_values` are disabled."""
    buttons = [
        '<button class="tab-btn active" data-value="all">All</button>'
    ]
    for value, label in options:
        disabled = "" if value in present_values else " disabled"
        buttons.append(
            f'<button class="tab-btn" data-value="{escape(value)}"{disabled}>'
            f'{escape(label)}</button>'
        )
    return (
        f'<div class="tab-group" data-filter="{filter_key}">'
        f'{"".join(buttons)}'
        f'</div>'
    )


def _present_marks(questions):
    """Return the set of marks-bucket values that appear in this topic."""
    out = set()
    for q, _ in questions:
        m = q.get("marks")
        try:
            m = int(m)
        except (TypeError, ValueError):
            continue
        out.add("5+" if m >= 5 else str(m))
    return out


def _present_simple(questions, field):
    return {q.get(field) for q, _ in questions if q.get(field)}


def _present_source(questions, field):
    return {src[field] for _, src in questions}


def build_topic_page(group_id, questions):
    """Build topic_N.html for a topic group."""
    name, subtopics, desc = TOPIC_GROUPS[group_id]

    # Filter options derived from actual data present in this topic
    present_subtopics  = _present_simple(questions, "topic")
    present_difficulty = _present_simple(questions, "difficulty")
    present_objective  = _present_simple(questions, "objective")
    present_bloom      = _present_simple(questions, "bloom_level")
    present_command    = sorted(_present_simple(questions, "command"))
    present_marks      = _present_marks(questions)
    present_years      = sorted(_present_source(questions, "year"))

    subtopic_opts = [(st, st) for st in subtopics]
    difficulty_opts = [(d, d) for d in DIFFICULTY_ORDER]
    objective_opts  = [(o, o) for o in OBJECTIVE_ORDER]
    bloom_opts      = [(b, b) for b in BLOOM_ORDER]
    command_opts    = [(c, c) for c in present_command]
    marks_opts      = [(m, m) for m in MARKS_BUCKETS]
    year_opts       = [(y, y) for y in present_years]

    filter_bar = (
        '<div class="filter-bar">'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Subtopic</span>'
        f'    {_tab_group("subtopic", subtopic_opts, present_subtopics)}'
        f'  </div>'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Difficulty</span>'
        f'    {_tab_group("difficulty", difficulty_opts, present_difficulty)}'
        f'  </div>'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Objective</span>'
        f'    {_tab_group("objective", objective_opts, present_objective)}'
        f'  </div>'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Bloom</span>'
        f'    {_tab_group("bloom", bloom_opts, present_bloom)}'
        f'  </div>'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Command</span>'
        f'    {_tab_group("command", command_opts, set(present_command))}'
        f'  </div>'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Marks</span>'
        f'    {_tab_group("marks", marks_opts, present_marks)}'
        f'  </div>'
        f'  <div class="filter-row">'
        f'    <span class="filter-label">Year</span>'
        f'    {_tab_group("year", year_opts, set(present_years))}'
        f'  </div>'
        f'  <div class="actions-row">'
        f'    <button class="action-btn" id="btn-reset">Reset filters</button>'
        f'    <button class="action-btn" id="btn-expand-all">Expand all</button>'
        f'    <button class="action-btn" id="btn-collapse-all">Collapse all</button>'
        f'  </div>'
        '</div>'
    )

    counter = (
        '<div class="counter">'
        'Showing <strong id="counter-shown">0</strong> of '
        '<strong id="counter-total">0</strong> questions'
        '</div>'
    )

    cards = "\n".join(
        render_question_card(q, source=src) for q, src in questions
    ) or '<div class="empty-state">No questions found for this topic.</div>'

    empty = (
        '<div class="empty-state" id="empty-state" style="display:none">'
        'No questions match the current filters.'
        '</div>'
    )

    crumbs = " · ".join(f"{st} {TOPIC_NAMES.get(st, st)}" for st in subtopics)
    paper_count = len({src["paper"] for _, src in questions})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Topic {group_id} · {escape(name)} — Cambridge IGCSE 0478 Revision</title>
<link rel="stylesheet" href="paper.css">
<link rel="stylesheet" href="topics.css">
</head>
<body>
<div class="page">
  <div class="topic-page-header">
    <div>
      <h1>Topic {group_id} · {escape(name)}</h1>
      <div class="crumbs">{escape(crumbs)}</div>
      <div class="crumbs">{len(questions)} questions across {paper_count} papers</div>
    </div>
    <a class="back-link" href="topics.html">← All topics</a>
  </div>
  {filter_bar}
  {counter}
  {cards}
  {empty}
</div>
<script src="paper.js"></script>
<script src="topics.js"></script>
</body>
</html>"""


def build_index(by_group, total_papers):
    """Build topics.html index page."""
    cards = []
    for group_id, (name, subtopics, desc) in TOPIC_GROUPS.items():
        qs = by_group.get(group_id, [])
        chips = "".join(
            f'<span class="subtopic-chip">{escape(st)}</span>' for st in subtopics
        )
        cards.append(
            f'<a class="topic-card" href="topic_{group_id}.html">'
            f'  <div class="topic-num">{group_id}</div>'
            f'  <div class="topic-name">{escape(name)}</div>'
            f'  <div class="topic-desc">{escape(desc)}</div>'
            f'  <div class="subtopic-chips">{chips}</div>'
            f'  <div class="topic-meta">'
            f'    <span><strong>{len(qs)}</strong> questions</span>'
            f'    <span>{len(subtopics)} subtopics</span>'
            f'  </div>'
            f'</a>'
        )

    total_questions = sum(len(v) for v in by_group.values())

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Topics — Cambridge IGCSE 0478 Revision</title>
<link rel="stylesheet" href="paper.css">
<link rel="stylesheet" href="topics.css">
</head>
<body>
<div class="page">
  <div class="topics-index-header">
    <h1>Cambridge IGCSE 0478 · Topic Revision</h1>
    <p>Browse {total_questions} questions across {total_papers} past papers, grouped by syllabus topic.</p>
    <div class="links">
      <a href="statistics.html">📊 Statistics</a>
    </div>
  </div>
  <div class="topic-index-grid">
    {"".join(cards)}
  </div>
</div>
</body>
</html>"""


def main():
    all_qs = load_all_questions()
    if not all_qs:
        print("No questions found in output/json/")
        return

    by_group = {g: [] for g in TOPIC_GROUPS}
    for q, src in all_qs:
        g = (q.get("topic") or "")[:1]
        if g in by_group:
            by_group[g].append((q, src))

    for g, lst in by_group.items():
        lst.sort(key=lambda t: question_sort_key(t[0], t[1]))

    out_dir = Path("output/html")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Shared assets
    (out_dir / "paper.css").write_text(PAPER_CSS, encoding="utf-8")
    (out_dir / "paper.js").write_text(PAPER_JS, encoding="utf-8")
    (out_dir / "topics.css").write_text(TOPICS_CSS, encoding="utf-8")
    (out_dir / "topics.js").write_text(TOPICS_JS, encoding="utf-8")

    # Topic pages
    for g in TOPIC_GROUPS:
        path = out_dir / f"topic_{g}.html"
        path.write_text(build_topic_page(g, by_group[g]), encoding="utf-8")
        print(f"Written: {path}  ({len(by_group[g])} questions)")

    # Index
    total_papers = len({src["paper"] for _, src in all_qs})
    index_path = out_dir / "topics.html"
    index_path.write_text(build_index(by_group, total_papers), encoding="utf-8")
    print(f"Written: {index_path}  (index)")


if __name__ == "__main__":
    main()
