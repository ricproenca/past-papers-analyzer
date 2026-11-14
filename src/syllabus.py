"""Single source of truth for the syllabus: topic names, what each topic covers,
the assessment objectives, and exam-session labels.

Content is taken from the official Cambridge IGCSE Computer Science 0478 syllabus
(2023–2025, input/0478/0478 Syllabus.pdf). The official syllabus has no sub-topics in
chapters 7, 9 and 10; the 7.1–7.5, 9.1–9.2 and 10.1–10.4 codes are this project's
subdivision, and each official learning point is assigned to one of them below.
The Phase 1+2 prompt's TOPICS and OBJECTIVES blocks are generated from this module."""

TOPIC_NAMES = {
    "1.1":  "Number Systems",
    "1.2":  "Text, Sound and Images",
    "1.3":  "Data Storage and Compression",
    "2.1":  "Types and Methods of Data Transmission",
    "2.2":  "Methods of Error Detection",
    "2.3":  "Encryption",
    "3.1":  "Computer Architecture",
    "3.2":  "Input and Output Devices",
    "3.3":  "Data Storage",
    "3.4":  "Network Hardware",
    "4.1":  "Types of Software and Interrupts",
    "4.2":  "Types of Programming Language, Translators and IDEs",
    "5.1":  "The Internet and the World Wide Web",
    "5.2":  "Digital Currency",
    "5.3":  "Cyber Security",
    "6.1":  "Automated Systems",
    "6.2":  "Robotics",
    "6.3":  "Artificial Intelligence",
    "7.1":  "Computational Thinking Skills",
    "7.2":  "Algorithms",
    "7.3":  "Standard Methods of Solution",
    "7.4":  "Validation and Verification",
    "7.5":  "Test Data",
    "8.1":  "Programming Concepts",
    "8.2":  "Arrays",
    "8.3":  "File Handling",
    "9.1":  "Database Structure",
    "9.2":  "SQL",
    "10.1": "Logic Gates",
    "10.2": "Logic Circuits",
    "10.3": "Truth Tables",
    "10.4": "Logic Expressions",
}


SESSION_LETTER_NAMES = {"m": "March", "s": "Summer", "w": "Winter"}


