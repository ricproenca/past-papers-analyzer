import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.extractor import extract


def extract_one(pdf_path: Path, output: str | None = None, ms_path: str | None = None) -> Path:
    out = Path(output) if output else Path("output/json") / (pdf_path.stem + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    extract(str(pdf_path), str(out), ms_path=ms_path)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from Cambridge exam PDFs using Claude."
    )
    parser.add_argument("pdf_path", help="Path to an exam paper PDF or a folder of PDFs")
    parser.add_argument("--output", "-o", help="Output JSON path (single-file mode only)")
    parser.add_argument("--marking-scheme", "-ms", help="Marking scheme PDF (single-file mode only)")
    parser.add_argument("--model", "-m", help="Claude model to use (default: claude-sonnet-4-6)")
    args = parser.parse_args()

    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model

    target = Path(args.pdf_path)

    if target.is_dir():
        qp_files = sorted(target.glob("*_qp_*.pdf"))
        if not qp_files:
            parser.error(f"No question-paper PDFs (*_qp_*.pdf) found in {target}")
        for pdf in qp_files:
            ms_candidate = pdf.parent / pdf.name.replace("_qp_", "_ms_")
            ms = str(ms_candidate) if ms_candidate.is_file() else None
            if ms:
                print(f"Processing: {pdf.name} + {ms_candidate.name}")
            else:
                print(f"Processing: {pdf.name} (no marking scheme found)")
            extract_one(pdf, ms_path=ms)
    else:
        if not target.is_file():
            parser.error(f"Exam paper PDF not found: {target}")
        if args.marking_scheme and not Path(args.marking_scheme).is_file():
            parser.error(f"Marking scheme PDF not found: {args.marking_scheme}")
        extract_one(target, output=args.output, ms_path=args.marking_scheme)


if __name__ == "__main__":
    main()
