# Past Papers Analyzer

CLI tool that extracts structured question data from Cambridge exam PDFs using Claude, outputting validated JSON mapped to syllabus topics.

## Setup

```bash
uv sync            # or: pip install -e .   (dependencies live in pyproject.toml; uv.lock is committed)
cp .env.example .env   # add ANTHROPIC_API_KEY
```

## Usage

```bash
python extract.py <pdf_path>                                      # output: output/json/<pdf_stem>.json
python extract.py <pdf_path> -ms <ms_pdf_path>                    # include Phase 3 (answers)
python extract.py <pdf_path> -o results/out.json                  # custom output path
python extract.py <pdf_path> -m claude-sonnet-4-6                 # override model

python extract.py <folder>                                        # process all *_qp_*.pdf in folder
python extract.py <folder> --skip-existing                        # ...skipping papers already extracted
python extract.py <folder> --workers 4                            # papers in parallel (first one alone to warm the prompt cache)
python extract.py <folder> --batch                                # Batch API: half price, results arrive asynchronously
python extract.py <pdf_path> --vision                             # also send page images where a diagram is likely (+~1.5k tokens/page)
```

In folder mode, marking schemes are auto-paired by replacing `_qp_` with `_ms_` in the filename (e.g. `0478_m24_qp_12.pdf` → `0478_m24_ms_12.pdf`). If no match is found, Phase 3 is skipped for that paper. Existing JSON files are overwritten unless `--skip-existing` is passed (resumes an interrupted batch). A paper that fails is reported and the batch continues; the command exits non-zero at the end if any failed.

## Architecture

```
extract.py          # CLI entry point (argparse, loads .env)
render.py           # CLI: render existing JSON to HTML; accepts a file or a folder of JSONs
generate_stats.py   # CLI: builds output/html/statistics.html from all paper JSONs
generate_topics.py  # CLI: builds output/html/topic_*.html + topics.html (questions grouped by topic)
backfill_enrichment.py  # re-run enrichment + statistics over existing JSONs
src/
  pdf_reader.py     # pdfplumber: boilerplate-free text, table classification, diagram cue, MS preamble trimming
  postprocess.py    # fills what the model need not write: topic names, canonical commands, TermDefinitionGrid rows,
                    #   subject code/variant from the file name; fixes line-matching layouts
  prompts.py        # builds Phase 1+2 (extraction + topics) and Phase 3 (answers) prompt messages
  claude_client.py  # Anthropic SDK wrapper (prompt caching, retries, truncation handling)
  extractor.py      # orchestrates Phase 1+2 → Phase 3 → enrichment → Phase 4 pipeline
  schema.py         # validates Claude's output
  enricher.py / statistics.py / visuals.py / syllabus.py
  assets.py         # read_asset(): loads CSS/JS from src/static/
  static/           # the pages' CSS/JS as real files: paper.{css,js}, circuit.js, match.js,
                    #   stats.{css,js} (statistics page), topics.{css,js} (topic pages)
  renderer/         # HTML generation (package)
    __init__.py     #   public API: render, render_html, render_question_card, PAPER_CSS/JS
    page.py         #   whole page + writing static assets next to it
    question.py     #   one question card
    layouts.py      #   one renderer per layout_type + dispatch table
    matching.py     #   "draw lines to match" questions
    text.py         #   shared helpers: badges, pipe tables, code stems, prose
tests/              # pytest suite (see Tests)
scripts/
  compare_extractions.py  # diff two extractions of a paper (fields, text, AO, answers); exit 1 on structural change
  audit_extractions.py    # validate + consistency warnings + profile for every paper, no API calls
.claude/skills/     # project skills (see Skills)
docs/
  question_extractor.md  # prompt spec: extraction + topic mapping + answers
  syllabus.md            # syllabus topics (1.x–10.x) used in Phase 1+2
  assesssment.md         # assessment objectives (AO1–AO3) used in Phase 1+2
  command_words.md       # command word definitions used in Phase 1+2
```

Edit CSS/JS in `src/static/`, then re-render (`python render.py output/json`, `python generate_stats.py`, `python generate_topics.py`) — the golden HTML test fails until the committed pages match.

## Pipeline

All phases run sequentially in a single command:

