from typing import List, Dict, Any

PHASE1_SYSTEM = """You are an expert at reading Cambridge exam papers.
Your job is to identify every question (and sub-question) on the exam provided.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

RULES:
- Treat each numbered question and each lettered/roman-numeral sub-question as a separate item.
- Read all questions, let categories emerge, reconcile to syllabus in the end.
- Never invent question numbers — use exactly what is printed on the paper.
- When a question genuinely spans two topics, pick the first one.


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
"questions": for each question must have these exact keys:
    "id"   : question identifier, e.g. "Q1", "Q1a", "Q1b_i", "Q2"
    "text" : the full question text (include all parts of the question)
    "command": Command word used (e. g. State, Explain)
    "objective": primary assessment objective — exactly one of: "AO1", "AO2", "AO3"
    "marks": amount of marks in each question
    "visuals": array with visuals elements like diagrams, tables, graphs, images. Empty array if nothing
    "page": the paper page number of the question

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
Calculate	    Work out; show working	                Wrong formula"""

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
- If a question has no marking scheme entry, set "marking_points" to an empty array []."""

PHASE2_SYSTEM = """Update the json deliverable. Map each question to syllabus topics and add:
    "topic": topic from the syllabus (e.g. 1.2)
    "topic_name": the name of the topic (e. g. Data Representation: Text, Sound, and Images)

Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

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


def build_phase1_messages(pages: List[Dict[str, Any]]):
    system = [
        {
            "type": "text",
            "text": PHASE1_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    pdf_text = build_pdf_text(pages)
    messages = [
        {"role": "user", "content": pdf_text}
    ]
    return system, messages


def build_phase3_messages(phase2_json: str, ms_pages: List[Dict[str, Any]]):
    system = [
        {
            "type": "text",
            "text": PHASE3_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    ms_text = build_pdf_text(ms_pages)
    user_content = (
        "Here is the Phase 2 extraction result:\n\n"
        + phase2_json
        + "\n\nHere is the marking scheme text:\n\n"
        + ms_text
    )
    messages = [{"role": "user", "content": user_content}]
    return system, messages


def build_phase2_messages(phase1_json: str, pages: List[Dict[str, Any]]):
    system = [
        {
            "type": "text",
            "text": PHASE2_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    pdf_text = build_pdf_text(pages)
    user_content = (
        "Here is the Phase 1 extraction result:\n\n"
        + phase1_json
        + "\n\nHere is the original exam paper text for reference:\n\n"
        + pdf_text
    )
    messages = [
        {"role": "user", "content": user_content}
    ]
    return system, messages
