import glob
import json
from pathlib import Path

from src import enricher, statistics
from src.extractor import _reorder


def main() -> None:
    paths = sorted(glob.glob("output/json/*.json"))
    if not paths:
        print("No JSON files found in output/json/")
        return
    for path in paths:
        data = json.loads(Path(path).read_text())
        enricher.enrich_paper(data)
        statistics.attach_statistics(data)
        data = _reorder(data)
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"enriched: {path}")


if __name__ == "__main__":
    main()
