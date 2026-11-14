---
name: extract-paper
description: Extract or re-extract a Cambridge 0478 past paper (question paper + marking scheme) with Claude, check the result against the previous extraction, and only then replace the committed JSON and HTML. Use when the user asks to extract, re-extract, refresh, add or update a past paper (e.g. "extract w25 12", "add the new March paper", "re-run 0478_s24_qp_11").
---

# Extract a past paper safely

Extraction costs real API money and can silently regress, so never write straight
over `output/json/`. Extract into `output/staging/` (gitignored), compare, then promote.

## 1. Find the files

Papers live under `input/` (gitignored, nested by year). The marking scheme has the
same name with `_ms_` instead of `_qp_`:

```bash
find input -name "0478_w25_qp_12.pdf" -o -name "0478_w25_ms_12.pdf"
```

If the marking scheme is missing, extract anyway (no answers) and say so.

## 2. Tell the user the cost before a large run

Per paper on the default model: Phase 1+2 ≈ 2.5–4k input tokens + ~5.8k cached system
prompt, 6–9k output tokens; Phase 3 ≈ 11k input + 4k output. Roughly $0.20–0.30 per
paper. For many papers prefer `--batch` (half price, asynchronous) or `--workers 4`.
One or two papers: just run them.

## 3. Extract into staging

```bash
python extract.py <qp.pdf> -ms <ms.pdf> -o output/staging/<stem>.json
# add --vision for papers with diagrams you care about (+~1.5k input tokens per diagram page)
```

Read the run's output: `[!]` lines are consistency warnings, `Warning:` lines are
pairing/answer problems. A validation failure saves the raw response under
`output/debug/` — report its path; never re-run blindly.

### A whole folder (a new session, or re-extracting everything)

Folder mode has no staging: `-o` is single-file only, so it writes straight to
`output/json/` and overwrites. Git is the safety net — start from a clean tree
(`git status --short output/json` prints nothing) so every change is a reviewable diff.

```bash
python extract.py input/0478/<folder> --batch            # half price, asynchronous
python extract.py input/0478/<folder> --workers 4        # faster, full price
python extract.py input/0478/<folder> --skip-existing    # only papers with no JSON yet (new session, or resume)
```

Marking schemes are paired by file name. The command exits non-zero and lists the
papers that failed; the others are still written. Compare each overwritten paper with
its committed version, then audit and rebuild (steps 5–6, without the `mv`):

```bash
git show HEAD:output/json/<stem>.json > output/staging/<stem>.old.json
python scripts/compare_extractions.py output/json/<stem>.json output/staging/<stem>.old.json
git checkout -- output/json/<stem>.json      # to reject one paper's new extraction
```

## 4. Compare with the committed extraction (if one exists)

```bash
python scripts/compare_extractions.py output/staging/<stem>.json output/json/<stem>.json
```

- Exit code 1 = different question ids or marks: stop and show the user.
- Expected differences, not regressions: MCQ options, truth tables and other grids
  now live only in `structure_data` (not repeated in `text`); sub-questions may gain
  parent context the old extraction missed.
- Real regressions: a sentence of parent context missing, a layout change that
  renders worse, a topic or objective change you cannot justify from the paper.
  For a precise view use `python -c` to print the two `text` fields side by side.

## 5. Audit

```bash
python scripts/audit_extractions.py output/staging/<stem>.json
```

## 6. Promote and rebuild

Only when 4 and 5 look right (or the paper is new):

```bash
mv output/staging/<stem>.json output/json/<stem>.json
python render.py output/json/<stem>.json
python generate_stats.py && python generate_topics.py
pytest -q
```

The golden HTML tests must pass after rendering. Remove the rest of
`output/staging/<stem>*` when done. Summarise: questions, marks, warnings, notable
differences, tokens used — and ask before committing.
