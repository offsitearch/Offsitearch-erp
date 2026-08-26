"""CLI script to generate bulk test data and export to JSON.

Usage::

    python -m app.seeds.bulk.run_export

Outputs JSON files to ``app/seeds/bulk/sample/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend to path so imports work when run as script
_backend = Path(__file__).resolve().parents[2]
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from app.seeds.bulk import export_json, generate_all, print_summary  # noqa: E402


def main() -> None:
    print("Generating test data...")
    data = generate_all()
    print_summary(data)

    sample_dir = Path(__file__).resolve().parent / "sample"
    print(f"\nExporting to {sample_dir} ...")
    export_json(data, sample_dir)
    print("Done.")


if __name__ == "__main__":
    main()
