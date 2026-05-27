"""Placeholder for downloading seed arXiv PDFs.

Phase 6 will populate this with 3-5 specific public arXiv preprints. For now,
print instructions so the demo runs against whatever PDFs the user drops into
data/sources/.
"""

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    sources_dir = DEMO_ROOT / "data" / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    existing = list(sources_dir.glob("*.pdf"))
    if existing:
        print(f"data/sources/ already has {len(existing)} PDF(s):")
        for p in existing:
            print(f"  - {p.name}")
        return

    print("no PDFs in data/sources/.")
    print()
    print("for the Phase 1 demo, drop 1-5 PDFs into data/sources/ manually:")
    print(f"  {sources_dir}")
    print()
    print("then run:  python -m openacad.cli._legacy_main ingest data/sources/your-paper.pdf")
    print()
    print("Phase 6 will wire automatic download of 3-5 public arXiv preprints here.")
    sys.exit(0)


if __name__ == "__main__":
    main()
