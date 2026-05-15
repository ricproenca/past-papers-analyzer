# Past Papers Analyzer

CLI tool that extracts structured question data from Cambridge exam PDFs using Claude AI, outputting validated JSON enriched with syllabus topics and marking scheme answers.

## What it does

Runs a four-phase pipeline against a Cambridge exam paper (and optionally its marking scheme):

1. **Phase 1** — Extracts every question and sub-question with metadata (`id`, `text`, `command word`, `objective`, `marks`, `visuals`, `page`)
2. **Phase 2** — Maps each question to its syllabus topic (e.g. `1.2 Text, Sound and Images`)
3. **Phase 3** — Adds structured marking scheme answers as a list of `{text, marks}` criteria *(requires marking scheme PDF)*
4. **Phase 4** — Renders an HTML review page from the final JSON (`output/html/<stem>.html`)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
```

## Usage

```bash
# Phase 1 + 2 + 4 (question extraction, topic mapping, HTML render)
python extract.py input/0478_m25_qp_12.pdf
# → output/json/0478_m25_qp_12.json
# → output/html/0478_m25_qp_12.html

# Phase 1 + 2 + 3 + 4 (includes marking scheme answers)
python extract.py input/0478_m25_qp_12.pdf -ms input/0478_m25_ms_12.pdf

# Re-render HTML from an existing JSON (Phase 4 only)
python render.py output/json/0478_m25_qp_12.json

# Custom output path
python extract.py input/0478_m25_qp_12.pdf -ms input/0478_m25_ms_12.pdf -o results/out.json

# Override Claude model
python extract.py input/0478_m25_qp_12.pdf -m claude-opus-4-7
```

## Output format

```json
{
  "board": "CIE",
  "level": "IGCSE",
  "subject_code": "0478",
  "subject_name": "Computer Science",
  "variant": "12",
  "qp": "0478_m25_qp_12.pdf",
  "ms": "0478_m25_ms_12.pdf",
  "questions": [
    {
      "id": "Q1a",
      "text": "State what is meant by the term bit.",
      "command": "State",
      "objective": "AO1",
      "marks": 1,
      "visuals": [],
      "page": 2,
      "topic": "1.3",
      "topic_name": "Data Storage and Compression",
      "answers": {
        "type": "text",
        "visuals": [],
        "scoring_rule": null,
        "marking_points": [
          { "text": "A single binary digit / 0 or 1", "marks": 1 }
        ]
      }
    }
  ]
}
```

## Project structure

```
extract.py          # CLI entry point
render.py           # CLI: re-render an existing JSON to HTML (Phase 4 only)
src/
  pdf_reader.py     # pdfplumber: extracts text and tables per page
  prompts.py        # builds prompt messages for each phase
  claude_client.py  # Anthropic SDK wrapper (caching, retries, token reporting)
  extractor.py      # orchestrates Phase 1 → Phase 2 → Phase 3 → Phase 4
  renderer.py       # HTML page generator; writes paper.css / paper.js alongside
  schema.py         # validates JSON output structure after each phase
docs/
  question_extractor.md  # prompt spec for all three phases
  syllabus.md            # syllabus topics 1.x–6.x
  assesssment.md         # assessment objectives AO1–AO3
  command_words.md       # command word definitions
input/                   # place exam PDFs here
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Model to use |
| `CLAUDE_MAX_TOKENS` | `16384` | Max output tokens per API call |