# What each topic covers, condensed from the syllabus "Candidates should be able to"
# points and their notes. Used to map questions to topics.
TOPIC_CONTENT = {
    "1.1":  "why computers use binary; denary/binary/hexadecimal and conversions (positive integers, up to 16-bit); uses of hexadecimal; adding 8-bit binary integers; overflow; logical left/right binary shifts and their effect; two's complement 8-bit integers",
    "1.2":  "representing text with character sets (ASCII, Unicode); representing sound (sampling, sample rate, sample resolution); representing images (pixels, resolution, colour depth) and the effect on quality and file size",
    "1.3":  "units of data storage (bit, nibble, byte, KiB, MiB, GiB, TiB, PiB, EiB); calculating image and sound file sizes; purpose of compression; lossy and lossless compression (run length encoding)",
    "2.1":  "packets (header with destination address, packet number, originator's address; payload; trailer); packet switching and routers; serial, parallel, simplex, half-duplex, full-duplex and their suitability; the USB interface",
    "2.2":  "why errors occur in transmission (interference: data loss, gain, change); parity check (odd/even, parity byte, parity block), checksum, echo check; check digits for data entry (ISBN, bar codes); automatic repeat query (ARQ) with acknowledgements and timeout",
    "2.3":  "need for and purpose of encryption; symmetric and asymmetric encryption, public and private keys",
    "3.1":  "role of the CPU; microprocessors; Von Neumann architecture: ALU, CU, registers (PC, MAR, MDR, CIR, ACC), address/data/control buses; the fetch-decode-execute cycle; cores, cache and clock and their effect on performance; instruction sets; embedded systems (dedicated function, e.g. appliances, cars, security, lighting, vending machines) versus general-purpose computers",
    "3.2":  "input devices (barcode and QR code scanners, digital camera, keyboard, microphone, optical mouse, touch screens, 2D/3D scanners); output devices (actuator, DLP and LCD projectors, inkjet/laser/3D printers, LED/LCD screens, speaker); sensors (acoustic, accelerometer, flow, gas, humidity, infra-red, level, light, magnetic field, moisture, pH, pressure, proximity, temperature) and choosing one for a context",
    "3.3":  "primary storage (RAM, ROM, why both are needed); secondary storage; operation of magnetic (platters, tracks, sectors), optical (lasers, pits and lands) and solid-state (NAND/NOR, control and floating gates) storage; virtual memory; cloud storage and its advantages/disadvantages versus local storage",
    "3.4":  "network interface card (NIC); MAC addresses (structure, manufacturer and serial code, hexadecimal); IP addresses (static, dynamic, IPv4 versus IPv6); the role of a router",
    "4.1":  "system software (operating system, utilities) versus application software; functions of an operating system (files, interrupts, interface, peripherals and drivers, memory, multitasking, platform for applications, security, user accounts); hardware, firmware (bootloader) and OS needed to run applications; hardware and software interrupts and interrupt service routines",
    "4.2":  "high-level versus low-level languages; assembly language, mnemonics and assemblers; compilers versus interpreters (how they translate, how errors are reported, when each is used); IDE functions (code editor, run-time environment, translator, error diagnostics, auto-completion, auto-correction, prettyprint)",
    "5.1":  "internet versus world wide web; URLs (protocol, domain name, file name); HTTP and HTTPS; web browser purpose and functions; how a web page is located, retrieved and displayed (browser, IP address, DNS, web server, HTML); session and persistent cookies and their uses",
    "5.2":  "digital currency; blockchain as a time-stamped ledger tracking transactions",
    "5.3":  "threats: brute-force attack, data interception, DDoS, hacking, malware (virus, worm, Trojan horse, spyware, adware, ransomware), pharming, phishing, social engineering; solutions: access levels, anti-malware, authentication (passwords, biometrics, two-step verification), automatic software updates, checking spelling/tone and URLs, firewalls, privacy settings, proxy servers, SSL",
    "6.1":  "sensors, microprocessors and actuators working together in automated systems; advantages and disadvantages of automated systems in industry, transport, agriculture, weather, gaming, lighting, science",
    "6.2":  "what robotics is (factory equipment, domestic robots, drones); characteristics of a robot (mechanical structure, sensors/microprocessors/actuators, programmable); roles of robots and their advantages and disadvantages",
    "6.3":  "what artificial intelligence is; its characteristics (data and rules, reasoning, learning and adapting); expert systems (knowledge base, rule base, inference engine, interface) and machine learning",
    "7.1":  "the program development life cycle (analysis: abstraction, decomposition, requirements; design; coding; testing); systems made of sub-systems; decomposing a problem into inputs, processes, outputs and storage; structure diagrams",
    "7.2":  "designing solutions with flowcharts and pseudocode; stating the purpose of and describing a given algorithm; completing trace tables (variables, outputs, prompts); identifying and correcting errors in algorithms; writing and amending algorithms for a given problem or scenario",
    "7.3":  "standard methods of solution: linear search, bubble sort, totalling, counting, finding maximum, minimum and average values",
    "7.4":  "validation checks (range, length, type, presence, format, check digit) and writing algorithms for them; verification checks (visual check, double entry check)",
    "7.5":  "suggesting and applying test data: normal, abnormal, extreme and boundary",
    "8.1":  "variables and constants; data types (integer, real, char, string, Boolean); input and output; sequence, selection (IF, CASE) and iteration (count-controlled, pre- and post-condition loops); totalling and counting in code; string handling (length, substring, upper, lower); arithmetic, logical and Boolean operators (incl. MOD, DIV, ^); nested statements; procedures, functions, parameters; local and global variables; library routines (MOD, DIV, ROUND, RANDOM); maintainable programs (meaningful identifiers, comments)",
    "8.2":  "declaring and using 1D and 2D arrays; indexes (variables as indexes, first index 0 or 1); writing to and reading from arrays with (nested) iteration",
    "8.3":  "purpose of storing data in a file; opening, closing, reading and writing files (single items and lines of text)",
    "9.1":  "defining a single-table database (fields, records, validation); suitable data types (text/alphanumeric, character, Boolean, integer, real, date/time); primary keys",
    "9.2":  "reading, understanding and completing SQL scripts on a single table, limited to SELECT, FROM, WHERE, ORDER BY, SUM, COUNT; identifying the output of an SQL statement",
    "10.1": "standard logic gate symbols; functions of NOT, AND, OR, NAND, NOR, XOR and their outputs for all inputs",
    "10.2": "drawing logic circuits (up to three inputs, one output, no simplification) from a problem statement, logic expression or truth table",
    "10.3": "completing a truth table from a problem statement, logic expression or logic circuit",
    "10.4": "writing a logic expression from a problem statement, logic circuit or truth table",
}

