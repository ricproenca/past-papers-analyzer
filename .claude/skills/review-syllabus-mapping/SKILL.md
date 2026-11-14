---
name: review-syllabus-mapping
description: Review or correct how past-paper questions are mapped to 0478 syllabus topics and assessment objectives (AO1/AO2/AO3), check topic coverage across papers, and keep the syllabus data in src/syllabus.py faithful to the official syllabus. Use when the user asks which topics a paper covers, why a question has a given topic or AO, whether AO splits look right, which topics are never examined, or to update the syllabus/topic definitions.
---

# Review the syllabus mapping (Phase 2)

Topic and objective are assigned by the Phase 1+2 call; the prompt's TOPICS and
OBJECTIVES blocks are generated from `src/syllabus.py`, which is condensed from the
official syllabus at `input/0478/0478 Syllabus.pdf` (2023–2025). Treat the PDF as the
authority — not memory, not `docs/syllabus.md`.

## See the mapping

```bash
python scripts/syllabus_report.py                         # marks per topic for Paper 1 / Paper 2, never-examined topics, AO split per paper
python scripts/syllabus_report.py output/json/<stem>.json  # one paper, question by question
```

AO splits are compared with the syllabus weighting (Paper 1: 60/20/20, Paper 2:
20/60/20 for AO1/AO2/AO3 by marks). Individual papers vary; a paper with AO3 near 0%
is the known failure mode of older extractions.

## Check a question

1. Read its text (`python -c "import json; ..."` or the report line).
2. Compare with `TOPIC_CONTENT[...]` in `src/syllabus.py`; when unsure, open the
   syllabus page: `python -c "import pdfplumber; print(pdfplumber.open('input/0478/0478 Syllabus.pdf').pages[N-1].extract_text())"`
   (subject content is on pages 11–31; AO definitions and weightings on page 10).
3. AO: use `AO_DEFINITIONS` — AO1 general knowledge, AO2 applied to the given
   context/data/code (incl. writing algorithms), AO3 judgement (suitability, best
   choice, justify, improve/fix a stated problem, evaluate).
4. Marking schemes state an AO split only for Paper 2's final scenario question
   ("AO2 (maximum 9 marks), AO3 (maximum 6 marks)"); that is stored as `objective_marks`.

## Fix

- One question wrong in one paper: edit `topic`/`objective` in `output/json/<stem>.json`
  (`topic_name` must match `TOPIC_NAMES`), then `python backfill_enrichment.py`,
  `python render.py output/json/<stem>.json`, `python generate_stats.py && python generate_topics.py`, `pytest -q`.
- Systematic error (same confusion across papers): fix the cause in `src/syllabus.py`
  (topic content, AO guidance) or the routing rule in `src/prompts.py`, quoting the
  syllabus page that justifies it; add a test in `tests/test_syllabus.py`; list the
  papers that need re-extraction (`extract-paper` skill) — do not hand-edit dozens of
  questions.
- Topic codes 7.1–7.5, 9.1–9.2 and 10.1–10.4 are this project's subdivision of
  chapters the syllabus leaves undivided; keep codes stable — renaming them breaks
  every JSON and the generated pages.
