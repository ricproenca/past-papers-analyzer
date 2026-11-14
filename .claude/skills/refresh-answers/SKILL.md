---
name: refresh-answers
description: Re-extract only the marking-scheme answers (Phase 3) for papers that are already extracted, compare them with the current answers, and promote them. Use when the user asks to redo, fix or refresh the answers/marking points/mark scheme of a paper, after changing the Phase 3 prompt, or when a paper was extracted without its marking scheme.
---

# Refresh the answers of an extracted paper (Phase 3)

`answers.py` keeps all Phase 1+2 data (questions, topics, objectives) and replaces only
`answers` and `objective_marks`, then re-enriches, writes and renders. One call: about
10k input tokens for a Paper 1 marking scheme, 16k for Paper 2, ~4k output.

## 1. Run into staging

```bash
python answers.py output/json/<stem>.json -o output/staging/<stem>.json
# marking scheme is found under input/ by replacing _qp_ with _ms_; otherwise add -ms <path>
```

`<id>: marking scheme splits its marks across objectives {...}` means the scheme states an
AO split (Paper 2's scenario question); it is stored as `objective_marks` and used by the
statistics.

## 2. Compare and audit

```bash
python scripts/compare_extractions.py output/staging/<stem>.json output/json/<stem>.json
python scripts/audit_extractions.py output/staging/<stem>.json
```

- `text` must stay identical (21/21, 32/32 ...): only answers changed.
- `marking points identical N/M`: between two runs 85–95% identical is normal; look at
  the differing questions with a quick `python -c` print of both `answers`.
- Conventions the prompt enforces (check them when a difference appears): one point per
  criterion and never merged alternatives ("MP3 ... OR MP4" = two points); banded marks
  list every expected item at 1 mark with the band in `scoring_rule`; level descriptors
  carry the TOP of their band as `marks`.
- Audit warnings to act on: `no marking points`, `marking points offer N mark(s) for an
  M-mark question` (a criterion was dropped), `MCQ answer has N marking points`.

## 3. Promote

```bash
mv output/staging/<stem>.json output/json/<stem>.json
python render.py output/json/<stem>.json
python generate_stats.py && python generate_topics.py
pytest -q
rm -rf output/staging/<stem>*
```

For every paper at once (`python answers.py output/json`) tell the user the cost first
(15 papers ≈ 15 calls, roughly $3–4) — it overwrites in place, so commit or back up
`output/json` before running it.
