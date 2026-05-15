# PHASE 1
You are an expert at reading Cambridge exam papers. 
Your job is to identify every question (and sub-question) on the exam provided.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

RULES:
- Treat each numbered question and each lettered/roman-numeral sub-question as a separate item.
- Read all questions, let categories emerge, reconcile to syllabus in the end.
- Never invent question numbers — use exactly what is printed on the paper.
- When a question genuinely spans two topics, pick the first one.


OUTCOME FROM PAPER:
Build a clean, structured JSON deliverable:
"board": the exam board, CIE
"level": the exam level IGCSE, AS Level, A Level only
"subject_code": subject code (e.g. 0478, 9618)
"subject_name": The subject name (e.g. Computer Science)
"variant": Variants (e.g. 11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43)
"qp": question paper filename (e.g. "0478_m25_qp_12.pdf") — injected by the pipeline, not extracted from the PDF
"ms": marking scheme filename (e.g. "0478_m25_ms_12.pdf"), or null if no marking scheme provided — injected by the pipeline
"questions": for each question must have these exact keys:
    "id": question identifier, e.g. "Q1", "Q1a", "Q1bi", "Q2"
    "text" : the full question text (include all parts of the question)
    "command": Command word used (e. g. State, Explain)
    "objective": primary assessment objective — exactly one of: AO1, AO2, AO3
    "marks": amount of marks in each question
    "visuals": array with visuals elements like diagrams, tables, graphs, images. Empty array if nothing
    "page": the paper page number of the question


# PHASE 2
Update the json deliverable. Map each question to syllabus topics and add:
    "topic": topic from the "syllabus.md" (e. g., 1.2)
    "topic_name": the name of the topic from "syllabus.md" (e. g. Data Representation: Text, Sound, and Images)

# PHASE 3
Update the json deliverable. Map each question to the answer in the marlking scheme:
"answers":
    "type": type of the answer (e.g., text, diagram, pseudocode, MCQ)
    "visuals": array with visuals elements like diagrams, tables, graphs, images. Empty array if nothing
    "scoring_rule": the scoring instruction stated in the marking scheme, copied verbatim (e.g. "Any three from", "1 mark for each correct item (in bold)"). null if no explicit rule.
    "marking_points": array of marking criteria, each with:
        "text": the marking criterion text, exactly as in the marking scheme
        "marks": integer number of marks awarded for this criterion



