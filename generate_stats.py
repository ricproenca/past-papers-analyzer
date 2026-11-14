#!/usr/bin/env python3
"""Generate output/html/statistics.html from all paper JSONs in output/json/."""

import glob
import json
import re
from pathlib import Path

from src.assets import read_asset
from src.syllabus import TOPIC_NAMES


SESSION_LABELS = {
    "m24": "March 2024",
    "s24": "Summer 2024",
    "w24": "Winter 2024",
    "m25": "March 2025",
    "s25": "Summer 2025",
    "w25": "Winter 2025",
}


def load_papers():
    papers = {}
    sessions = {}
    for path in sorted(glob.glob("output/json/*.json")):
        stem = Path(path).stem
        m = re.match(r"0478_([a-z0-9]+)_qp_(\d+)", stem)
        if not m:
            continue
        session, variant = m.group(1), m.group(2)
        data = json.loads(Path(path).read_text())
        papers[stem] = {
            "session": session,
            "variant": variant,
            "qp": data.get("qp", ""),
            "total_marks": data.get("total_marks", 0),
            "summary": data.get("summary", {}),
            "statistics": data.get("statistics", {}),
        }
        sessions.setdefault(session, []).append(stem)
    return papers, sessions


_CSS = read_asset("stats.css")

_JS_LOGIC = read_asset("stats.js")


