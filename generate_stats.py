#!/usr/bin/env python3
"""Generate output/html/statistics.html from all paper JSONs in output/json/."""

import glob
import json
import re
from pathlib import Path


SESSION_LABELS = {
    "m24": "March 2024",
    "s24": "Summer 2024",
    "w24": "Winter 2024",
    "m25": "March 2025",
    "s25": "Summer 2025",
    "w25": "Winter 2025",
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
    "4.2": "Types of Programming Language, Translators and IDEs",
    "5.1": "The Internet and the World Wide Web",
    "5.2": "Digital Currency",
    "5.3": "Cyber Security",
    "6.1": "Automated Systems",
    "6.2": "Robotics",
    "6.3": "Artificial Intelligence",
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


_CSS = """\
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #f0f4f8;
  color: #1a202c;
  line-height: 1.5;
}
.page { max-width: 1100px; margin: 0 auto; padding: 0 1rem 3rem; }

.page-header {
  background: #1e3a5f;
  color: white;
  padding: 1.5rem 1rem;
  margin: 0 -1rem 1.5rem;
}
.page-header h1 { font-size: 1.5rem; font-weight: 700; }
.page-header p { font-size: 0.875rem; opacity: 0.75; margin-top: 0.25rem; }

.selector-bar {
  background: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}
.selector-row { display: flex; align-items: center; gap: 0.75rem; }
.selector-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  width: 4.5rem;
  flex-shrink: 0;
}
.tab-group { display: flex; gap: 0.375rem; flex-wrap: wrap; }
.tab-btn {
  padding: 0.375rem 0.875rem;
  border-radius: 6px;
  border: 1.5px solid #e2e8f0;
  background: white;
  color: #4a5568;
  font-size: 0.825rem;
  cursor: pointer;
  transition: all 0.15s;
}
.tab-btn:hover:not(:disabled) { border-color: #1e3a5f; color: #1e3a5f; }
.tab-btn.active { background: #1e3a5f; color: white; border-color: #1e3a5f; }
.tab-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.current-label {
  font-size: 0.8rem;
  color: #718096;
  margin-bottom: 1rem;
  padding-left: 0.25rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 0.875rem;
  margin-bottom: 1.25rem;
}
.summary-card {
  background: white;
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  text-align: center;
}
.summary-card .value {
  font-size: 1.875rem;
  font-weight: 700;
  color: #1e3a5f;
  line-height: 1;
  margin-bottom: 0.375rem;
}
.summary-card .label {
  font-size: 0.675rem;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.charts-container { display: flex; flex-direction: column; gap: 1rem; }
.chart-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
.chart-row-2 { display: grid; grid-template-columns: 1fr 1.5fr; gap: 1rem; }
.chart-card {
  background: white;
  border-radius: 8px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.chart-card h2 {
  font-size: 0.8rem;
  font-weight: 700;
  color: #2d3748;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}
.chart-note {
  font-size: 0.725rem;
  color: #718096;
  margin-bottom: 0.75rem;
}
.chart-wrapper { position: relative; min-height: 180px; }
.chart-wrapper.tall { height: 500px; }
.chart-wrapper.medium { height: 260px; }

@media (max-width: 700px) {
  .chart-row, .chart-row-2 { grid-template-columns: 1fr; }
}
"""


_JS_LOGIC = """\
Chart.register(ChartDataLabels);
const DIFF_COLORS = { Low: '#22c55e', Medium: '#f59e0b', High: '#ef4444' };
const LOAD_COLORS = { Low: '#34d399', Medium: '#60a5fa', High: '#f97316' };
const OBJ_COLORS  = { AO1: '#3b82f6', AO2: '#22c55e', AO3: '#f97316' };
const BLOOM_ORDER  = ['Remember','Understand','Apply','Analyse','Evaluate','Create'];
const BLOOM_COLORS = ['#f87171','#fb923c','#facc15','#4ade80','#60a5fa','#a78bfa'];

let currentYear       = 'all';
let currentSession    = 'all';
let currentVariant    = 'all';
let currentTopicGroup = 'all';
let currentStats      = {};
const charts = {};

const TOPIC_GROUP_LABELS = {
  '1': 'Data Representation',
  '2': 'Data Transmission',
  '3': 'Hardware',
  '4': 'Software',
  '5': 'Internet & Cyber',
  '6': 'Emerging Tech',
};

const LAYOUT_NAMES = {
  'SimpleSingleBlock':     'Open Response',
  'NumberedMultiList':     'Multi-part List',
  'MatrixGrid':            'Grid / Matrix',
  'MultiPartLabeledBlock': 'Labelled Multi-part',
  'TermDefinitionGrid':    'Term–Definition Table',
  'InlineCloze':           'Fill in the Blank',
  'AnnotatedDiagram':      'Annotated Diagram',
  'ValueTraceMatrix':      'Value Trace Table',
  'LabelledPartResponse':  'Labelled Part Response',
  'FixedRegisterArray':    'Register Array',
};

function sessionYear(s) {
  const m = s.match(/([a-z]+)(\d+)$/);
  return m ? '20' + m[2] : null;
}

function getFilteredSessionKeys() {
  let keys = Object.keys(SESSIONS);
  if (currentYear !== 'all') keys = keys.filter(s => sessionYear(s) === currentYear);
  if (currentSession !== 'all') keys = keys.filter(s => s === currentSession);
  return keys;
}

function getFilteredPaperKeys() {
  let paperKeys = getFilteredSessionKeys().flatMap(s => SESSIONS[s] || []);
  if (currentVariant !== 'all') paperKeys = paperKeys.filter(pk => PAPERS[pk].variant === currentVariant);
  return paperKeys;
}

function aggregateStats(paperKeys) {
  const result = {};
  const axes = ['topic','difficulty','bloom_level','cognitive_load','objective','layout_type','command','answer_type'];
  for (const axis of axes) {
    for (const prefix of ['marks_by_', 'count_by_']) {
      const key = prefix + axis;
      result[key] = {};
      for (const pk of paperKeys) {
        const src = (PAPERS[pk].statistics || {})[key] || {};
        for (const [k, v] of Object.entries(src)) {
          result[key][k] = (result[key][k] || 0) + v;
        }
      }
    }
  }
  return result;
}

function aggregateSummary(paperKeys, stats) {
  const totalMarks = paperKeys.reduce((s, pk) => s + (PAPERS[pk].total_marks || 0), 0);
  const qCount     = paperKeys.reduce((s, pk) => s + (PAPERS[pk].summary.question_count || 0), 0);
  const mcqCount   = paperKeys.reduce((s, pk) => s + (PAPERS[pk].summary.mcq_count || 0), 0);
  const maxMarks   = paperKeys.length ? Math.max(...paperKeys.map(pk => PAPERS[pk].summary.max_marks_per_question || 0)) : 0;
  return {
    total_marks: totalMarks,
    question_count: qCount,
    mcq_count: mcqCount,
    mean_marks_per_question: qCount ? (totalMarks / qCount).toFixed(2) : 0,
    max_marks_per_question: maxMarks,
    unique_topics_count: Object.keys(stats.marks_by_topic || {}).length,
  };
}

function getCurrentData() {
  const paperKeys = getFilteredPaperKeys();
  if (paperKeys.length === 0) {
    return { stats: {}, summary: { question_count: 0, mcq_count: 0, mean_marks_per_question: 0, max_marks_per_question: 0, unique_topics_count: 0 }, totalMarks: 0 };
  }
  if (paperKeys.length === 1) {
    const p = PAPERS[paperKeys[0]];
    return { stats: p.statistics, summary: p.summary, totalMarks: p.total_marks };
  }
  const stats   = aggregateStats(paperKeys);
  const summary = aggregateSummary(paperKeys, stats);
  return { stats, summary, totalMarks: summary.total_marks };
}

function sortedEntries(obj, limit) {
  let entries = Object.entries(obj).filter(([, v]) => v > 0);
  entries.sort((a, b) => b[1] - a[1]);
  return limit ? entries.slice(0, limit) : entries;
}

function destroyChart(id) {
  if (charts[id]) { charts[id].destroy(); delete charts[id]; }
}

function makeHBar(id, labels, data, color) {
  destroyChart(id);
  const ctx = document.getElementById(id);
  if (!ctx) return;
  const total = data.reduce((s, v) => s + v, 0);
  charts[id] = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ data, backgroundColor: color, borderRadius: 3, borderSkipped: false }] },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { right: 48 } },
      plugins: {
        legend: { display: false },
        datalabels: {
          anchor: 'end',
          align: 'end',
          color: '#4a5568',
          font: { size: 10, weight: '600' },
          formatter: (value) => {
            const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
            return `${pct}%`;
          }
        }
      },
      scales: {
        x: { beginAtZero: true, grid: { color: '#f0f4f8' }, ticks: { font: { size: 11 } } },
        y: { ticks: { font: { size: 11 } } }
      }
    }
  });
}

function makeDoughnut(id, labels, data, colors) {
  destroyChart(id);
  const ctx = document.getElementById(id);
  if (!ctx) return;
  const total = data.reduce((s, v) => s + v, 0);
  charts[id] = new Chart(ctx, {
    type: 'doughnut',
    data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 2, borderColor: 'white' }] },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '55%',
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 10 }, padding: 10, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const val = ctx.parsed;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
              return ` ${ctx.label}: ${val} marks (${pct}%)`;
            }
          }
        },
        datalabels: {
          color: 'white',
          font: { size: 11, weight: 'bold' },
          formatter: (value) => {
            const pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
            return pct >= 5 ? `${pct}%` : '';
          }
        }
      }
    }
  });
}

function renderSummaryCards(summary, totalMarks) {
  const cards = [
    { value: totalMarks,                          label: 'Total Marks' },
    { value: summary.question_count,              label: 'Questions' },
    { value: summary.mcq_count,                   label: 'MCQ' },
    { value: summary.mean_marks_per_question,     label: 'Mean Marks/Q' },
    { value: summary.max_marks_per_question,      label: 'Max Marks/Q' },
    { value: summary.unique_topics_count,         label: 'Topics Covered' },
  ];
  document.getElementById('summary-cards').innerHTML = cards
    .map(c => `<div class="summary-card"><div class="value">${c.value}</div><div class="label">${c.label}</div></div>`)
    .join('');
}

function renderTopicChart(stats) {
  let entries = sortedEntries(stats.marks_by_topic || {});
  if (currentTopicGroup !== 'all')
    entries = entries.filter(([code]) => code.startsWith(currentTopicGroup + '.'));
  const labels = entries.map(([code]) => `${code}  ${TOPIC_NAMES[code] || code}`);
  makeHBar('chart-topic', labels, entries.map(([, v]) => v), '#3b82f6');
}

function renderDifficultyChart(stats) {
  const raw    = stats.marks_by_difficulty || {};
  const labels = ['Low', 'Medium', 'High'].filter(k => raw[k]);
  makeDoughnut('chart-difficulty', labels, labels.map(k => raw[k]), labels.map(k => DIFF_COLORS[k]));
}

function renderBloomChart(stats) {
  const raw    = stats.marks_by_bloom_level || {};
  const labels = BLOOM_ORDER.filter(k => raw[k]);
  makeDoughnut('chart-bloom', labels, labels.map(k => raw[k]),
    labels.map((_, i) => BLOOM_COLORS[i % BLOOM_COLORS.length]));
}

function renderCognitiveChart(stats) {
  const raw    = stats.marks_by_cognitive_load || {};
  const labels = ['Low', 'Medium', 'High'].filter(k => raw[k]);
  makeDoughnut('chart-cognitive', labels, labels.map(k => raw[k]), labels.map(k => LOAD_COLORS[k]));
}

function renderObjectiveChart(stats) {
  const raw    = stats.marks_by_objective || {};
  const labels = ['AO1', 'AO2', 'AO3'].filter(k => raw[k]);
  makeDoughnut('chart-objective', labels, labels.map(k => raw[k]), labels.map(k => OBJ_COLORS[k]));
}

function renderLayoutChart(stats) {
  const entries = sortedEntries(stats.marks_by_layout_type || {});
  makeHBar('chart-layout', entries.map(([k]) => LAYOUT_NAMES[k] || k), entries.map(([, v]) => v), '#8b5cf6');
}

function renderCommandChart(stats) {
  const entries = sortedEntries(stats.count_by_command || {}, 12);
  makeHBar('chart-command', entries.map(([k]) => k), entries.map(([, v]) => v), '#06b6d4');
}

function renderAnswerTypeChart(stats) {
  const entries = sortedEntries(stats.marks_by_answer_type || {});
  makeHBar('chart-answer-type', entries.map(([k]) => k), entries.map(([, v]) => v), '#f97316');
}

function renderAll() {
  const { stats, summary, totalMarks } = getCurrentData();
  currentStats = stats;
  const yearLabel    = currentYear === 'all' ? 'All years' : currentYear;
  const sessionLabel = currentSession === 'all' ? 'All sessions' : (SESSION_LABELS[currentSession] || currentSession);
  const variantLabel = currentVariant === 'all' ? 'All variants' : `Variant ${currentVariant}`;
  document.getElementById('current-label').textContent =
    `Showing: ${yearLabel} — ${sessionLabel} — ${variantLabel}`;
  renderSummaryCards(summary, totalMarks);
  buildTopicGroupTabs();
  renderTopicChart(stats);
  renderDifficultyChart(stats);
  renderBloomChart(stats);
  renderCognitiveChart(stats);
  renderObjectiveChart(stats);
  renderLayoutChart(stats);
  renderCommandChart(stats);
  renderAnswerTypeChart(stats);
}

function buildTopicGroupTabs() {
  const container = document.getElementById('topic-group-tabs');
  container.innerHTML = '';
  const allBtn = document.createElement('button');
  allBtn.className = 'tab-btn' + (currentTopicGroup === 'all' ? ' active' : '');
  allBtn.textContent = 'All';
  allBtn.addEventListener('click', () => {
    currentTopicGroup = 'all'; buildTopicGroupTabs(); renderTopicChart(currentStats);
  });
  container.appendChild(allBtn);
  for (const g of ['1','2','3','4','5','6']) {
    const btn = document.createElement('button');
    const ok  = Object.keys(currentStats.marks_by_topic || {}).some(k => k.startsWith(g + '.'));
    btn.className = 'tab-btn' + (currentTopicGroup === g ? ' active' : '');
    btn.textContent = g;
    btn.title = TOPIC_GROUP_LABELS[g] || g;
    btn.disabled = !ok;
    if (ok) btn.addEventListener('click', () => {
      currentTopicGroup = g; buildTopicGroupTabs(); renderTopicChart(currentStats);
    });
    container.appendChild(btn);
  }
}

function buildYearTabs() {
  const container = document.getElementById('year-tabs');
  container.innerHTML = '';
  const years = [...new Set(Object.keys(SESSIONS).map(sessionYear))].filter(Boolean).sort();
  for (const [yr, label] of [['all', 'All'], ...years.map(y => [y, y])]) {
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (yr === currentYear ? ' active' : '');
    btn.textContent = label;
    btn.addEventListener('click', () => {
      currentYear = yr; currentSession = 'all'; currentVariant = 'all';
      buildYearTabs(); buildSessionTabs(); buildVariantPills(); renderAll();
    });
    container.appendChild(btn);
  }
}

function buildSessionTabs() {
  const container = document.getElementById('session-tabs');
  container.innerHTML = '';
  let available = Object.keys(SESSIONS);
  if (currentYear !== 'all') available = available.filter(s => sessionYear(s) === currentYear);
  available.sort();

  const allBtn = document.createElement('button');
  allBtn.className = 'tab-btn' + (currentSession === 'all' ? ' active' : '');
  allBtn.textContent = 'All';
  allBtn.addEventListener('click', () => {
    currentSession = 'all'; currentVariant = 'all';
    buildSessionTabs(); buildVariantPills(); renderAll();
  });
  container.appendChild(allBtn);

  for (const s of available) {
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (s === currentSession ? ' active' : '');
    btn.textContent = SESSION_LABELS[s] || s;
    btn.addEventListener('click', () => {
      currentSession = s; currentVariant = 'all';
      buildSessionTabs(); buildVariantPills(); renderAll();
    });
    container.appendChild(btn);
  }
}

function buildVariantPills() {
  const container = document.getElementById('variant-pills');
  container.innerHTML = '';
  const available = new Set(
    getFilteredSessionKeys().flatMap(s => SESSIONS[s] || []).map(pk => PAPERS[pk].variant)
  );

  const allBtn = document.createElement('button');
  allBtn.className = 'tab-btn' + (currentVariant === 'all' ? ' active' : '');
  allBtn.textContent = 'All';
  allBtn.addEventListener('click', () => {
    currentVariant = 'all'; buildVariantPills(); renderAll();
  });
  container.appendChild(allBtn);

  for (const v of ['11', '12', '13']) {
    const btn = document.createElement('button');
    const ok  = available.has(v);
    btn.className = 'tab-btn' + (currentVariant === v ? ' active' : '');
    btn.textContent = `V${v}`;
    btn.disabled = !ok;
    if (ok) {
      btn.addEventListener('click', () => {
        currentVariant = v; buildVariantPills(); renderAll();
      });
    }
    container.appendChild(btn);
  }
}

buildYearTabs();
buildSessionTabs();
buildVariantPills();
renderAll();
buildTopicGroupTabs();
"""


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
      <div class="selector-row">
        <span class="selector-label">Year</span>
        <div class="tab-group" id="year-tabs"></div>
      </div>
      <div class="selector-row">
        <span class="selector-label">Session</span>
        <div class="tab-group" id="session-tabs"></div>
      </div>
      <div class="selector-row">
        <span class="selector-label">Variant</span>
        <div class="tab-group" id="variant-pills"></div>
      </div>
    </div>

    <div class="current-label" id="current-label"></div>

    <div class="summary-grid" id="summary-cards"></div>

    <div class="charts-container">
      <div class="chart-card">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
          <h2 style="margin-bottom:0">Topic Coverage</h2>
          <div class="tab-group" id="topic-group-tabs"></div>
        </div>
        <div class="chart-wrapper tall"><canvas id="chart-topic"></canvas></div>
      </div>

      <div class="chart-row">
        <div class="chart-card">
          <h2>Difficulty</h2>
          <div class="chart-wrapper"><canvas id="chart-difficulty"></canvas></div>
        </div>
        <div class="chart-card">
          <h2>Bloom's Taxonomy</h2>
          <div class="chart-wrapper"><canvas id="chart-bloom"></canvas></div>
        </div>
        <div class="chart-card">
          <h2>Cognitive Load</h2>
          <div class="chart-wrapper"><canvas id="chart-cognitive"></canvas></div>
        </div>
      </div>

      <div class="chart-row-2">
        <div class="chart-card">
          <h2>Assessment Objectives</h2>
          <p class="chart-note">Cambridge target: AO1 40% · AO2 40% · AO3 20%</p>
          <div class="chart-wrapper"><canvas id="chart-objective"></canvas></div>
        </div>
        <div class="chart-card">
          <h2>Answer Types</h2>
          <div class="chart-wrapper medium"><canvas id="chart-answer-type"></canvas></div>
        </div>
      </div>

      <div class="chart-card">
        <h2>Layout Types</h2>
        <div class="chart-wrapper medium"><canvas id="chart-layout"></canvas></div>
      </div>

      <div class="chart-card">
        <h2>Command Words <span style="font-size:0.7rem;color:#718096;font-weight:400">(by count, top 12)</span></h2>
        <div class="chart-wrapper medium"><canvas id="chart-command"></canvas></div>
      </div>
    </div>
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
