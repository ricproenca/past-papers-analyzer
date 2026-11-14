Chart.register(ChartDataLabels);
const DIFF_COLORS = { Low: '#22c55e', Medium: '#f59e0b', High: '#ef4444' };
const LOAD_COLORS = { Low: '#34d399', Medium: '#60a5fa', High: '#f97316' };
const OBJ_COLORS  = { AO1: '#3b82f6', AO2: '#22c55e', AO3: '#f97316' };
const BLOOM_ORDER  = ['Remember','Understand','Apply','Analyse','Evaluate','Create'];
const BLOOM_COLORS = ['#f87171','#fb923c','#facc15','#4ade80','#60a5fa','#a78bfa'];

let currentYear       = 'all';
let currentSession    = 'all';
let currentPaperNum   = '1';
let currentVariant    = 'all';
let currentTopicGroup = 'all';
let currentStats      = {};
const charts = {};

const TOPIC_GROUP_LABELS = {
  '1':  'Data Representation',
  '2':  'Data Transmission',
  '3':  'Hardware',
  '4':  'Software',
  '5':  'Internet & Cyber',
  '6':  'Emerging Tech',
  '7':  'Algorithm Design',
  '8':  'Programming',
  '9':  'Databases',
  '10': 'Boolean Logic',
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
  'CodeBlockResponse':     'Code Block',
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
  if (currentPaperNum !== 'all') paperKeys = paperKeys.filter(pk => (PAPERS[pk].variant || '')[0] === currentPaperNum);
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

function chaptersFromStats(stats) {
  return new Set(
    Object.keys(stats.marks_by_topic || {}).map(k => k.split('.')[0])
  ).size;
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
    unique_chapters_count: chaptersFromStats(stats),
  };
}

function getCurrentData() {
  const paperKeys = getFilteredPaperKeys();
  if (paperKeys.length === 0) {
    return { stats: {}, summary: { question_count: 0, mcq_count: 0, mean_marks_per_question: 0, max_marks_per_question: 0, unique_topics_count: 0, unique_chapters_count: 0 }, totalMarks: 0 };
  }
  if (paperKeys.length === 1) {
    const p = PAPERS[paperKeys[0]];
    const stats = p.statistics || {};
    const summary = { ...(p.summary || {}), unique_chapters_count: chaptersFromStats(stats) };
    return { stats, summary, totalMarks: p.total_marks };
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

function makeHBarGrouped(id, labels, datasets) {
  // Plot bars as % of each series' own total so the two series are directly
  // comparable (a 25% Marks bar is the same length as a 25% Questions bar).
  // Raw values stay accessible via the tooltip.
  destroyChart(id);
  const ctx = document.getElementById(id);
  if (!ctx) return;
  const totals = datasets.map(ds => ds.data.reduce((s, v) => s + v, 0));
  charts[id] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: datasets.map((ds, i) => ({
        label: ds.label,
        data: ds.data.map(v => totals[i] > 0 ? (v / totals[i]) * 100 : 0),
        rawData: ds.data,
        backgroundColor: ds.color,
        borderRadius: 3,
        borderSkipped: false,
      })),
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      layout: { padding: { right: 56 } },
      plugins: {
        legend: { display: true, position: 'top', labels: { font: { size: 11 }, boxWidth: 12, padding: 12 } },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const raw = ctx.dataset.rawData[ctx.dataIndex];
              const pct = ctx.parsed.x.toFixed(1);
              return ` ${ctx.dataset.label}: ${raw} (${pct}%)`;
            }
          }
        },
        datalabels: {
          anchor: 'end',
          align: 'end',
          color: '#4a5568',
          font: { size: 10, weight: '600' },
          formatter: (value) => `${value.toFixed(1)}%`,
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          max: 100,
          grid: { color: '#f0f4f8' },
          ticks: { font: { size: 11 }, callback: (v) => `${v}%` }
        },
        y: { ticks: { font: { size: 11 } } }
      }
    }
  });
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
    { value: summary.unique_chapters_count,       label: 'Chapters Covered' },
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
  const marksMap = stats.marks_by_layout_type || {};
  const countMap = stats.count_by_layout_type || {};
  const keys = new Set([...Object.keys(marksMap), ...Object.keys(countMap)]);
  const entries = [...keys]
    .map(k => [k, marksMap[k] || 0, countMap[k] || 0])
    .filter(([, m, c]) => m > 0 || c > 0)
    .sort((a, b) => b[1] - a[1]);
  const labels = entries.map(([k]) => LAYOUT_NAMES[k] || k);
  makeHBarGrouped('chart-layout', labels, [
    { label: 'Marks',     data: entries.map(([, m]) => m), color: '#8b5cf6' },
    { label: 'Questions', data: entries.map(([, , c]) => c), color: '#fb923c' },
  ]);
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
  const paperLabel   = `Paper ${currentPaperNum}`;
  const variantLabel = currentVariant === 'all' ? 'All variants' : `Variant ${currentVariant}`;
  document.getElementById('current-label').textContent =
    `Showing: ${yearLabel} — ${sessionLabel} — ${paperLabel} — ${variantLabel}`;
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
  updateFilterSummary(summary);
}

