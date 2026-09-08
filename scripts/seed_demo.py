"""Seed demo database for FinSight AI."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import settings
from ingestion.loaders import seed_database


def main() -> None:
    bankbench_path = Path(settings.bankbench_sqlite_path) if settings.bankbench_sqlite_path else None
    seed_database(settings.duckdb_path, bankbench_path)
    print(f"Seeded database at {settings.duckdb_path}")


if __name__ == "__main__":
    main()
