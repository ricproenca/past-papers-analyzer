# Question Extractor: output specification

This page describes the JSON that `extract.py` writes to `output/json/<qp stem>.json`, and who produces each field. The prompts themselves live in `src/prompts.py`:
- `PHASE12_SYSTEM` covers extraction and topic mapping;
- `PHASE3_SYSTEM` covers the answers.

That file is the source of truth; this page summarises it. Layouts are described in detail in `docs/questions_types.md`.

## Pipeline

| Step | Who | What |
|---|---|---|
| Pre-processing | `src/pdf_reader.py` | Cleans the page text and cuts the cover to its identity lines. Adds `[LAYOUT:…]` / `[TABLE_TYPE:…]` annotations and flags tables and likely diagrams. Trims the marking scheme to its answer tables. |
| Phase 1+2 | model (one call) | Every question and sub-question: wording, command, objective, marks, layout, topic. |
| Post-processing | `src/postprocess.py` | Fills in or corrects everything deterministic (see "Filled in by the pipeline"). |
| Phase 3 | model (one call) | Answers from the marking scheme, returned as an `{id: answer}` map and merged by `extractor._merge_answers`. Skipped without `-ms`. |
| Enrichment | `src/enricher.py`, `src/statistics.py` | Derived per-question fields, `summary` and `statistics`. |
| Visuals | `src/visuals.py` | `visual_image`: a PNG of the page, for questions whose visual cannot be drawn. |
| Phase 4 | `src/renderer/` | The HTML review page; no model call. |

`src/schema.py` validates the output after Phase 1+2 and again after Phase 3.

## Top-level fields

| Field | Source |
|---|---|
| `board`, `level`, `subject_name`, `total_marks` | model |
| `subject_code`, `variant` | file name (`0478_w25_qp_12.pdf` → `"0478"`, `"12"`); overrides what the model wrote |
| `qp`, `ms` | file names; `ms` is null without a marking scheme |
| `summary`, `statistics` | `statistics.attach_statistics` |
| `questions` | see below |

## Question fields

| Field | Source | Notes |
|---|---|---|
| `id` | model | `Q1`, `Q1a`, `Q1a_i` (the paper's `1(a)(i)`). Must match `^Q\d{1,2}[a-z]?(_[ivx]+)?$` and be unique, or validation fails. |
| `text` | model | The printed wording, verbatim, starting with the parent's context: everything printed before the parent's first part label, in full, including code listings and reference tables. Obvious extraction artefacts are repaired. Text the model invents is removed afterwards (`drop_unsourced_text`). Inline gaps are `[blank]`. |
| `command` | model → pipeline | One word from the closed list in `src/enricher.py`, reduced to its canonical form (`"Complete and annotate"` → `"Complete"`). |
| `objective` | model | `AO1`, `AO2` or `AO3`, using the syllabus definitions and weightings in `src/syllabus.py`. |
| `marks` | model | Integer; the marks must add up to `total_marks`. |
| `visuals` | model | A description of any diagram, table or image. Descriptions go here, never in `text`. |
| `page` | model | Page number on the paper. |
| `layout_type` | model (some corrected by the pipeline) | One of 13 layouts (table below). |
| `structure_data` | model / pipeline | Depends on the layout. |
| `topic` | model | A syllabus code `1.1`–`10.4`; must be in `TOPIC_NAMES`. A warning if it is outside the paper's chapters (Paper 1: 1–6, Paper 2: 7–10). |
| `topic_name` | pipeline | From `src/syllabus.py`. |
| `answers` | Phase 3 | See below. |
| `objective_marks` | pipeline | Only when the marking scheme splits a question across objectives ("AO2 (maximum 9 marks) AO3 (maximum 6 marks)"); `statistics` counts the split. |
| `difficulty`, `bloom_level`, `cognitive_load` | enricher | Command × marks, command, and layout respectively. |
| `visual_image` | visuals | Path of the page PNG, when one was rendered. |

## Layouts

| Layout | `structure_data` | Written by |
|---|---|---|
| `SimpleSingleBlock` | `line_count` | model |
| `MultiPartLabeledBlock` | `labels` | model |
| `NumberedMultiList` | `list_count` | model |
| `InlineCloze` | `inline_gap_count` (pipeline, counted from `text`), `has_word_bank` | model / pipeline |
| `MatrixGrid` | `matrix_headers`, `row_count`, `rows` | model |
| `ValueTraceMatrix` | `matrix_headers`, `row_count`, `rows`, optional `row_header`, `row_values` | model |
| `FixedRegisterArray` | `register_size` | model |
| `TermDefinitionGrid` | `headers`, `row_count`, `rows` [{`term`, `definition`}] | pipeline, from the PDF table |
| `LabelledPartResponse` | `labels`, `reference` | model |
| `AnnotatedDiagram` | `diagram_type`, `partial_elements` | model |
| `CodeBlockResponse` | `language`, `line_count` | model |
| `LineMatching` | `left_header`, `right_header`, `left_items`, `right_items` | pipeline, from the pipe table in `text` |
| `WorkingAnswer` | `working_space`, `answer_labels`, `unit` | model |

## Filled in by the pipeline

The model is never asked to write these:
- `topic_name`;
- the canonical `command`;
- `subject_code` and `variant`;
- `TermDefinitionGrid` contents;
- `InlineCloze` gap counts;
- `LineMatching` columns, including relabelling a matching question typed as MatrixGrid or AnnotatedDiagram;
- `objective_marks`;
- the derived fields.

`python backfill_enrichment.py` re-applies these steps to the committed JSONs without API calls. It refreshes `TermDefinitionGrid` contents only when the source PDF is under `input/`.

## Answers (Phase 3)

The model receives only `id`, `marks`, `layout_type` and `text` for each question, plus the marking scheme from its first answer table onward.

```json
"answers": {
  "type": "text" | "diagram" | "pseudocode" | "MCQ",
  "visuals": [],
  "scoring_rule": "Any three from:" | null,
  "marking_points": [{"text": "…", "marks": 1}]
}
```

### Conventions

- **Id mapping:** `1(a)(i)` ↔ `Q1a_i`.
- **Marking points:** one per criterion, verbatim and in the scheme's order. Alternatives are never merged: `MP3 … OR MP4 …` gives two points.
- **Named parts** (e.g. Input / Output): each point is prefixed with its label (`"Input: Microphone"`).
- **MCQ:** one point, the correct option letter, worth 1 mark.
- **Banded marks:** the band wording goes in `scoring_rule`; each expected item is its own 1-mark point.
- **Levels of response:** one point per band descriptor, with `marks` set to the top of that band.
- **`scoring_rule`:** copied verbatim. With "Any N from", the points offer more marks than the question; schema warnings flag the opposite case (fewer).
- **Missing questions:** a question absent from the marking scheme keeps its id with `marking_points: []`.
