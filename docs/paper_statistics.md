# Paper Statistics

Every parsed paper carries two top-level blocks produced by `src/statistics.py`:
a `summary` object (six headline scalars) and a `statistics` object that rolls
per-question fields up into 16 aggregate dicts (eight axes × two views:
`marks_by_*` and `count_by_*`). This doc explains why each one earns its place,
what story it tells in a webpage, and which additions are worth considering.

---

## 1. Overview

The `statistics` block is generated deterministically — no Claude calls — by
aggregating the `questions[]` array. It has two consumption modes:

- **By-paper**: read `<paper>.summary` and `<paper>.statistics` directly to describe one paper.
- **By-year**: sum the corresponding `marks_by_*` / `count_by_*` dicts across the
  three variants of a session (e.g. `s25_qp_11`, `s25_qp_12`, `s25_qp_13`) to
  describe a whole year. See [Section 6](#6-year-level-aggregation) for the recipe.

Every field is cheap to recompute, so don't be afraid to throw it away and rebuild
when the schema evolves.

The canonical axis list lives in `src/statistics.py:AXES` — when adding or
renaming axes, update both the code and this doc.

### The two views — `marks_by_X` vs `count_by_X`

They look duplicative but answer different questions:

- **marks_by_X**: *how much weight* the paper assigns to category X. A topic with
  one 6-mark question vs six 1-markers has the same marks-by total but very
  different student experience — the count-by view captures that difference.
- **count_by_X**: *how often* category X appears. Frequency drives variety
  (a paper with five MCQs feels different from one with one MCQ even if marks
  are equal).

Keep both for every axis.

---

## 2. The `summary` block (headline scalars)

A small top-level object holding paper-level numbers that a webpage paper-card
needs at a glance, without re-scanning `questions[]`:

| Field | What it tells you |
|-------|-------------------|
| `question_count` | Number of (sub-)questions in the paper. |
| `mcq_count` | How many are multiple-choice. Captures format mix at a glance. |
| `mean_marks_per_question` | Average mark size — high mean = fewer/larger questions. |
| `median_marks_per_question` | Robust to outliers; tells you the "typical" question size. |
| `max_marks_per_question` | The largest single question — sets the upper bound on time-per-item. |
| `unique_topics_count` | Breadth measure — how many of the 18 syllabus topics this paper covers. |

Webpage use: a small card per paper showing these six numbers, plus the
percentage of MCQs (`mcq_count / question_count`).

---

## 3. Why each axis matters

### 3.1 `topic` — syllabus coverage

`marks_by_topic`: which syllabus areas dominate the paper's *weight*. If a paper
gives 12 marks to topic `1.3` (Data Storage) and 2 marks to topic `6.3` (AI), the
weight signal tells a student where to focus revision.

`count_by_topic`: which areas appear at all (breadth). A paper covering 14 of the
18 syllabus topics is broad; one covering 6 is narrow.

By-paper: drives a horizontal bar chart sorted by marks, with the topic name and
% of paper marks next to each bar.

By-year: aggregate to detect which topics are *always* tested (appear in every
variant) versus rotating ones. This is the most directly useful axis for an exam
builder — past papers become coverage templates.

### 3.2 `difficulty` — overall hardness

Derived deterministically from `command × marks` (see `src/enricher.py`). Values
are `"Low" | "Medium" | "High"`.

`marks_by_difficulty`: the marks-weighted difficulty curve — the headline number
when someone asks "how hard is this paper?". A paper with 31% of marks at High
difficulty is materially tougher than one at 9%.

`count_by_difficulty`: the headcount of easy/medium/hard items. Useful for time
planning — many 1-mark Lows feel different from a few 4-mark Highs even at the
same marks split.

By-paper: stacked bar (one bar, three coloured segments) or a 3-slice donut.

By-year: a line chart of `% High` over time surfaces difficulty drift — important
if examiners are gradually raising the bar.

### 3.3 `bloom_level` — cognitive kind

Values: `Remember | Understand | Apply | Analyse | Evaluate | Create`. Derived from
the command word alone (`src/enricher.py:BLOOM_MAP`).

`marks_by_bloom_level`: weighted by marks, so a 6-mark "Evaluate" outweighs a
1-mark "State". Captures whether the paper rewards recall or higher-order thinking.

`count_by_bloom_level`: how many questions of each kind. The distinction matters
because students prepare differently for recall vs application questions.

By-paper: pie or donut, optionally with a target distribution overlay.

By-year: line/area chart of each Bloom level over years — answers "is the
syllabus shifting toward higher-order thinking?".

### 3.4 `cognitive_load` — format-driven mental effort

Values: `Low | Medium | High`. Derived from `layout_type` alone
(`src/enricher.py:LOAD_MAP`). Captures the mental gymnastics the *format* demands,
independent of marks: a 1-mark trace through a ValueTraceMatrix is High load even
though it scores only one mark.

`marks_by_cognitive_load`: where the paper *invests* mental effort by weight.

`count_by_cognitive_load`: how many high-load items the student faces. One
ValueTraceMatrix and one AnnotatedDiagram are exhausting even if they collectively
score 8 marks.

By-paper: a third stacked bar alongside `difficulty` and `bloom_level` — together
they triangulate "hardness" from three angles.

By-year: track whether papers are getting structurally more demanding regardless
of mark totals.

### 3.5 `objective` — Cambridge assessment objective weighting

Values: `AO1 | AO2 | AO3`. Cambridge's spec mandates ~40/40/20.

`marks_by_objective`: the weighted AO mix. **This is the most important compliance
metric on the paper**. Cambridge papers should hit 40/40/20 within tolerance.

`count_by_objective`: number of questions per AO — useful but less authoritative
than the mark-weighted view (because Cambridge measures compliance by marks).

By-paper: pie chart with a 40/40/20 overlay; deviation highlighted in red.

By-year: line chart per AO over years to check compliance trend. **Heads up**:
the current corpus shows 53–84% AO1 across all 7 papers — heavily skewed vs the
target. The webpage should make this gap visible rather than hide it; either the
papers are non-compliant or our Phase 1+2 classifier is biased toward AO1, and
either finding is worth surfacing.

### 3.6 `layout_type` — answer-format variety

Values: one of 10 layouts (`SimpleSingleBlock`, `MatrixGrid`, `ValueTraceMatrix`,
…). See `docs/questions_types.md`.

`marks_by_layout_type`: which formats carry the marks. A paper that gives most
marks to `SimpleSingleBlock` is essentially long-form prose; one that spreads
across `MatrixGrid`, `InlineCloze`, and `ValueTraceMatrix` is structurally varied.

`count_by_layout_type`: how many of each format appear. Drives a "variety score" —
a paper using 7 of the 10 layouts is more varied than one using 3.

By-paper: horizontal bar with layout name + small icon per layout.

By-year: track which formats are gaining or losing favour. Combined with command
distribution, it's a strong signal for what styles to expect on the next paper.

### 3.7 `command` — command word distribution

The raw command word ("State", "Identify", "Explain", "Calculate", …). Note this
*partly* overlaps with `bloom_level` (which is *derived* from this same field),
but at a finer grain — `State`, `Identify`, `Define`, `Name`, `List` all collapse
to `Remember`, but the command word breakdown shows which of those Cambridge
actually uses.

`marks_by_command`: which commands carry the marks. If "Explain" carries 30 marks
and "Evaluate" carries 0, students should drill explanations.

`count_by_command`: how often each command shows up. Surfaces favourites —
Cambridge tends to use "State" much more than "Discuss" in IGCSE.

By-paper: bar chart sorted by frequency, useful as a tooltip-rich glossary view.

By-year: tracks which command words are trending. A rise in "Explain" / "Analyse"
signals a shift toward higher-order assessment that students should prepare for.

### 3.8 `answer_type` — what the student produces

Values come from `q.answers.type`: `"MCQ"`, `"text"`, `"diagram"`, `"pseudocode"`.

This is genuinely distinct from `layout_type`: layout describes the *paper format*
(SimpleSingleBlock, MatrixGrid…); `answer_type` describes *what the student
produces* (tick a box vs write prose vs draw vs write code). A paper can be all
`SimpleSingleBlock` by layout but mix `text` + `pseudocode` by answer type.

`marks_by_answer_type`: which output modes carry the marks. A paper with 12 marks
of `pseudocode` tells a student to drill algorithm writing.

`count_by_answer_type`: how many questions per mode. Frequency drives revision
focus — even 1 MCQ vs 5 MCQs feels materially different.

By-paper: small horizontal bar or pill row beside the layout chart.

By-year: track whether Cambridge is shifting toward more diagram-heavy questions
over time. **Note on corpus scope**: the current 7 papers are all IGCSE 0478
**Paper 1** (theory). Paper 1 doesn't include pseudocode — that belongs to
Paper 2 (programming). So the corpus showing zero `pseudocode` is expected, not
a classifier issue. If Paper 2 PDFs are added later, pseudocode marks will
appear and segmenting the dataset by paper number becomes important.

---

## 4. Audit notes

- **`command` partly overlaps `bloom_level`** — both derive from the command word.
  But `command` gives finer granularity than the 6 Bloom levels. **Keep both.**
- **`marks_by_X` and `count_by_X` look duplicative** but encode different signals
  (weight vs frequency). **Keep both** for every axis.
- **All 14 fields are reachable from a webpage chart** — none are wasted.
- **The AO1 skew (53–84%) is real, surface it.** Either the papers are
  out-of-spec or the classifier is biased; either way the webpage should display
  the gap with the 40/40/20 target overlay rather than hide it.

---

## 5. Proposed additions (not yet implemented)

### 5a. `marks_by_page` / `count_by_page` — nice-to-have

Values come from `q.page` (already present on every question).

Why: visualising paper *density* (which pages carry the most marks) is fun for a
heatmap or a paper-flow ribbon. Not essential — only worth adding if the webpage
wants a layout/density view.

Code change: append one line to `AXES` in `src/statistics.py`:

```python
("page", lambda q: q.get("page")),
```

---

## 6. Year-level aggregation

The webpage builds yearly stats by summing per-paper dicts. Python's `Counter`
makes this one line per axis:

```python
from collections import Counter
import json

papers = [json.load(open(p)) for p in [
    "output/json/0478_s25_qp_11.json",
    "output/json/0478_s25_qp_12.json",
    "output/json/0478_s25_qp_13.json",
]]

year_marks_by_topic = Counter()
for paper in papers:
    year_marks_by_topic.update(paper["statistics"]["marks_by_topic"])
# year_marks_by_topic is now a Counter over all 3 papers' topic marks
```

Repeat for every `marks_by_*` and `count_by_*` field.

### Year-only insights worth surfacing

Some signals only make sense once you've aggregated:

- **Topic ubiquity**: how many of the 3 variants in the session covered each
  topic. A topic that appears in 3/3 is "always tested"; one in 1/3 is rotating.
  Compute at display time — no need to store.
- **Cross-paper variance**: which axes are stable across variants and which jump
  around. A high-variance axis is one to watch for the next paper.
- **Variant spread**: are paper 11, 12, 13 calibrated similarly (intended), or
  is one materially harder? A small "spread" widget on the year page can show
  the High-difficulty % for each variant side by side.

These are presentation concerns — implement them in the webpage layer, not in
the JSON statistics block.
