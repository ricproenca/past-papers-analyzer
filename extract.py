import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.extractor import extract


def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from Cambridge exam PDFs using Claude."
    )
    parser.add_argument("pdf_path", help="Path to the exam paper PDF")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: <pdf_stem>.json)")
    parser.add_argument("--marking-scheme", "-ms", help="Path to marking scheme PDF (enables Phase 3)")
    parser.add_argument("--model", "-m", help="Claude model to use (default: claude-sonnet-4-6)")
    args = parser.parse_args()

    if not Path(args.pdf_path).is_file():
        parser.error(f"Exam paper PDF not found: {args.pdf_path}")
    if args.marking_scheme and not Path(args.marking_scheme).is_file():
        parser.error(f"Marking scheme PDF not found: {args.marking_scheme}")

    if args.model:
        os.environ["CLAUDE_MODEL"] = args.model

    output_path = args.output or str(Path(args.pdf_path).stem + ".json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    extract(args.pdf_path, output_path, ms_path=args.marking_scheme)


if __name__ == "__main__":
    main()
