---
name: add-layout-type
description: Add a new question layout_type, or change the structure_data or rendering of an existing one, across every place a layout is defined (prompt, schema, enricher, PDF pre-processing, renderer, CSS, docs, tests). Use when the "New question type detected" warning appears, when a kind of question has no fitting layout, or when the user asks to add, rename, split or rework a layout such as MatrixGrid or TermDefinitionGrid.
---

# Add or change a layout type

A layout is defined in seven places. Missing one gives a silent fallback
(`SimpleSingleBlock` rendering, `Medium` cognitive load) rather than an error, so work
through the list in order.

First check that an existing layout does not already fit: the 11 current ones are the
keys of `_LAYOUT_RENDERERS` in `src/renderer/layouts.py`. A new layout costs prompt
tokens on every paper; a new `structure_data` field on an existing one is cheaper.

## Checklist

1. **Schema** — `src/schema.py`: add the name to `_VALID_LAYOUT_TYPES`; add a
   consistency warning if `structure_data` can disagree with `text` or `marks`
   (see the `InlineCloze` gap-count and `TermDefinitionGrid` blank-count checks).
2. **Enricher** — `src/enricher.py`: add it to `LOAD_MAP` (Low/Medium/High).
   `tests/test_enricher.py` fails if a valid layout is missing here.
3. **PDF pre-processing** — `src/pdf_reader.py`, only if the layout can be detected
   from the page: a `[LAYOUT:Name key=value]` annotation (answer-space patterns,
   `_annotate_cloze_blocks`) or a `[TABLE_TYPE:Name ...]` from `_classify_table`.
   To see what pdfplumber gives for a table:
   `python scripts/diagnose_table.py <pdf> --page N`.
   Rules in `_classify_table` are ordered; add a test per rule in `tests/test_pdf_reader.py`.
4. **Prompt** — `src/prompts.py`, section `LAYOUT TYPES` of `PHASE12_SYSTEM`: the
   description, its "PDF signals" line, the `structure_data` fields, and the count in
   "exactly one of the 11 types". If rows can come straight from the PDF table, fill
   them in `src/postprocess.py` (as `fill_term_def_grids` does) instead of asking the
   model to retype them. A prompt change must be measured: use the `tune-prompt` skill.
5. **Renderer** — `src/renderer/layouts.py`: a `_render_<name>(q, structure_data)`
   function and its entry in `_LAYOUT_RENDERERS`. Input names and ids must be built
   from `q["id"]` (topic pages pass a paper-qualified id). In
   `src/renderer/question.py`, strip from `text` whatever the renderer now draws, so
   it is not shown twice (see the `MatrixGrid` / `MultiPartLabeledBlock` branches).
6. **CSS/JS** — `src/static/paper.css`; a widget script goes in `src/static/`, in
   `ASSET_FILES` (`src/renderer/page.py`) and in `interactive_script_tags()` so it
   loads only on pages that use it.
7. **Docs** — `docs/questions_types.md` (currently lists ten; `CodeBlockResponse` is
   missing) and the layout list in `docs/question_extractor.md`.

## Verify

```bash
pytest -q        # test_renderer renders every valid layout; test_enricher checks LOAD_MAP
```

Add a renderer test with a minimal question dict in `tests/test_renderer.py`. If
committed JSONs should use the new layout, change them deliberately (re-extract with
`extract-paper`, or edit the affected questions and say so), then run the
`rebuild-site` skill: the golden HTML test fails until `output/html` is regenerated.