function bindFilterCollapse() {
  const bar = document.querySelector('.selector-bar');
  const toggle = bar?.querySelector('.filter-toggle');
  if (!toggle) return;
  toggle.addEventListener('click', () => {
    const collapsed = bar.classList.toggle('collapsed');
    toggle.setAttribute('aria-expanded', String(!collapsed));
  });
}

function updateFilterSummary(summary) {
  const el = document.querySelector('.filter-summary');
  if (!el) return;
  const filters = [];
  if (currentYear !== 'all')    filters.push(currentYear);
  filters.push(`Paper ${currentPaperNum}`);
  if (currentVariant !== 'all') filters.push(`V${currentVariant}`);
  if (currentSession !== 'all') filters.push(SESSION_LABELS[currentSession] || currentSession);
  const qcount = summary?.question_count ?? 0;
  el.textContent = `· ${filters.join(' · ')} · ${qcount} questions`;
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
  for (const g of ['1','2','3','4','5','6','7','8','9','10']) {
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
      // Paper stays sticky across year/session changes (no longer has 'all' value).
      buildYearTabs(); buildSessionTabs(); buildPaperTabs(); buildVariantPills(); renderAll();
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
    buildSessionTabs(); buildPaperTabs(); buildVariantPills(); renderAll();
  });
  container.appendChild(allBtn);

  for (const s of available) {
    const btn = document.createElement('button');
    btn.className = 'tab-btn' + (s === currentSession ? ' active' : '');
    btn.textContent = SESSION_LABELS[s] || s;
    btn.addEventListener('click', () => {
      currentSession = s; currentVariant = 'all';
      buildSessionTabs(); buildPaperTabs(); buildVariantPills(); renderAll();
    });
    container.appendChild(btn);
  }
}

function buildPaperTabs() {
  const container = document.getElementById('paper-tabs');
  container.innerHTML = '';
  let sessionPapers = getFilteredSessionKeys().flatMap(s => SESSIONS[s] || []);
  const available = new Set(sessionPapers.map(pk => (PAPERS[pk].variant || '')[0]).filter(Boolean));

  for (const p of ['1', '2']) {
    const btn = document.createElement('button');
    const ok  = available.has(p);
    btn.className = 'tab-btn' + (currentPaperNum === p ? ' active' : '');
    btn.textContent = `Paper ${p}`;
    btn.disabled = !ok;
    if (ok) {
      btn.addEventListener('click', () => {
        currentPaperNum = p; currentVariant = 'all';
        buildPaperTabs(); buildVariantPills(); renderAll();
      });
    }
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

  for (const v of ['11', '12', '13', '21', '22', '23']) {
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
buildPaperTabs();
buildVariantPills();
bindFilterCollapse();
renderAll();
buildTopicGroupTabs();
