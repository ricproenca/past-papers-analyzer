import base64
from typing import List, Dict, Any

from .enricher import COMMAND_TIER
from .syllabus import objectives_prompt_block, topics_prompt_block

PHASE12_SYSTEM = """You are an expert at reading Cambridge exam papers.
Your job is to identify every question (and sub-question) on the exam provided AND map each one to a syllabus topic.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

RULES:
- Treat each numbered question and each lettered/roman-numeral sub-question as a separate item.
- Map each question to the single best-fitting syllabus topic: the one whose key content matches what the question actually tests.
- Never invent question numbers — use exactly what is printed on the paper.
- When a question genuinely spans two topics, pick the first one.
- Paper routing — Paper 1 (variants 1x) covers chapters 1–6 (theory). Paper 2 (variants 2x) covers chapters 7–10. Algorithm questions map by what the algorithm is FOR: implementing a validation or verification check → 7.4; a standard method (linear search, bubble sort, totalling, counting, maximum/minimum/average) → 7.3; choosing test data → 7.5; otherwise algorithm design, flowcharts, trace tables and correcting errors → 7.2, and questions about one programming construct (data types, loops, string handling, procedures, operators) → 8.1; arrays → 8.2; files → 8.3. SQL questions map to 9.2. Logic gates / logic circuits / truth tables / Boolean expressions map to 10.x. The variant field in `qp` filename (e.g. `0478_m25_qp_22.pdf` → variant 22) determines the paper number from the first digit.
- For every sub-question (e.g. Q2c_ii), always include the parent question's context/stem at the beginning of the "text" field so each question is fully self-contained when read in isolation. The parent context is exactly the text printed BEFORE the parent's first part label — before "(a)" for Q2, before "(i)" for Q2c; text printed after a part label belongs to that part only. Copy that parent context IN FULL — every sentence, even ones that seem unrelated to this part — plus any pseudocode/program listing (numbered code lines) or reference table the parent introduces. Do NOT copy the words extracted from inside a diagram, flowchart or logic circuit (scattered box labels such as "START", "INPUT Answer", "Yes", "No"): that is the drawing itself, shown to the reader as an image; just keep the sentence that introduces it.
- Answer-space dotted lines have been removed. Answer label lines (e.g. 'Method', 'Input', '1', '14B') are preserved with their dots stripped — include them as-is in the 'text' field as structural cues for what the question asks for. Inline blanks appear as '[blank]'. Do not reconstruct or add dots, dashes, or extra answer-space lines.
- "text" is verbatim: only words printed on the paper — but repair obvious PDF-extraction artefacts: symbols displaced into words ("t←otal" → "Total ←" in its proper place), split words ("av erage" → "average"), and lost line breaks in numbered code listings (one numbered line per line). Never describe, summarise or interpret a diagram, flowchart or image in "text" — put any description in "visuals".
- Line-matching questions ("Draw one line from each ... to ..."): write the two printed columns in "text" as a pipe table — first line "<left header> | <right header>", then one line per row "<left item> | <right item>" in printed order (the rows are NOT matched pairs; leave a side empty if a column is shorter). Their layout_type is LineMatching.
- Tables that a structured layout renders from structure_data (MatrixGrid, ValueTraceMatrix, TermDefinitionGrid) must NOT be copied into "text"; "text" holds the prose only.
- Preserve paragraph breaks from the PDF in the "text" field. When the source PDF visually shows two prose paragraphs separated by a blank line / vertical gap (e.g. a setup paragraph "X happens in context Y." followed by a new instruction paragraph "Describe the process for Z."), put a literal blank line (`\n\n`) between them in the "text" field. Do NOT insert `\n\n` for line wraps within one paragraph, between a prose paragraph and a table, or between a paragraph and answer-space labels — those already have their own structure markers and don't need extra blank lines.



OUTCOME FROM PAPER:
Build a clean, structured JSON deliverable:
"board": the exam board, CIE
"level": the exam level IGCSE, AS Level, A Level only
"subject_code": subject code (e.g. 0478, 9618)
"subject_name": The subject name (e.g. Computer Science)
"variant": Variants (e.g. 11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43)
"total_marks": total marks for the entire paper (printed on the paper cover or final page)
"questions": for each question must have these exact keys:
    "id"   : question identifier, e.g. "Q1", "Q1a", "Q1b_i", "Q2"
    "text" : the full question text, starting with the parent question's context/stem (do not copy tables that structure_data renders)
    "command": exactly one word from the COMMAND WORDS list below
    "objective": primary assessment objective — exactly one of: "AO1", "AO2", "AO3" (see OBJECTIVES below)
    "marks": amount of marks in each question
    "visuals": array with visuals elements like diagrams, tables, graphs, images. Empty array if nothing
    "page": the paper page number of the question
    "layout_type": the question's visual answer format — exactly one of the 13 types listed in LAYOUT TYPES below
    "structure_data": object with type-specific metadata fields (see LAYOUT TYPES); use {} if no data is detectable
    "topic": topic code from the syllabus (e.g. "1.2") — see TOPICS below. Do NOT output the topic name; it is added automatically.

<<OBJECTIVES>>

LAYOUT TYPES:
The page text contains [LAYOUT:TYPE key=value] and [TABLE_TYPE:TYPE key=value] annotations inserted by the
pre-processor. Use them as the primary signal for layout_type and structure_data. When no annotation is
present, infer from context using the indicators below.

SimpleSingleBlock — single open answer space (one or more blank answer lines, no structural sub-labels)
  PDF signals: [LAYOUT:SimpleSingleBlock line_count=N]; or a single trailing answer space with no other structure
  structure_data: { "line_count": N }  // number of answer lines detected; use 1 if unknown

MultiPartLabeledBlock — labeled sub-answer slots with category prefixes before each answer space
  PDF signals: [LAYOUT:MultiPartLabeledBlock labels=Justification,Explanation]; or repeated label lines with no annotation
    (e.g. "Error 1 line number" / "Correction" / "Error 2 line number" / "Correction" ...) — still MultiPartLabeledBlock, labels in printed order
  Pairs: Justification/Explanation, Benefit/Drawback, Advantage/Disadvantage
  structure_data: { "labels": ["Justification", "Explanation"] }

NumberedMultiList — discrete numbered answer items (1 / 2 / 3 … each on their own line)
  PDF signals: [LAYOUT:NumberedMultiList count=N]
  structure_data: { "list_count": N }

InlineCloze — fill-in-the-gap prose; blanks appear as [blank] mid-sentence; may include a word bank box
  PDF signals: [LAYOUT:InlineCloze gap_count=N]
  structure_data: { "inline_gap_count": N, "has_word_bank": true/false }
  Set has_word_bank to true if a word bank list or table is visible near the question.

MatrixGrid — a table answered with ticks/selections. Two patterns:
  (1) Comparison grid — option columns, one tick per row.
      structure_data: { "matrix_headers": ["Statement","True","False"], "row_count": N, "rows": ["statement text", ...] }
      rows: the left-column text of each row, in order.
  (2) Single-select MCQ — "Tick (✓) one box…" with options A/B/C/… listed below the prompt; one row per option.
      structure_data: { "matrix_headers": ["Option","Tick"], "row_count": N, "rows": ["A <full statement>", "B <full statement>", ...] }
      Also "Circle three …" questions with a printed list of options and no letters: one row per option,
      headers ["Option","Select"] — never SimpleSingleBlock.
      Exactly two headers, the right one "Tick", "Select", "Choose" or "Mark". Never put the option letters in matrix_headers
      or collapse the options into one row. These two headers are not printed on the paper: never write them into "text".

ValueTraceMatrix — a table where students write cell values: trace tables (every data cell blank) and data tables with
  some cells printed (parity blocks, truth tables, conversion and test-data tables).
  PDF signals: [TABLE_TYPE:ValueTraceMatrix]; headers are registers (PC, ACC, MAR …), variable names or bit positions.
  structure_data: { "matrix_headers": ["parity bit","bit 7","bit 6"], "row_count": N, "rows": ["byte 1","byte 2","parity byte"],
                    "row_header": "Byte", "row_values": [["1","1","0"], ["0","1","1"], null] }
  matrix_headers: the data columns only — not the left-most row-label column (put its printed heading in optional "row_header").
  rows: the left-most label of each row, in order.
  row_values (optional): parallel to rows; null = every cell of that row is blank, otherwise one string per data column
    with "" for a blank cell. Omit it for a pure trace table. Self-check: blank cells usually equal marks.

FixedRegisterArray — 8 or 16 isolated single-bit boxes for binary/hex writing
  PDF signals: [TABLE_TYPE:FixedRegisterArray register_size=N]
  structure_data: { "register_size": N }  // N is 8 or 16

TermDefinitionGrid — two-column "label / explanation" table where SOME cells are pre-filled and OTHERS blank.
  PDF signals: [TABLE_TYPE:TermDefinitionGrid] — REQUIRED. Use this layout ONLY for a two-column table the page marks with that
    annotation. A table with three or more columns, or one without the annotation, is ValueTraceMatrix or MatrixGrid.
  structure_data: {}   // the pipeline copies the headers and every cell verbatim from the PDF table — do not type them
  text: the prose stem/instruction only. Do NOT write the table, its header row or "(blank)" cells into "text".
  marks: one blank cell is typically one mark.

LabelledPartResponse — a reference item (URL, code, expression) with parts marked a/b/c; short inline answer slots
  PDF signals: [LAYOUT:LabelledPartResponse labels=a,b,c]; a line of the form "a ..... b ..... c ....."
  structure_data: { "labels": ["a", "b", "c"], "reference": "https://www.cieclothes.com/index.html" }
  labels: the callout letters or numbers in order.
  reference: the URL, code line, expression, or brief description of the item being labelled.

AnnotatedDiagram — the student draws or completes a diagram (network, data flow, system architecture, logic circuit …).
  PDF signals: "Draw and annotate a diagram", "Complete (and annotate) the diagram", "Draw a logic circuit", "Sketch";
               the page flag [Likely contains a diagram/drawing]; no answer lines — the drawing area is the answer space.
  structure_data: { "diagram_type": "network" | "flowchart" | "circuit" | "data flow" | "system architecture" | "other",
                    "partial_elements": ["Patient's computer", "www.cihospital.com"] }
  partial_elements: every pre-drawn or pre-labelled node/component; for a logic circuit the inputs then the output (A, B, C, Z).

LineMatching — "Draw one line from each … to …": two printed columns of items to connect.
  text: the two columns as a pipe table (see RULES). structure_data: {}   // the pipeline copies the columns from the pipe table

WorkingAnswer — a numeric calculation or conversion (Convert, Calculate, Add …) with a working area and/or labelled answer lines.
  PDF signals: [LAYOUT:WorkingAnswer working_space=true]; a "Working space" line; one label line per value to convert
               ("429", "1A3"); an answer line such as "Answer ..... KiB" or "Denary value". A conversion with one plain
               answer line and no working area stays SimpleSingleBlock.
  structure_data: { "working_space": true, "answer_labels": ["429", "1A3"], "unit": "KiB" }
  working_space: true when the paper prints "Working space" or asks to show working. answer_labels: the printed label of
    each answer line, in order ([] for a single unlabelled answer). unit: the unit printed after the answer line, else null.

DataReferenceTable handling — when a page contains [TABLE_TYPE:DataReferenceTable], this is a lookup or context table provided IN the question (e.g. a database table, a data set, a reference grid) that students must READ to answer the sub-questions. It is NOT an answer format.
  MANDATORY: Include the full table in the "text" field of the FIRST sub-question that references it, in pipe-separated format: one row per line, first line = header, subsequent lines = data rows (no separator line). Position the table right after the opening prose stem (the sentence that introduces it) and before any sub-question prompt.
  For subsequent sub-questions on later pages that reference the same table (e.g. Q8b, Q8c, Q8d after Q8a introduced MajorCity), also include the full table in their "text" field so each question is self-contained.
  The question's layout_type must still be the ANSWER FORMAT (e.g. MultiPartLabeledBlock, CodeBlockResponse), not DataReferenceTable.
  Example — Q8a text with a provided database table:
    "A database table, MajorCity, stores some details about a number of cities around the world.\n\n| Code | City | Capital | Country | Continent | Population |\n| ASY6 | Abu Dhabi | TRUE | United Arab Emirates | Asia | 1,566,999 |\n...\n\nState the number of fields and records in this database table.\n\nFields\nRecords"

CodeBlockResponse — student writes multi-line pseudocode, SQL, or an algorithm into a monospace area.
  PDF signals: Paper 2 only (variants 21/22/23); marks ≥ 3 AND the answer itself is pseudocode, an algorithm, SQL or
               program code — whatever the command word ("Write", "Complete", "Amend", "Rewrite" ...).
               A 1- or 2-mark "write the SELECT statement" should stay SimpleSingleBlock — Code block is for
               substantive write-ups, not single-line answers.
  structure_data: {
    "language": "pseudocode" | "sql" | "code",
    "line_count": N
  }
  language: "pseudocode" for algorithm / pseudocode writing; "sql" for SQL queries; "code" for any other.
  line_count: roughly marks × 2 (so a 5-mark pseudocode question gets 10 lines of room). Adjust upward
              if the question explicitly asks for many distinct steps.

Fallback rule: if no annotation is present and no table exists, assign SimpleSingleBlock with line_count: 1.

COMMAND WORDS:
The "command" value must be exactly ONE word from this closed list: <<COMMAND_LIST>>. If the instruction has several words (e.g. "Complete and annotate the diagram") use its first word ("Complete"); if the printed word is not in the list choose the closest one.
Guidance for the main ones:
Command word	What to do in Computer Science	        Common mistake
State	        Short answer; one point per mark	    Overwriting
Identify	    Choose from code/diagram/data	        Adding explanation
Define	        Precise computing meaning	            Vague or everyday language
Describe	    What the code/process does; no "why"	Adding explanation
Explain	        Why or how; use "because"	            Only describing
Suggest	        Apply to context; propose solution	    Generic answer
Compare	        Similarities and differences	        Listing separately
Analyse	        Break down; show relationships	        Only describing
Evaluate	    Judge; conclude with evidence	        No conclusion
Outline	        Main points only	                    Too much detail
Sketch	        Simple diagram; key features	        Too detailed
Write	        Produce pseudocode/algorithm	        Wrong syntax
Trace	        Follow through step by step	            Missing steps
Calculate	    Work out; show working	                Wrong formula

<<TOPICS>>"""

