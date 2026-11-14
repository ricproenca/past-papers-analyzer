---
name: tune-prompt
description: Change an extraction or answers prompt rule (src/prompts.py, the syllabus/AO text in src/syllabus.py, the command list in src/enricher.py) and measure the effect with real API runs against the committed extractions before keeping it. Use when the user asks to change, tighten, shorten or fix the prompt, says the model keeps doing something wrong across papers, or wants to cut tokens in a Claude call.
---

# Change a prompt rule and measure it

A prompt edit that reads well can still regress: the "write each stem once" design and
temperature 0 both looked like wins and both made the model drop context sentences.
Nothing is kept on the strength of how the rule reads; it is kept on a comparison.

## 1. Decide whether it belongs in the prompt at all

Prefer code when the fact is deterministic. The model does not write `topic_name`,
`subject_code`, `variant`, canonical commands or `TermDefinitionGrid` rows — 
`src/postprocess.py` fills them. A new rule is for something only the model can judge.

Where the text lives:
- `src/prompts.py` — `PHASE12_SYSTEM` (extraction + topics) and `PHASE3_SYSTEM` (answers).
- `src/syllabus.py` — the TOPICS and OBJECTIVES blocks (`topics_prompt_block`,
  `objectives_prompt_block`); wording must stay faithful to `input/0478/0478 Syllabus.pdf`.
- `src/enricher.py` — the closed command list.

## 2. Say what it will cost, then run the two reference papers

One Paper 1 and one Paper 2, both with committed extractions:

```bash
find input -name "0478_w25_qp_12.pdf" -o -name "0478_w25_ms_12.pdf" \
        -o -name "0478_m25_qp_22.pdf" -o -name "0478_m25_ms_22.pdf"
python extract.py <qp.pdf> -ms <ms.pdf> -o output/staging/<stem>.json
```

Roughly $0.20–0.30 per paper per run; a measured change usually takes 2–3 runs of each.
For a Phase 3-only change use `python answers.py output/json/<stem>.json -o output/staging/<stem>.json`
(one answers call, no extraction).

## 3. Compare

```bash
python scripts/compare_extractions.py output/staging/<stem>.json output/json/<stem>.json --show 10
python scripts/audit_extractions.py output/staging/<stem>.json
```

- Exit code 1 (ids or marks differ) is a structural regression: stop.
- A difference seen once may be run-to-run variation. Run the same paper again before
  blaming or crediting the rule; report "n of m runs".
- Read the run's `[total]` line for input/output/cached tokens and compare with the
  run before the change. A rule that adds 200 prompt tokens costs them on every paper.

## 4. Keep or revert

Keep only if the target behaviour changed and nothing else got worse. A regression is
fixed with a narrower rule or with post-processing, not by accepting it. If the change
is rejected, revert it and still record why (step 5) so it is not tried again.

Constraints:
- `PHASE12_SYSTEM` carries `cache_control`; `PHASE3_SYSTEM` is below the cacheable
  minimum (1,024 tokens) and is deliberately unmarked. If it grows past that, mark it.
- Placeholders `<<COMMAND_LIST>>`, `<<TOPICS>>`, `<<OBJECTIVES>>` are filled from code;
  do not paste their content into the prompt text.
- The staging JSONs are evidence, not output: do not promote them unless the user asks
  for a re-extraction (that is the `extract-paper` skill).

## 5. Record

- `pytest -q` (`tests/test_prompts.py` pins parts of the prompt).
- Add or amend the matching bullet in CLAUDE.md "Key Decisions" with the measurement
  (papers, runs, numbers), and update `docs/question_extractor.md` if the spec changed.
- Delete `output/staging/<stem>*`. Summarise: rule, runs, differences, token change,
  API cost — and ask before committing.
