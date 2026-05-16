# Past Papers Analyzer

CLI tool that extracts structured question data from Cambridge exam PDFs using Claude, outputting validated JSON mapped to syllabus topics.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY
```

## Usage

```bash
python extract.py <pdf_path>                                      # output: output/json/<pdf_stem>.json
python extract.py <pdf_path> -ms <ms_pdf_path>                    # include Phase 2 (answers)
python extract.py <pdf_path> -o results/out.json                  # custom output path
python extract.py <pdf_path> -m claude-sonnet-4-6                 # override model
```

## Architecture

```
extract.py          # CLI entry point (argparse, loads .env)
render.py           # CLI: render existing JSON to HTML (thin wrapper around src/renderer.py)
src/
  pdf_reader.py     # pdfplumber: text + table/image detection per page
  prompts.py        # builds Phase 1 (extraction + topics) and Phase 2 (answers) prompt messages
  claude_client.py  # Anthropic SDK wrapper (prompt caching, retries)
  extractor.py      # orchestrates Phase 1 → Phase 2 → Phase 3 pipeline
  renderer.py       # HTML page generator (render_html, render); writes paper.css / paper.js
docs/
  question_extractor.md  # prompt spec: extraction + topic mapping + answers
  syllabus.md            # syllabus topics (1.x–6.x) used in Phase 1
  assesssment.md         # assessment objectives (AO1–AO3) used in Phase 1
  command_words.md       # command word definitions used in Phase 1
```

## Three-Phase Pipeline

All phases run sequentially in a single command:

- **Phase 1** — Claude reads all PDF pages and returns a JSON object covering both question extraction and syllabus topic mapping. Top-level fields: `board`, `level`, `subject_code`, `subject_name`, `variant`, `qp`, `ms` (last two injected by the pipeline, not by Claude). Each question has: `id`, `text`, `command`, `objective` (one of AO1/AO2/AO3), `marks`, `visuals`, `page`, `layout_type`, `structure_data`, `topic` (e.g. `"1.2"`), `topic_name` (e.g. `"Text, Sound and Images"`). Prompt built in `src/prompts.py:build_phase12_messages()`. (Historically this was two separate calls — Phase 1 for extraction and Phase 2 for topic mapping — merged to reduce token costs by ~25–30%.)
- **Phase 2** — Claude receives the Phase 1 JSON + marking scheme text and enriches each question with answers. Adds `answers` with `type`, `visuals`, `scoring_rule`, and `marking_points` (array of `{text, marks}` objects). Prompt built in `src/prompts.py:build_phase3_messages()`. (Skipped when no `-ms` flag is provided.)
- **Phase 3** — `src/renderer.py` generates an HTML review page from the final JSON. Output goes to `output/html/<stem>.html` (or next to the JSON for custom `-o` paths). Shared CSS/JS assets (`paper.css`, `paper.js`) are written to the same directory. Can also be run standalone: `python render.py <json_path>`.

## Key Decisions

- **Model**: `claude-sonnet-4-6` by default; override via `--model` flag or `CLAUDE_MODEL` env var.
- **Prompt caching**: `cache_control: {"type": "ephemeral"}` on both system prompt blocks — the instruction text never changes between papers, so repeated runs benefit from cache hits.
- **JSON fence stripping**: Claude occasionally wraps output in markdown fences despite instructions; `src/claude_client.py:_strip_fences()` handles this before `json.loads()` validation.
- **Retry**: `RateLimitError` and `APIConnectionError` (including timeouts) retry up to 3 times with exponential backoff (2^attempt seconds).
- **Visual detection**: `src/pdf_reader.py` flags pages with tables or images via `[Contains table(s)]` / `[Contains image(s)/diagram(s)]` in the prompt — Claude uses these hints when populating the `visuals` field. Full image extraction via vision is a future enhancement.

## Docs Reference

- **`docs/question_extractor.md`** — Full prompt spec for the Claude phases (Phase 3 has no prompt; it's pure rendering).
- **`docs/syllabus.md`** — Syllabus topics 1.x–6.x used by Phase 1 for `topic` / `topic_name` mapping.
- **`docs/assesssment.md`** — Assessment objectives (AO1: knowledge 40%, AO2: application 40%, AO3: evaluation 20%) used by Phase 1 for `objective` mapping.
- **`docs/command_words.md`** — Command word definitions (State, Explain, Evaluate, etc.) used by Phase 1 for `command` field guidance.

## Syllabus Topics (Computer Science)

Topics 1.x–6.x as defined in `docs/syllabus.md`:
1. Data Representation — 1.1 Number Systems, 1.2 Text, Sound and Images, 1.3 Data Storage and Compression
2. Data Transmission — 2.1 Types and Methods of Data Transmission, 2.2 Methods of Error Detection, 2.3 Encryption
3. Hardware — 3.1 Computer Architecture, 3.2 Input and Output Devices, 3.3 Data Storage, 3.4 Network Hardware
4. Software — 4.1 Types of Software and Interrupts, 4.2 Types of Programming Language, Translators and IDEs
5. The Internet and its Uses — 5.1 The Internet and the World Wide Web, 5.2 Digital Currency, 5.3 Cyber Security
6. Automated and Emerging Technologies — 6.1 Automated Systems, 6.2 Robotics, 6.3 Artificial Intelligence
