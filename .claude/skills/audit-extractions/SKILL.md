---
name: audit-extractions
description: Audit the extracted past-paper JSONs for quality problems without calling the API — schema validity, consistency warnings, AO balance, missing marking points — and fix confirmed problems in the JSON. Use when the user asks to check, audit, review or sanity-check the extracted papers or a specific paper's data quality.
---

# Audit extracted papers

```bash
python scripts/audit_extractions.py                      # every paper in output/json
python scripts/audit_extractions.py output/json/X.json   # one paper
```

Each paper prints a profile line (questions, marks/total, AO split by marks, top
layouts) plus warnings. Exit code 1 means a paper fails schema validation.

## Reading the warnings

| Warning | Usual cause | How to confirm |
|---|---|---|
| `inline_gap_count=N but text has M [blank]` | model miscounted gaps | count the dotted gaps on that PDF page |
| `a N-mark question has a one-line answer space` | `line_count` guessed low | look at the answer lines on the page |
| `N blank cell(s) but M mark(s)` (TermDefinitionGrid) | table paired with the wrong question, or a merged cell | compare `structure_data.rows` with the PDF table |
| `Unmapped command word` | new command word | add it to `COMMAND_TIER`/`BLOOM_MAP` in `src/enricher.py` (the prompt list is generated from it) |
| `no marking points for [...]` | Phase 3 could not match the id | check the marking scheme entry for that question |

Read the PDF page before changing anything:

```bash
python -c "from src import pdf_reader as pr; p = pr.extract_pages('input/.../X.pdf'); print(p[N-1]['text'])"
```

## Fixing

- Only fix a field when the PDF (or marking scheme) confirms it. Edit the JSON
  directly, keep the key order, then run `python backfill_enrichment.py` (recomputes
  difficulty/bloom/statistics), `python render.py output/json/X.json`,
  `python generate_stats.py && python generate_topics.py`, and `pytest -q`.
- If a problem repeats across papers, fix the cause instead (prompt in
  `src/prompts.py`, deterministic step in `src/postprocess.py`, or a check in
  `src/schema.py`) and say which papers need re-extraction (`extract-paper` skill).
- AO balance: Paper 1 is AO1/AO2 heavy; a paper with 0 AO3 marks is common in the
  current data, so report it rather than "fixing" it without evidence.

Summarise per paper: valid or not, warnings found, what you fixed and why.
