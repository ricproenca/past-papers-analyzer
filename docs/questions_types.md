# Question Layout Types

Every question has exactly one `layout_type`: the shape of its **answer space**, which decides how the review page draws the input. `structure_data` carries the layout's details. There are 13 layouts. The prompt text that defines them for the model is in `src/prompts.py` (section `LAYOUT TYPES`), the valid names in `src/schema.py` (`_VALID_LAYOUT_TYPES`), and the renderers in `src/renderer/layouts.py` (`_LAYOUT_RENDERERS`). `tests/test_prompts.py` fails if this page, the extractor spec or the prompt lists a different set.

**Annotations.** The pre-processor (`src/pdf_reader.py`) marks answer spaces in the page text before the model reads it:
- `[LAYOUT:…]` for dotted-line answer spaces;
- `[TABLE_TYPE:…]` for tables, classified by `_classify_table`.

The model treats these as its primary signal. Fields marked *pipeline* are filled in code (`src/postprocess.py`); the model leaves them out.

Counts are for the 15 committed papers (477 questions: 14 Paper 1, 1 Paper 2). By layout: SimpleSingleBlock 262, NumberedMultiList 68, WorkingAnswer 42, MatrixGrid 37, MultiPartLabeledBlock 17, InlineCloze 14, TermDefinitionGrid 14, AnnotatedDiagram 13, ValueTraceMatrix 4, CodeBlockResponse 3, and 1 each of FixedRegisterArray, LineMatching and LabelledPartResponse.

---

### 1. SimpleSingleBlock
- **Answer space:** one open answer area of one or more lines. This is the default when nothing else fits.
- **Signals:** `[LAYOUT:SimpleSingleBlock line_count=N]`, or a single trailing answer line.
- **`structure_data`:** `{ "line_count": N }`.
- **Seen:** 262 questions. Most are 1–4-mark State/Give/Explain answers.

### 2. MultiPartLabeledBlock
- **Answer space:** separate answer slots, each with a printed label.
- **Signals:** `[LAYOUT:MultiPartLabeledBlock labels=Benefit,Drawback]`, or repeated label lines without dots (e.g. "Error 1 line number" / "Correction").
- **`structure_data`:** `{ "labels": ["Benefit", "Drawback"] }`, in printed order.
- **Rendering:** a label containing "number", "line number", "code" or "mark" gets a one-line input; other labels get a textarea.

### 3. NumberedMultiList
- **Answer space:** a fixed number of numbered lines (1, 2, 3 …).
- **Signals:** `[LAYOUT:NumberedMultiList count=N]`.
- **`structure_data`:** `{ "list_count": N }`.

### 4. InlineCloze
- **Answer space:** gaps inside prose (fill in the blanks), sometimes with a word bank.
- **Signals:** `[LAYOUT:InlineCloze gap_count=N]`, added once per passage. The gaps appear in `text` as `[blank]`.
- **`structure_data`:** `{ "inline_gap_count": N, "has_word_bank": true | false }`.
- **Gaps:** the pre-processor writes each gap as `[blank]`, including gaps printed with the ellipsis character and gaps at the end of a line; one long gap printed as two dotted runs is one gap. `postprocess.normalise_cloze` then sets `inline_gap_count` from the text (*pipeline*).

### 5. MatrixGrid
- **Answer space:** a table answered with ticks. There are two patterns:
  1. **Comparison grid.** Option columns, one tick per row: `{ "matrix_headers": ["Statement", "True", "False"], "row_count": N, "rows": ["statement", …] }`.
  2. **Single-select MCQ.** "Tick (✓) one box", with options A/B/C/… listed below: `{ "matrix_headers": ["Option", "Tick"], "row_count": N, "rows": ["A <statement>", "B <statement>", …] }`.
- **Circle questions:** "Circle three …" with a printed list of options and no letters is the MCQ pattern too, with headers `["Option", "Select"]` and one row per option.
- **Rules for the MCQ pattern:**
  - It has exactly two headers, and the right one is Tick, Select, Choose or Mark.
  - Option letters never go in the headers.
  - The headers are not printed on the paper, so they are never written into `text`.
- **Rendering:** the number of ticks ("Tick two boxes") is read from the question text. Tick-one uses radio buttons; tick-N uses checkboxes.

### 6. ValueTraceMatrix
- **Answer space:** a table in which students write values. It covers:
  - trace tables, where every data cell is blank;
  - data tables with some cells printed (parity blocks, truth tables, conversion and test-data tables).
- **Signals:** `[TABLE_TYPE:ValueTraceMatrix]`. The headers are registers, variable names or bit positions.
- **`structure_data`:** `{ "matrix_headers": [...], "row_count": N, "rows": [...], "row_header": "...", "row_values": [...] }`
  - `matrix_headers`: the data columns only.
  - `rows`: the left-most label of each row.
  - `row_header` (optional): the printed heading of the row-label column. The default is "Step".
  - `row_values` (optional): parallel to `rows`. `null` means the whole row is blank; otherwise one string per column, with `""` for a blank cell. Omit it for a pure trace table.

