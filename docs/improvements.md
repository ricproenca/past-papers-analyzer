# Vision for diagram pages

Implemented as an opt-in flag: `python extract.py <pdf> --vision`.

- `pdf_reader` marks pages likely to hold a diagram (text cue or many curves; `page.images` is always empty on Cambridge PDFs).
- `render_pages_to_png_bytes()` renders those pages at 110 dpi; `prompts.build_phase12_messages(pages, page_images)` attaches them as image blocks.
- Measured on `0478_w25_qp_12` (1 diagram page): +~1,550 input tokens, the `visuals` description gained spatial detail, `layout_type` and `structure_data` were unchanged.

- add a calculator to the site

Not done: a dedicated diagram-reading pass that returns node/edge structure for flowcharts and circuits (the renderer's circuit editor and flowchart images still rely on the page-reference heuristic in `src/visuals.py`).

