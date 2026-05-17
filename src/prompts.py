from typing import List, Dict, Any

PHASE12_SYSTEM = """You are an expert at reading Cambridge exam papers.
Your job is to identify every question (and sub-question) on the exam provided AND map each one to a syllabus topic.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

RULES:
- Treat each numbered question and each lettered/roman-numeral sub-question as a separate item.
- Read all questions, let categories emerge, reconcile to syllabus in the end.
- Never invent question numbers — use exactly what is printed on the paper.
- When a question genuinely spans two topics, pick the first one.
- For every sub-question (e.g. Q2c_ii), always include the parent question's context/stem at the beginning of the "text" field so each question is fully self-contained when read in isolation.
- Answer-space dotted lines have been removed. Answer label lines (e.g. 'Method', 'Input', '1', '14B') are preserved with their dots stripped — include them as-is in the 'text' field as structural cues for what the question asks for. Inline blanks appear as '[blank]'. Do not reconstruct or add dots, dashes, or extra answer-space lines.
- Preserve paragraph breaks from the PDF in the "text" field. When the source PDF visually shows two prose paragraphs separated by a blank line / vertical gap (e.g. a setup paragraph "X happens in context Y." followed by a new instruction paragraph "Describe the process for Z."), put a literal blank line (`\n\n`) between them in the "text" field. Do NOT insert `\n\n` for line wraps within one paragraph, between a prose paragraph and a table, or between a paragraph and answer-space labels — those already have their own structure markers and don't need extra blank lines.


Assessment Objectives
Code	Description	                                                            Weighting
AO1	    Demonstrate knowledge and understanding of the principles and concepts	40%
AO2	    Apply knowledge and understanding to given contexts	                    40%
AO3	    Evaluate, make reasoned judgements, present conclusions	                20%

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
    "text" : the full question text (include all parts of the question)
    "command": Command word used (e. g. State, Explain)
    "objective": primary assessment objective — exactly one of: "AO1", "AO2", "AO3"
    "marks": amount of marks in each question
    "visuals": array with visuals elements like diagrams, tables, graphs, images. Empty array if nothing
    "page": the paper page number of the question
    "layout_type": the question's visual answer format — exactly one of the 10 types listed in LAYOUT TYPES below
    "structure_data": object with type-specific metadata fields (see LAYOUT TYPES); use {} if no data is detectable
    "topic": topic from the syllabus (e.g. "1.2") — see TOPICS below
    "topic_name": the name of the topic (e.g. "Text, Sound and Images") — see TOPICS below

LAYOUT TYPES:
The page text contains [LAYOUT:TYPE key=value] and [TABLE_TYPE:TYPE key=value] annotations inserted by the
pre-processor. Use them as the primary signal for layout_type and structure_data. When no annotation is
present, infer from context using the indicators below.

SimpleSingleBlock — single open answer space (one or more blank answer lines, no structural sub-labels)
  PDF signals: [LAYOUT:SimpleSingleBlock line_count=N]; or a single trailing answer space with no other structure
  structure_data: { "line_count": N }  // number of answer lines detected; use 1 if unknown

MultiPartLabeledBlock — labeled sub-answer slots with category prefixes before each answer space
  PDF signals: [LAYOUT:MultiPartLabeledBlock labels=Justification,Explanation]
  Pairs: Justification/Explanation, Benefit/Drawback, Advantage/Disadvantage
  structure_data: { "labels": ["Justification", "Explanation"] }

NumberedMultiList — discrete numbered answer items (1 / 2 / 3 … each on their own line)
  PDF signals: [LAYOUT:NumberedMultiList count=N]
  structure_data: { "list_count": N }

InlineCloze — fill-in-the-gap prose; blanks appear as [blank] mid-sentence; may include a word bank box
  PDF signals: [LAYOUT:InlineCloze gap_count=N]
  structure_data: { "inline_gap_count": N, "has_word_bank": true/false }
  Set has_word_bank to true if a word bank list or table is visible near the question.

MatrixGrid — table that requires ticks/selections. Covers TWO sub-patterns:

  (1) MATRIX COMPARISON — multiple option columns; each row gets ONE tick.
      Example headers: ["Statement", "True", "False"], ["Feature", "RAM", "ROM", "Flash"].
      structure_data: { "matrix_headers": ["Statement","True","False"], "row_count": N,
                        "rows": ["statement text", ...] }
      rows: the text of each statement/feature row (left-most column), in order.

  (2) SINGLE-SELECT MCQ — one tick column with N alternative options labelled A/B/C/…
      Triggered by "Tick (✓) one box…", "Tick (✓) two boxes…", etc. each option is one row.
      structure_data: { "matrix_headers": ["Option", "Tick"], "row_count": N,
                        "rows": ["A <full statement>", "B <full statement>", ...] }
      • Headers MUST be exactly two columns: the LEFT header is the row-label (e.g. "Option",
        "Statement"); the RIGHT header signals selection — use one of: "Tick", "Select",
        "Choose", "Mark".
      • rows MUST be one row PER OPTION. Each row string starts with the option letter/number
        (A, B, C, …) followed by a space and the full statement text. Do NOT put the option
        letters in matrix_headers (that produces an unusable layout). Do NOT collapse the
        question to a single row like ["Tick one box"] with letters as headers.
      • The renderer derives tick-count (one/two/three/…) from the question text directly,
        so no extra field is needed.
      • CRITICAL — text field: the headers ["Option","Tick"] (or similar) are CANONICAL
        placeholders that live in structure_data ONLY. The PDF does NOT print a literal
        "Option | Tick" row above the options. NEVER write a synthetic header line like
        "Option | Tick" (or any "<left> | <right>" canonical-header line) into the "text"
        field. The text field must contain only the prose stem and what is actually printed
        on the PDF — never the pipe-separated canonical headers.
      Common command words for this pattern: "Tick", "Circle", "Select".

  Distinguishing the two: if the question reads "Tick one box to show…" with options labelled
  A/B/C/D listed BELOW the prompt, it is pattern (2). If each row already has its own True/False
  or category choice, it is pattern (1).

ValueTraceMatrix — multi-column data table where students fill in cell values; covers BOTH:
    (a) algorithm/register trace tables (all data cells blank — students compute values)
    (b) data-grid tables with rows prefilled and only some rows blank (e.g. parity block check tables)
  PDF signals: [TABLE_TYPE:ValueTraceMatrix]; headers include PC, ACC, IX, MAR, MDR, CIR, SR, variable names,
    or bit/byte positions like "parity bit, bit 7, bit 6, …, bit 1".
  structure_data: {
    "matrix_headers": ["parity bit","bit 7","bit 6","bit 5","bit 4","bit 3","bit 2","bit 1"],
    "row_count": N,
    "rows": ["byte 1","byte 2","byte 3","byte 4","byte 5","byte 6","byte 7","parity byte"],
    "row_values": [
      ["1","1","0","0","1","1","1","0"],   // byte 1 — fully prefilled
      ["1","0","0","0","0","1","1","0"],   // byte 2 — fully prefilled
      ["0","1","0","0","0","0","0","0"],   // byte 3 — fully prefilled
      ["0","1","0","0","1","1","1","1"],   // byte 4 — fully prefilled
      ["1","0","0","0","0","0","0","0"],   // byte 5 — fully prefilled
      ["0","1","1","1","1","1","1","1"],   // byte 6 — fully prefilled
      ["1","1","0","0","1","1","0","1"],   // byte 7 — fully prefilled
      null                                  // parity byte — all 8 cells blank
    ]
  }
  matrix_headers: only the DATA column headers; do NOT include the leftmost row-label column.
  rows: the step / instruction / byte label for each row (left-most column), in order.
  row_values (NEW, optional): parallel array to rows giving prefilled cell values per row:
    • null (or omit the field entirely) → that row's data cells are ALL blank for the student to fill
    • [v0, v1, …] → list of strings, one per matrix_headers column, in the same order;
                    use null or "" inside the array for an individual blank cell
  When most cells in the table are prefilled and only a subset of rows / cells are blank (typical of
  parity check tables or "complete the table" data-fill questions), POPULATE row_values. When the table
  is a pure trace (algorithm walk-through, register trace), OMIT row_values — the renderer treats every
  data cell as blank.
  Self-check: the number of blank cells in your row_values (counting all nulls — including each entry of
  any null/missing row entry) should align with the question's "marks" value (one blank = one mark, typical).

FixedRegisterArray — 8 or 16 isolated single-bit boxes for binary/hex writing
  PDF signals: [TABLE_TYPE:FixedRegisterArray register_size=N]
  structure_data: { "register_size": N }  // N is 8 or 16

TermDefinitionGrid — two-column "label / explanation" table where SOME cells are pre-filled and OTHERS blank.

  ===========================================================================
  MANDATORY EXTRACTION RULE (overrides all instinct/heuristics):
  ===========================================================================
  When the page text contains a `[TERM_DEF_TABLE_DATA]…[/TERM_DEF_TABLE_DATA]` JSON block
  (the preprocessor emits one for every TermDefinitionGrid table), it is THE AUTHORITATIVE
  source for cell contents. You MUST:
    1. Parse the JSON inside the block.
    2. Copy its "rows" array INTO structure_data.rows POSITIONALLY, with this transformation
       and NO OTHER changes:
         • For each cell value, if it is "" (empty string) → write null in structure_data.
         • If it is a non-empty string → copy that exact string verbatim.
       Do NOT swap fields. Do NOT move text from "term" to "definition" or vice-versa even if
       the wording "looks like" a description or a name. The LEFT cell in the PDF goes to
       "term"; the RIGHT cell goes to "definition". Always.
    3. Set "row_count" to the number of rows you wrote.
  Do NOT re-read the markdown table to "verify" or "correct" cell positions. The model has
  no better view of the PDF than the preprocessor does; trust the JSON block.

  In the "text" field, also keep the table as "(left) | (right)" lines with the header row
  first; write "(blank)" for empty cells — this is a human-readable mirror only, not a
  source of truth.

  Header names VARY across questions: real Cambridge examples include
    "Function name | Description", "Component name | Description", "Internet term | Description",
    "Type of secondary storage | Description", "Term | Description", "Term | Definition".
  Headers come from the JSON block's "headers" array — copy verbatim into "text".

  Example. If the page text contains:
    [TERM_DEF_TABLE_DATA]
    {"headers": ["Function name", "Description"],
     "rows": [
       {"term": "managing memory",    "definition": ""},
       {"term": "",                   "definition": "allows application software to run on the computer"},
       {"term": "managing peripherals","definition": ""}
     ]}
    [/TERM_DEF_TABLE_DATA]
  Then structure_data MUST be:
    {
      "row_count": 3,
      "rows": [
        { "term": "managing memory",    "definition": null },
        { "term": null,                 "definition": "allows application software to run on the computer" },
        { "term": "managing peripherals","definition": null }
      ]
    }
  And "text" includes the lines:
    Function name | Description
    managing memory | (blank)
    (blank) | allows application software to run on the computer
    managing peripherals | (blank)

  Fallback (no JSON block emitted — rare): read each row's LEFT and RIGHT cell independently
  from the markdown table. Blanks may appear in EITHER column and the pattern can vary row by
  row. Set the cell's field to null if it is an empty dotted/underscore answer line, else copy
  the printed text verbatim. Self-check: total nulls across rows should match the question's
  "marks" value (one blank = one mark, typical case).

LabelledPartResponse — a reference item (URL, code, expression) with parts marked a/b/c; short inline answer slots
  PDF signals: [LAYOUT:LabelledPartResponse labels=a,b,c]; a line of the form "a ..... b ..... c ....."
  structure_data: { "labels": ["a", "b", "c"], "reference": "https://www.cieclothes.com/index.html" }
  labels: the callout letters or numbers in order.
  reference: the URL, code line, expression, or brief description of the item being labelled.

AnnotatedDiagram — a partially drawn diagram canvas; student adds missing nodes, connections, and labels
  PDF signals: command words "Complete and annotate the diagram", "Complete the diagram", "Draw", or "Sketch";
               page contains vector shapes (lines, boxes, arrows) with pre-labelled anchor elements;
               no dot answer lines — the diagram itself is the answer space
  structure_data: {
    "diagram_type": "network" | "flowchart" | "circuit" | "data flow" | "system architecture" | "other",
    "partial_elements": ["Patient's computer", "www.cihospital.com"]
  }
  diagram_type: choose the closest category for the diagram shown.
  partial_elements: list every pre-drawn or pre-labelled node/component visible in the question diagram.

Fallback rule: if no annotation is present and no table exists, assign SimpleSingleBlock with line_count: 1.

COMMAND WORDS:
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

TOPICS (code — name — key content):
1.1 Number Systems — binary, denary, hexadecimal, BCD; base conversion; binary arithmetic; two's complement; overflow
1.2 Text, Sound and Images — ASCII, Unicode; sampling rate and bit depth for audio; pixel, resolution, colour depth for images
1.3 Data Storage and Compression — units (bit to TB); lossy vs lossless compression; run-length encoding; Huffman coding
2.1 Types and Methods of Data Transmission — serial vs parallel; simplex/half-duplex/full-duplex; USB, Bluetooth, Wi-Fi; packet switching
2.2 Methods of Error Detection — parity bits, checksums, check digits, ARQ
2.3 Encryption — symmetric vs asymmetric; public/private keys; Caesar/Vernam cipher; SSL/TLS
3.1 Computer Architecture — CPU, ALU, CU, registers, fetch-decode-execute cycle; Von Neumann model; cache
3.2 Input and Output Devices — keyboards, mice, scanners, cameras, sensors; monitors, printers, actuators
3.3 Data Storage — primary (RAM, ROM), secondary (HDD, SSD, optical, flash); virtual memory
3.4 Network Hardware — NIC, hub, switch, router, WAP, modem; LAN vs WAN; cloud storage
4.1 Types of Software and Interrupts — OS functions; utility software; interrupts; scheduling algorithms
4.2 Types of Programming Language, Translators and IDEs — high/low-level languages; compilers, interpreters, assemblers; IDE features
5.1 The Internet and the World Wide Web — DNS, HTTP/S, IP, TCP/IP; HTML; search engines; URLs
5.2 Digital Currency — cryptocurrency; blockchain; mining; wallets
5.3 Cyber Security — malware, phishing, brute-force, DDoS; firewalls, anti-malware, authentication, encryption
6.1 Automated Systems — feedback loops; sensors and actuators; control systems; autonomous vehicles
6.2 Robotics — actuators, effectors; robot applications; advantages and limitations
6.3 Artificial Intelligence — machine learning; neural networks; expert systems; natural language processing"""

