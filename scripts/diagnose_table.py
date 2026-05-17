"""Throwaway diagnostic: print pdfplumber's table extraction for a given PDF page.

Usage:
    uv run python scripts/diagnose_table.py <pdf_path> [--page N]

If --page is omitted, scans every page and prints any table whose first row contains
"Description" or "Definition" in its right cell.
"""
import argparse
import sys
from pathlib import Path

import pdfplumber


def looks_like_term_def(table) -> bool:
    if not table or not table[0] or len(table[0]) != 2:
        return False
    right = str(table[0][1] or "").strip().lower()
    return "descrip" in right or "defin" in right


def dump_table(pdf_path: str, target_page: int | None):
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            if target_page is not None and i != target_page:
                continue
            tables = page.extract_tables() or []
            for t_idx, t in enumerate(tables):
                if target_page is None and not looks_like_term_def(t):
                    continue
                print(f"\n{'='*70}")
                print(f"Page {i}, table {t_idx} — {len(t)} rows × {len(t[0]) if t else 0} cols")
                print(f"{'='*70}")
                for r_idx, row in enumerate(t):
                    print(f"  Row {r_idx}:")
                    for c_idx, cell in enumerate(row):
                        raw = repr(cell)
                        marker = "  [HEADER]" if r_idx == 0 else ("  [BLANK]" if not str(cell or "").strip() else "")
                        print(f"    col {c_idx}: {raw}{marker}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path")
    ap.add_argument("--page", type=int, default=None)
    args = ap.parse_args()
    if not Path(args.pdf_path).exists():
        print(f"PDF not found: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
    dump_table(args.pdf_path, args.page)


if __name__ == "__main__":
    main()