PHASE3_SYSTEM = """You are given an extraction of an exam paper (JSON) and its marking scheme. For each question, find its answer in the marking scheme.
Return ONLY a valid JSON object that maps each question "id" to its answer object — no markdown, no explanation, no code fences, and do NOT repeat any question fields. Shape:
{
  "Q1a": {"type": "...", "visuals": [], "scoring_rule": "...", "marking_points": [{"text": "...", "marks": 1}]},
  "Q1b_i": {...}
}
Use every "id" from the extraction exactly as written, once each. Each answer object has:
    "type": type of answer — "text", "diagram", "pseudocode", or "MCQ"
    "visuals": array of visual elements referenced in the answer. Empty array if none
    "scoring_rule": the scoring instruction stated in the marking scheme, copied verbatim (e.g. "Any three from", "1 mark for each correct item (in bold)", "1 mark for naming, max 2 for describing"). Set to null if no explicit rule is stated.
    "marking_points": array of marking criteria, each with:
        "text": the marking criterion text, exactly as in the marking scheme
        "marks": integer number of marks awarded for this criterion

RULES:
- Match each question by its "id" to the corresponding marking scheme entry.
- For MCQ questions set "type" to "MCQ" and use a single marking_point with the correct option letter as "text" and 1 as "marks".
- For pseudocode/algorithm answers set "type" to "pseudocode".
- For diagram-based answers set "type" to "diagram".
- For all other answers set "type" to "text".
- Copy each marking criterion verbatim — do not abbreviate or paraphrase.
- "scoring_rule" must capture exactly what the marking scheme states before the bullet points: e.g. "Any one from", "Any three from", "1 mark for each correct item (in bold)", "1 mark for correct working, 1 mark for each correct nibble", "1 mark for naming, max 2 for describing". Set to null only when there is no such instruction (e.g. plain MCQ or single fixed answer).
- Distinguish "Any N from:" (student picks N answers from a larger pool of alternatives) from "1 mark for each correct answer" (student must identify N fixed required answers). Use "1 mark for each correct answer" for 'circle/tick/identify exactly N specific items' questions — not "Any one from:".
- When a question has multiple independent named parts with separate answer lines (e.g. "Input ....." and "Output ....."), prefix each marking_point "text" with its part label: e.g. "Input: Microphone", "Output: Speaker".
- Question numbers: the marking scheme writes "1(a)(i)", "2(b)", "10"; the extraction ids are "Q1a_i", "Q2b", "Q10".
- One marking point per criterion the marking scheme lists, in its order. Never merge alternatives: "MP3 ... OR MP4 ..." are two points. Keep every listed item of a "column"/"row" answer (e.g. include the prompts in a trace-table column).
- Banded marks ("4 marks for all eight correct outputs, 3 marks for six or seven ..."): put the band wording in "scoring_rule" verbatim and list each expected item (each output row, each cell) as its own point with "marks": 1.
- Levels of response (mark bands such as "AO2 1–3 marks: ..."): one point per band descriptor, verbatim including its label, with "marks" = the TOP of that band (0 for a "0 marks" band).
- If a question has no marking scheme entry, still include its id and set "marking_points" to an empty array []."""