# Paper 1 (variants 1x) covers chapters 1–6, Paper 2 (variants 2x) chapters 7–10.
PAPER_CHAPTERS = {"1": range(1, 7), "2": range(7, 11)}

# Assessment objectives, verbatim from the syllabus, with the component weightings.
AO_DEFINITIONS = {
    "AO1": "Demonstrate knowledge and understanding of the principles and concepts of computer science.",
    "AO2": "Apply knowledge and understanding of the principles and concepts of computer science to a given context, "
           "including the analysis and design of computational or programming problems.",
    "AO3": "Provide solutions to problems by: evaluating computer systems; making reasoned judgements; presenting conclusions.",
}
AO_WEIGHTING = {"1": {"AO1": 60, "AO2": 20, "AO3": 20}, "2": {"AO1": 20, "AO2": 60, "AO3": 20}}


def topic_in_paper(topic: str, variant) -> bool | None:
    """True/False when the paper number is known from the variant (e.g. "12" -> Paper 1)."""
    chapters = PAPER_CHAPTERS.get(str(variant or "")[:1])
    if chapters is None or not topic:
        return None
    try:
        return int(str(topic).split(".")[0]) in chapters
    except ValueError:
        return None


def topics_prompt_block() -> str:
    lines = ["TOPICS (code name — what the syllabus covers; map each question to the ONE topic whose content it tests):",
             "Paper 1 (variants 1x) uses chapters 1–6 only; Paper 2 (variants 2x) uses chapters 7–10 only."]
    lines += [f"{code} {TOPIC_NAMES[code]} — {TOPIC_CONTENT[code]}" for code in TOPIC_NAMES]
    return "\n".join(lines)


def objectives_prompt_block() -> str:
    w1, w2 = AO_WEIGHTING["1"], AO_WEIGHTING["2"]
    return "\n".join([
        "OBJECTIVES (official definitions — choose by what the question demands, not by command word alone):",
        *(f"{ao} — {text}" for ao, text in AO_DEFINITIONS.items()),
        "How they show up in questions:",
        "AO1 — knowledge: recall, define or describe a concept in general terms — even when the question has a scenario, if the answer does not depend on it (\"Describe what is meant by a core\", \"State one use of ROM\").",
        "AO2 — application: the answer must use the given scenario, data or code — calculations, conversions, traces, completing tables or diagrams from given data, writing/amending/correcting algorithms, programs, SQL or logic circuits, explaining how something works in that scenario.",
        "AO3 — judgement: the answer must evaluate, justify or recommend — explain why something is (or is not) suitable, the best choice, or an example of X in the scenario; compare options for the scenario and conclude; suggest and justify improvements; explain how to change an algorithm or system to fix a stated problem; evaluate a given system or solution.",
        "The final 15-mark scenario question of Paper 2 is marked AO2 + AO3 together: give it AO2 as its primary objective (the marking scheme's split is captured separately).",
        f"Calibration: each paper is designed to these weightings by marks — Paper 1: AO1 {w1['AO1']}%, AO2 {w1['AO2']}%, AO3 {w1['AO3']}%; "
        f"Paper 2: AO1 {w2['AO1']}%, AO2 {w2['AO2']}%, AO3 {w2['AO3']}% — so a 75-mark paper has roughly 15 marks of AO3. Classify each question on its own merits, "
        "then add up the marks per objective: if AO3 is below about 10 marks, revisit the questions that ask why something is (un)suitable, which option is best, "
        "or how to improve, change or prevent something, and give AO3 to those that genuinely require a reasoned judgement.",
    ])
