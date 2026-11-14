---
name: fix-question
description: Diagnose and fix one question (or a few) that is wrong in the extracted data or looks wrong on its HTML page — missing or duplicated text, a broken table or grid, wrong layout, wrong marks, a missing diagram, bad marking points. Use when the user names a question such as "Q5b on s24 11 looks wrong", pastes a broken card, or reports a rendering glitch on a paper or topic page.
---

# Fix a question at the level where it went wrong

The HTML is generated, so never edit `output/html/`. Find which of four stages
produced the fault and fix that stage; a fix one stage too late hides the same fault
in other papers.

## 1. Look at all three versions

```bash
# the stored question
python -c "import json,sys; d=json.load(open('output/json/<stem>.json')); print(json.dumps(next(q for q in d['questions'] if q['id']=='Q5b'), indent=2, ensure_ascii=False))"

# what the model was sent for that page (cleaned text + annotations)
python -c "from src import pdf_reader; p=pdf_reader.extract_pages('<qp.pdf>'); print(next(x for x in p if x['page']==7)['text'])"

# raw pdfplumber tables on that page
python scripts/diagnose_table.py <qp.pdf> --page 7
```

Find the PDF with `find input -name "<stem>.pdf"`; the page is the question's `page`
field. Then look at the card itself in `output/html/<stem>.html` (`id="Q5b"`).

## 2. Decide the stage

| Symptom | Stage | Fix in |
|---|---|---|
| Text sent to the model is already wrong: missing lines, junk, wrong `[LAYOUT:...]` / `[TABLE_TYPE:...]` annotation | PDF pre-processing | `src/pdf_reader.py` (+ `tests/test_pdf_reader.py`) |
| Input was right, JSON is wrong: dropped context, wrong layout, topic, objective, marks | Model | one paper → correct the JSON; several papers → a prompt rule via `tune-prompt` |
| Model output was fine but a filled-in field is wrong (`topic_name`, command, grid rows, `objective_marks`, a sentence removed) | Post-processing | `src/postprocess.py` (+ `tests/test_postprocess.py`) |
| JSON is right, page is wrong: duplicate table, missing input, bad escaping, widget inert | Renderer | `src/renderer/` or `src/static/` (+ `tests/test_renderer.py`) |
| Marking points wrong, missing or too few marks | Answers | `refresh-answers` skill |
| Topic or AO looks wrong | Mapping | `review-syllabus-mapping` skill |

To see whether a fault is one paper or many, search all papers before choosing:

```bash
python scripts/audit_extractions.py            # every paper, no API calls
grep -l '"layout_type": "MatrixGrid"' output/json/*.json
```

## 3. Fix

- **Code fix**: write the failing test first from the real example, then the fix.
  `text`-stripping rules in `src/renderer/question.py` name the paper and question
  they were written for; do the same.
- **JSON fix** (a one-off model error): edit only the wrong fields in
  `output/json/<stem>.json`, keep `text` verbatim to the paper, then
  `python backfill_enrichment.py` so derived fields and statistics follow. Say in the
  summary that the JSON was hand-corrected and which fields.
- A missing diagram image: `visuals.attach_visual_images` runs in `finalize`; check
  that the page was flagged (`has_diagram`) before touching the renderer.

## 4. Rebuild and check

Run the `rebuild-site` skill (render, stats, topics, `scripts/check_site.py`,
`pytest -q`). `git diff --stat output/html` should show only pages containing the
question — its paper page and its topic page. Anything else changing means the fix is
wider than intended: look before committing.