# The closed command list, the topics and the objectives are generated from src/enricher.py and
# src/syllabus.py so prompt, schema and enrichment can never disagree.
PHASE12_SYSTEM = (PHASE12_SYSTEM
                  .replace("<<COMMAND_LIST>>", ", ".join(COMMAND_TIER))
                  .replace("<<TOPICS>>", topics_prompt_block())
                  .replace("<<OBJECTIVES>>", objectives_prompt_block()))


def build_pdf_text(pages: List[Dict[str, Any]]) -> str:
    parts = []
    for p in pages:
        flags = []
        if p["has_table"]:
            flags.append("[Contains table(s)]")
        if p["has_image"]:
            flags.append("[Contains image(s)]")
        if p.get("has_diagram"):
            flags.append("[Likely contains a diagram/drawing]")
        if not p["text"].strip() and not flags:
            continue                      # blank page: nothing to send
        header = f"[Page {p['page']}]"
        if flags:
            header += " " + " ".join(flags)
        parts.append(header + "\n" + p["text"])
    return "\n\n".join(parts)


def build_phase12_messages(pages: List[Dict[str, Any]], page_images: Dict[int, bytes] | None = None):
    """Build the Phase 1+2 request. `page_images` ({page: PNG bytes}) optionally
    attaches the pages that hold diagrams, so the model sees them instead of guessing."""
    system = [
        {
            "type": "text",
            "text": PHASE12_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    pdf_text = build_pdf_text(pages)
    if not page_images:
        return system, [{"role": "user", "content": pdf_text}]
    content = [{"type": "text", "text": pdf_text}]
    for n in sorted(page_images):
        content.append({"type": "text", "text": f"Image of page {n} (use it to read the diagram; the text above is still authoritative for wording):"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                    "data": base64.b64encode(page_images[n]).decode("ascii")}})
    return system, [{"role": "user", "content": content}]


def build_phase3_messages(phase12_json: str, ms_pages: List[Dict[str, Any]]):
    system = [
        {
            "type": "text",
            # No cache_control: ~650 tokens is below the minimum cacheable prefix
            # (1024), so the API would silently ignore it.
            "text": PHASE3_SYSTEM,
        }
    ]
    ms_text = build_pdf_text(ms_pages)
    user_content = (
        "Here is the extraction result:\n\n"
        + phase12_json
        + "\n\nHere is the marking scheme text:\n\n"
        + ms_text
    )
    messages = [{"role": "user", "content": user_content}]
    return system, messages
