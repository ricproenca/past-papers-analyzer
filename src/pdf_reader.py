import pdfplumber
from typing import List, Dict, Any


def _table_to_markdown(table: list) -> str:
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(cell or "").strip() for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


def extract_pages(pdf_path: str) -> List[Dict[str, Any]]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            tables = page.extract_tables()
            images = page.images

            if tables:
                table_md = "\n\n".join(_table_to_markdown(t) for t in tables if t)
                if table_md:
                    text = text + "\n\n[TABLES]\n" + table_md

            pages.append({
                "page": i,
                "text": text,
                "has_table": bool(tables),
                "has_image": bool(images),
            })
    return pages
