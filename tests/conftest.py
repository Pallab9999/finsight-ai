"""Run every test against throwaway databases.

The suite used to write into the app's real files: test_csv_ingest uploaded
"weak.csv" for EcoTex into data/duckdb/finsight.duckdb, so after a test run the
dashboard scored EcoTex on a fake weak balance sheet (and declined it).
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def isolated_databases(tmp_path_factory):
    import app.duckdb_engine as ui_engine
    from backend.config import settings

    tmp = tmp_path_factory.mktemp("finsight-db")
    saved = (ui_engine.DB_DIR, ui_engine.DB_PATH, ui_engine._CONNECTION, settings.duckdb_path)

    ui_engine._CONNECTION = None
    ui_engine.DB_DIR = str(tmp / "ui")
    ui_engine.DB_PATH = str(tmp / "ui" / "finsight.duckdb")
    settings.duckdb_path = tmp / "finsight.duckdb"

    yield tmp

    if ui_engine._CONNECTION is not None:
        try:
            ui_engine._CONNECTION.close()
        except Exception:
            pass
    ui_engine.DB_DIR, ui_engine.DB_PATH, ui_engine._CONNECTION, settings.duckdb_path = saved
