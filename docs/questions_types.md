# Question Layout Types

Ten structural layouts used in Cambridge exam papers. Each question must be assigned exactly one `layout_type`. The `structure_data` object carries type-specific metadata.

---

### 1. SimpleSingleBlock
- **Description:** A single text prompt followed by one or more continuous writing lines.
- **PDF Indicators:** Two or more consecutive dot lines (`....................`) below the question stem. Single trailing answer lines also qualify.
- **`structure_data`:** `{ "line_count": N }` — number of answer lines detected.

---

### 2. MultiPartLabeledBlock
- **Description:** A single question prompt split into explicit sub-answer slots, each prefixed by a category label.
- **PDF Indicators:** Lines starting with a label anchor immediately before a dot sequence. Common pairs:
  - `Justification:` / `Explanation:`
  - `Benefit:` / `Drawback:`
  - `Advantage:` / `Disadvantage:`
- **`structure_data`:** `{ "labels": ["Benefit", "Drawback"] }` — ordered list of label strings found.

---

### 3. NumberedMultiList
- **Description:** A question demanding a fixed number of discrete items, each on its own numbered line.
- **PDF Indicators:** Left-aligned marginal integers followed by dot sequences (e.g., `1 ....`, `2 ....`, `3 ....`) breaking up a single question block.
- **`structure_data`:** `{ "list_count": N }` — number of numbered slots.

---

### 4. InlineCloze
- **Description:** Continuous prose with embedded missing tokens (fill-in-the-gaps). May be accompanied by a word bank box.
- **PDF Indicators:** Paragraph text interrupted mid-sentence by dot sequences (e.g., `"The data is sent via a ............ cable to the router."`). A bracketed word list nearby signals a word bank.
- **`structure_data`:** `{ "inline_gap_count": N, "has_word_bank": true | false }` — number of blanks and whether a word bank is present.

---

### 5. MatrixGrid
- **Description:** A multi-column comparison table requiring the student to place ticks, crosses, or discrete tokens in cells.
- **PDF Indicators:** Table headers represent states or categories (e.g., `True / False`, `RAM / ROM / Flash`). Rows contain feature statements. Instructions like `"Tick (✓) one box"` confirm this type.
- **`structure_data`:** `{ "matrix_headers": ["Statement", "True", "False"], "row_count": N, "rows": ["feature text", ...] }` — column headers and the text of each feature row.

---

### 6. ValueTraceMatrix
- **Description:** A structured tracking grid where the student fills in register or variable values step by step (e.g., assembly language or algorithm trace tables).
- **PDF Indicators:** A multi-row table whose column headers are CPU register names (`PC`, `ACC`, `IX`, `MAR`, `MDR`, `CIR`, `SR`) or named program variables.
- **`structure_data`:** `{ "matrix_headers": ["PC", "ACC", "MAR"], "row_count": N, "rows": ["LDD 050", "ADD #5", ...] }` — column headers and the instruction or step label for each row.

---

### 7. FixedRegisterArray
- **Description:** A fixed-width array of single-bit boxes for writing binary or hexadecimal values.
- **PDF Indicators:** A contiguous horizontal chain of exactly 8 or 16 small isolated boxes, each intended for a single binary digit (0 or 1).
- **`structure_data`:** `{ "register_size": 8 }` — total number of boxes (8 or 16).

---

### 8. TermDefinitionGrid
- **Description:** A two-column Term / Definition table where some cells are pre-filled and others are blank for the student to complete.
- **PDF Indicators:** A table with `Term` and `Definition` column headers. Each row has one column pre-filled and one blank — the student must supply the missing half.
- **`structure_data`:** `{ "row_count": N, "rows": [{ "term": "pixel" | null, "definition": "..." | null }, ...] }` — one object per row; set the pre-filled value as a string and the blank cell as `null`.

---

### 9. LabelledPartResponse
- **Description:** A reference item (URL, code snippet, diagram, expression) is shown with parts marked by letter or number callouts (a, b, c). The student writes a short answer for each callout in compact inline slots on a single line.
- **PDF Indicators:** A reference string or image above the answer area with callout markers (a, b, c or 1, 2, 3). Answer slots appear as `a ..... b ..... c .....` on a single line — each slot is short (one value, not multi-line).
- **`structure_data`:** `{ "labels": ["a", "b", "c"], "reference": "https://www.cieclothes.com/index.html" }` — the ordered callout labels and the reference item being labelled (URL, expression, code line, or a short description of the diagram element).

---

### 10. AnnotatedDiagram
- **Description:** A partially drawn diagram (network topology, flowchart, system architecture, logic circuit, etc.) where the student must complete missing nodes, draw connections, and add annotation labels.
- **PDF Indicators:** Command words such as "Complete and annotate the diagram", "Complete the diagram", "Draw a diagram", or "Sketch". The page contains vector graphics (lines, boxes, arrows) with some elements pre-labelled. No dot answer lines — the diagram canvas itself is the answer space.
- **`structure_data`:** `{ "diagram_type": "network" | "flowchart" | "circuit" | "data flow" | "system architecture" | "other", "partial_elements": ["Patient's computer", "www.cihospital.com"] }` — the diagram category and the list of pre-drawn/pre-labelled anchor elements visible in the question.