def generate_html(papers: dict, sessions: dict) -> str:
    papers_json       = json.dumps(papers, indent=2)
    sessions_json     = json.dumps(sessions, indent=2)
    topic_names_json  = json.dumps(TOPIC_NAMES, indent=2)
    session_labels_json = json.dumps(SESSION_LABELS, indent=2)

    data_block = (
        f"const PAPERS = {papers_json};\n"
        f"const SESSIONS = {sessions_json};\n"
        f"const TOPIC_NAMES = {topic_names_json};\n"
        f"const SESSION_LABELS = {session_labels_json};\n"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cambridge IGCSE 0478 — Paper Statistics</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
  <style>
{_CSS}  </style>
</head>
<body>
  <div class="page">
    <header class="page-header">
      <h1>Cambridge IGCSE 0478</h1>
      <p>Computer Science · Paper Statistics</p>
    </header>

    <div class="selector-bar">
      <button class="filter-toggle" type="button" aria-expanded="true">
        <span class="chevron">▾</span>
        <span class="filter-toggle-label">Filters</span>
        <span class="filter-summary"></span>
      </button>
      <div class="filter-body">
      <div class="selector-row">
        <span class="selector-label">Year</span>
        <div class="tab-group" id="year-tabs"></div>
      </div>
      <div class="selector-row">
        <span class="selector-label">Paper</span>
        <div class="tab-group" id="paper-tabs"></div>
      </div>
      <div class="selector-row">
        <span class="selector-label">Variant</span>
        <div class="tab-group" id="variant-pills"></div>
      </div>
      <div class="selector-row">
        <span class="selector-label">Session</span>
        <div class="tab-group" id="session-tabs"></div>
      </div>
      </div>
    </div>

    <div class="current-label" id="current-label"></div>

    <div class="summary-grid" id="summary-cards"></div>

    <div class="charts-container">
      <div class="chart-card">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
          <h2 style="margin-bottom:0">Topic Coverage <span class="unit-pill marks">Marks</span></h2>
          <div class="tab-group" id="topic-group-tabs"></div>
        </div>
        <div class="chart-wrapper tall"><canvas id="chart-topic"></canvas></div>
      </div>

      <div class="chart-row">
        <div class="chart-card">
          <h2>Difficulty <span class="unit-pill marks">Marks</span></h2>
          <div class="chart-wrapper"><canvas id="chart-difficulty"></canvas></div>
        </div>
        <div class="chart-card">
          <h2>Bloom's Taxonomy <span class="unit-pill marks">Marks</span></h2>
          <div class="chart-wrapper"><canvas id="chart-bloom"></canvas></div>
        </div>
        <div class="chart-card">
          <h2>Cognitive Load <span class="unit-pill marks">Marks</span></h2>
          <div class="chart-wrapper"><canvas id="chart-cognitive"></canvas></div>
        </div>
      </div>

      <div class="chart-row-2">
        <div class="chart-card">
          <h2>Assessment Objectives <span class="unit-pill marks">Marks</span></h2>
          <p class="chart-note">Cambridge target: AO1 40% · AO2 40% · AO3 20%</p>
          <div class="chart-wrapper"><canvas id="chart-objective"></canvas></div>
        </div>
        <div class="chart-card">
          <h2>Answer Types <span class="unit-pill marks">Marks</span></h2>
          <div class="chart-wrapper medium"><canvas id="chart-answer-type"></canvas></div>
        </div>
      </div>

      <div class="chart-card">
        <h2>Layout Types <span class="unit-pill marks">Marks</span> <span class="unit-pill count">Questions</span></h2>
        <div class="chart-wrapper tall"><canvas id="chart-layout"></canvas></div>
      </div>

      <div class="chart-card">
        <h2>Command Words <span class="unit-pill count">Questions</span> <span style="font-size:0.7rem;color:#718096;font-weight:400">(top 12)</span></h2>
        <div class="chart-wrapper medium"><canvas id="chart-command"></canvas></div>
      </div>
    </div>

    <section class="reading-guide">
      <h2>Reading the Charts</h2>
      <div class="intro">
        <p>Each chart shows the unit it measures next to its title.</p>
        <p><span class="unit-pill marks">Marks</span> = share of paper marks for that category.</p>
        <p><span class="unit-pill count">Questions</span> = number of questions.</p>
        <p>Percentages on bars and slices are always relative to the currently selected papers, not the whole corpus.</p>
      </div>
      <dl>
        <dt>Topic Coverage</dt>
        <dd>
          <p>Marks per syllabus subtopic (1.1, 1.2, … 6.3).</p>
          <p>Long bars mark heavily-examined areas; use the chapter tabs (1–6) to drill into one chapter.</p>
          <p>Surfaces examiner emphasis when revising.</p>
        </dd>

        <dt>Difficulty</dt>
        <dd>
          <p>Marks split across Low / Medium / High difficulty.</p>
          <p>Derived from command-word × marks.</p>
          <p>Reveals whether a paper leans easy/balanced/hard and where the demanding questions concentrate.</p>
        </dd>

        <dt>Bloom's Taxonomy</dt>
        <dd>
          <p>Marks by cognitive level (Remember → Create), derived from the command word.</p>
          <p>Shows the depth of thinking the paper requires.</p>
          <p>A Remember-heavy paper rewards recall; an Apply-/Analyse-heavy paper rewards practice on worked problems.</p>
        </dd>

        <dt>Cognitive Load</dt>
        <dd>
          <p>Marks by question-layout demand.</p>
          <p>Open-response and multi-part layouts score Higher; single-block and grid layouts score Lower.</p>
          <p>A high-load paper takes more time per mark.</p>
        </dd>

        <dt>Assessment Objectives</dt>
        <dd>
          <p>Marks split AO1 (knowledge) / AO2 (application) / AO3 (evaluation).</p>
          <p>Cambridge targets AO1 40% · AO2 40% · AO3 20%.</p>
          <p>Use this chart to spot drift from the published spec.</p>
        </dd>

        <dt>Answer Types</dt>
        <dd>
          <p>Marks by the kind of answer required (text, MCQ, table-fill, pseudocode, diagram, …).</p>
          <p>Highlights which response formats students need to practise most.</p>
        </dd>

        <dt>Layout Types</dt>
        <dd>
          <p>Two bars per layout: marks (purple) and number of questions (orange).</p>
          <p>Both bars plot the share of their own series total, so a 25% Marks bar is the same length as a 25% Questions bar.</p>
          <p>When the orange bar is longer than the purple, the layout has many low-mark questions; when the purple is longer, the layout has fewer questions but each is worth more.</p>
          <p>Hover any bar for the raw count.</p>
        </dd>

        <dt>Command Words</dt>
        <dd>
          <p>The only count-based chart: number of questions per command verb (State, Explain, Describe, …), top 12.</p>
          <p>Shows the verbs students need to be most fluent at responding to.</p>
        </dd>
      </dl>
    </section>
  </div>

  <script>
{data_block}
{_JS_LOGIC}
  </script>
</body>
</html>"""


def main():
    papers, sessions = load_papers()
    if not papers:
        print("No JSON files found in output/json/")
        return
    html = generate_html(papers, sessions)
    out_path = Path("output/html/statistics.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"Written: {out_path}  ({len(papers)} papers, {len(sessions)} sessions)")


if __name__ == "__main__":
    main()