PHASE3_SYSTEM = """Update the JSON deliverable. For each question, find its answer in the marking scheme and add an "answers" key:
    "type": type of answer — "text", "diagram", "pseudocode", or "MCQ"
    "visuals": array of visual elements referenced in the answer. Empty array if none
    "scoring_rule": the scoring instruction stated in the marking scheme, copied verbatim (e.g. "Any three from", "1 mark for each correct item (in bold)", "1 mark for naming, max 2 for describing"). Set to null if no explicit rule is stated.
    "marking_points": array of marking criteria, each with:
        "text": the marking criterion text, exactly as in the marking scheme
        "marks": integer number of marks awarded for this criterion

Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

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
- If a question has no marking scheme entry, set "marking_points" to an empty array []."""

def build_pdf_text(pages: List[Dict[str, Any]]) -> str:
    parts = []
    for p in pages:
        header = f"[Page {p['page']}]"
        flags = []
        if p["has_table"]:
            flags.append("[Contains table(s)]")
        if p["has_image"]:
            flags.append("[Contains image(s)/diagram(s)]")
        if flags:
            header += " " + " ".join(flags)
        parts.append(header + "\n" + p["text"])
    return "\n\n".join(parts)


def build_phase12_messages(pages: List[Dict[str, Any]]):
    system = [
        {
            "type": "text",
            "text": PHASE12_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    pdf_text = build_pdf_text(pages)
    messages = [
        {"role": "user", "content": pdf_text}
    ]
    return system, messages


def build_phase3_messages(phase12_json: str, ms_pages: List[Dict[str, Any]]):
    system = [
        {
            "type": "text",
            "text": PHASE3_SYSTEM,
            "cache_control": {"type": "ephemeral"},
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