### 7. FixedRegisterArray
- **Answer space:** a row of 8 or 16 single-bit boxes.
- **Signals:** `[TABLE_TYPE:FixedRegisterArray register_size=N]`.
- **`structure_data`:** `{ "register_size": 8 | 16 }`.

### 8. TermDefinitionGrid
- **Answer space:** a two-column table (term / description, type / statement, component / use, …) in which some cells are printed and others are blank.
- **Signals:** `[TABLE_TYPE:TermDefinitionGrid]` is required. Any other table is a ValueTraceMatrix or a MatrixGrid.
- **`structure_data`** (*pipeline*): `{ "headers": [left, right], "row_count": N, "rows": [{ "term": str | null, "definition": str | null }, …] }`.
  - `postprocess.fill_term_def_grids` copies it from the PDF table, pairing tables and questions by page and order.
  - The model writes `{}`.
  - `null` marks a blank cell.
- **Check:** the number of blank cells should equal `marks`.

### 9. LabelledPartResponse
- **Answer space:** a reference item (a URL, code line or expression) with parts marked a, b, c …, and one short answer slot per part on one line.
- **Signals:** `[LAYOUT:LabelledPartResponse labels=a,b,c]`.
- **`structure_data`:** `{ "labels": ["a", "b", "c"], "reference": "https://www.cieclothes.com/index.html" }`.

### 10. AnnotatedDiagram
- **Answer space:** a drawing area. The student draws or completes a diagram: network, data flow, system architecture, packet structure or logic circuit.
- **Signals:**
  - commands such as "Draw and annotate a diagram", "Complete (and annotate) the diagram", "Draw a logic circuit" or "Sketch";
  - the page flag `[Likely contains a diagram/drawing]`;
  - no answer lines.
- **`structure_data`:** `{ "diagram_type": "network" | "flowchart" | "circuit" | "data flow" | "system architecture" | "other", "partial_elements": [...] }`.
  - `partial_elements` lists the pre-drawn or pre-labelled parts.
  - For a circuit, it lists the inputs, then the output.
- **Rendering:** `diagram_type: "circuit"` opens the interactive logic-gate editor, which loads JointJS on that page only. Other diagram types get a textarea.

### 11. CodeBlockResponse
- **Answer space:** a monospace area for pseudocode, SQL or program code.
- **Signals:** Paper 2, at least 3 marks, and the answer is code, whatever the command word. A 1–2-mark single-line SQL answer stays SimpleSingleBlock.
- **`structure_data`:** `{ "language": "pseudocode" | "sql" | "code", "line_count": N }`, where `line_count` is about 2 × marks.

### 12. LineMatching
- **Answer space:** two printed columns, joined by drawing one line from each item on the left to an item on the right ("Draw one line from each … to …").
- **`text`:** the two columns as a pipe table, `"<left header> | <right header>"` followed by one row per printed line. The rows are not matched pairs.
- **`structure_data`** (*pipeline*): `{ "left_header", "right_header", "left_items": [...], "right_items": [...] }`.
  - `postprocess.fix_line_matching_layouts` copies it from the pipe table.
  - It also relabels a matching question the model typed as MatrixGrid or AnnotatedDiagram.
- **Rendering:** the interactive matcher, `match.js`.

### 13. WorkingAnswer
- **Answer space:** a numeric calculation or conversion (Convert, Calculate, Add …), with a working area and/or labelled answer lines.
- **Signals:**
  - `[LAYOUT:WorkingAnswer working_space=true]`, which the pre-processor adds when the answer lines follow a printed "Working space";
  - one label line per value to convert ("429", "1A3");
  - an answer line such as "Answer ….. KiB" or "Denary value".
- **`structure_data`:** `{ "working_space": true | false, "answer_labels": ["429", "1A3"], "unit": "KiB" | null }`. Use `answer_labels: []` for a single unlabelled answer.
- **Not this layout:** a conversion with one plain answer line and no working area stays SimpleSingleBlock.
- **Rendering:** a working area (unless `working_space` is false), then one input per label with the unit after it. The label lines are removed from the prose so they are not shown twice.

---

## Not a layout: DataReferenceTable

`[TABLE_TYPE:DataReferenceTable]` marks a table that students **read**, such as a database table or a data set. It is copied into `text` as a pipe table, for each sub-question that uses it. The question's layout stays its answer format.

## Derived from the layout

`src/enricher.py` maps each layout to `cognitive_load` (`LOAD_MAP`). The statistics and topic pages show the friendly names from `LAYOUT_NAMES` in `src/static/stats.js` and `generate_topics.py`.
