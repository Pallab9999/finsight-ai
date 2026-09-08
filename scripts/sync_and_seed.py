"""Sync Lombardia open data via bankbench-data-sync, then seed FinSight DuckDB."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BANKBENCH_DIR = ROOT / "bankbench-data-sync"
BANKBENCH_DB = BANKBENCH_DIR / "data" / "bankbench_data_sync.db"


def run_bankbench_sync() -> None:
    if not BANKBENCH_DIR.exists():
        raise FileNotFoundError(f"bankbench-data-sync not found at {BANKBENCH_DIR}")

    subprocess.run(
        [sys.executable, "main.py", "sync"],
        cwd=str(BANKBENCH_DIR),
        check=False,
    )


def seed_finsight() -> None:
    from backend.config import settings
    from ingestion.loaders import seed_database

    bankbench_path = BANKBENCH_DB if BANKBENCH_DB.exists() else None
    seed_database(settings.duckdb_path, bankbench_path)
    print(f"Seeded {settings.duckdb_path}")
    if bankbench_path:
        print(f"Merged Lombardia records from {bankbench_path}")
    else:
        print("No bankbench SQLite yet — using synthetic regional/sector data only.")


def main() -> None:
    print("Step 1/2: Syncing Open Data Lombardia via bankbench-data-sync...")
    run_bankbench_sync()
    print("Step 2/2: Seeding FinSight DuckDB...")
    seed_finsight()


if __name__ == "__main__":
    main()