- **Phase 1+2** — Claude reads all PDF pages and returns a JSON object covering both question extraction (Phase 1) and syllabus topic mapping (Phase 2). Top-level fields: `board`, `level`, `subject_code`, `subject_name`, `variant`, `qp`, `ms` (last two injected by the pipeline, not by Claude). Each question has: `id`, `text`, `command`, `objective` (one of AO1/AO2/AO3), `marks`, `visuals`, `page`, `layout_type`, `structure_data`, `topic` (e.g. `"1.2"`), `topic_name` (e.g. `"Text, Sound and Images"`). Claude writes only `topic`; `src/postprocess.py` adds `topic_name` from `src/syllabus.py`, reduces `command` to one canonical word (the prompt's closed list is generated from `src/enricher.py`), and copies `TermDefinitionGrid` headers/rows straight from the PDF table (`structure_data.headers/rows`) instead of asking the model to retype them. Prompt built in `src/prompts.py:build_phase12_messages()`. (These were originally two separate calls, merged to cut token costs by ~25–30%; the log label and docs still call them Phase 1 and Phase 2.)
- **Phase 3** — Claude receives the Phase 1+2 JSON + marking scheme text and returns only an `{id: answer}` map, which `extractor._merge_answers()` attaches to the questions (extraction fields are never re-emitted or altered). Each answer has `type`, `visuals`, `scoring_rule`, and `marking_points` (array of `{text, marks}` objects). Prompt built in `src/prompts.py:build_phase3_messages()`. (Skipped when no `-ms` flag is provided.)
- **Phase 4** — `src/renderer.py` generates an HTML review page from the final JSON. Output goes to `output/html/<stem>.html` (or next to the JSON for custom `-o` paths). Shared CSS/JS assets (`paper.css`, `paper.js`) are written to the same directory. Can also be run standalone: `python render.py <json_path>` (single file) or `python render.py <folder>` (renders all `*.json` files in the folder).

## Tests

```bash
uv sync --extra dev   # or: pip install -e ".[dev]"
pytest
```

Unit tests cover the PDF pre-processing regexes, table classification, enricher, statistics, schema validation, the Claude client (retries, truncation, debug dumps — against a fake client, no API calls), the extractor pipeline (stubbed Claude and PDF reader) and the renderer's parsers. Two data-driven suites run against the committed `output/json/` papers and **fail on drift**:
- `test_committed_html_matches_renderer` — `render_html(json)` must equal the committed `output/html/<stem>.html`. After changing the renderer or its CSS/JS, run `python render.py output/json` and commit the result.
- `test_committed_enrichment_is_up_to_date` / `test_every_extracted_command_is_known` — re-run `python backfill_enrichment.py` after changing the enricher or statistics, and map any new command word.

## Post-extraction Enrichment

After the Claude phases complete, `src/enricher.py` adds three deterministic per-question fields with zero API cost:
- `difficulty` (Low/Medium/High) — derived from command word × marks
- `bloom_level` (Remember/Understand/Apply/Analyse/Evaluate/Create) — derived from command word
- `cognitive_load` (Low/Medium/High) — derived from layout_type

Then `src/statistics.py` rolls those fields up into a top-level `statistics` object on each paper: `marks_by_*` and `count_by_*` for eight axes (`topic`, `difficulty`, `bloom_level`, `cognitive_load`, `objective`, `layout_type`, `command`, `answer_type`) — 16 dict fields in total — plus a top-level `summary` (question count, MCQ count, mean/median/max marks, unique topics). Mark sums per axis equal `total_marks` (modulo questions with missing field values). Useful for downstream analysis and as input for a future exam-builder tool.

The enrichment and statistics both run automatically inside `extractor.extract()` just before the JSON is written. To backfill older JSONs that pre-date these steps:

```bash
python backfill_enrichment.py
```

The script is idempotent — re-running it leaves files unchanged.

## Key Decisions

- **Model**: `claude-sonnet-4-6` by default; override via `--model` flag or `CLAUDE_MODEL` env var.
- **Prompt caching**: `cache_control: {"type": "ephemeral"}` on the Phase 1+2 system prompt (~5k tokens) — the instruction text never changes between papers, so repeated runs benefit from cache hits. The Phase 3 prompt is ~650 tokens, below the minimum cacheable size, so it is deliberately not marked.
- **JSON fence stripping**: Claude occasionally wraps output in markdown fences despite instructions; `src/claude_client.py:_strip_fences()` handles this before `json.loads()` validation.
- **Truncation & debug**: a response with `stop_reason == "max_tokens"` raises `TruncatedOutputError` (no retry — it would truncate again). Raw responses that are truncated, unparseable or fail validation are saved to `output/debug/` (override with `CLAUDE_DEBUG_DIR`); token usage is counted for failed calls too.
- **Retry**: `RateLimitError` and `APIConnectionError` (including timeouts) retry up to 3 times with exponential backoff (2^attempt seconds).
- **Input cleaning**: the question-paper cover is cut to its identity lines (title, code, session, duration, total marks) and its candidate-number tables are dropped. `pdf_reader.clean_page_text()` drops `(cid:N)` glyph noise, the mirrored margin text, barcodes, footers and copyright tails before anything is sent (~70% fewer paper-text tokens on 2024–25 papers). Marking schemes are trimmed to the pages from the first `Question Answer Marks` table onward (`drop_ms_preamble`). Blank pages are not sent.
- **Table classification** (`pdf_reader._classify_table`): besides header rules, a two-column table with blanks and printed text beside a blank or in the right column is a `TermDefinitionGrid` ("type | statement" tables), and a table with values printed beside blanks is a `ValueTraceMatrix` (parity, truth, conversion, test-data tables); only tick grids stay `MatrixGrid`.
- **Prompt text rules** (each fixed a regression measured against the committed extractions): `text` is verbatim but repairs extraction artefacts (displaced `←`, split words); the parent context is exactly the text before the parent's first part label, copied in full, including numbered code listings and reference tables but not words extracted from inside a flowchart/circuit; diagrams are described only in `visuals`; line-matching columns are written as a pipe table.
- **Diagram detection**: `[Likely contains a diagram/drawing]` is set from a text cue (words like diagram, flowchart, draw, circuit) or ≥20 curves on the page — it found 15 of 17 known diagram pages with 1 false positive. Vector-shape counts and `page.images` were tried and do not work on Cambridge papers. `--vision` attaches PNGs of the flagged pages (opt-in: it adds ~1.5k input tokens per page and enriched the diagram description in a test).
- **Temperature**: not sent by default. `CLAUDE_TEMPERATURE=<n>` opts in; a model that rejects the parameter is retried without it. (On one paper, temperature 0 made the model trim context sentences in 3 of 3 runs; the API default kept them in 2 of 2.)
- **Parent context stays repeated**: the model writes each sub-question's full text including its parent stem. A "write each stem once" design saved ~16% of output but the model then silently dropped shared context from some sub-questions (Q2, Q7(f) on the test paper), so it was not adopted.
- **Batch & parallel**: `--batch` submits all Phase 1+2 requests as one Message Batch, then all Phase 3 requests as a second (`extractor.extract_batch`); `--workers N` runs papers in threads (token totals are per thread).

## Docs Reference

- **`docs/question_extractor.md`** — Full prompt spec for the Claude phases (Phase 4 has no prompt; it's pure rendering).
- **`docs/syllabus.md`** — Syllabus topics 1.x–10.x used by Phase 1+2 for `topic` / `topic_name` mapping.
- **`docs/assesssment.md`** — Assessment objectives (AO1: knowledge 40%, AO2: application 40%, AO3: evaluation 20%) used by Phase 1+2 for `objective` mapping.
- **`docs/command_words.md`** — Command word definitions (State, Explain, Evaluate, etc.) used by Phase 1+2 for `command` field guidance.

## Syllabus Topics (Computer Science)

Topics 1.x–10.x as defined in `docs/syllabus.md` (names live in `src/syllabus.py`, shared by the generators and renderer). Paper 1 covers 1–6, Paper 2 covers 7–10:
1. Data Representation — 1.1 Number Systems, 1.2 Text, Sound and Images, 1.3 Data Storage and Compression
2. Data Transmission — 2.1 Types and Methods of Data Transmission, 2.2 Methods of Error Detection, 2.3 Encryption
3. Hardware — 3.1 Computer Architecture, 3.2 Input and Output Devices, 3.3 Data Storage, 3.4 Network Hardware
4. Software — 4.1 Types of Software and Interrupts, 4.2 Types of Programming Language, Translators and IDEs
5. The Internet and its Uses — 5.1 The Internet and the World Wide Web, 5.2 Digital Currency, 5.3 Cyber Security
6. Automated and Emerging Technologies — 6.1 Automated Systems, 6.2 Robotics, 6.3 Artificial Intelligence
7. Algorithm Design and Problem-solving — 7.1 Computational Thinking Skills, 7.2 Algorithms, 7.3 Standard Methods of Solution, 7.4 Validation and Verification, 7.5 Test Data
8. Programming — 8.1 Programming Concepts, 8.2 Arrays, 8.3 File Handling
9. Databases — 9.1 Database Structure, 9.2 SQL
10. Boolean Logic — 10.1 Logic Gates, 10.2 Logic Circuits, 10.3 Truth Tables, 10.4 Logic Expressions

## Skills

Project skills live in `.claude/skills/` (committed; the rest of `.claude/` is ignored):

| Skill | Phase | Use it to |
|---|---|---|
| `extract-paper` | 1–3 | extract a paper into `output/staging/`, compare with the committed JSON, then promote and rebuild |
| `audit-extractions` | 1–3 | validate every paper, read the consistency warnings, fix confirmed problems |
